#!/usr/bin/env python3
"""Opt-in, non-destructive IMAGE container recovery. Requires Python 3 and Docker CLI.

No image pulls, Compose edits, Git updates, network deletion, or container recreation.
Only containers explicitly enrolled while running are managed.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

STATE = Path(os.environ.get("IMAGE_RECOVERY_STATE", "/var/lib/image-recovery/enabled.json"))
LOCK = Path(os.environ.get("IMAGE_RECOVERY_LOCK", "/run/lock/image-recovery-warmup.lock"))
RETRIES = 3


def docker(*args, check=True, timeout=30):
    return subprocess.run(["docker", *args], text=True, capture_output=True,
                          timeout=timeout, check=check)


def inspect(name):
    try:
        result = docker("inspect", "--type", "container", name)
        return json.loads(result.stdout)[0]
    except (subprocess.CalledProcessError, IndexError, json.JSONDecodeError):
        return None


def load():
    if not STATE.exists():
        return []
    value = json.loads(STATE.read_text())
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError("Invalid recovery state file")
    return sorted(set(value))


def save(names):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE.parent, 0o700)
    temp = STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(sorted(set(names)), indent=2) + "\n")
    os.chmod(temp, 0o600)
    temp.replace(STATE)


def eligible(data):
    labels = data.get("Config", {}).get("Labels") or {}
    return labels.get("com.docker.compose.project") == "image"


def enroll(names):
    existing = set(load())
    for name in names:
        data = inspect(name)
        if not data or not eligible(data):
            raise ValueError(f"{name}: not a container in the IMAGE Compose project")
        if data["State"]["Status"] != "running":
            raise ValueError(f"{name}: enroll only running containers; do not revive stopped development work")
    for name in names:
        docker("update", "--restart", f"on-failure:{RETRIES}", name)
        existing.add(inspect(name)["Name"].lstrip("/"))
    save(existing)
    print("Enabled bounded recovery:", ", ".join(names))


def disable(names):
    existing = set(load())
    for name in names:
        data = inspect(name)
        canonical = data["Name"].lstrip("/") if data else name.lstrip("/")
        existing.discard(canonical)
        if data and eligible(data):
            docker("update", "--restart", "no", canonical)
    save(existing)
    print("Disabled automatic recovery:", ", ".join(names))


def boot():
    failed = []
    for name in load():
        data = inspect(name)
        if not data or not eligible(data):
            failed.append(f"{name}: missing or no longer IMAGE-managed")
            continue
        try:
            # Reapply policy after a Compose recreation, without recreating any container.
            docker("update", "--restart", f"on-failure:{RETRIES}", name)
            if data["State"]["Status"] != "running":
                docker("start", name, timeout=180)
                print(f"Started {name}", flush=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            failed.append(f"{name}: {exc}")
    for item in failed:
        print(item, file=sys.stderr)
    return 1 if failed else 0


def warmup(name, health_timeout=180, request_timeout=120, attempts=2):
    data = inspect(name)
    if not data or not eligible(data):
        raise ValueError(f"{name}: not an IMAGE Compose container")
    env = data.get("Config", {}).get("Env") or []
    if "WARMUP_ENABLED=true" not in env:
        return "not-enabled"
    labels = data.get("Config", {}).get("Labels") or {}
    port = labels.get("ca.mcgill.a11y.image.port")
    if not port:
        ports = [p.split("/")[0] for p in (data.get("Config", {}).get("ExposedPorts") or {}) if p.endswith("/tcp")]
        if len(ports) != 1:
            raise ValueError(f"{name}: ambiguous exposed HTTP port; specify ca.mcgill.a11y.image.port")
        port = ports[0]
    start = time.monotonic()
    while time.monotonic() - start < health_timeout:
        data = inspect(name)
        if not data or data["State"]["Status"] != "running":
            raise RuntimeError(f"{name}: stopped before warmup")
        health = (data["State"].get("Health") or {}).get("Status")
        if health == "unhealthy":
            raise RuntimeError(f"{name}: unhealthy before warmup")
        if health in (None, "healthy"):
            break
        time.sleep(2)
    else:
        raise TimeoutError(f"{name}: health check did not pass in {health_timeout}s")
    # Allow dependencies to settle; serialize GPU-intensive warmups.
    time.sleep(10)
    for attempt in range(attempts):
        try:
            r = docker("exec", name, "curl", "-fsS", "--max-time", str(request_timeout),
                       "-o", "/dev/null", f"http://localhost:{port}/warmup",
                       timeout=request_timeout + 15)
            if r.returncode == 0:
                return "ok"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"{name}: warmup attempt {attempt + 1} failed: {exc}", file=sys.stderr)
        if attempt + 1 < attempts:
            time.sleep(5)
    raise RuntimeError(f"{name}: warmup failed after {attempts} attempts")


def warmup_locked(name):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return warmup(name)


def warmup_all():
    failed = []
    for name in load():
        try:
            result = warmup_locked(name)
            print(f"{name}: {result}", flush=True)
        except Exception as exc:
            failed.append(f"{name}: {exc}")
    for item in failed:
        print(item, file=sys.stderr)
    return 1 if failed else 0


def watch():
    # Subscribe before starting the separate boot unit to avoid missing start events.
    while True:
        proc = subprocess.Popen(
            ["docker", "events", "--filter", "type=container", "--filter", "event=start",
             "--filter", "label=com.docker.compose.project=image", "--format", "{{json .}}"],
            stdout=subprocess.PIPE, text=True)
        try:
            for line in proc.stdout:
                try:
                    event = json.loads(line)
                    name = event.get("Actor", {}).get("Attributes", {}).get("name", "")
                    if name in load():
                        print(f"{name}: started; warmup scheduled", flush=True)
                        try:
                            print(f"{name}: {warmup_locked(name)}", flush=True)
                        except Exception as exc:
                            print(f"{name}: warmup FAILED: {exc}", file=sys.stderr, flush=True)
                except (ValueError, json.JSONDecodeError) as exc:
                    print(f"event processing error: {exc}", file=sys.stderr, flush=True)
        finally:
            proc.wait()
        print("Docker event stream ended; reconnecting", file=sys.stderr, flush=True)
        time.sleep(5)


def status():
    failed = False
    report = []
    for name in load():
        data = inspect(name)
        if not data or not eligible(data):
            report.append({"name": name, "status": "missing", "health": None, "restarts": None})
            failed = True
            continue
        state = data["State"]
        health = (state.get("Health") or {}).get("Status")
        policy = data["HostConfig"]["RestartPolicy"]["Name"]
        status = state["Status"]
        if status != "running" or health == "unhealthy" or policy != "on-failure":
            failed = True
        report.append({"name": name, "status": status, "health": health,
                       "restarts": data.get("RestartCount", 0), "policy": policy,
                       "exit_code": state.get("ExitCode")})
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("enable", "disable"):
        p = sub.add_parser(command)
        p.add_argument("containers", nargs="+")
    for command in ("boot", "watch", "warmup", "status"):
        sub.add_parser(command)
    a = parser.parse_args()
    try:
        if a.command == "enable":
            enroll(a.containers)
        elif a.command == "disable":
            disable(a.containers)
        elif a.command == "boot":
            return boot()
        elif a.command == "watch":
            watch()
        elif a.command == "warmup":
            return warmup_all()
        else:
            return status()
    except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        print(f"IMAGE recovery error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

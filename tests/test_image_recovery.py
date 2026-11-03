"""Tests for opt-in, non-destructive recovery policy (no Docker daemon required)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "image_recovery.py"
spec = importlib.util.spec_from_file_location("image_recovery", SCRIPT)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def container(name, running=True, enabled=True):
    return {
        "Name": "/" + name,
        "State": {"Status": "running" if running else "exited", "ExitCode": 1},
        "Config": {
            "Labels": {"com.docker.compose.project": "image",
                       "ca.mcgill.a11y.image.port": "5000"},
            "Env": ["WARMUP_ENABLED=true"] if enabled else [],
            "ExposedPorts": {"5000/tcp": {}},
        },
        "HostConfig": {"RestartPolicy": {"Name": "on-failure"}},
        "RestartCount": 0,
    }


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = patch.object(recovery, "STATE", Path(self.tmp.name) / "enabled.json")
        self.state.start()
        self.addCleanup(self.state.stop)

    def test_enroll_rejects_stopped_containers(self):
        with patch.object(recovery, "inspect", return_value=container("image-test-1", False)):
            with patch.object(recovery, "docker") as docker:
                with self.assertRaisesRegex(ValueError, "enroll only running"):
                    recovery.enroll(["image-test-1"])
                docker.assert_not_called()

    def test_enroll_sets_bounded_policy_and_disable_restores_no_restart(self):
        data = container("image-test-1")
        with patch.object(recovery, "inspect", return_value=data), patch.object(recovery, "docker") as docker:
            recovery.enroll(["image-test-1"])
            self.assertEqual(recovery.load(), ["image-test-1"])
            docker.assert_any_call("update", "--restart", "on-failure:3", "image-test-1")
            recovery.disable(["image-test-1"])
            docker.assert_any_call("update", "--restart", "no", "image-test-1")
            self.assertEqual(recovery.load(), [])

    def test_boot_does_not_create_or_recreate(self):
        recovery.save(["image-test-1"])
        with patch.object(recovery, "inspect", return_value=container("image-test-1", False)):
            with patch.object(recovery, "docker") as docker:
                self.assertEqual(recovery.boot(), 0)
                docker.assert_any_call("start", "image-test-1", timeout=180)
                self.assertFalse(any("up" in call.args or "pull" in call.args
                                     for call in docker.call_args_list))

    def test_status_reports_stopped_as_failure(self):
        recovery.save(["image-test-1"])
        with patch.object(recovery, "inspect", return_value=container("image-test-1", False)):
            self.assertEqual(recovery.status(), 1)

    def test_warmup_skips_services_without_flag(self):
        with patch.object(recovery, "inspect", return_value=container("image-test-1", enabled=False)):
            with patch.object(recovery, "docker") as docker:
                self.assertEqual(recovery.warmup("image-test-1"), "not-enabled")
                docker.assert_not_called()


if __name__ == "__main__":
    unittest.main()

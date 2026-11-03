# Opt-in IMAGE recovery (pilot; Unicorn only)

This is a **non-destructive alternative** to the existing `scripts/imageup` reset.
It does not run Git, pull images, load Compose configurations, recreate
containers, remove networks, or modify developer overrides.

## Policy and deliberate stops

Only containers enrolled **while running** are managed. Enrollment changes the
existing container's Docker restart policy to `on-failure:3` and persists its
name in `/var/lib/image-recovery/enabled.json` (root-only). Docker retries a
quick nonzero-exit failure up to three times. It will not retry a clean exit.
Unlike `unless-stopped`, `on-failure:3` does **not** bring containers back
after a daemon/host restart, which is why the optional boot service exists.

**Important:** Docker resets its restart backoff/retry accounting after
sufficient successful runtime (approximately 10 seconds). This is bounded
protection against rapid crash loops, **not a strict lifetime/rolling-window
crash budget**. Long-running services that repeatedly fail still need
monitoring; the supplied health timer detects stopped and unhealthy services.
Do not describe this alone as guaranteed crash-loop quarantine.

**Before intentionally stopping an enrolled development container, disable
recovery for it**. A boot-time restore cannot reliably distinguish a manually
stopped container from one that was stopped by a reboot. Disabling also
restores its `restart=no` policy:

```bash
sudo python3 /var/docker/image/IMAGE-server/scripts/image_recovery.py disable image-graphic-caption-1
sudo docker stop image-graphic-caption-1
```

To opt back in, start and verify it first, then enable it. A recreated
container with the same name may be re-enrolled automatically at boot, so
review the membership list after changing the deployment.

## Pilot procedure

1. **Do not change the current Compose files** or Jeffrey's symlinked override.
   Confirm the actual deployed IMAGE project and service selection.
2. Choose a small set of healthy, persistent services. Do not enroll test jobs,
   intentionally stopped services, or all 40+ containers by default.
3. Enroll a running container:

   ```bash
   sudo python3 /var/docker/image/IMAGE-server/scripts/image_recovery.py enable image-memcached-1
   sudo python3 /var/docker/image/IMAGE-server/scripts/image_recovery.py status
   ```

4. Copy the units from `deploy/systemd/` to `/etc/systemd/system/` only
   after host review; the paths assume the standard McGill layout.
5. `sudo systemctl daemon-reload`, then enable
   `image-recovery-events.service`, `image-recovery-boot.service`, and
   `image-recovery-health.timer`. Enablement is an **operational change**;
   do not do this merely by merging the branch. Test manually before any
   controlled reboot.
6. Check the journal for both warmup outcomes and the health service:
   `journalctl -u image-recovery-events.service -u image-recovery-boot.service -u image-recovery-health.service`.
   A failed one-shot health service is intentionally visible to systemd.
   Connect that signal to StableBot's incident/notification pipeline before
   treating this as an unattended production recovery solution.

**Boot semantics:** the boot unit runs `docker start` only for enrolled
containers, without `docker compose up`; it does not reconcile drift or
create missing containers. This avoids the destructive `imageup` reset and
preserves local GPU, environment, and override settings.

**Warmup semantics:** the event watcher listens for Docker `start` events
in the IMAGE Compose project. For enrolled containers with
`WARMUP_ENABLED=true`, it waits (bounded) for health, serializes the
warmup work via a host lock, and runs a bounded request to the container's
`/warmup` endpoint. The boot service also runs warmup for enrolled
containers as a fallback if the event watcher missed the boot start. It
may therefore perform an additional harmless warmup on boot.
Warmup failure is logged, not silently interpreted as readiness.

This mechanism depends on the container having `curl` installed and a
discoverable HTTP port. An ambiguous port requires the existing
`ca.mcgill.a11y.image.port` label. The endpoint is not a strong readiness
check by itself; readiness and latency tests are necessary before production.

## Rollback

Stop and disable the three pilot units/timer, then run `disable` for
each enrolled container. Do not delete the state file as a substitute for
reverting the Docker restart policies. The existing `imageup` reset remains
available for explicit recovery operations.

## Validation still required before live deployment

- Verify unit ordering and Docker event delivery on Unicorn.
- Verify boot restoration with an approved test container.
- Test a fast, repeatable nonzero-exit crash and verify bounded retries.
- Test an unhealthy-but-running process and StableBot incident notification.
- Test warmup failures and timeouts on GPU services without saturating VRAM.
- Verify the behavior of two SuperCollider replicas and intentionally stopped
  developer containers.
- Reconcile Compose policies eventually: `docker compose up` can recreate
  containers with the main repository's `restart: "no"`. Enrollment is
  reapplied by the boot unit, but any **new** container name must be enrolled
  separately.
- Integrate with StableBot; the timer/journal are observability signals,
  **not yet a Slack alert integration**.

The original `imageup` continues to perform a destructive reset. This
pilot does not alter that script or the existing daily cron job; disable
the daily reset only after separately auditing its schedule and verifying
that the recovery pilot works.

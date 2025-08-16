# Self-Healing Supervisor - Security Notes

Socket access policy (docker.sock)
- Mount the Docker socket as read-only when feasible (bind mount `:ro`) for metadata-only operations.
- For environments requiring container lifecycle control, prefer a Docker Socket Proxy (e.g., `tecnativa/docker-socket-proxy`) and grant only required API subsets.
- Drop ambient capabilities and run as non-root (UID:GID 10001:10001). Avoid `--privileged` and host PID/NET unless strictly necessary.
- Isolate with seccomp/apparmor profiles where supported.

Runtime recommendations
- Health endpoint on 9008 must be HTTP-only and expose no admin actions.
- Use `tini` as PID 1 and keep writable paths restricted to `/app/data` and `/app/logs`.
- Log and rate-limit recovery actions; avoid infinite restart loops.

Audit checklist
- Validate container runs as non-root and belongs to `docker` group only if socket is required.
- If using socket proxy, remove membership in `docker` group.
- Confirm `HEALTHCHECK` is active and fail-closed.
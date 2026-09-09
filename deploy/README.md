# Production: mymag.littlemaster.fun

Existing host Caddy terminates HTTPS and renews certificates. Add `deploy/Caddyfile` as a separate site to its configuration; back up, validate, then reload Caddy without restarting other sites. Only `127.0.0.1:18080` is published by this Compose project; the API and PostgreSQL are private Docker services.

Layout on the server:

- `/opt/meiyu/releases/<git-commit>/`: audited source and frontend `dist`.
- `/opt/meiyu/current`: active release symlink.
- `/opt/meiyu/secrets/`: secrets, never included in releases, images, or Git.
- Docker volumes `meiyu_database`, `meiyu_uploads`: persistent data; **never use `docker compose down -v`**.

## Initial deployment

Run frontend tests and `pnpm build` in `front-end`. Upload audited source (e.g. `git archive HEAD`) and only `front-end/dist` over SSH. Do not upload local `.env`, `uploads`, `.git`, or Android build outputs. Initialize private config once with `node deploy/prepare-secrets.mjs`; transfer only `backend.env` and `db_password` into the private server directory. `backend.env` must be readable by container UID 10001, `db_password` by the PostgreSQL container UID. Both files should be mode 0600 and the host secrets directory mode 0700. Keep `administrator.txt` only in your password manager / private local folder.

From `/opt/meiyu/current`:

```sh
docker compose -f deploy/compose.yml build api
docker compose -f deploy/compose.yml up -d db
docker compose -f deploy/compose.yml run --rm api alembic upgrade head
docker compose -f deploy/compose.yml run --rm api python -m app.db.seed
docker compose -f deploy/compose.yml up -d
```

Production seed creates venues and the explicitly configured administrator only, not demo requests. Existing data volumes are kept across releases. Run a single API worker: the upstream SMS captcha session currently lives in process memory.

Copy the supplied expiry service/timer to `/etc/systemd/system`, run `systemctl daemon-reload`, then `systemctl enable --now meiyu-expirations.timer`. The timer processes application expiration hourly; in production this can send notification emails as part of normal application workflows.

## Security and operations

- Production JWT and database/admin passwords are independently generated; JWT access tokens expire in 30 minutes, refresh tokens in 7 days. No production default password exists.
- API/SMTP credentials are loaded from the read-only mounted `.env`, not Docker image layers or Compose environment variables. SSH transports them encrypted. SMTP uses certificate-validated TLS on 465; AI uses HTTPS.
- Public docs/OpenAPI are disabled. Authentication routes are rate limited. Responses containing API data are not cached. Public static roots contain no backend source or upload directory.
- API and web processes run without root privileges, with read-only roots and no extra capabilities. App uploads and database are the only persistent writable stores.
- Frontend CSP explicitly permits `blob:` texture fetching for embedded GLB textures. Do not remove it: doing so causes white 3D models.
- Do not log Authorization headers, request bodies, passwords, or token-bearing URLs. Standard service logs contain request paths/status only.
- The current client stores JWTs in local storage. CSP helps reduce script injection exposure but is not a substitute for a full security review. Refresh-token revocation and administrator MFA are not implemented yet.
- Rotate any previously exposed credentials with their providers. Never copy a developer JWT secret to production.

Before upgrades, back up PostgreSQL (`pg_dump` inside the DB container), uploads, and private config into root-only storage. Snapshot the current release path. After migration/build/start, check HTTPS, `/api/v1/health`, login, protected file access, template download, and 3D texture loading. Do not exercise real SMS, AI submissions, or email notifications merely as a health check.

For rollback, point `current` to the previous release and recreate API/web containers. Database migrations may not be reversible; take a backup before migration and review the migration first. The server's other sites and Docker projects are outside this deployment's scope.

Use `docker compose -f deploy/compose.yml ps`, `logs --tail=100 api`, and `systemctl list-timers meiyu-expirations.timer` for status. Avoid `docker compose config` if you change the deployment to interpolate secrets in future.

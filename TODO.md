# TODO

## ✅ Completed

- [x] Move SSH key to GitLab CI/CD Variable (`EC2_SSH_KEY`, File type)
- [x] Fix Alembic migration `0005` FK seed issue and re-enable in `docker-compose.yml`
- [x] Upgrade Node.js to 20 (EC2 + `frontend/Dockerfile`)
- [x] Pin Poetry to `2.4.1` in `Dockerfile`
- [x] Fix ASGI entrypoint to use `socket_app`
- [x] Remove `./backend:/app` volume mount
- [x] Enable `depends_on` with `service_healthy` for backend → postgres

---

## ⚠️ Keycloak SSO — Temporary workarounds to revert

> These were added in `feat/cadf-framework_Keycloke_SSO` to unblock the EC2 deployment.
> Revert or replace properly before merging to main.

- [ ] **JIT user provisioning in `/auth/me`** (`backend/app/api/routers/auth.py`) — creates a `users` row on first Keycloak login using token claims. Replace with a proper Keycloak event webhook or SCIM sync so the DB is populated before the first request.
- [ ] **`KEYCLOAK_URL=http://keycloak:8080` hardcoded in `docker-compose.prod.yml`** — backend uses the Docker-internal hostname while `.env.production` holds the public IP. Split into `KEYCLOAK_INTERNAL_URL` (backend) and `KEYCLOAK_PUBLIC_URL` (frontend) env vars instead.
- [ ] **`VITE_KEYCLOAK_URL` injected via runtime `environment:` in `docker-compose.prod.yml`** — Vite bakes env vars at build time; injecting at runtime only works because we run `npm run dev`, not a built image. Switch to a proper Docker build-arg pipeline (`--build-arg VITE_KEYCLOAK_URL=...`) when moving to a production nginx image.
- [ ] **`TEMPORAL_ENABLED=false` added to `.env.production`** — belt-and-suspenders because `docker-compose.prod.yml` already sets it. Remove from `.env.production` once the root cause (stale host env var on EC2) is confirmed fixed.

---

## 🔴 High Priority

- [ ] **Secrets** — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SECRET_KEY` are in `.env.docker` (committed to git). Move to AWS Secrets Manager or GitLab CI variables
- [ ] **`SECRET_KEY`** — still default value. Generate: `openssl rand -hex 32`
- [ ] **SSL/TLS** — services exposed on HTTP only. Add HTTPS with domain + AWS Certificate Manager
- [ ] **PostgreSQL persistence** — `db/data/` is on root EBS volume, lost if EC2 terminated. Switch to RDS

---

## 🟡 Medium Priority

- [ ] **`APP_ENV=development`** — change to `production` in `.env.docker`
- [ ] **DB password** — `Root` is weak for production
- [ ] **CORS origins** — currently allows localhost. Lock down to actual domain
- [ ] **Container resource limits** — no memory/CPU limits in `docker-compose.yml`
- [ ] **Rate limiting** — no API rate limiting

---

## 🟢 Lower Priority

- [ ] **Centralized logging** — no CloudWatch or similar
- [ ] **Error monitoring** — no Sentry or equivalent
- [ ] **Frontend** — Vite dev server not suitable for high production traffic (nginx recommended)
- [ ] **DB backups** — no automated backup strategy
- [ ] **Staging environment** — no separate staging before production deploy

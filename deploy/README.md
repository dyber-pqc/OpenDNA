# OpenDNA Web Demo Deployment

This directory contains scaffolding to bring up a public OpenDNA demo at
`https://opendna.org` on a GPU host with automatic HTTPS and rate limiting.

## Files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Brings up the `opendna` server + `caddy` reverse proxy |
| `Caddyfile` | Caddy reverse-proxy config (auto-HTTPS via Let's Encrypt) |
| `rate_limit.caddy` | 60 req/min per-IP policy (requires `caddy-ratelimit`) |
| `fly.toml` | Fly.io alternative (single-machine deploy) |

## Quick start on a GPU box (vast.ai / Lambda / RunPod)

1. **Rent a GPU instance.** A single RTX 4090 or A10G is enough for ESMFold;
   add an A100 (40 GB+) for ColabFold multimer and Boltz. Pick an Ubuntu 22.04
   image with Docker + NVIDIA Container Toolkit preinstalled (all three providers
   offer such templates).

2. **Open ports 80 and 443** in the provider's firewall panel. vast.ai: set
   "Direct TCP ports" to `80,443`. Lambda/RunPod: add inbound rules in the
   console.

3. **Point DNS at the box.** At your DNS provider create A (and optionally
   AAAA) records:
   ```
   opendna.org       A   <public-ip>
   www.opendna.org   A   <public-ip>
   ```
   Wait for propagation (`dig opendna.org`) before starting Caddy — it needs
   to resolve to the host to obtain certificates.

4. **Clone the repo and build the server image:**
   ```bash
   git clone https://github.com/dyber-pqc/OpenDNA.git
   cd OpenDNA
   docker build -t opendna/server:latest -f python/Dockerfile python/
   ```

5. **Build Caddy with the rate-limit plugin** (one-time; the stock image does
   not include it):
   ```bash
   docker build -t caddy:2-ratelimit - <<'EOF'
   FROM caddy:2-builder AS builder
   RUN xcaddy build --with github.com/mholt/caddy-ratelimit
   FROM caddy:2-alpine
   COPY --from=builder /usr/bin/caddy /usr/bin/caddy
   EOF
   ```
   Then edit `docker-compose.yml` and change `image: caddy:2-alpine` to
   `image: caddy:2-ratelimit`.

6. **Bring the stack up:**
   ```bash
   cd deploy
   docker compose up -d
   docker compose logs -f caddy  # watch for "certificate obtained successfully"
   ```

7. **Verify.** From another machine:
   ```bash
   curl https://opendna.org/health
   ```
   You should get `{"status":"ok",...}`.

## Rate limiting

The default policy in `rate_limit.caddy` allows **60 requests/minute per
client IP**. Tune `events` and `window` if the demo is more or less popular.
Heavier endpoints (`/v1/fold/cascade`, `/v1/md_full`) can get their own zones
by duplicating the block in `Caddyfile` under `@heavy { path /v1/fold/cascade /v1/md_full }`
and importing a stricter limiter.

## Authentication

The `OPENDNA_AUTH_REQUIRED` flag toggles the PQC-token auth middleware:

- `OPENDNA_AUTH_REQUIRED=0` (default here) — open public demo. Rate limit is
  the only defence.
- `OPENDNA_AUTH_REQUIRED=1` — every non-`/health` request must carry a valid
  Dilithium-signed bearer token (issued via `/v1/auth/token`). Use this if
  you expose expensive endpoints to authenticated users only.

Set per environment:
```bash
OPENDNA_AUTH_REQUIRED=1 docker compose up -d
```

## Fly.io (alternative, no GPU)

`fly.toml` is a single-machine config suitable for a CPU-only demo that
hits ESMFold on a fallback path. `flyctl launch --copy-config --no-deploy`,
then `flyctl deploy`. See the comments in `fly.toml` for GPU scaling
(A100 machines are available in `ord`, `iad`, `sjc`).

## Costs (rough, April 2026)

| Host | GPU | ~$/hr | Notes |
| --- | --- | --- | --- |
| vast.ai | RTX 4090 | 0.35-0.50 | cheapest, interruptible |
| Lambda | A10G 24 GB | 0.75 | reserved, stable uptime |
| RunPod | A100 40 GB | 1.10-1.40 | needed for Boltz |
| Fly.io | a100-40gb | 2.50 | no DevOps, premium pricing |

A burstable demo (auto-stop when idle) on Fly or RunPod Serverless keeps
bills under $50/month for casual traffic.

Hermes Agent runs as two Docker containers built from the same image. The `gateway` container is the agent runtime plus messaging integrations (outbound only — no published ports). The `dashboard` container serves the web UI on `127.0.0.1:9119` of the host (loopback only — LAN cannot reach it). Both bind-mount the repo-local `./hermes-data/` directory as `/opt/data` for persistent state (overrides upstream's `~/.hermes:/opt/data` so your home directory stays untouched).

Authentication: the dashboard has no built-in auth. Access is restricted at the network layer — only the host's loopback can reach it. From another machine, use SSH tunneling (see fork/NOTE-4-secure-remote-access.md).

This note covers a clean install from zero to working. For day-to-day operations see fork/NOTE-5-operations.md.

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Compose plugin v2.24+ (Linux)
- An LLM provider account or API key (fork/NOTE-2-llm-providers.md)
- A Discord bot already created in the Discord Developer Portal if Discord access is wanted (fork/NOTE-3-discord.md)

### Fork-local files

| File | Purpose |
|---|---|
| `docker-compose.override.yml` | Auto-merged on top of upstream `docker-compose.yml`. Adds: external-skills mount, repo-local `hermes-data` override of `~/.hermes`, env passthrough, `host.docker.internal` for native Linux Docker, dashboard loopback bind + `--tui` flag, custom build for the dashboard's TUI fix |
| `Dockerfile.fork` | Extends `hermes-agent:fork` with a `chown -R hermes:hermes /opt/hermes/ui-tui` so the runtime user can rewrite the TUI dist when `--tui` triggers a rebuild on startup |
| `.env` | Local-only secrets, gitignored, auto-loaded by Compose for variable substitution |
| `.env.fork.example` | Committed template — copy to `.env` and fill |
| `fork/config.yaml.example` | The single `skills.external_dirs` snippet to merge into `hermes-data/config.yaml` so `my-skills/` is discovered |
| `hermes-data/` | Persistent Hermes state (config, sessions, OAuth tokens, credentials). Gitignored except `SOUL.md` |
| `my-skills/` | User-authored skill folders, read-only mount into the container |

### Step 1 — copy the env template

```powershell
copy .env.fork.example .env
```

Open `.env` and fill values. Empty values are passed through harmlessly to the container.

### Step 2 — fill messaging credentials

For Discord, paste the bot token from the Developer Portal:

```
DISCORD_BOT_TOKEN=<bot-token>
```

Leave `DISCORD_ALLOWED_USERS` empty plus set `GATEWAY_ALLOW_ALL_USERS=true` if you want unrestricted access. Otherwise fill `DISCORD_ALLOWED_USERS` with comma-separated user IDs.

### Step 3 — fill any skill API keys

Blockchain, OSINT, Gmail OAuth, and other skill keys are listed in `.env.fork.example`. Fill what is needed, leave the rest blank.

### Step 4 — build and start the containers

```powershell
docker compose build gateway
docker compose build dashboard
docker compose up -d
```

Two explicit `build` calls because `Dockerfile.fork` does `FROM hermes-agent:fork` — gateway must finish first to produce that tag (see fork/NOTE-5-operations.md "Build order"). The first start creates `./hermes-data/` in the repo root.

Tail the gateway logs:

```powershell
docker compose logs -f gateway
```

### Step 5 — configure an LLM provider

See fork/NOTE-2-llm-providers.md. Come back here when a provider is configured and `hermes doctor` shows it as logged in.

### Step 6 — enable user-authored skills

Hermes generates `hermes-data/config.yaml` with defaults on first run. The only fork-specific change you need to merge in is the `external_dirs` entry under `skills:` — see `fork/config.yaml.example` for the exact snippet. Open `hermes-data/config.yaml` and replace the existing `skills:` block (or just its `external_dirs: []` line) with:

```yaml
skills:
  external_dirs:
    - /opt/data/external-skills
```

Without this, the folders in `my-skills/` are mounted into the container but not discovered.

### Step 7 — apply config and verify

```powershell
docker compose restart gateway dashboard
docker compose exec gateway /opt/hermes/.venv/bin/hermes doctor
docker compose exec gateway /opt/hermes/.venv/bin/hermes skills list
docker compose exec gateway ls /opt/data/external-skills
```

### Step 8 — open the dashboard

On the host running Docker:

```
http://localhost:9119
```

From another machine on your LAN or remote: SSH tunnel — see fork/NOTE-4-secure-remote-access.md.

### Where state lives

- `./my-skills/` — user-authored skills, read-only mount source
- `./.env` — Compose-time secrets, gitignored
- `./Dockerfile.fork` — TUI-chown fix layered on the upstream image
- `./hermes-data/config.yaml` — Hermes runtime config (model, provider, `skills.external_dirs`)
- `./hermes-data/auth.json` — OAuth tokens (MiniMax, Anthropic, Google), refreshable
- `./hermes-data/credentials/` — skill credential files such as `google_token.json`
- `./hermes-data/sessions/` — conversation history
- `./hermes-data/skills/` — bundled + agent-created skills
- `./hermes-data/SOUL.md` — agent personality, the only file under `hermes-data/` that's tracked in git

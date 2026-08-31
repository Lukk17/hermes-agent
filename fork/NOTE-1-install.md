Hermes Agent runs as two Docker containers built from the same image. The `gateway` container is the agent runtime plus messaging integrations (outbound only, no published ports). The `dashboard` container serves the web UI on `127.0.0.1:9119` of the host (loopback only, LAN cannot reach it). Both bind-mount the repo-local `./hermes-data/` directory as `/opt/data` for runtime state (overrides upstream's `~/.hermes:/opt/data` so your home directory stays untouched). The three fork-specific config files (SOUL.md, config.yaml, cron/jobs.json) are sourced from `./fork/hermes-config/` via file-specific bind mounts that shadow the same paths inside `/opt/data/`.

Authentication: the dashboard has no built-in auth. Access is restricted at the network layer, only the host's loopback can reach it. From another machine, use SSH tunneling (see fork/NOTE-4-secure-remote-access.md).

This note covers a clean install from zero to working. For day-to-day operations see fork/NOTE-5-operations.md.

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Compose plugin v2.24+ (Linux)
- An LLM provider account or API key (fork/NOTE-2-llm-providers.md)
- A Discord bot already created in the Discord Developer Portal if Discord access is wanted (fork/NOTE-3-discord.md)

### Fork-local files

| File | Purpose |
|---|---|
| `docker-compose.override.yml` | Auto-merged on top of upstream `docker-compose.yml`. Adds: file-specific bind mounts for `./fork/hermes-config/SOUL.md`, `config.yaml`, `cron/jobs.json` at `/opt/data/...`; `./fork/projects:/opt/projects`; `.agents/skills:/opt/external-skills:ro`; `./skills:/opt/skills:ro`; env passthrough; dashboard loopback bind + `--tui` flag; custom build for the dashboard TUI fix |
| `Dockerfile.fork` | Extends `hermes-agent:fork` with a `chown -R hermes:hermes /opt/hermes/ui-tui` so the runtime user can rewrite the TUI dist when `--tui` triggers a rebuild on startup |
| `.env` | Local-only secrets, gitignored, auto-loaded by Compose for variable substitution |
| `.env.fork.example` | Committed template, copy to `.env` and fill |
| `fork/config.yaml.example` | The single `skills.external_dirs` snippet to merge into `fork/hermes-config/config.yaml` so `.agents/skills/` is discovered |
| `fork/hermes-config/` | Tracked fork-specific config. SOUL.md, config.yaml, cron/jobs.json live here. Bind-mounted at `/opt/data/...` inside the container. Re-base onto upstream hermes never conflicts with this directory because upstream does not ship it. |
| `hermes-data/` | Persistent Hermes runtime state (state.db, logs/, sessions/, cache/, auth.json, memories/, credentials/). Gitignored entirely. |
| `.agents/skills/` | User-authored skill folders, read-only mount into the container as `/opt/external-skills`. Tracked in git, mirrors a curated subset of `Lukk17/agent-standards/.agents/skills/` |
| `./skills/` | Bundled hermes skills, read-only mount into the container as `/opt/skills` |

### Step 1, copy the env template

```powershell
copy .env.fork.example .env
```

Open `.env` and fill values. Empty values are passed through harmlessly to the container.

### Step 2, fill messaging credentials

For Discord, paste the bot token from the Developer Portal:

```
DISCORD_BOT_TOKEN=<bot-token>
```

Leave `DISCORD_ALLOWED_USERS` empty plus set `GATEWAY_ALLOW_ALL_USERS=true` if you want unrestricted access. Otherwise fill `DISCORD_ALLOWED_USERS` with comma-separated Discord user IDs.

### Step 3, fill any skill API keys

Blockchain, OSINT, Gmail OAuth, and other skill keys are listed in `.env.fork.example`. Fill what is needed, leave the rest blank.

### Step 4, build and start the containers

```powershell
docker compose build gateway
docker compose build dashboard
docker compose up -d
```

Two explicit `build` calls because `Dockerfile.fork` does `FROM hermes-agent:fork`, so gateway must finish first to produce that tag (see fork/NOTE-5-operations.md "Build order"). The first start creates `./hermes-data/` in the repo root.

Tail the gateway logs:

```powershell
docker compose logs -f gateway
```

### Step 5, configure an LLM provider

See fork/NOTE-2-llm-providers.md. Come back here when a provider is configured and `hermes doctor` shows it as logged in.

### Step 6, enable user-authored skills

`fork/hermes-config/config.yaml` already declares the skills paths:

```yaml
skills:
  external_dirs:
    - /opt/external-skills
    - /opt/skills
```

`/opt/external-skills` reads from `.agents/skills/` (host). `/opt/skills` reads from `./skills/` (host). Both are read-only bind mounts. If you have a curated subset of skills you want to ship with the fork, they go in `.agents/skills/`. If you want to add new per-project skills, they go in `./skills/`.

### Step 7, verify

```powershell
docker compose exec gateway /opt/hermes/.venv/bin/hermes doctor
docker compose exec gateway /opt/hermes/.venv/bin/hermes skills list
docker compose exec gateway ls /opt/external-skills | Select-Object -First 3
docker compose exec gateway ls /opt/skills | Select-Object -First 3
docker compose exec gateway ls /opt/projects
```

### Step 8, open the dashboard

On the host running Docker:

```
http://localhost:9119
```

From another machine on your LAN or remote, SSH tunnel (see fork/NOTE-4-secure-remote-access.md) or nginx with basic auth (see fork/NOTE-6-minipc-proxmox.md).

### Where state lives

- `./fork/hermes-config/SOUL.md` — agent persona (tracked, bind-mounted at `/opt/data/SOUL.md`)
- `./fork/hermes-config/config.yaml` — Hermes runtime config (model, provider, `skills.external_dirs`, channel_prompts; bind-mounted at `/opt/data/config.yaml`)
- `./fork/hermes-config/cron/jobs.json` — scheduled jobs (bind-mounted at `/opt/data/cron/jobs.json`)
- `./fork/projects/` — project workspaces (one subdir per Discord channel; tracked; bind-mounted at `/opt/projects/`)
- `./.agents/skills/` — curated skill set, bind-mounted at `/opt/external-skills` (read-only)
- `./skills/` — bundled hermes skills, bind-mounted at `/opt/skills` (read-only)
- `./hermes-data/` — runtime state ONLY (state.db, logs/, sessions/, cache/, auth.json, memories/, credentials/). Gitignored entirely.
- `./.env` — Compose-time secrets, gitignored

### Deploying to a minipc (Proxmox VM with Docker Engine)

See `fork/NOTE-6-minipc-proxmox.md` for the minipc-specific deltas: which files to copy, how to pull the prebuilt image from Docker Hub, how to keep `.agents/skills/` in sync from `agent-standards`, and the optional nginx reverse-proxy setup if you want LAN browser access without an SSH tunnel.
# Fork customization (Lukk17)

This fork (a personal instance of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)) keeps all local customization in net-new files so that future merges of upstream stay clean. The repository root IS the hermes-agent checkout, so upstream files sit at the top level and are intentionally untouched: `docker-compose.yml`, `Dockerfile`, `README.md`, `AGENTS.md`, every top-level `*.py` (`run_agent.py`, `cli.py`, `model_tools.py`, `toolsets.py`, ...), and `agent/`, `gateway/`, `tools/`, `hermes_cli/`, `cron/`, `plugins/`, `providers/`, `web/`, `ui-tui/`, `apps/`, `website/`, `tests/`, and the rest. The fork rebases onto upstream tags via `fork/NOTE-7-updating-from-upstream.md`.

This file is the entry point. Read it once. Then go to `fork/NOTE-1-install.md` for the install walkthrough.

## What is added by this fork

| File or directory | Purpose |
|---|---|
| `docker-compose.override.yml` | Auto-merged on top of upstream `docker-compose.yml`. Adds file-specific bind mounts for `./fork/hermes-config/SOUL.md`, `config.yaml`, `cron/jobs.json` at `/opt/data/...`; `./fork/projects:/opt/projects` for project workspaces; `.agents/skills:/opt/external-skills:ro` and `./skills:/opt/skills:ro` for skill discovery; env passthrough for messaging and OSINT keys; the dashboard loopback bind on `127.0.0.1:9119`; the `Dockerfile.fork` build for both services with `BASE_IMAGE=hermes-agent:upstream`; and the build-only `upstream-base` service that produces that base image. |
| `Dockerfile.fork` | The fork's tools image, built on `BASE_IMAGE` (default `hermes-agent:upstream`, produced from the untouched upstream `Dockerfile`). Adds OSINT apt dependencies, pyenv with Python 3.11 (crypto-monitor) and 3.12 (osint), `chown -R hermes:hermes /opt/hermes/ui-tui` so the runtime user can rewrite the dashboard's UI dist, and a `/opt/data/.local/bin/hermes` symlink so `hermes doctor` passes. Used by BOTH the gateway and the dashboard service. |
| `.env` (gitignored) | Local-only secrets and tokens. Auto-loaded by Docker Compose for variable substitution in `docker-compose.override.yml`. |
| `fork/hermes-config/` | Tracked fork-specific config (formerly lived in `hermes-data/`). Contains `SOUL.md` (persona), `config.yaml` (runtime config), `cron/jobs.json` (scheduled jobs). File-specific bind mounts shadow the same paths inside the container at `/opt/data/`. Rebase onto upstream hermes never conflicts with this directory because upstream does not ship it. |
| `fork/projects/` | Tracked project workspaces. One subdirectory per Discord channel. Mounted at `/opt/projects/` inside the container. Each subdir has its own `.venv/` (with leading dot, gitignored), `AGENTS.md`, source code. Currently: `crypto-monitor/`, `osint/`, `research/`. |
| `.agents/skills/` | Curated fork-authored skill set (33 skills), mirrored from `Lukk17/agent-standards/.agents/skills/`. Read-only mount at `/opt/external-skills/`. Listed in `fork/hermes-config/config.yaml` under `skills.external_dirs`. |
| `./skills/` | Bundled hermes skills (16 skills, hermes-shipped). Read-only mount at `/opt/skills/`. Listed in `fork/hermes-config/config.yaml` under `skills.external_dirs`. |
| `hermes-data/` (gitignored) | Runtime state ONLY. Contains `state.db` (SQLite sessions), `auth.json` (OAuth tokens), `logs/`, `sessions/`, `cache/`, `memories/` (MEMORY.md, USER.md). Rebase does not touch this directory because it is entirely gitignored. |
| `fork/AGENTS.md` | Coding agent guide for the fork overlay (Kilo / Claude Code / OpenCode / Copilot / Cursor). Imported from `.claude/CLAUDE.md`. |
| `fork/NOTE-*.md` | Reference docs for this fork. Install, Discord, operations, minipc, updating from upstream. Read `fork/NOTE-1-install.md` first. |
| `.claude/CLAUDE.md` | Claude Code entry point. `@`-imports `../AGENTS.md` (upstream) and `../fork/AGENTS.md` (fork overlay). |
| `.kilo/`, `.opencode/`, `.codex/`, `.github/agents/`,`.github/hooks/` | Per-tool entries for Kilo, OpenCode, Codex, GitHub Copilot. Tracked, fork-owned. |

## How the mount layout works

Three mount layers on the gateway container:

```
./hermes-data/                          -> /opt/data/                       (runtime state, RW)
./fork/projects/                        -> /opt/projects/                   (project workspaces, RW)
./.agents/skills/                       -> /opt/external-skills/             (curated skills, RO)
./skills/                               -> /opt/skills/                     (bundled skills, RO)

# File-specific overrides that shadow paths inside /opt/data/
./fork/hermes-config/SOUL.md            -> /opt/data/SOUL.md                 (agent persona)
./fork/hermes-config/config.yaml        -> /opt/data/config.yaml             (runtime config)
./fork/hermes-config/cron/jobs.json    -> /opt/data/cron/jobs.json         (scheduled jobs)
```

The dashboard container has the same hermes-data and fork/projects mounts plus SOUL.md (for the persona banner). It does NOT need skills, cron, or fork/hermes-config beyond SOUL.md.

## How the credentials wiring works

1. `.env` (next to `docker-compose.yml`) holds raw values. Gitignored.
2. `docker-compose.override.yml` references each variable by name with `${VAR}` substitution under the gateway service's `environment:` block.
3. On `docker compose up`, Compose reads `.env`, substitutes values into the merged compose config, starts the container with those env vars set. Hermes and its skills read them via `os.getenv` at runtime.

Variables wired in (full list in `docker-compose.override.yml`):

- Discord: `DISCORD_BOT_TOKEN`, `DISCORD_ALLOWED_USERS`, `DISCORD_HOME_CHANNEL`, `DISCORD_REQUIRE_MENTION`, `DISCORD_FREE_RESPONSE_CHANNELS`, `DISCORD_AUTO_THREAD`, `DISCORD_COMMAND_SYNC_POLICY`, `GATEWAY_ALLOW_ALL_USERS`
- On-chain: `BLOCKSCOUT_API_KEY`, `ALCHEMY_API_KEY`, `CRYPTOPANIC_API_KEY`
- Gmail OAuth: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`
- OSINT / threat-intel: `HUNTER_API_KEY`, `ABSTRACT_API_KEY`, `EMAILREP_API_KEY`, `NUMVERIFY_API_KEY`, `VIRUSTOTAL_API_KEY`, `URLSCAN_API_KEY`, `OTX_API_KEY`, `ABUSEIPDB_API_KEY`, `CENSYS_API_KEY`, `IPQS_API_KEY`, `DEHASHED_API_KEY`, `BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY`
- Misc: `ASCEND_SCRAPPER_URL`

To add another secret: append to `.env`, add `- VAR=${VAR}` under `gateway.environment:` in `docker-compose.override.yml`, recreate the gateway.

## Discord setup checklist

The fork wires up the Discord token. You still have to do the Discord Developer Portal work yourself.

1. Create an application at [Discord Developer Portal](https://discord.com/developers/applications).
2. In the `Bot` tab, enable **Privileged Gateway Intents**: `Message Content Intent` and `Server Members Intent`. Save. Without these the bot will be rejected at WebSocket connection time on hermes-agent v0.20.x and later.
3. In the `Bot` tab, click `Reset Token` to get a fresh token (the token is shown once, copy immediately). Paste into `.env` as `DISCORD_BOT_TOKEN=`.
4. In the `Bot` tab, leave `Requires OAuth2 Code Grant` OFF. That toggle is for OAuth2 user-facing apps, not bots. If it is on, you will see a "You must specify at least one URI" warning and the bot install will fail.
5. In `OAuth2 > URL Generator`, set `Integration Type` to `Guild Install`, scope `bot` plus `applications.commands`, permissions per `fork/NOTE-3-discord.md`.
6. Open the generated URL, pick your server, authorize. The bot joins.
7. Get your Discord user ID (Settings > Advanced > Developer Mode, then right-click your name > Copy User ID) and put it in `DISCORD_ALLOWED_USERS`. Without this the gateway denies all users. Set `GATEWAY_ALLOW_ALL_USERS=true` to skip the per-user check.

Full guide with screenshots and failure-mode table: see `fork/NOTE-3-discord.md`.

## Bringing it up

```powershell
docker compose config
```

```powershell
docker compose --profile build build upstream-base
```

```powershell
docker compose build gateway
```

```powershell
docker compose build dashboard
```

```powershell
docker compose up -d
```

```powershell
docker compose exec gateway hermes doctor
```

```powershell
docker compose exec gateway hermes cron list
```

```powershell
docker compose exec gateway ls /opt/projects
```

`upstream-base` builds the untouched upstream `Dockerfile` into `hermes-agent:upstream`, the base both fork images sit on. It is a build-only service and never runs.

The dashboard listens on `127.0.0.1:9119` of the host by default. For remote access use SSH tunnel (`ssh -L 9119:localhost:9119 <host>`) or nginx with basic auth (see `fork/NOTE-6-minipc-proxmox.md`).

## After editing fork files

In-container files do not survive a recreate. The general protocol:

1. Identify the file path on the host (e.g. `fork/hermes-config/config.yaml`).
2. Tell the user: "Open `<path>`. Change line N from X to Y. Save. Then run `docker compose up -d --force-recreate gateway dashboard` from the repo root."
3. Wait for the user to confirm.

The agent does NOT edit these files itself and does NOT recreate the container itself. Both are user actions. See `fork/AGENTS.md` for the full editing protocol.

## What is NOT in scope for this fork

- Bundling additional upstream messages platforms beyond Discord, the `messaging` tool, and the `telegram` placeholder. Adding one is a one-line credential addition to `.env` plus matching env passthrough in `docker-compose.override.yml`. Telegram env vars are commented out in the override, ready to uncomment.
- A bundled kanban board UI. Hermes has kanban via the kanban DB (`hermes-data/kanban.db`), but no dedicated web UI for it. The dashboard exposes the existing chat surface only.
- A web UI for the projects directories. Project workspaces are file-system-only. Operate through `git`, `docker compose exec`, and the hermes agent itself.
- Re-bundling upstream hermes source into a single image. We use the upstream source via `hermes-agent:upstream` plus the fork's tools layer and runtime overrides. No forks of the Python source are maintained.

## Migration from earlier fork versions

Earlier versions of this fork (before `v2026.5.29.2` rebase) used `my-skills/` instead of `.agents/skills/`, and put config files in `hermes-data/`. The current structure was finalized in commit `b7c6df52a1` and earlier. If you are coming from an older fork branch, the migration steps are:

1. `mv my-skills .agents/skills`
2. Move `hermes-data/SOUL.md`, `hermes-data/config.yaml`, `hermes-data/cron/jobs.json`, `hermes-data/.gitignore` to `fork/hermes-config/`. Drop the old `hermes-data/.gitignore` whitelist. `hermes-data/` is now runtime state only.
3. Update `docker-compose.override.yml` to add the file-specific bind mounts for the three config files.
4. Recreate the gateway. Skills, config, cron all load from the new paths.

See `fork/NOTE-7-updating-from-upstream.md` for the full rebase procedure.
# Fork customization (Lukk17)

This fork (a personal instance of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)) keeps all local customization in net-new files so that future merges of upstream stay clean. The repository root IS the hermes-agent checkout, so upstream files sit at the top level and are intentionally untouched: `docker-compose.yml`, `Dockerfile`, `README.md`, `AGENTS.md`, every top-level `*.py` (`run_agent.py`, `cli.py`, `model_tools.py`, `toolsets.py`, ...), and `agent/`, `gateway/`, `tools/`, `hermes_cli/`, `cron/`, `plugins/`, `providers/`, `web/`, `ui-tui/`, `apps/`, `website/`, `tests/`, and the rest. The fork rebases onto upstream tags via `fork/NOTE-7-updating-from-upstream.md`.

This file is the entry point. Read it once. Then go to `fork/NOTE-1-install.md` for the install walkthrough.

## Shell variants in this note

Docker and git commands are identical in PowerShell and in a Unix shell, so they appear once, in a block tagged `bash`, and paste unchanged into PowerShell on Windows, into bash or zsh on Linux, and into zsh on macOS. Anything that genuinely differs between the two, file copies, variable assignment, redirection, reading a file, gets one block per shell with a label above it saying which is which. A command that only makes sense on one platform gets a single block and a sentence saying why there is no second variant.

## The one idea behind the layout

Everything hermes owns lives in one directory on your machine, `hermes-data/`, which is bind-mounted into the container as `/opt/data`. That is the container's home directory, so every file hermes creates, its persona, its memories, its sessions, its logs, its project workspaces, lands back in `hermes-data/` on the host. There is no Docker volume, and nothing is hidden inside the image.

`hermes-data/` is its own git repository, a clone of the private `Lukk17/hermes-projects` (branch `master`), not a submodule. This repo's own `.gitignore` ignores it wholesale with one line, `/hermes-data/`, so this repo never tracks a single byte of it. Inside that nested repository, `hermes-data/.gitignore` decides which of those files travel between machines the same way this repo's `.gitignore` used to: it ignores everything by default and then re-includes exactly the pieces worth carrying, `config.yaml`, `SOUL.md`, `cron/jobs.json`, `memories/*.md`, everything under `projects/`, `scripts/crypto-monitor-daily.sh`, the runtime `skills/`, `plugins/`, `hooks/` and `skins/` folders, and `.gitignore` itself. Databases, logs, caches, OAuth tokens and `hermes-data/.env` stay on the machine that made them.

That is what makes the intended workflow work. Use hermes on one machine, let it update its own SOUL and memories as it goes, then inside `hermes-data/`, `git commit` and `git push` to `hermes-projects`. On the other machine, `git pull` inside `hermes-data/` and `docker compose up -d` from the repo root, and the same persona, memories, cron jobs and projects are there with no setup step.

One exception to hermes writing whatever it likes: `hermes-data/config.yaml` and `hermes-data/scripts/crypto-monitor-daily.sh` are re-mounted read-only on top of the read-write parent. Hermes cannot rewrite them at runtime. To change either one, edit the file on the host and recreate the container.

Whenever a path appears below, `hermes-data/...` and anything else without a leading `/opt` is on your machine, and `/opt/...` is inside the container.

## What is added by this fork

| File or directory | Purpose |
|---|---|
| `docker-compose.override.yml` | Auto-merged on top of upstream `docker-compose.yml`. Points `/opt/data` at `./hermes-data` instead of upstream's `~/.hermes`; re-mounts `./hermes-data/config.yaml` and `./hermes-data/scripts/crypto-monitor-daily.sh` read-only on top of it; adds `.agents/skills:/opt/data/external-skills:ro` and `./skills:/opt/data/bundled-skills:ro` for skill discovery; sets `HERMES_SKIP_CONFIG_MIGRATION=1` so the boot hook does not try to rewrite the read-only config; env passthrough for on-chain and OSINT keys; the dashboard loopback bind on `127.0.0.1:9119`; the `Dockerfile.fork` build for both services with `BASE_IMAGE=hermes-agent:upstream`; and the build-only `upstream-base` service that produces that base image. |
| `Dockerfile.fork` | The fork's tools image, built on `BASE_IMAGE` (default `hermes-agent:upstream`, produced from the untouched upstream `Dockerfile`). Adds OSINT apt dependencies, pyenv with Python 3.11 (crypto-monitor) and 3.12 (osint), `chown -R hermes:hermes /opt/hermes/ui-tui` so the runtime user can rewrite the dashboard's UI dist, and a `/opt/data/.local/bin/hermes` symlink so `hermes doctor` passes. Used by BOTH the gateway and the dashboard service. |
| `.env` (gitignored) | Local-only secrets and tokens. Auto-loaded by Docker Compose for variable substitution in `docker-compose.override.yml`. |
| `hermes-data/` | The whole of hermes' home directory, mounted at `/opt/data` in the container. Its own git repository, a clone of the private `Lukk17/hermes-projects` (branch `master`), not a submodule. Holds tracked config and untracked runtime state side by side. This repo's own `.gitignore` ignores it wholesale with one line, so a rebase of this repo never touches it at all. |
| `hermes-data/config.yaml` (tracked in `hermes-projects`) | Runtime config: model, provider, `skills.external_dirs`, Discord channel prompts. Re-mounted READ-ONLY in the container, so hermes cannot rewrite it. Edit on the host, recreate to apply. |
| `hermes-data/SOUL.md` (tracked in `hermes-projects`) | Agent persona. Writable at runtime, so hermes can update its own SOUL and the change lands on the host ready to commit inside `hermes-data/`. |
| `hermes-data/cron/jobs.json` (tracked in `hermes-projects`) | Scheduled jobs. Writable at runtime; `hermes cron` edits it in place. |
| `hermes-data/memories/*.md` (tracked in `hermes-projects`) | `MEMORY.md` and `USER.md`, the memory subsystem's own files. Writable at runtime, tracked so memories follow you to the other machine. |
| `hermes-data/projects/` (tracked in `hermes-projects`) | Project workspaces, one subdirectory per Discord channel. Reachable at `/opt/data/projects/` in the container. Each subdir has its own `.venv/` (with leading dot, gitignored, built once per machine), `AGENTS.md`, source code. Currently: `crypto-monitor/`, `osint/`, `research/`. |
| `hermes-data/scripts/crypto-monitor-daily.sh` (tracked in `hermes-projects`) | The cron job's entry point. Re-mounted READ-ONLY, same recreate-to-change rule as `config.yaml`. |
| `hermes-data/skills/`, `plugins/`, `hooks/`, `skins/` (tracked in `hermes-projects`) | Skills, plugins, hooks and skins that hermes installs or writes at runtime, including the skill usage file `skills/.usage.json` and `skills/.bundled_manifest`. Tracked so they follow you to the other machine. Curator backup snapshots and lock files under `skills/` stay ignored. |
| everything else in `hermes-data/` (ignored by `hermes-data/.gitignore`) | `state.db` (SQLite sessions), `auth.json` (OAuth tokens), `.env` (secrets hermes child processes read), `logs/`, `sessions/`, `cache/`, lock files. Per-machine, never committed. |
| `.agents/skills/` | Curated fork-authored skill set, mirrored from `Lukk17/agent-standards/.agents/skills/`. Read-only mount at `/opt/data/external-skills/`. Listed in `hermes-data/config.yaml` under `skills.external_dirs`. |
| `./skills/` | Bundled hermes skills, shipped by upstream. Read-only mount at `/opt/data/bundled-skills/`. Listed in `hermes-data/config.yaml` under `skills.external_dirs`. |
| `fork/AGENTS.md` | Coding agent guide for the fork overlay (Kilo / Claude Code / OpenCode / Copilot / Cursor). Imported from `.claude/CLAUDE.md`. |
| `fork/NOTE-*.md` | Reference docs for this fork. Install, Discord, operations, minipc, updating from upstream. Read `fork/NOTE-1-install.md` first. |
| `.claude/CLAUDE.md` | Claude Code entry point. `@`-imports `../AGENTS.md` (upstream) and `../fork/AGENTS.md` (fork overlay). |
| `.kilo/`, `.opencode/`, `.codex/`, `.github/agents/`,`.github/hooks/` | Per-tool entries for Kilo, OpenCode, Codex, GitHub Copilot. Tracked, fork-owned. |

## How the mount layout works

Left of the arrow is a path on your machine, relative to the repo root. Right of the arrow is where it appears inside the container.

```
./hermes-data/              -> /opt/data                        everything, read-write
./.agents/skills/           -> /opt/data/external-skills        curated skills, read-only
./skills/                   -> /opt/data/bundled-skills         upstream skills, read-only

# re-mounted read-only on top of the read-write parent
./hermes-data/config.yaml   -> /opt/data/config.yaml
./hermes-data/scripts/crypto-monitor-daily.sh
                            -> /opt/data/scripts/crypto-monitor-daily.sh
```

`SOUL.md`, `cron/jobs.json`, `memories/` and `projects/` need no mount line of their own. They are already inside `hermes-data/`, which is mounted whole, so they appear at `/opt/data/SOUL.md`, `/opt/data/cron/jobs.json`, `/opt/data/memories/` and `/opt/data/projects/` and hermes can write to all of them.

The container's home directory is `/opt/data`, set by the upstream image at `Dockerfile:386` (`ENV HERMES_HOME=/opt/data`). The same image already restricts agent writes to that tree at `Dockerfile:387` (`ENV HERMES_WRITE_SAFE_ROOT=/opt/data`). Since everything the fork cares about now lives under `/opt/data`, that default is already correct and the compose file sets no override for it.

The dashboard container gets the same `hermes-data` mount and the same read-only `config.yaml`. It does not mount the two skills directories, because only the gateway loads skills.

## How the credentials wiring works

1. `.env` (next to `docker-compose.yml`) holds raw values. Gitignored.
2. `docker-compose.override.yml` references each variable by name with `${VAR}` substitution under the gateway service's `environment:` block.
3. On `docker compose up`, Compose reads `.env`, substitutes values into the merged compose config, starts the container with those env vars set. Hermes and its skills read them via `os.getenv` at runtime.

Variables wired in (full list in `docker-compose.override.yml`):

- Discord: `DISCORD_COMMAND_SYNC_POLICY` only. Everything else Discord-related has moved. The bot token lives in `hermes-data/.env`, not in the compose passthrough, because hermes strips messaging and provider credentials from every subprocess it spawns, so only that file reaches a cron script shelling out to `hermes send`. Full reasoning in `fork/NOTE-3-discord.md`. The behavioural settings (`require_mention`, `free_response_channels`, `auto_thread`, `allow_all_users`, `channel_prompts`) live in `hermes-data/config.yaml` under `discord:`.
- On-chain: `BLOCKSCOUT_API_KEY`, `ALCHEMY_API_KEY`, `CRYPTOPANIC_API_KEY`
- Gmail OAuth: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`
- OSINT / threat-intel: `HUNTER_API_KEY`, `ABSTRACT_API_KEY`, `EMAILREP_API_KEY`, `NUMVERIFY_API_KEY`, `VIRUSTOTAL_API_KEY`, `URLSCAN_API_KEY`, `OTX_API_KEY`, `ABUSEIPDB_API_KEY`, `CENSYS_API_KEY`, `IPQS_API_KEY`, `DEHASHED_API_KEY`, `BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY`
- Misc: `ASCEND_SCRAPPER_URL`

To add another secret: append to `.env`, add `- VAR=${VAR}` under `gateway.environment:` in `docker-compose.override.yml`, recreate the gateway.

## Discord setup checklist

The fork wires up the Discord token. You still have to do the Discord Developer Portal work yourself.

1. Create an application at [Discord Developer Portal](https://discord.com/developers/applications).
2. In the `Bot` tab, enable **Privileged Gateway Intents**: `Message Content Intent` and `Server Members Intent`. Save. Without these the bot will be rejected at WebSocket connection time on hermes-agent v0.20.x and later.
3. In the `Bot` tab, click `Reset Token` to get a fresh token (the token is shown once, copy immediately). Paste it into `hermes-data/.env` as `DISCORD_BOT_TOKEN=`, not into the repo-root `.env`, which compose does not forward it from. That file is also the only one a hermes child process can read the token from. See `fork/NOTE-3-discord.md`.
4. In the `Bot` tab, leave `Requires OAuth2 Code Grant` OFF. That toggle is for OAuth2 user-facing apps, not bots. If it is on, you will see a "You must specify at least one URI" warning and the bot install will fail.
5. In `OAuth2 > URL Generator`, set `Integration Type` to `Guild Install`, scope `bot` plus `applications.commands`, permissions per `fork/NOTE-3-discord.md`.
6. Open the generated URL, pick your server, authorize. The bot joins.
7. Decide who may talk to the bot, in `hermes-data/config.yaml` under `discord:`. Either set `allow_all_users: true`, or list your own Discord user ID under `allowed_users` (Settings > Advanced > Developer Mode, then right-click your name > Copy User ID). Without one of the two the gateway denies every sender. This fork ships `allow_all_users: true`.

Full guide with screenshots and failure-mode table: see `fork/NOTE-3-discord.md`.

## Bringing it up

```bash
docker compose config
```

```bash
docker compose --profile build build upstream-base
```

```bash
docker compose build gateway dashboard
```

```bash
docker compose up -d
```

```bash
docker compose exec gateway hermes doctor
```

```bash
docker compose exec gateway hermes cron list
```

```bash
docker compose exec gateway ls /opt/data/projects
```

`upstream-base` builds the untouched upstream `Dockerfile` into `hermes-agent:upstream`, the base both fork images sit on. It is a build-only service and never runs.

The dashboard listens on `127.0.0.1:9119` of the host by default. For remote access use SSH tunnel (`ssh -L 9119:localhost:9119 <host>`) or nginx with basic auth (see `fork/NOTE-6-minipc-proxmox.md`).

## After editing fork files

Because `hermes-data/` is bind-mounted whole, a file you edit on the host is already changed inside the container the moment you save it. Whether that is enough depends on the file.

- `hermes-data/SOUL.md`, `cron/jobs.json`, `memories/*.md`, anything under `projects/`: no recreate. The next session or the next cron tick reads the new content.
- `hermes-data/config.yaml` and `hermes-data/scripts/crypto-monitor-daily.sh`: recreate. Config is read once at startup, and both files are read-only inside the container so nothing can pick up a change on its own.
- `docker-compose.override.yml`, `Dockerfile.fork`, `.env`: recreate, and rebuild for `Dockerfile.fork`.

The recreate command, run from the repo root:

```bash
docker compose up -d --force-recreate gateway dashboard
```

A coding agent does NOT recreate the container itself. It says which file to change and whether a recreate is needed, then waits. See `fork/AGENTS.md` for the full editing protocol.

## What is NOT in scope for this fork

- Bundling additional upstream messages platforms beyond Discord, the `messaging` tool, and the `telegram` placeholder. Adding one is a one-line credential addition to `.env` plus matching env passthrough in `docker-compose.override.yml`. Telegram env vars are commented out in the override, ready to uncomment.
- A bundled kanban board UI. Hermes has kanban via the kanban DB (`hermes-data/kanban.db`), but no dedicated web UI for it. The dashboard exposes the existing chat surface only.
- A web UI for the projects directories. Project workspaces are file-system-only. Operate through `git`, `docker compose exec`, and the hermes agent itself.
- Re-bundling upstream hermes source into a single image. We use the upstream source via `hermes-agent:upstream` plus the fork's tools layer and runtime overrides. No forks of the Python source are maintained.

## Moving the setup to another machine

This is the workflow the layout exists for.

On the machine you have been working on, commit whatever hermes changed about itself and push, from inside `hermes-data/`, which is its own git repository, a clone of the private `Lukk17/hermes-projects`:

```bash
cd hermes-data
```

```bash
git add -A
```

```bash
git commit -m "state: soul, memories, cron, projects"
```

```bash
git push
```

```bash
cd ..
```

Setting up a brand new machine needs two clones, in this order, from the directory that will hold the checkout. The second clone has to happen before the first container start, because `docker compose up` creates `hermes-data/` itself if it does not exist yet, and `git clone` refuses to clone into a directory that already has files in it:

```bash
git clone https://github.com/Lukk17/hermes-agent.git hermes-agent
```

```bash
git clone https://github.com/Lukk17/hermes-projects.git hermes-agent/hermes-data
```

`hermes-projects` is private, so the second clone needs GitHub authentication on that machine first, either `gh auth login` or a credential helper backed by a personal access token.

If `hermes-data/` already exists on a machine with runtime files in it, so the clone above would refuse, recover in place instead, from inside `hermes-data/`:

```bash
git init
```

```bash
git remote add origin https://github.com/Lukk17/hermes-projects.git
```

```bash
git fetch origin
```

```bash
git checkout -f -b master origin/master
```

On a machine that already has both clones, pull both and bring it up:

```bash
git pull
```

```bash
cd hermes-data
```

```bash
git pull
```

```bash
cd ..
```

```bash
docker compose up -d
```

What does not travel, and has to exist on each machine separately: the repo-root `.env` and `hermes-data/.env` (secrets), `hermes-data/auth.json` (OAuth tokens, re-run the login), the per-project `.venv/` directories (rebuild them, see `fork/NOTE-1-install.md`), and the session databases and logs. Everything else, the persona, the memories, the cron schedule, the project workspaces and the runtime skills, plugins, hooks and skins, comes across in the `hermes-projects` clone.

See `fork/NOTE-6-minipc-proxmox.md` for the Linux side of this, including the one command that makes the container's user id match the host file owner, and `fork/NOTE-7-updating-from-upstream.md` for the rebase procedure.
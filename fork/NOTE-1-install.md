Hermes Agent runs as two Docker containers built from the same image. The `gateway` container is the agent runtime plus messaging integrations (outbound only, no published ports). The `dashboard` container serves the web UI on `127.0.0.1:9119` of the host (loopback only, LAN cannot reach it).

Both mount one directory from the repo, `./hermes-data/`, at `/opt/data` inside the container. That path is hermes' home directory, so everything hermes writes, config, persona, memories, sessions, logs and the project workspaces, is a file in `hermes-data/` on your machine. Upstream's compose mounts `~/.hermes` there instead; the fork's override points it at the repo so your home directory stays untouched and so the interesting files can be tracked in git.

Two files inside that mount are re-mounted read-only on top of it: `hermes-data/config.yaml` and `hermes-data/scripts/crypto-monitor-daily.sh`. A running hermes cannot rewrite either. Because the boot-time schema migration would try to rewrite `config.yaml` and fail against a read-only mount, the override also sets `HERMES_SKIP_CONFIG_MIGRATION=1`.

Wherever a path appears in this note, `hermes-data/...` is on your machine and `/opt/...` is inside the container.

### Shell variants in this note

Docker and git commands are identical in PowerShell and in a Unix shell, so they appear once, in a block tagged `bash`, and paste unchanged into PowerShell on Windows, into bash or zsh on Linux, and into zsh on macOS. Anything that genuinely differs between the two, file copies, variable assignment, redirection, reading a file, gets one block per shell with a label above it saying which is which. A command that only makes sense on one platform gets a single block and a sentence saying why there is no second variant.

### Container user id on a Linux host

Only native Linux passes real file ownership through a bind mount, and this is the one setup step that differs by operating system.

The container drops to an internal `hermes` user, uid 10000 by default. On native Linux, if that uid does not own your checkout, every write the agent makes under `/opt/data` fails with EACCES: SOUL.md, memories, cron jobs, project files. Run this once per Linux machine, from the repo root, to pin the container's uid to yours. Compose reads `.env` on every `up` afterwards, so there is nothing to remember later:

```bash
printf 'HERMES_UID=%s\nHERMES_GID=%s\n' "$(id -u)" "$(id -g)" >> .env
```

That block has no PowerShell variant on purpose. It reads the calling user's numeric uid and gid, which Windows does not have, and it is only needed on a host that enforces those ids through a bind mount. Writing a PowerShell version would produce a line nobody should ever add to `.env` on Windows.

On Windows with Docker Desktop this is not needed and was measured not to be: the 9p/drvfs gateway squashes permissions, so uid 10000 writes into `/opt/data` cleanly with nothing set. On macOS with Docker Desktop it is believed not to be needed for the same reason, but that has not been measured. `.env.fork.example` carries a one-command check for the macOS case if you want to confirm it rather than assume it.

### Torn writes on a bind mount

Writes to a file that is itself a bind-mount target are NOT crash-atomic. `utils.py:194-276` tries `os.replace()` first, but a rename across a bind mount fails with `EXDEV`/`EBUSY`, so the writer falls back to copy-then-fsync-then-unlink in place. This applied to the old file-level config mounts and still applies to `hermes-data/config.yaml`, which is the one file this fork still mounts individually. The tracked files inside the directory mount (`SOUL.md`, `cron/jobs.json`, `memories/`) are ordinary files in a mounted directory and rename normally. Keeping everything in git is the safety net either way: treat an unexpected diff as a possible torn write.

Authentication: the dashboard has no built-in auth. Access is restricted at the network layer, only the host's loopback can reach it. From another machine, use SSH tunneling (see fork/NOTE-4-secure-remote-access.md).

This note covers a clean install from zero to working. For day-to-day operations see fork/NOTE-5-operations.md.

It is written for a dev box that builds the images locally. Every `docker compose` command here relies on Compose merging `docker-compose.override.yml` automatically, so this machine's `.env` must not carry a `COMPOSE_FILE` line. A minipc that pulls prebuilt images never uses the override and follows fork/NOTE-6-minipc-proxmox.md instead.

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Compose plugin v2.24+ (Linux)
- An LLM provider account or API key (fork/NOTE-2-llm-providers.md)
- A Discord bot already created in the Discord Developer Portal if Discord access is wanted (fork/NOTE-3-discord.md)

### Fork-local files

| File | Purpose |
|---|---|
| `docker-compose.override.yml` | Auto-merged on top of upstream `docker-compose.yml`. Points `/opt/data` at `./hermes-data`; re-mounts `./hermes-data/config.yaml` and `./hermes-data/scripts/crypto-monitor-daily.sh` read-only on top of it; adds `.agents/skills:/opt/data/external-skills:ro` and `./skills:/opt/data/bundled-skills:ro`; sets `HERMES_SKIP_CONFIG_MIGRATION=1`; env passthrough; the `Dockerfile.fork` build for both services with `BASE_IMAGE=hermes-agent:upstream`; and the build-only `upstream-base` service that produces that base image |
| `Dockerfile.fork` | The fork's tools image. Takes `BASE_IMAGE` as a build arg (default `hermes-agent:upstream`) and layers on: OSINT apt dependencies, pyenv with Python 3.11 (crypto-monitor) and 3.12 (osint), a `chown -R hermes:hermes /opt/hermes/ui-tui`, and a `/opt/data/.local/bin/hermes` symlink so `hermes doctor` passes. Both the gateway and the dashboard build from it |
| `.env` (repo root, gitignored) | Compose-time values: the API keys the override forwards, and `HERMES_UID`/`HERMES_GID` on Linux. Auto-loaded by Compose for `${VAR}` substitution |
| `.env.fork.example` | Committed template, copy to `.env` and fill |
| `hermes-data/.env` (gitignored) | Runtime secrets that hermes and its child processes read directly. `DISCORD_BOT_TOKEN`, `MINIMAX_API_KEY` and `GITHUB_TOKEN` belong here rather than in the compose passthrough. See fork/NOTE-5-operations.md for why. Template: `hermes-data/.env.example` |
| `hermes-data/` | Hermes' whole home directory, mounted at `/opt/data`. Its own git repository, a clone of the private `Lukk17/hermes-projects` (branch `master`), not a submodule. Tracked inside that repository: `config.yaml`, `SOUL.md`, `cron/jobs.json`, `memories/*.md`, `projects/`, the top-level entry scripts `scripts/*.sh`, `skills/`, `plugins/`, `hooks/`, `skins/`, `plans/`, `workspace/`, `local/`, `.env.example`, and its own `.gitignore`. Ignored inside it: `state.db`, `auth.json`, `.env`, `logs/`, `sessions/`, `cache/` and the rest of the runtime state. The fork repository ignores the whole directory with one line, `/hermes-data/`, so a rebase of the fork never touches it |
| `.agents/skills/` | User-authored skill folders, read-only mount into the container as `/opt/data/external-skills`. Tracked in git, mirrors a curated subset of `Lukk17/agent-standards/.agents/skills/` |
| `./skills/` | Bundled hermes skills, read-only mount into the container as `/opt/data/bundled-skills` |

### Clone hermes-data before the first container start

`hermes-data/` is its own git repository, a clone of the private `Lukk17/hermes-projects` (branch `master`), not a submodule. Clone it into place before you run `docker compose up` for the first time: the gateway container creates `hermes-data/` itself if it does not exist, and `git clone` refuses to clone into a directory that already has files in it. From the repo root:

```bash
git clone https://github.com/Lukk17/hermes-projects.git hermes-data
```

`hermes-projects` is private, so this clone needs GitHub authentication on this machine first, either `gh auth login` or a credential helper backed by a personal access token.

If `hermes-data/` already exists on this machine with runtime files in it, so the clone above would refuse, recover in place instead, from inside `hermes-data/`:

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

### Step 1, copy the env template

PowerShell:

```powershell
Copy-Item .env.fork.example .env
```

Unix shell:

```bash
cp .env.fork.example .env
```

Open `.env` and fill values. Empty values are passed through harmlessly to the container.

On a native Linux host, also append the container user id here now, before the first `up`. Linux only, for the reason given above:

```bash
printf 'HERMES_UID=%s\nHERMES_GID=%s\n' "$(id -u)" "$(id -g)" >> .env
```

### Step 2, fill messaging credentials

The Discord bot token does NOT go in the repo-root `.env`, and compose does not forward it. It goes in `hermes-data/.env`, because hermes strips messaging and provider credentials from every subprocess it spawns and that file is the one each child re-reads at startup. Full reasoning in `fork/NOTE-3-discord.md`. Create or open `hermes-data/.env` (gitignored) and put it there:

```
DISCORD_BOT_TOKEN=<bot-token>
```

Who is allowed to talk to the bot is a config setting, not an env var. In `hermes-data/config.yaml` under `discord:`, either set `allow_all_users: true` or list Discord user IDs under `allowed_users`. This fork ships `allow_all_users: true`.

### Step 3, fill any skill API keys

Blockchain, OSINT, Gmail OAuth, and other skill keys are listed in `.env.fork.example`. Fill what is needed, leave the rest blank.

### Step 4, build and start the containers

```bash
docker compose --profile build build upstream-base
```

```bash
docker compose build gateway dashboard
```

```bash
docker compose up -d
```

`upstream-base` goes first because it builds the untouched upstream `Dockerfile` into the tag `hermes-agent:upstream`, which is the `BASE_IMAGE` both fork images sit on. It is a build-only service (`profiles: ["build"]`) and never runs. The gateway and dashboard builds are independent of each other. `./hermes-data/` already has the tracked config, persona, cron jobs, memories and projects in it, from the `hermes-data` clone above. The first start fills in the untracked runtime state beside them (`state.db`, `logs/`, `sessions/`, `cache/`).

Tail the gateway logs:

```bash
docker compose logs -f gateway
```

### Step 5, configure an LLM provider

See fork/NOTE-2-llm-providers.md. Come back here when a provider is configured and `hermes doctor` shows it as logged in.

### Step 6, enable user-authored skills

`hermes-data/config.yaml` already declares the skills paths:

```yaml
skills:
  external_dirs:
    - /opt/data/external-skills
    - /opt/data/bundled-skills
```

`/opt/data/external-skills` reads from `.agents/skills/` (host). `/opt/data/bundled-skills` reads from `./skills/` (host). Both are read-only bind mounts. If you have a curated subset of skills you want to ship with the fork, they go in `.agents/skills/`. If you want to add new per-project skills, they go in `./skills/`.

### Step 6b, build the two project venvs

Required, not optional. `hermes-data/projects/crypto-monitor/.venv/` and
`hermes-data/projects/osint/.venv/` are gitignored and are NOT in the image, so a fresh
clone has neither. The crypto-monitor pipeline hard-requires `.venv/bin/python`
and exits 2 without it, and every osint command runs through its own venv.

```bash
docker compose exec -u hermes gateway bash -lc "cd /opt/data/projects/crypto-monitor && uv venv .venv --python python3.11 && uv pip install --python ./.venv/bin/python -e ."
```

```bash
docker compose exec -u hermes gateway bash -lc "cd /opt/data/projects/osint && uv venv .venv --python python3.12 && uv pip install --python ./.venv/bin/python -e ."
```

The chain inside the quotes runs in the container's bash, not in your shell, so both blocks paste unchanged into PowerShell.

On the minipc, run the same two commands from `/opt/docker-stack/hermes`. They pick up `docker-compose.yml` plus `docker-compose.minipc.yml` from the `COMPOSE_FILE` line in the minipc's `.env`, see "Every docker compose command on the minipc uses both files" in fork/NOTE-6-minipc-proxmox.md.

Build them as the `hermes` user, not root, or the venvs land root-owned and the
supervised gateway cannot use them.

### Step 7, verify

```bash
docker compose exec gateway hermes doctor
```

```bash
docker compose exec gateway hermes skills list
```

```bash
docker compose exec gateway ls /opt/data/projects
```

The two skill listings are long, so trim them on your side of the pipe. That trim is the one thing in this step that differs by shell, because the pipe is consumed by PowerShell or by your Unix shell rather than by the container.

PowerShell:

```powershell
docker compose exec gateway ls /opt/data/external-skills | Select-Object -First 3
```

```powershell
docker compose exec gateway ls /opt/data/bundled-skills | Select-Object -First 3
```

Unix shell:

```bash
docker compose exec gateway ls /opt/data/external-skills | head -3
```

```bash
docker compose exec gateway ls /opt/data/bundled-skills | head -3
```

### Step 8, open the dashboard

On the host running Docker:

```
http://localhost:9119
```

From another machine on your LAN or remote, SSH tunnel (see fork/NOTE-4-secure-remote-access.md, or fork/NOTE-6-minipc-proxmox.md for the minipc-specific tunnel).

### Where state lives

Everything below is a path on your machine. The container sees all of `./hermes-data/` at `/opt/data`. Two separate git repositories cover this tree: the fork repository you cloned to get this file, and `hermes-data/`, which is its own clone of the private `Lukk17/hermes-projects`.

Tracked inside `hermes-data/`'s own repository, so it travels to another machine in that clone:

- `./hermes-data/config.yaml`: model, provider, `skills.external_dirs`, Discord channel prompts. Read-only inside the container
- `./hermes-data/SOUL.md`: agent persona. Hermes can rewrite it at runtime and the change lands here
- `./hermes-data/cron/jobs.json`: scheduled jobs
- `./hermes-data/memories/MEMORY.md` and `USER.md`: the memory subsystem's files
- `./hermes-data/projects/`: project workspaces, one subdir per Discord channel
- `./hermes-data/scripts/*.sh`: the top-level cron entry scripts. `crypto-monitor-daily.sh` is read-only inside the container
- `./hermes-data/skills/`: skills hermes installs or writes at runtime, with `.usage.json` and `.bundled_manifest`. Curator backups and lock files inside it stay ignored
- `./hermes-data/plugins/`, `./hermes-data/hooks/`, `./hermes-data/skins/`: plugins, hooks and skins added at runtime
- `./hermes-data/plans/`, `./hermes-data/workspace/`, `./hermes-data/local/`: plans, workspace and local folders written at runtime
- `./hermes-data/.env.example`: the template for `hermes-data/.env`, with placeholders and no real values

Tracked by the fork repository itself, so it travels in the `hermes-agent` clone:

- `./.agents/skills/`: curated skill set, mounted read-only at `/opt/data/external-skills`
- `./skills/`: bundled hermes skills, mounted read-only at `/opt/data/bundled-skills`

Ignored by `hermes-data/.gitignore`, so it stays on this machine and has to be recreated on the next one:

- `./hermes-data/state.db`, `./hermes-data/sessions/`, `./hermes-data/logs/`, `./hermes-data/cache/`: sessions, logs, caches
- `./hermes-data/auth.json`: OAuth tokens. Re-run the provider login on the other machine
- `./hermes-data/.env`: runtime secrets hermes and its child processes read
- `./hermes-data/projects/*/.venv/`: per-project virtualenvs. Rebuild with Step 6b

Ignored by the fork repository's own `.gitignore`:

- `./.env`: Compose-time values, including `HERMES_UID`/`HERMES_GID` on Linux

### Deploying to a minipc (Proxmox VM with Docker Engine)

See `fork/NOTE-6-minipc-proxmox.md` for the minipc-specific deltas: which files to copy, how to pull the prebuilt image from Docker Hub, how to keep `.agents/skills/` in sync from `agent-standards`, and how to open the dashboard through an SSH tunnel, the only remote access path.
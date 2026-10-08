Day-to-day operations against a working Hermes Agent install. Assumes fork/NOTE-1-install.md has been followed and containers are up.

### Shell variants in this note

Docker and git commands are identical in PowerShell and in a Unix shell, so they appear once, in a block tagged `bash`, and paste unchanged into PowerShell on Windows, into bash or zsh on Linux, and into zsh on macOS. Anything that genuinely differs between the two, file copies, variable assignment, redirection, reading a file, gets one block per shell with a label above it saying which is which. A command that only makes sense on one platform gets a single block and a sentence saying why there is no second variant.

### Which machine these commands are for

Every `docker compose` command in this note is written for the dev box that builds the images locally. Its `.env` has no `COMPOSE_FILE` line, so Compose uses `docker-compose.yml` plus the automatically merged `docker-compose.override.yml`.

On the minipc the lifecycle, logs, `exec`, recreate and OAuth commands work unchanged, as long as they run from `/opt/docker-stack/hermes` and the minipc's `.env` carries the `COMPOSE_FILE` line that selects `docker-compose.yml` plus `docker-compose.minipc.yml`. How to add it is in "Every docker compose command on the minipc uses both files" in `fork/NOTE-6-minipc-proxmox.md`. The build commands are for the dev box only: "Build order", "Updating to the latest upstream", "Full clean rebuild" and the `docker compose build` row in the troubleshooting table. The minipc never builds, it pulls, see "Updating to a new upstream image" in `fork/NOTE-6-minipc-proxmox.md`.

### Container lifecycle

Start everything in the background:

```bash
docker compose up -d
```

Stop everything (containers removed, volumes kept):

```bash
docker compose down
```

Stop without removing containers (faster restart):

```bash
docker compose stop
```

Bring stopped containers back without rebuilding:

```bash
docker compose start
```

Restart a single service:

```bash
docker compose restart gateway
```

```bash
docker compose restart dashboard
```

Recreate a service (forces re-read of env, override, and command changes):

```bash
docker compose up -d --force-recreate gateway
```

Recreate everything, which is the usual move after editing `config.yaml`, `docker-compose.override.yml` or `.env`:

```bash
docker compose up -d --force-recreate
```

A recreate is not needed for most edits. `./hermes-data/` on the host is mounted whole at `/opt/data` in the container, so a file you save on the host is already changed inside the container. What you actually need per file:

- `./hermes-data/SOUL.md`, `./hermes-data/cron/jobs.json`, `./hermes-data/memories/*.md`, anything under `./hermes-data/projects/`: nothing. The next session or the next cron tick reads the new content.
- `./hermes-data/config.yaml`: recreate. Config is read once at process start, and the file is mounted read-only, so the running process will never pick it up.
- `./hermes-data/scripts/crypto-monitor-daily.sh`: recreate. Same read-only mount.
- `docker-compose.override.yml` or `.env`: recreate. Mounts and environment only apply to a freshly created container.
- `Dockerfile.fork`: rebuild, then recreate.

### Logs

```bash
docker compose logs -f gateway
```

```bash
docker compose logs --tail 50 dashboard
```

Those two read the container's stdout. The persistent logs are ordinary files on the host under `./hermes-data/logs/`, because `hermes-data/` is hermes' home directory: `gateway.log` (the gateway), `agent.log` (INFO and above), `errors.log` (WARNING and above). They survive container recreation and are gitignored. Inside the container the same files are at `/opt/data/logs/`.

### Container shell

`docker compose exec` runs against the already-running container. It does not spawn a new one.

Interactive Hermes CLI inside the gateway:

```bash
docker compose exec -it gateway hermes
```

Raw bash shell:

```bash
docker compose exec -it gateway bash
```

One-off Hermes subcommands:

```bash
docker compose exec gateway hermes doctor
```

```bash
docker compose exec gateway hermes skills list
```

```bash
docker compose exec gateway hermes cron list
```

### Build order

`Dockerfile.fork` takes a `BASE_IMAGE` build arg, defaulting to `hermes-agent:upstream`. That tag is produced by the build-only `upstream-base` service, which builds the untouched upstream `Dockerfile`. Build it first:

```bash
docker compose --profile build build upstream-base
```

After that, `gateway` and `dashboard` both build from `Dockerfile.fork` on top of that base and are independent of each other, so their order does not matter, and one `docker compose build gateway dashboard` covers both.

### Updating to the latest upstream

See `fork/NOTE-7-updating-from-upstream.md` for the full procedure. Short form:

```bash
git fetch upstream --tags
```

```bash
git checkout master
```

```bash
git rebase v<TAG>
```

```bash
docker compose --profile build build upstream-base
```

```bash
docker compose build gateway dashboard
```

```bash
docker compose up -d --force-recreate gateway dashboard
```

### Full clean rebuild (clear start)

```bash
docker compose down
```

```bash
docker compose --profile build build --no-cache upstream-base
```

```bash
docker compose build --no-cache gateway dashboard
```

```bash
docker compose up -d
```

`./hermes-data/` survives `docker compose down`, and it survives `docker compose down -v` too. `-v` removes named volumes, and this fork uses none: `/opt/data` is a bind mount from the repo, so `-v` never touches it. To get a true zero-state you would have to delete files under `./hermes-data/` yourself on the host, which is destructive and irreversible, and would also delete the tracked config, persona, cron jobs, memories and project workspaces that live in the same directory. If you want a clean runtime without losing those, delete only the untracked parts, from inside `hermes-data/` itself: it is its own git repository now, so a `git clean` run from the fork's repo root skips it as a nested repository instead of entering it. `cd hermes-data && git clean -xdf` removes exactly what `hermes-data/.gitignore` excludes and leaves the tracked files alone. Check what it would remove first with `git clean -xdn`, run from the same directory.

### Adding a new credential

Append to `.env` (host repo root):

```
NEW_API_KEY=value
```

Add a passthrough line in `docker-compose.override.yml` under `gateway.environment:`:

```yaml
- NEW_API_KEY=${NEW_API_KEY}
```

Recreate the gateway so it picks up the new env passthrough:

```bash
docker compose up -d --force-recreate gateway
```

### Adding a new user-authored skill

Drop a new folder under `.agents/skills/` with a `SKILL.md` (YAML frontmatter: `name`, `description`, optional `version`, `metadata.hermes.tags`). For new skills that exist upstream in `Lukk17/agent-standards/.agents/skills/` but not locally, use the `git archive` snippet in `fork/NOTE-6-minipc-proxmox.md` to copy just that skill from agent-standards.

The container reads `.agents/skills/` from `/opt/data/external-skills/` (read-only bind mount). `hermes-data/config.yaml` already lists `/opt/data/external-skills` in `skills.external_dirs`. The skill appears in the next session. Force a rescan without restarting:

```bash
docker compose exec gateway hermes skills reload
```

### Hermes cannot rewrite config.yaml, by design

`hermes tools`, `hermes setup`, and the `/skin` and `/model` slash commands write `config.yaml` back out through a YAML dump that strips every comment and every key still sitting at its default value. That used to silently shorten the tracked config. It cannot happen now: `docker-compose.override.yml` re-mounts `./hermes-data/config.yaml` at `/opt/data/config.yaml` read-only on top of the read-write parent mount, so any in-container write to it fails. The same override sets `HERMES_SKIP_CONFIG_MIGRATION=1`, because the boot-time schema migration writes the file plus a `.bak-` copy beside it and both are impossible under that mount.

The consequence to internalise: config.yaml only ever changes when you change it on your machine.

### Changing config, for example switching LLM providers

Edit `./hermes-data/config.yaml` on the host:

```yaml
model:
  default: MiniMax-M3
  provider: minimax
```

Then recreate, because the file is read once at startup and is read-only inside the container:

```bash
docker compose up -d --force-recreate gateway dashboard
```

`hermes model` and `hermes tools` inside the container will not work for this, for the reason above. The file is tracked in `hermes-data`'s own git repository, so `git diff config.yaml`, run from inside `hermes-data/`, always shows exactly what you changed before you commit it there.

### Re-running OAuth login

If MiniMax or Anthropic OAuth fails with `refresh_token_reused`, `invalid_grant`, or "not logged in":

```bash
docker compose exec -it gateway hermes auth add minimax-oauth --no-browser
```

```bash
docker compose exec -it gateway hermes auth add anthropic --type oauth
```

### Backing up

Config, persona, cron jobs, memories and project workspaces are tracked in `hermes-data`'s own git repository (a clone of the private `hermes-projects`), so committing and pushing from inside `hermes-data/` is the backup for those, and it is also how they reach another machine. See the last section of `FORK.md`.

What git does not cover is the untracked half of `./hermes-data/`: `state.db` and `sessions/` (conversation history), `auth.json` (OAuth tokens), `kanban.db`, `.env`, and the logs. One copy of the whole directory catches both halves.

This is one of the few commands with no shared form, because the copy tool differs per platform.

PowerShell on Windows:

```powershell
robocopy .\hermes-data .\hermes-data-backup /MIR
```

Unix shell on Linux or macOS:

```bash
rsync -a --delete ./hermes-data/ ./hermes-data-backup/
```

Take the copy with the containers stopped if you want a consistent `state.db`. SQLite write-ahead log files (`state.db-wal`, `state.db-shm`) are live while the gateway runs.

### Run the CLI as `hermes`, never by absolute path

`docker compose exec` enters the container as **root**. `/opt/hermes/bin/hermes` is a privilege-drop shim (`docker/hermes-exec-shim.sh`) that upstream puts first on `PATH` deliberately: invoked as root it drops to the `hermes` user (uid 10000) via `s6-setuidgid`, exports `HOME=/opt/data`, then execs the real venv binary. Calling `/opt/hermes/.venv/bin/hermes` directly skips all of that and runs as root, so every file it writes under `/opt/data` lands root-owned and unreadable to the supervised gateway. The damage is not always `auth.json`: with the shim bypassed `$HOME` stays `/root`, so any library resolving paths off `$HOME` (XDG caches, lockfiles, `.config` writes) misbehaves too.

If you genuinely need root semantics, for example to inspect root-only state, set `HERMES_DOCKER_EXEC_AS_ROOT=1` rather than reaching for the absolute path. That is the supported opt-out and it keeps the intent visible.

### Any credential a hermes CHILD process needs belongs in `hermes-data/.env`

Compose passthrough is not enough on its own. Hermes strips provider and messaging credentials from the environment of every subprocess it spawns, which covers cron scripts and agent terminal calls alike. The blocklist is built at `tools/environments/local.py:338` from the provider registry plus every `OPTIONAL_ENV_VARS` entry in the `tool` or `messaging` category.

Against this fork's actual passthrough that strips exactly two of 21 keys, `DISCORD_BOT_TOKEN` and `MINIMAX_API_KEY`. All nineteen others, including every OSINT and collector key, survive. So a pipeline that shells out to `hermes send` or `hermes -z` cannot see those two unless they are also in `hermes-data/.env`, which every hermes child loads at startup (`hermes_cli/env_loader.py:500`).

`terminal.env_passthrough` cannot rescue them. `tools/env_passthrough.py:113` refuses to register anything matching `_is_hermes_provider_credential`, citing a published advisory.

Both the repo-root `.env` and `hermes-data/.env` are gitignored, so this is not a secrets-in-git question. It is about which process actually gets to read the value.

### Troubleshooting checklist

| Symptom | First thing to check |
|---|---|
| Dashboard unreachable on `http://localhost:9119` | `docker compose ps` shows dashboard running; check `docker compose logs dashboard` for bind errors |
| Dashboard chat tab missing | Not a flag problem. The embedded chat surface is always on; `--tui` is an accepted-and-ignored compat shim and adding it changes nothing. Check `docker compose logs dashboard` for a failed UI build instead |
| `TUI build failed ... permission denied` | `Dockerfile.fork` not applied, rebuild with `docker compose build dashboard` |
| Bot offline, gateway log shows `discord.errors.PrivilegedIntentsRequired` | Privileged Gateway Intents not enabled in the Discord Developer Portal `Bot` tab. Enable `Message Content Intent` and `Server Members Intent`, Save changes, recreate the gateway |
| Bot online but silent in Discord | Message Content Intent disabled (legacy failure mode) |
| `Unauthorized user` in gateway logs | `GATEWAY_ALLOW_ALL_USERS=true` not set, or fill `DISCORD_ALLOWED_USERS` |
| `hermes doctor` reports auth missing | Re-run the OAuth flow for that provider |
| `host.docker.internal` not resolving | Already handled by `extra_hosts` in the override; check Docker version supports `host-gateway` |
| `.agents/skills/` content not visible to hermes | `hermes-data/config.yaml` missing `skills.external_dirs`, or the gateway not recreated after that edit. Config is read-only in the container, so a config change always needs a recreate |
| New env value not in container | Recreate the service: `docker compose up -d --force-recreate gateway` |
| Cron job not firing | `hermes cron list` does not show the job, or job is `enabled: false`. Check `hermes-data/cron/jobs.json` on the host, which is the same file the container reads at `/opt/data/cron/jobs.json`. It is writable at runtime, so no recreate is needed after editing it |
| Cron job reports `last_status: ok` every day but its data is stale | The job's `script` path resolves outside `/opt/data/scripts`, so it is blocked at every fire. `cron/scheduler.py:4296` emits `Blocked: script path resolves outside the scripts directory (/opt/data/scripts):` and `cron/scheduler.py:4568` folds that into the prompt under a `## Script Error` heading and runs the agent anyway. The agent turn succeeds, so the job is recorded green while the script never ran. Fix the path, not the job. The same swallow has a second entrance: a script that runs and exits non-zero (`Script exited with code 5`) was also reported `ok` whenever the agent turn after it succeeded. Setting `no_agent: true` closes that second route, because then the script's exit code is the only signal |
| Cron script fails with `Platform 'discord' is not configured. Set up credentials in ~/.hermes/config.yaml or environment variables.` | The credential is in the compose passthrough but not in `hermes-data/.env`, so it is stripped from the child process. `DISCORD_BOT_TOKEN` and `MINIMAX_API_KEY` are the two keys this fork passes that hermes strips from subprocesses. Add them to `hermes-data/.env` as well. See "Any credential a hermes CHILD process needs" above |
| Channel not responding | The channel ID is missing from `discord.free_response_channels` and `discord.allowed_channels` in `hermes-data/config.yaml` |
| Dashboard not finding skills mounts | Dashboard intentionally does not mount skills (only the gateway needs them). Behavior is expected, no action needed |
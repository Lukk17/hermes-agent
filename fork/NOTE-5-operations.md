Day-to-day operations against a working Hermes Agent install. Assumes fork/NOTE-1-install.md has been followed and containers are up.

### Container lifecycle

Start everything in the background:

```powershell
docker compose up -d
```

Stop everything (containers removed, volumes kept):

```powershell
docker compose down
```

Stop without removing containers (faster restart):

```powershell
docker compose stop
```

Bring stopped containers back without rebuilding:

```powershell
docker compose start
```

Restart a single service:

```powershell
docker compose restart gateway
docker compose restart dashboard
```

Recreate a service (forces re-read of env, override, and command changes):

```powershell
docker compose up -d --force-recreate gateway
```

For changes inside `./fork/hermes-config/` (SOUL.md, config.yaml, cron/jobs.json) or `./fork/projects/`, this is required. The new bind mounts and overrides only apply to a freshly created container, not to a restarted one.

### Logs

```powershell
docker compose logs -f gateway
docker compose logs --tail 50 dashboard
```

The persistent gateway log is at `hermes-data/logs/gateway.log` (host path). It survives container recreation.

### Container shell

`docker compose exec` runs against the already-running container. It does not spawn a new one.

Interactive Hermes CLI inside the gateway:

```powershell
docker compose exec -it gateway hermes
```

Raw bash shell:

```powershell
docker compose exec -it gateway bash
```

One-off Hermes subcommands:

```powershell
docker compose exec gateway hermes doctor
docker compose exec gateway hermes skills list
docker compose exec gateway hermes cron list
```

### Build order

`Dockerfile.fork` takes a `BASE_IMAGE` build arg, defaulting to `hermes-agent:upstream`. That tag is produced by the build-only `upstream-base` service, which builds the untouched upstream `Dockerfile`. Build it first:

```powershell
docker compose --profile build build upstream-base
```

After that, `gateway` and `dashboard` both build from `Dockerfile.fork` on top of that base and are independent of each other, so their order does not matter.

### Updating to the latest upstream

See `fork/NOTE-7-updating-from-upstream.md` for the full procedure. Short form:

```powershell
git fetch upstream --tags
git checkout master
git rebase v<TAG>
docker compose --profile build build upstream-base
docker compose build gateway
docker compose build dashboard
docker compose up -d --force-recreate gateway dashboard
```

### Full clean rebuild (clear start)

```powershell
docker compose down
docker compose --profile build build --no-cache upstream-base
docker compose build --no-cache gateway
docker compose build --no-cache dashboard
docker compose up -d
```

`./hermes-data/` (runtime state) and `./fork/hermes-config/` (tracked config) both survive `docker compose down`, and they survive `docker compose down -v` too. `-v` removes named volumes; both of those are BIND mounts from the repo, so `-v` never touches them. To get a true zero-state you have to delete `./hermes-data/` yourself on the host, which is destructive and irreversible.

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

```powershell
docker compose up -d --force-recreate gateway
```

### Adding a new user-authored skill

Drop a new folder under `.agents/skills/` with a `SKILL.md` (YAML frontmatter: `name`, `description`, optional `version`, `metadata.hermes.tags`). For new skills that exist upstream in `Lukk17/agent-standards/.agents/skills/` but not locally, use the `git archive` snippet in `fork/NOTE-6-minipc-proxmox.md` to copy just that skill from agent-standards.

The container reads `.agents/skills/` from `/opt/external-skills/` (read-only bind mount). `fork/hermes-config/config.yaml` already lists `/opt/external-skills` in `skills.external_dirs`. The skill appears in the next session. Force a rescan without restarting:

```powershell
docker compose exec gateway hermes skills reload
```

### Do not let hermes rewrite config.yaml

`hermes tools`, `hermes setup`, and the `/skin` and `/model` slash commands write `config.yaml` back out through a YAML dump. That dump strips every comment and every key still sitting at its default value, so running any of them inside the container silently rewrites `fork/hermes-config/config.yaml` (it is bind-mounted at `/opt/data/config.yaml`) into a shorter, comment-free file. Edit the file on the host instead, then recreate the gateway. If one of them has already run, `git diff fork/hermes-config/config.yaml` shows exactly what was dropped.

### Switching LLM providers

Edit `fork/hermes-config/config.yaml` on the host:

```yaml
model:
  default: MiniMax-M3
  provider: minimax
```

Then `docker compose up -d --force-recreate gateway`. Do NOT use `hermes model` inside the container for this: see the warning above.

### Re-running OAuth login

If MiniMax or Anthropic OAuth fails with `refresh_token_reused`, `invalid_grant`, or "not logged in":

```powershell
docker compose exec -it gateway hermes auth add minimax-oauth --no-browser
docker compose exec -it gateway hermes auth add anthropic --type oauth
```

### Backing up runtime state

State lives in `./hermes-data/` on the host. Config that the fork owns lives in `./fork/hermes-config/`. Both are worth backing up separately.

Windows (dev box):

```powershell
robocopy .\hermes-data .\hermes-data-backup /MIR
robocopy .\fork\hermes-config .\fork\hermes-config-backup /MIR
```

Linux (minipc):

```bash
rsync -a --delete ./hermes-data/ ./hermes-data-backup/
rsync -a --delete ./fork/hermes-config/ ./fork-hermes-config-backup/
```

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
| `.agents/skills/` content not visible to hermes | `fork/hermes-config/config.yaml` missing `skills.external_dirs`, or services not recreated after the edit |
| New env value not in container | Recreate the service: `docker compose up -d --force-recreate gateway` |
| Cron job not firing | `hermes cron list` does not show the job, or job is `enabled: false`. Verify `hermes-data/cron/jobs.json` (mounted from `fork/hermes-config/cron/jobs.json`) and recreate the gateway |
| Cron job reports `last_status: ok` every day but its data is stale | The job's `script` path resolves outside `/opt/data/scripts`, so it is blocked at every fire. `cron/scheduler.py:4296` emits `Blocked: script path resolves outside the scripts directory (/opt/data/scripts):` and `cron/scheduler.py:4568` folds that into the prompt under a `## Script Error` heading and runs the agent anyway. The agent turn succeeds, so the job is recorded green while the script never ran. Fix the path, not the job. The same swallow has a second entrance: a script that runs and exits non-zero (`Script exited with code 5`) was also reported `ok` whenever the agent turn after it succeeded. Setting `no_agent: true` closes that second route, because then the script's exit code is the only signal |
| Cron script fails with `Platform 'discord' is not configured. Set up credentials in ~/.hermes/config.yaml or environment variables.` | The credential is in the compose passthrough but not in `hermes-data/.env`, so it is stripped from the child process. `DISCORD_BOT_TOKEN` and `MINIMAX_API_KEY` are the two keys this fork passes that hermes strips from subprocesses. Add them to `hermes-data/.env` as well. See "Any credential a hermes CHILD process needs" above |
| Channel not responding | The channel ID is missing from `discord.free_response_channels` and `discord.allowed_channels` in `fork/hermes-config/config.yaml` |
| Dashboard not finding skills mounts | Dashboard intentionally does not mount skills (only the gateway needs them). Behavior is expected, no action needed |
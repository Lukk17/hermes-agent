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
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes
```

Raw bash shell:

```powershell
docker compose exec -it gateway bash
```

One-off Hermes subcommands:

```powershell
docker compose exec gateway /opt/hermes/.venv/bin/hermes doctor
docker compose exec gateway /opt/hermes/.venv/bin/hermes skills list
docker compose exec gateway /opt/hermes/.venv/bin/hermes cron list
```

### Build order

`Dockerfile.fork` does `FROM hermes-agent:fork`, so gateway's build must finish before dashboard's starts. Compose builds services in parallel by default, so always build gateway first, dashboard second.

### Updating to the latest upstream

See `fork/NOTE-7-updating-from-upstream.md` for the full procedure. Short form:

```powershell
git fetch upstream --tags
git checkout master
git rebase v<TAG>
docker compose build gateway
docker compose build dashboard
docker compose up -d --force-recreate gateway dashboard
```

### Full clean rebuild (clear start)

```powershell
docker compose down
docker compose build --no-cache gateway
docker compose build --no-cache dashboard
docker compose up -d
```

`./hermes-data/` (runtime state) and `./fork/hermes-config/` (tracked config) both survive `docker compose down`. To wipe `hermes-data/` too, add `-v` to `down`. Destructive, only do this if you want a true zero-state.

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
docker compose exec gateway /opt/hermes/.venv/bin/hermes skills reload
```

### Switching LLM providers

```powershell
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes model
```

Or set explicitly in `fork/hermes-config/config.yaml`:

```yaml
model:
  default: MiniMax-M3
  provider: minimax
```

Then `docker compose up -d --force-recreate gateway`.

### Re-running OAuth login

If MiniMax or Anthropic OAuth fails with `refresh_token_reused`, `invalid_grant`, or "not logged in":

```powershell
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes auth add minimax-oauth --no-browser
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes auth add anthropic --type oauth
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

### Troubleshooting checklist

| Symptom | First thing to check |
|---|---|
| Dashboard unreachable on `http://localhost:9119` | `docker compose ps` shows dashboard running; check `docker compose logs dashboard` for bind errors |
| Dashboard chat tab missing | `--tui` flag missing from the dashboard command in the override |
| `TUI build failed ... permission denied` | `Dockerfile.fork` not applied, rebuild with `docker compose build dashboard` |
| Bot offline, gateway log shows `discord.errors.PrivilegedIntentsRequired` | Privileged Gateway Intents not enabled in the Discord Developer Portal `Bot` tab. Enable `Message Content Intent` and `Server Members Intent`, Save changes, recreate the gateway |
| Bot online but silent in Discord | Message Content Intent disabled (legacy failure mode) |
| `Unauthorized user` in gateway logs | `GATEWAY_ALLOW_ALL_USERS=true` not set, or fill `DISCORD_ALLOWED_USERS` |
| `hermes doctor` reports auth missing | Re-run the OAuth flow for that provider |
| `host.docker.internal` not resolving | Already handled by `extra_hosts` in the override; check Docker version supports `host-gateway` |
| `.agents/skills/` content not visible to hermes | `fork/hermes-config/config.yaml` missing `skills.external_dirs`, or services not recreated after the edit |
| New env value not in container | Recreate the service: `docker compose up -d --force-recreate gateway` |
| Cron job not firing | `hermes cron list` does not show the job, or job is `enabled: false`. Verify `hermes-data/cron/jobs.json` (mounted from `fork/hermes-config/cron/jobs.json`) and recreate the gateway |
| Channel not responding | The channel ID is missing from `discord.free_response_channels` and `discord.allowed_channels` in `fork/hermes-config/config.yaml` |
| Dashboard not finding skills mounts | Dashboard intentionally does not mount skills (only the gateway needs them). Behavior is expected, no action needed |
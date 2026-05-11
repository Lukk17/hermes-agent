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

### Logs

```powershell
docker compose logs -f gateway
docker compose logs --tail 50 dashboard
```

### Container shell

`docker compose exec` runs against the already-running container — it does not spawn a new one.

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
```

### Build order

`Dockerfile.fork` does `FROM hermes-agent:fork`, so gateway's build must finish before dashboard's starts. Compose builds services in parallel by default, so always build gateway first, dashboard second.

### Updating to the latest upstream

```powershell
git pull upstream master
docker compose build gateway
docker compose build dashboard
docker compose up -d
```

### Full clean rebuild (clear start)

```powershell
docker compose down
docker compose build --no-cache gateway
docker compose build --no-cache dashboard
docker compose up -d
```

`./hermes-data/` (config, sessions, credentials) survives `docker compose down`. To wipe that too, add `-v` to `down` and delete `./hermes-data/` manually — destructive, only do this if you want a true zero-state.

### Adding a new credential

Append to `.env`:

```
NEW_API_KEY=value
```

Add a passthrough line in `docker-compose.override.yml` under `gateway.environment:`:

```yaml
- NEW_API_KEY=${NEW_API_KEY}
```

Recreate the gateway:

```powershell
docker compose up -d --force-recreate gateway
```

### Adding a new user-authored skill

Drop a new folder under `my-skills/` with a `SKILL.md` (YAML frontmatter: `name`, `description`, optional `version`, `metadata.hermes.tags`).

Hermes scans `external_dirs` on session start, so the new skill appears in the next session. Force a rescan without restarting:

```powershell
docker compose exec gateway /opt/hermes/.venv/bin/hermes skills reload
```

### Switching LLM providers

```powershell
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes model
```

Or set explicitly:

```powershell
docker compose exec gateway /opt/hermes/.venv/bin/hermes config set provider <provider-id>
docker compose exec gateway /opt/hermes/.venv/bin/hermes config set model <model-name>
```

### Re-running OAuth login

If MiniMax or Anthropic OAuth fails with `refresh_token_reused`, `invalid_grant`, or "not logged in":

```powershell
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes auth add minimax-oauth --no-browser
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes auth add anthropic --type oauth
```

### Backing up the data directory

State lives in `./hermes-data/` on the host:

```powershell
robocopy .\hermes-data .\hermes-data-backup /MIR
```

Linux:

```bash
rsync -a --delete ./hermes-data/ ./hermes-data-backup/
```

### Troubleshooting checklist

| Symptom | First thing to check |
|---|---|
| Dashboard unreachable on `http://localhost:9119` | `docker compose ps` shows dashboard running; check `docker compose logs dashboard` for bind errors |
| Dashboard chat tab missing | `--tui` flag missing from the dashboard command in the override |
| `TUI build failed ... permission denied` | `Dockerfile.fork` not applied — rebuild with `docker compose build dashboard` |
| Bot online but silent in Discord | Message Content Intent disabled in the Discord Developer Portal |
| `Unauthorized user` in gateway logs | `GATEWAY_ALLOW_ALL_USERS=true` not set, or fill `DISCORD_ALLOWED_USERS` |
| `hermes doctor` reports auth missing | Re-run the OAuth flow for that provider |
| `host.docker.internal` not resolving | Already handled by `extra_hosts` in the override; check Docker version supports `host-gateway` |
| `my-skills/` content not visible | `skills.external_dirs` not in `./hermes-data/config.yaml`, or services not restarted after the edit |
| New env value not in container | Recreate the service: `docker compose up -d --force-recreate gateway` |

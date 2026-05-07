# Note 1 — Hermes Agent fork: what we configured and how to run it

This is a customized fork of `NousResearch/hermes-agent`. All customization sits in **net-new files** so upstream merges stay clean. Upstream files (`docker-compose.yml`, `Dockerfile`, `README.md`) are not modified.

## Files added by the fork

| File | Purpose |
|---|---|
| `docker-compose.override.yml` | Compose auto-merges this on top of upstream `docker-compose.yml` on every `docker compose up`. Adds: skills mount, env passthrough for messaging tokens and skill API keys, `host.docker.internal` for Linux Docker, dashboard bind override. |
| `.env` | Local-only secrets and tokens, gitignored. Loaded automatically by Compose. |
| `.env.my.example` | Template for `.env`, committed. Copy to `.env` and fill values. |
| `my-skills/` | Fork-authored skills. Each subfolder has a `SKILL.md` with YAML frontmatter (`name`, `description`, optional `version`, `metadata.hermes.tags`). |
| `FORK.md` | What the fork adds and why. |
| `SETUP.md` | Full setup walkthrough. |

## How the skills mount works

```
./my-skills  ->  /opt/data/external-skills   (read-only)
```

Mounted **outside** the local `~/.hermes/skills/` tree. Hermes picks it up via the first-class `skills.external_dirs` config option (`agent/skill_utils.py:174`). Read-only on purpose: user-authored skills are source of truth and the agent must not mutate them. Agent-created skills continue to land in writable `~/.hermes/skills/` on the host.

**One-time config required** in `~/.hermes/config.yaml` (Windows: `C:\Users\<you>\.hermes\config.yaml`):

```yaml
skills:
  external_dirs:
    - /opt/data/external-skills
```

## How credentials wiring works

1. `.env` (next to `docker-compose.yml`) holds raw values. Gitignored.
2. `docker-compose.override.yml` references each var as `${VAR}` under `gateway.environment:`.
3. On `docker compose up`, Compose reads `.env`, substitutes values, starts the container with those env vars set. Hermes and skills read them via `os.getenv` at runtime.

Variables wired in:

- **Discord**: `DISCORD_BOT_TOKEN`, `DISCORD_ALLOWED_USERS` (empty = allow all), `DISCORD_HOME_CHANNEL`, `DISCORD_REQUIRE_MENTION`
- **Telegram**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS` (empty = allow all)
- **Blockchain**: `BLOCKSCOUT_API_KEY`, `ALCHEMY_API_KEY`, `CRYPTOPANIC_API_KEY`
- **Gmail OAuth client** (refresh token NOT here, it lives in `~/.hermes/credentials/google_token.json` after first OAuth): `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`
- **OSINT / threat-intel**: `HUNTER_API_KEY`, `ABSTRACT_API_KEY`, `EMAILREP_API_KEY`, `NUMVERIFY_API_KEY`, `VIRUSTOTAL_API_KEY`, `URLSCAN_API_KEY`, `OTX_API_KEY`, `ABUSEIPDB_API_KEY`, `CENSYS_API_KEY`, `IPQS_API_KEY`, `DEHASHED_API_KEY`, `BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY`
- **Local services**: `ASCEND_SCRAPPER_URL=http://host.docker.internal:7021/api/v2/web/read`

Adding a new credential: append `NEW_VAR=value` to `.env`, add `- NEW_VAR=${NEW_VAR}` under `gateway.environment:` in the override, then `docker compose up -d`.

## First-run sequence

```powershell
# 1. Bring services up
docker compose up -d
docker compose logs -f gateway

# 2. Configure LLM provider, see NOTE-2 (MiniMax / Claude)

# 3. Add skills.external_dirs to ~/.hermes/config.yaml (snippet above)

# 4. Restart so config takes effect
docker compose restart gateway dashboard

# 5. Verify
docker compose exec gateway hermes doctor
docker compose exec gateway hermes skills list
docker compose exec gateway ls /opt/data/external-skills

# 6. Talk to it
# - Discord: DM the bot
# - CLI: docker compose exec -it gateway hermes
# - Web dashboard: http://127.0.0.1:9119
```

## Day-2 ops

```powershell
git pull upstream master            # sync upstream
docker compose build
docker compose up -d                # apply

docker compose logs -f gateway      # tail logs
docker compose exec -it gateway bash  # shell into container
```

## What lives where

| Location | What |
|---|---|
| `./my-skills/` | Fork skills (read-only mount) |
| `./.env` | Compose-time secrets, gitignored |
| `~/.hermes/config.yaml` | Hermes runtime config (model, provider, skills.external_dirs) |
| `~/.hermes/auth.json` | OAuth tokens (MiniMax, Anthropic, Google), refreshable |
| `~/.hermes/credentials/` | Skill credential files (e.g. `google_token.json`) |
| `~/.hermes/sessions/` | Conversation history |
| `~/.hermes/skills/` | Local + agent-created skills |

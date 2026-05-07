# Fork customization

This fork keeps all local customization in net-new files so that future merges
of upstream NousResearch/hermes-agent stay clean. Upstream files
(`docker-compose.yml`, `Dockerfile`, `README.md`, etc.) are intentionally
untouched.

## What is added by this fork

| File | Purpose |
|------|---------|
| `docker-compose.override.yml` | Mounts `./my-skills` into the gateway and dashboard containers and passes through messaging and skill API credentials from `.env`. |
| `.env` | Local-only secrets and tokens. Gitignored. Loaded automatically by Docker Compose for variable substitution in `docker-compose.override.yml`. |
| `my-skills/` | Fork-authored skill folders. Each subdirectory should contain a `SKILL.md` with proper YAML frontmatter (`name`, `description`, optional `version`, `metadata.hermes.tags`). |
| `FORK.md` | This document. |

## How the skills mount works

Compose merges `docker-compose.override.yml` on top of `docker-compose.yml`
on every `docker compose up`. No flags needed. The merge adds a read-only
bind mount on both services:

```
./my-skills  ->  /opt/data/external-skills   (read-only)
```

The mount sits **outside** the local `~/.hermes/skills/` tree. Hermes picks
external locations up via the first-class `skills.external_dirs` config
option (see `agent/skill_utils.py:174`), which is the officially supported
extension point for fork-authored skill bundles.

### One-time config

After your first `docker compose up` (which creates `~/.hermes/`), add this
to `~/.hermes/config.yaml` on the host:

```yaml
skills:
  external_dirs:
    - /opt/data/external-skills
```

That tells Hermes to scan that path **in addition to** `~/.hermes/skills/`.
Both `gateway` and `dashboard` read the same `~/.hermes/config.yaml` (it
lives inside the bind-mounted `~/.hermes` volume), so a single config edit
covers both services.

The mount is read-only on purpose: user-authored skills are source of truth
and the agent must not mutate them. Skills the agent creates itself continue
to land in the writable `~/.hermes/skills/` location on the host. On a name
collision, the local skill wins — that matches upstream's resolution order.

## How the credentials wiring works

1. `.env` (next to `docker-compose.yml`) holds raw values. It is gitignored.
2. `docker-compose.override.yml` references each variable by name with
   `${VAR}` substitution under the gateway service's `environment:` block.
3. On `docker compose up`, Compose reads `.env`, substitutes the values into
   the merged compose config, and starts the container with those env vars
   set. Hermes and its skills read them via `os.getenv` at runtime.

Variables wired in:

- **Discord**: `DISCORD_BOT_TOKEN`, `DISCORD_ALLOWED_USERS`,
  `DISCORD_HOME_CHANNEL`, `DISCORD_REQUIRE_MENTION`
- **Telegram**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`
- **Blockchain**: `BLOCKSCOUT_API_KEY`, `ALCHEMY_API_KEY`, `CRYPTOPANIC_API_KEY`
- **Gmail OAuth**: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`
- **OSINT / threat-intel**: `HUNTER_API_KEY`, `ABSTRACT_API_KEY`,
  `EMAILREP_API_KEY`, `NUMVERIFY_API_KEY`, `VIRUSTOTAL_API_KEY`,
  `URLSCAN_API_KEY`, `OTX_API_KEY`, `ABUSEIPDB_API_KEY`, `CENSYS_API_KEY`,
  `IPQS_API_KEY`, `DEHASHED_API_KEY`, `BREACHDIRECTORY_VIA_RAPIDAPI_API_KEY`

To add another secret, append a line to `.env` and add a matching
`- VAR=${VAR}` line under `gateway.environment:` in
`docker-compose.override.yml`.

## Discord setup checklist

The fork wires up the Discord token but you still have to do the Discord
Developer Portal work yourself:

1. Create an application at https://discord.com/developers/applications
2. Add a bot user. Enable **Message Content Intent** and
   **Server Members Intent** (without these the bot will be online but
   silent).
3. Copy the bot token into `.env` as `DISCORD_BOT_TOKEN`.
4. Get your Discord user ID (Settings -> Advanced -> Developer Mode, then
   right-click your name -> Copy User ID) and put it in
   `DISCORD_ALLOWED_USERS`. Without this the gateway denies all users.
5. Generate an invite URL and add the bot to your server.

Full guide: see `website/docs/user-guide/messaging/discord.md` in the repo.

## Bringing it up

```bash
docker compose config       # inspect the merged result
docker compose up -d        # gateway + dashboard come up
docker compose logs -f gateway
```

Verification:

```bash
docker compose exec gateway ls /opt/data/external-skills
docker compose exec gateway hermes skills list
```

The dashboard listens on `127.0.0.1:9119` by default. For remote access,
SSH-tunnel it: `ssh -L 9119:localhost:9119 <host>`.

## What is not in scope for this fork yet

- `SOUL.md`, `USER.md`, `MEMORY.md` bootstrapping. Configure these later via
  the dashboard or `hermes setup`.
- Other messaging platforms (Slack, Matrix, WhatsApp, etc.). Adding any of
  them is a one-line credential addition to `.env` plus matching env
  passthrough in `docker-compose.override.yml`.

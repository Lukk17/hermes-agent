# Setup and run guide (this fork)

This document walks you through bringing up this fork of Hermes Agent on
Docker, plugging in MiniMax (subscription) or Anthropic Claude (Max
subscription) as the LLM provider, and verifying everything is wired up.

For an explanation of *what* this fork adds on top of upstream
NousResearch/hermes-agent, see `FORK.md`.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Compose plugin (Linux).
- A MiniMax account on minimax.io, or a Claude Max subscription with extra
  usage credits, or any other provider supported by Hermes (OpenRouter,
  Gemini, OpenAI, Ollama, etc.).
- Discord bot (already configured for this fork — token in `.env`).

## File map

The fork ships these net-new files. Upstream files are not modified.

| File | What it does |
|------|------|
| `docker-compose.override.yml` | Mounts `./my-skills` as an external skills dir, passes credentials through to the container, adds `host.docker.internal` for Linux Docker. |
| `.env` | Local-only secrets and tokens. Gitignored. Loaded by Compose. |
| `my-skills/` | Fork-authored skills. Discovered via `skills.external_dirs` in `~/.hermes/config.yaml`. |
| `FORK.md` | What the fork adds and why. |
| `SETUP.md` | This file. |

## First run

### 1. Bring services up

```powershell
docker compose up -d
docker compose logs -f gateway
```

This starts:

- `gateway` (container `hermes`): the messaging gateway and agent runtime.
- `dashboard` (container `hermes-dashboard`): a web UI on
  http://127.0.0.1:9119 (localhost-only by default).

The first `up` creates `~/.hermes/` on the host (Windows path:
`C:\Users\Lukk\.hermes\`). That directory is the persistent state for the
agent — sessions, skills, credentials, config, logs.

### 2. Configure the LLM provider

Pick **one** of the paths below. You can add more providers later via
`hermes model`.

#### Path A: MiniMax (browser OAuth, recommended)

Your MiniMax subscription works directly through Hermes' first-class
`minimax-oauth` provider. No API key, no credit card, no env var.

The container has no browser, so use the device-code flow:

```powershell
docker compose exec -it gateway hermes auth add minimax-oauth --no-browser
```

Hermes prints a verification URL and a short user code. Open the URL on
any device with a browser, sign in to MiniMax, paste the code, approve.
The container polls and stores tokens in `~/.hermes/auth.json`.

Then set MiniMax as the default model:

```powershell
docker compose exec -it gateway hermes config set provider minimax-oauth
docker compose exec -it gateway hermes config set model MiniMax-M2.7
```

China region: append `--region cn` to the auth command.

Refresh is automatic (Hermes refreshes the access token at every session
start when it is within 60 seconds of expiry).

#### Path B: Claude (Anthropic OAuth via Claude Max subscription)

Hermes can route through your Claude Max subscription using Anthropic
OAuth (the same backing flow Claude Code uses). Requirements:

- A **Claude Max** plan (Pro is not enough).
- **Extra usage credits** purchased on top of the Max plan. The base Max
  allowance bundled with Claude Code is **not** consumed by Hermes — only
  the extra/overage credits you have explicitly added on top are.

If you do not have Max + extra credits, use a normal `ANTHROPIC_API_KEY`
instead (pay per token, billed against the API org — see Path C).

```powershell
docker compose exec -it gateway hermes auth add anthropic --type oauth
```

Same device-code flow as MiniMax: open the URL on any device, sign in to
Anthropic, approve. Tokens are stored in Hermes' credential store
(refreshable). Then:

```powershell
docker compose exec -it gateway hermes config set provider anthropic
docker compose exec -it gateway hermes config set model claude-sonnet-4-6
```

If you already have Claude Code installed locally and authenticated,
Hermes auto-detects its credential files when the gateway runs with a
shared `~/.hermes` and falls back to them. With this Dockerized setup,
running the explicit `hermes auth add anthropic --type oauth` inside the
container is the cleanest path.

#### Path C: Anthropic API key (pay-per-token)

Add to `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Add to `docker-compose.override.yml` under `gateway.environment:`:

```yaml
- ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

Then `docker compose up -d` to apply. Set the provider:

```powershell
docker compose exec -it gateway hermes config set provider anthropic
docker compose exec -it gateway hermes config set model claude-sonnet-4-6
```

#### Path D: OpenRouter (one key, many models)

Same as Path C with `OPENROUTER_API_KEY` instead.

### 3. Enable fork-authored skills

Edit `~/.hermes/config.yaml` (Windows: `C:\Users\Lukk\.hermes\config.yaml`)
and add:

```yaml
skills:
  external_dirs:
    - /opt/data/external-skills
```

This tells Hermes to scan `my-skills/` (mounted at
`/opt/data/external-skills` inside the container) in addition to the
default `~/.hermes/skills/` location.

### 4. Restart so config and auth take effect

```powershell
docker compose restart gateway dashboard
```

### 5. Verify

```powershell
docker compose exec gateway hermes doctor
docker compose exec gateway hermes skills list
docker compose exec gateway ls /opt/data/external-skills
docker compose logs gateway --tail 50
```

`hermes doctor` should show:

- `Auth Providers`: a checkmark on whichever provider you configured
  (MiniMax OAuth / Anthropic OAuth / etc.)
- `Discord` and `Telegram` lines indicating the gateway connected to the
  bot APIs (assuming the tokens in `.env` are valid)

`hermes skills list` should include the entries from `my-skills/`.

`docker compose logs gateway --tail 50` is your friend if anything looks
off — connection failures, missing config, bad tokens, all surface there.

### 6. Talk to the agent

- **Discord**: DM your bot, or @mention it in a channel where the bot
  has access. Allowed-users list is empty, so anyone the bot can see can
  chat with it.
- **Telegram**: message your bot directly.
- **CLI inside the container**:
  ```powershell
  docker compose exec -it gateway hermes
  ```
- **Web dashboard**: http://127.0.0.1:9119 — provides a chat UI,
  configuration, skills browser, sessions list, and credentials manager.
  Localhost only; for remote access tunnel via SSH:
  `ssh -L 9119:localhost:9119 <host>`.

## Day-2 operations

### Updating

Pull upstream and rebuild:

```powershell
git pull upstream master
docker compose build
docker compose up -d
```

Because all customization is in `docker-compose.override.yml`, `.env`,
`my-skills/`, `FORK.md`, and `SETUP.md`, upstream merges should not
conflict with the fork's customization.

### Logs and shell

```powershell
docker compose logs -f gateway       # gateway runtime logs
docker compose logs -f dashboard     # dashboard process logs
docker compose exec -it gateway bash # shell inside the container
```

### Adding a new credential

1. Add `NEW_VAR=value` to `.env`.
2. Add `- NEW_VAR=${NEW_VAR}` under `gateway.environment:` in
   `docker-compose.override.yml`.
3. `docker compose up -d` to recreate the container with the new env.

### Adding a new skill

Drop a new folder under `my-skills/` containing a `SKILL.md` with proper
YAML frontmatter (`name`, `description`, optional `version`,
`metadata.hermes.tags`). It will be picked up on the next session start —
no restart needed for the gateway, but the in-flight session may need
`/skills reload` or a fresh session to see it.

### Switching providers

```powershell
docker compose exec -it gateway hermes model
```

Pick a different provider from the menu; Hermes runs the wizard to add
credentials if needed.

## What lives where

| Location | What |
|---|---|
| `./my-skills/` (host) | Fork-authored skills, mounted read-only into `/opt/data/external-skills` |
| `./.env` (host) | Compose-time secrets, gitignored |
| `~/.hermes/config.yaml` (host) | Hermes runtime config, including `skills.external_dirs` |
| `~/.hermes/auth.json` (host) | OAuth tokens (MiniMax, Anthropic, Google, etc.) — refreshable, do not commit |
| `~/.hermes/sessions/` (host) | Conversation history |
| `~/.hermes/skills/` (host) | Local skills (agent-created and dashboard-installed) |
| `~/.hermes/credentials/` (host) | Skill credential files such as `google_token.json` |

## Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Discord bot online but does not respond | Privileged intents disabled | Discord Developer Portal → Bot → enable Message Content Intent and Server Members Intent → Save |
| `host.docker.internal` not resolving on Linux | Native Docker Engine without auto-mapping | Already handled by `extra_hosts` in the override file |
| MiniMax auth times out | Did not approve in browser fast enough | Re-run `hermes auth add minimax-oauth --no-browser` |
| Anthropic OAuth refuses with "no extra credits" | Claude Max base allowance only | Buy extra credits, or switch to `ANTHROPIC_API_KEY` (Path C) |
| Skills from `my-skills/` not showing up | `skills.external_dirs` not added to `config.yaml`, or services not restarted | Add the snippet, then `docker compose restart gateway dashboard` |

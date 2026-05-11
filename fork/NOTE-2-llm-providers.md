Hermes Agent supports many LLM providers (OpenRouter, Gemini, OpenAI, Ollama, Anthropic, MiniMax, etc.). Two of them — MiniMax and Anthropic Claude — can be used through a subscription via browser OAuth without any API key.

The web dashboard at `http://localhost:9119` (or via SSH tunnel from another machine — see fork/NOTE-4-secure-remote-access.md) is the recommended path for adding any provider. The CLI inside the container also works but is more awkward in a Dockerized setup because the OAuth flow defaults to opening a browser the container doesn't have. Treat the CLI as a fallback.

### MiniMax via browser OAuth

First-class support, provider ID `minimax-oauth`. No API key, no credit card.

| Field | Value |
|---|---|
| Provider ID | `minimax-oauth` |
| Auth | Browser OAuth, PKCE device-code flow |
| Models | `MiniMax-M2.7`, `MiniMax-M2.7-highspeed` |
| Endpoint, global | `https://api.minimax.io/anthropic` |
| Endpoint, China | `https://api.minimaxi.com/anthropic` |
| Env var needed | None (`MINIMAX_API_KEY` is for the API-key provider only) |
| Token storage | `./hermes-data/auth.json` |

### MiniMax setup via the dashboard

Open the dashboard, go to the providers/models section, click Add Provider, pick MiniMax (OAuth). The dashboard opens MiniMax's authorization page in a new browser tab. Sign in, approve, the dashboard finalizes the flow and stores tokens in `./hermes-data/auth.json` on the host. Then pick MiniMax-M2.7 as the active model.

Tokens auto-refresh at every session start when within 60 seconds of expiry.

### Anthropic Claude via Claude Max subscription

Routes through Anthropic OAuth (the same backing flow Claude Code uses).

Hard requirements:

- Claude Max plan, not Pro.
- Extra usage credits purchased on top of Max. The base Max allowance bundled with Claude Code is not consumed by Hermes — only the extra/overage credits are.

Without Max + extra credits, use a regular `ANTHROPIC_API_KEY` (pay per token, fallback below).

### Anthropic Claude setup via the dashboard

Open the dashboard, Add Provider, pick Anthropic (OAuth). Sign in to Anthropic in the new tab, approve, dashboard stores the refreshable token. Pick a Claude model (e.g. `claude-sonnet-4-6`).

### Anthropic API key fallback (pay-per-token)

For users without a Claude Max + credits subscription. Add to `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Add to `docker-compose.override.yml` under `gateway.environment:`:

```yaml
- ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

Apply the env passthrough:

```powershell
docker compose up -d
```

Then in the dashboard, Add Provider → Anthropic (API key) → it picks up the env var.

### CLI fallback

The `hermes` binary inside the container is at `/opt/hermes/.venv/bin/hermes`, not on the default `PATH`. Prefix all CLI commands with the full path. Also note: running `hermes auth add ...` inside a fresh container can fail with "Not logged into MiniMax OAuth" because the device-code wizard relies on session state from `hermes model`. The dashboard does not have this problem.

If you really want CLI:

Open an interactive Hermes session (this is the supported flow):

```powershell
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes model
```

Pick the provider from the menu, follow the OAuth prompts. For headless/no-browser cases the CLI prints a URL + user code; open them on any device.

For accounts on the China MiniMax platform, the dashboard offers a region selector. CLI equivalent:

```powershell
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes auth add minimax-oauth --no-browser --region cn
```

(Run this from inside `hermes model` first to bootstrap the session, otherwise expect the "Not logged in" error.)

### Switching providers later

Easiest: dashboard, click the active provider, swap.

CLI equivalent:

```powershell
docker compose exec -it gateway /opt/hermes/.venv/bin/hermes model
```

### Verifying

The dashboard's status page shows the active provider and whether auth is healthy. CLI equivalent:

```powershell
docker compose exec gateway /opt/hermes/.venv/bin/hermes doctor
```

The Auth Providers section lists each configured provider with logged-in / not-logged-in state.

### Common errors

| Error | Cause | Fix |
|---|---|---|
| Anthropic OAuth: "no extra credits available" | Only the bundled Max allowance, no overage credits | Buy extra credits, or switch to API key |
| MiniMax/Anthropic: "Authorization timed out" | Did not approve in browser fast enough | Restart the OAuth flow from the dashboard |
| `refresh_token_reused` / `invalid_grant` | Token store corrupted or session reused | Restart the OAuth flow from the dashboard |
| "Not logged into MiniMax OAuth" from `hermes auth add` | CLI device-code flow needs the `hermes model` session bootstrap | Use the dashboard, or start with `hermes model` instead of `hermes auth add` |

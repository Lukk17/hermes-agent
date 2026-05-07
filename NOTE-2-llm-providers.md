# Note 2 — Configuring LLM providers (MiniMax and Claude)

Hermes supports many providers (OpenRouter, Gemini, OpenAI, Ollama, Anthropic, MiniMax, etc.). The two below are subscription-based options that don't require an API key.

## MiniMax (subscription via browser OAuth)

First-class support. Provider ID `minimax-oauth`. No API key, no credit card.

| Field | Value |
|---|---|
| Provider ID | `minimax-oauth` |
| Auth | Browser OAuth (PKCE device-code) |
| Models | `MiniMax-M2.7`, `MiniMax-M2.7-highspeed` |
| Endpoint (global) | `https://api.minimax.io/anthropic` |
| Endpoint (China) | `https://api.minimaxi.com/anthropic` |
| Env var needed | None (`MINIMAX_API_KEY` is for the API-key provider, not OAuth) |
| Token storage | `~/.hermes/auth.json` |

### Setup (Docker, no browser inside container)

Use the device-code flow:

```powershell
docker compose exec -it gateway hermes auth add minimax-oauth --no-browser
```

Hermes prints a URL and a short user code. Open the URL on any device with a browser, sign in to minimax.io, paste the code, approve. The container polls and stores tokens.

China region:

```powershell
docker compose exec -it gateway hermes auth add minimax-oauth --no-browser --region cn
```

Set as default:

```powershell
docker compose exec -it gateway hermes config set provider minimax-oauth
docker compose exec -it gateway hermes config set model MiniMax-M2.7
```

Tokens auto-refresh at every session start when within 60 seconds of expiry.

Verify:

```powershell
docker compose exec gateway hermes doctor
# Look for: ✓ MiniMax OAuth (logged in, region=global)
```

## Claude (Anthropic OAuth via Claude Max subscription)

Hermes can route through your Claude Max subscription using the same OAuth flow Claude Code uses.

**Hard requirements:**

- **Claude Max** plan (Pro is not enough)
- **Extra usage credits purchased on top** of Max. The base Max allowance bundled with Claude Code is **NOT** consumed by Hermes, only the extra/overage credits are.

If you don't have Max + extra credits, use a regular `ANTHROPIC_API_KEY` (pay per token, separate billing, see fallback below).

### Setup (Docker)

```powershell
docker compose exec -it gateway hermes auth add anthropic --type oauth
```

Same device-code flow as MiniMax: URL + code, approve in browser. Tokens stored in Hermes' credential store, refreshable.

Set as default:

```powershell
docker compose exec -it gateway hermes config set provider anthropic
docker compose exec -it gateway hermes config set model claude-sonnet-4-6
```

### Fallback: Anthropic API key (pay-per-token, no subscription)

Add to `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Add to `docker-compose.override.yml` under `gateway.environment:`:

```yaml
- ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

Then:

```powershell
docker compose up -d
docker compose exec -it gateway hermes config set provider anthropic
docker compose exec -it gateway hermes config set model claude-sonnet-4-6
```

## Switching between providers later

```powershell
docker compose exec -it gateway hermes model
```

Pick from the menu; wizard runs the OAuth or key flow as needed.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| Anthropic OAuth: "no extra credits available" | Only the bundled Max allowance, no overage credits purchased | Buy extra credits in your Anthropic account, or switch to API key path |
| MiniMax: "Authorization timed out" | Did not approve in browser fast enough | Re-run `hermes auth add minimax-oauth --no-browser` |
| `refresh_token_reused` / `invalid_grant` | Token store corrupted or session reused | Re-run the `hermes auth add ...` command for that provider |
| "Not logged into MiniMax OAuth" at runtime | Auth file deleted or never created | `hermes auth add minimax-oauth --no-browser` |

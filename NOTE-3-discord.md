# Note 3 — Configuring Discord

Hermes has first-class Discord support. The bot lives at `gateway/platforms/discord.py`. Each Discord message goes through: authorization, mention/free-response check, session lookup, agent execution, reply delivery.

## How the bot behaves

| Context | Behavior |
|---|---|
| **DMs** | Responds to every message. No `@mention` needed. Each DM is its own session. |
| **Server channels** | Only responds to `@mention` by default. Set `DISCORD_REQUIRE_MENTION=false` to respond to every message. |
| **Free-response channels** | List specific channels in `DISCORD_FREE_RESPONSE_CHANNELS` to skip the mention requirement. |
| **Threads** | Replies in the same thread, with isolated session history from parent channel. |
| **Shared channels** | By default each user gets their own session inside a shared channel. Toggle `group_sessions_per_user: false` in `~/.hermes/config.yaml` for one shared transcript. |

## One-time Discord Developer Portal setup

1. https://discord.com/developers/applications then **New Application**, name it.
2. **Bot** tab, bot user is auto-created. Copy/reset the token (only shown once).
3. **Privileged Gateway Intents**, both required, otherwise bot is online but silent:
   - **Server Members Intent** ON
   - **Message Content Intent** ON  (#1 cause of "bot online but doesn't reply")
4. Save changes.
5. **Installation** tab, **Discord Provided Link**, enable scopes: `bot`, `applications.commands`. Permissions integer `274878286912` (View Channels, Send Messages, Read Message History, Attach Files, Embed Links, Send Messages in Threads, Add Reactions).
6. Open the invite URL, pick your server, Authorize.
7. (Optional) In your Discord client: Settings, Advanced, Developer Mode ON. Then right-click the bot in the member list, Copy User ID for any allowlist work.

## Hermes-side configuration

This fork wires Discord through `.env` + `docker-compose.override.yml`. **Allowlist intentionally empty = allow all users.** Hermes treats an empty `DISCORD_ALLOWED_USERS` and empty `DISCORD_ALLOWED_ROLES` as no restriction (verified in `discord.py:2125`).

`.env`:

```bash
DISCORD_BOT_TOKEN=<your-bot-token>
DISCORD_ALLOWED_USERS=
DISCORD_HOME_CHANNEL=
DISCORD_REQUIRE_MENTION=true
```

`docker-compose.override.yml` already has these wired under `gateway.environment:`:

```yaml
- DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
- DISCORD_ALLOWED_USERS=${DISCORD_ALLOWED_USERS}
- DISCORD_HOME_CHANNEL=${DISCORD_HOME_CHANNEL:-}
- DISCORD_REQUIRE_MENTION=${DISCORD_REQUIRE_MENTION:-true}
```

To restrict to specific users later: comma-separate Discord user IDs in `DISCORD_ALLOWED_USERS`.

## Optional configuration

Add to `~/.hermes/config.yaml` if needed:

```yaml
group_sessions_per_user: true   # default. set false for shared channel transcripts.
```

Optional env additions (not currently wired, add to `.env` and override if you use them):

| Variable | Purpose |
|---|---|
| `DISCORD_ALLOWED_ROLES` | Comma-separated role IDs (OR-semantics with allowed users) |
| `DISCORD_FREE_RESPONSE_CHANNELS` | Channel IDs that don't require `@mention` |
| `DISCORD_IGNORE_NO_MENTION` | Default `true`, bot stays silent when others are mentioned but it isn't |
| `DISCORD_COMMAND_SYNC_POLICY` | `safe` (default) / `bulk` / `off` for slash-command startup sync |

## Bring it up

```powershell
docker compose up -d
docker compose logs -f gateway
# Look for Discord login lines: "Logged in as <bot-name>#1234"
```

## Verify

- DM the bot from your Discord account, should reply.
- `@mention` it in a server channel, should reply.
- `docker compose exec gateway hermes doctor`, Discord section should show connected.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Bot online, never replies in channels | Message Content Intent disabled | Developer Portal, Bot, enable, Save |
| Bot online, doesn't see usernames | Server Members Intent disabled | Developer Portal, Bot, enable, Save |
| Bot offline | Bad/expired token, or token committed and rotated | Reset token in Developer Portal, update `.env`, `docker compose up -d` |
| Bot replies to DMs but not server | `DISCORD_REQUIRE_MENTION=true` (default) and you didn't `@mention` | Either `@mention` it, set `DISCORD_REQUIRE_MENTION=false`, or add the channel to `DISCORD_FREE_RESPONSE_CHANNELS` |
| "user not in DISCORD_ALLOWED_USERS" in logs | Allowlist set to specific IDs that don't include yours | Empty the list to allow all, or add your user ID |

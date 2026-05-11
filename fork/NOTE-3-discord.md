Hermes Agent has first-class Discord support. The bot lives at `gateway/platforms/discord.py`. Each Discord message goes through: authorization → mention/free-response check → session lookup → agent execution → reply delivery.

### Bot behavior by context

| Context | Behavior |
|---|---|
| DMs | Responds to every message. No `@mention` needed. Each DM is its own session. |
| Server channels | Only responds to `@mention` by default. Set `DISCORD_REQUIRE_MENTION=false` to respond to every message. |
| Free-response channels | List specific channels in `DISCORD_FREE_RESPONSE_CHANNELS` to skip the mention requirement. |
| Threads | Replies in the same thread. Isolated session history from parent channel. |
| Shared channels | By default each user gets their own session inside a shared channel. Set `group_sessions_per_user: false` in `./hermes-data/config.yaml` for one shared transcript. |

### Discord Developer Portal setup

Open `https://discord.com/developers/applications` and create a new application.

In the Bot tab, the bot user is auto-created. Copy or reset the token (only shown once).

Enable Privileged Gateway Intents (both required, otherwise bot is online but silent):

- Server Members Intent ON
- Message Content Intent ON

Save changes.

In the Installation tab, choose Discord Provided Link, enable scopes `bot` and `applications.commands`, and use permissions integer `274878286912` (View Channels, Send Messages, Read Message History, Attach Files, Embed Links, Send Messages in Threads, Add Reactions).

Open the invite URL, pick the server, authorize.

### Hermes-side configuration

The token and behavior toggles live in `.env`. The override passes them through to the container.

In `.env`:

```
DISCORD_BOT_TOKEN=<bot-token>
DISCORD_ALLOWED_USERS=
DISCORD_HOME_CHANNEL=
DISCORD_REQUIRE_MENTION=true
DISCORD_FREE_RESPONSE_CHANNELS=
DISCORD_AUTO_THREAD=false
GATEWAY_ALLOW_ALL_USERS=true
```

Access control: by default Hermes denies all users. Either fill `DISCORD_ALLOWED_USERS` with comma-separated Discord user IDs, or set `GATEWAY_ALLOW_ALL_USERS=true` for unrestricted access.

Currently wired in `docker-compose.override.yml` under `gateway.environment:`:

```yaml
- DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
- DISCORD_ALLOWED_USERS=${DISCORD_ALLOWED_USERS}
- DISCORD_HOME_CHANNEL=${DISCORD_HOME_CHANNEL:-}
- DISCORD_REQUIRE_MENTION=${DISCORD_REQUIRE_MENTION:-true}
- DISCORD_FREE_RESPONSE_CHANNELS=${DISCORD_FREE_RESPONSE_CHANNELS:-}
- DISCORD_AUTO_THREAD=${DISCORD_AUTO_THREAD:-false}
- GATEWAY_ALLOW_ALL_USERS=${GATEWAY_ALLOW_ALL_USERS:-false}
```

### Optional toggles

In `./hermes-data/config.yaml`:

```yaml
group_sessions_per_user: true
```

Default is `true`. Set `false` for one shared transcript per channel.

Env vars Hermes supports but the override doesn't currently pass (add to `.env` and the override if used):

| Variable | Purpose |
|---|---|
| `DISCORD_ALLOWED_ROLES` | Comma-separated role IDs (OR-semantics with allowed users) |
| `DISCORD_IGNORE_NO_MENTION` | Default `true`, bot stays silent when others are mentioned but it isn't |
| `DISCORD_COMMAND_SYNC_POLICY` | `safe` (default), `bulk`, or `off` for slash-command startup sync |

### Bring it up

```powershell
docker compose up -d
```

Tail logs and look for the Discord login line:

```powershell
docker compose logs -f gateway
```

### Verification

DM the bot from a Discord account → should reply.

`@mention` it in a server channel → should reply.

```powershell
docker compose exec gateway /opt/hermes/.venv/bin/hermes doctor
```

The Discord section should show connected.

### Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Bot online, never replies in channels | Message Content Intent disabled | Developer Portal, Bot tab, enable, Save |
| Bot online, doesn't see usernames | Server Members Intent disabled | Developer Portal, Bot tab, enable, Save |
| Bot offline | Bad/expired/rotated token | Reset token in Developer Portal, update `.env`, recreate container |
| Bot replies to DMs but not server | `DISCORD_REQUIRE_MENTION=true` (default) and you didn't `@mention` | `@mention` it, set `DISCORD_REQUIRE_MENTION=false`, or add channel to `DISCORD_FREE_RESPONSE_CHANNELS` |
| "user not in DISCORD_ALLOWED_USERS" in logs | Allowlist set to specific IDs not including yours | Empty the list to allow all, or add your user ID |

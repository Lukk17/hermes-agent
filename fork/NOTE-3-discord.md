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

The Discord UI for bot creation changes regularly. The steps below are current as of August 2026. If a button name differs, look for the equivalent label in the left sidebar.

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and log in.
2. Click `New Application` at the top right. Enter a name for your bot and agree to the terms. Click `Create`.
3. The bot user is auto-created. You do NOT need to click `Add Bot`. Skip directly to the `Bot` tab in the left sidebar.
4. In the `Bot` tab, scroll down to `Privileged Gateway Intents`. Enable BOTH of these and `Save changes` (the bot stays online but silent if either is off):
   - `Server Members Intent`: ON
   - `Message Content Intent`: ON
5. To get the bot token, click `Reset Token` in the `Bot` tab. Discord displays the new token ONCE. Copy it immediately. The old token (if any) is invalidated, so anything still pointing at the old one will stop working.
6. In the left sidebar, click `OAuth2` then `URL Generator`. At the top of that page, set `Integration Type` to `Guild Install` (the default works for normal bots). Pick `User Install` only if you also want the bot to work in DMs without being in a server.
7. Under `Scopes`, check `bot` and `applications.commands`.
8. Under `Bot Permissions`, check the boxes you need. For Hermes a useful minimum is:
   - `View Channels` (General Permissions)
   - `Send Messages` (Text Permissions)
   - `Create Public Threads` (Text Permissions)
   - `Send Messages in Threads` (Text Permissions)
   - `Embed Links` (Text Permissions)
   - `Attach Files` (Text Permissions)
   - `Read Message History` (Text Permissions)
   - `Add Reactions` (Text Permissions)
   - `Send Voice Messages` (Text Permissions) (only if you want voice channel support)
   - `Connect`, `Speak`, `Request To Speak` (Voice Permissions) (only if you want voice channel support)
9. At the bottom of the URL Generator page, copy the generated URL. Open it in your browser, pick your `AscendAI` server from the dropdown, click `Authorize`. Complete the CAPTCHA. The bot appears in your server's member list within a few seconds.
10. In the `Bot` tab, look for `Requires OAuth2 Code Grant` (it sits in the `Authorization` section of the `Bot` tab, not under `OAuth2 > General`). Leave it OFF. That toggle is for OAuth2 user-facing apps that exchange an authorization code for a token, which is NOT what a Discord bot does. Enabling it forces you to register a redirect URI, which is irrelevant for bot installation and is the source of the "You must specify at least one URI for authentication to work" warning. If you accidentally enabled it, uncheck it in the `Bot` tab. The `OAuth2 > General` page does not control this for bots.

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

After editing `.env`, recreate the gateway so the new token is loaded. A plain `restart` does NOT re-read `.env`:

```powershell
docker compose up -d --force-recreate gateway
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
| Bot offline, `Improper token has been passed` in logs | Token was `Reset` after you copied it, or `.env` was edited but the container was not recreated | `Reset Token` again, paste the freshly-displayed token into `.env`, recreate the container: `docker compose up -d --force-recreate gateway`. Compose does NOT re-read `.env` on a plain `restart`, only on `up` against a recreated service. |
| Bot offline, no login attempt in logs | Token is missing or empty | Confirm `DISCORD_BOT_TOKEN=` line is non-empty in `.env`, recreate the container |
| Bot never appeared in your server's member list | Invite URL was never opened, or the wrong scopes were selected | Re-open the OAuth2 URL Generator URL with `bot` in Scopes and the required permissions, authorize the bot to the server again |
| "user not in DISCORD_ALLOWED_USERS" in logs | Allowlist set to specific IDs not including yours | Empty the list to allow all, or add your user ID |
| Bot replies to DMs but not server | `DISCORD_REQUIRE_MENTION=true` (default) and you didn't `@mention` | `@mention` it, set `DISCORD_REQUIRE_MENTION=false`, or add channel to `DISCORD_FREE_RESPONSE_CHANNELS` |
| "scopes not valid" warning in Developer Portal | `Requires OAuth2 Code Grant` was enabled in the `Bot` tab, or `Install Link` is set to `None` in the `Installation` tab | Uncheck `Requires OAuth2 Code Grant` in the `Bot` tab (Authorization section), ignore the `Installation` tab (the invite URL comes from `OAuth2 > URL Generator` instead) |
| "You must specify at least one URI for authentication to work" warning | Caused by enabling `Requires OAuth2 Code Grant` for a bot that does not use it | Uncheck it in the `Bot` tab. No URI needed for bot installation. |

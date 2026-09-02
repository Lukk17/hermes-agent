Hermes Agent has first-class Discord support. The bot lives at `gateway/platforms/discord.py`. Each Discord message goes through: authorization → mention/free-response check → session lookup → agent execution → reply delivery.

### Bot behavior by context

| Context | Behavior |
|---|---|
| DMs | Responds to every message. No `@mention` needed. Each DM is its own session. |
| Server channels | Only responds to `@mention` by default. Set `DISCORD_REQUIRE_MENTION=false` to respond to every message. |
| Free-response channels | List specific channels in `DISCORD_FREE_RESPONSE_CHANNELS` to skip the mention requirement. |
| Threads | Replies in the same thread. Isolated session history from parent channel. |
| Shared channels | By default each user gets their own session inside a shared channel. Set `group_sessions_per_user: false` in `./hermes-data/config.yaml` (bind-mounted at `/opt/data/config.yaml` inside the container) for one shared transcript. |

### Discord Developer Portal setup

The Discord UI for bot creation changes regularly. The steps below are current as of August 2026. If a button name differs, look for the equivalent label in the left sidebar.

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and log in.
2. Click `New Application` at the top right. Enter a name for your bot and agree to the terms. Click `Create`.
3. The bot user is auto-created. You do NOT need to click `Add Bot`. Skip directly to the `Bot` tab in the left sidebar.
4. In the `Bot` tab, scroll down to `Privileged Gateway Intents`. This is the most common reason a Hermes bot fails to connect: from hermes-agent v0.20.x onwards (the codebase that this fork now tracks after the v2026.8.27 rebase), the Discord client refuses the WebSocket connection unless these are explicitly enabled. Enable BOTH and click `Save changes`. The bot is silent without them even when online.
   - `Server Members Intent`: ON
   - `Message Content Intent`: ON (required for hermes to read message text — without this the gateway log shows `discord.errors.PrivilegedIntentsRequired: Shard ID None is requesting privileged intents that have not been explicitly enabled in the developer portal.`)
   - Optional `Presence Intent`: enable only if you plan to use hermes's presence-tracking features.
5. To get the bot token, click `Reset Token` in the `Bot` tab. Discord displays the new token ONCE. Copy it immediately. The old token (if any) is invalidated, so anything still pointing at the old one will stop working. Resetting again invalidates the freshly pasted one — only reset when you have somewhere ready to paste.
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
DISCORD_REQUIRE_MENTION=false
DISCORD_FREE_RESPONSE_CHANNELS=
DISCORD_AUTO_THREAD=false
DISCORD_COMMAND_SYNC_POLICY=off
GATEWAY_ALLOW_ALL_USERS=true
```

Access control: by default Hermes denies all users. Either fill `DISCORD_ALLOWED_USERS` with comma-separated Discord user IDs, or set `GATEWAY_ALLOW_ALL_USERS=true` for unrestricted access.

Standing condition for this deployment: `GATEWAY_ALLOW_ALL_USERS=true` with an empty `DISCORD_ALLOWED_USERS` means anyone who can post in the four channels listed in `discord.allowed_channels` gets an agent with shell and filesystem access inside the container, and that is deliberate, but it is only safe while those four channels stay private. If any of them is ever opened up, or the bot is added to another server, fill `DISCORD_ALLOWED_USERS` first.

Currently wired in `docker-compose.override.yml` under `gateway.environment:`:

```yaml
- DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
- DISCORD_ALLOWED_USERS=${DISCORD_ALLOWED_USERS}
- DISCORD_HOME_CHANNEL=${DISCORD_HOME_CHANNEL:-}
- DISCORD_REQUIRE_MENTION=${DISCORD_REQUIRE_MENTION:-true}
- DISCORD_FREE_RESPONSE_CHANNELS=${DISCORD_FREE_RESPONSE_CHANNELS:-}
- DISCORD_AUTO_THREAD=${DISCORD_AUTO_THREAD:-false}
- DISCORD_COMMAND_SYNC_POLICY=${DISCORD_COMMAND_SYNC_POLICY:-off}
- GATEWAY_ALLOW_ALL_USERS=${GATEWAY_ALLOW_ALL_USERS:-false}
```

### Optional toggles

In `./hermes-data/config.yaml` (bind-mounted at `/opt/data/config.yaml` inside the container):

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

DM the bot from a Discord account, should reply.

`@mention` it in a server channel, should reply.

```powershell
docker compose exec gateway hermes doctor
```

The Discord section should show connected.

### Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Bot offline, gateway log shows `discord.errors.PrivilegedIntentsRequired: Shard ID None is requesting privileged intents that have not been explicitly enabled in the developer portal.` | Privileged Gateway Intents (especially `Message Content Intent`) are not enabled in the Discord Developer Portal `Bot` tab. From hermes-agent v0.20.x onwards this is enforced at connection time; the WebSocket is rejected before any message processing. | Open the Developer Portal, select your bot application, `Bot` tab, scroll to `Privileged Gateway Intents`, enable `Message Content Intent` and `Server Members Intent`, click `Save Changes`, then `docker compose up -d --force-recreate gateway`. |
| Bot online, never replies in channels | Message Content Intent disabled (the legacy failure mode; not usually the cause after v0.20.x because that check now blocks the connection entirely) | Developer Portal, Bot tab, enable, Save |
| Bot online, doesn't see usernames | Server Members Intent disabled | Developer Portal, Bot tab, enable, Save |
| Bot offline, `Improper token has been passed` in logs | Token was `Reset` after you copied it, or `.env` was edited but the container was not recreated | `Reset Token` again, paste the freshly-displayed token into `.env`, recreate the container: `docker compose up -d --force-recreate gateway`. Compose does NOT re-read `.env` on a plain `restart`, only on `up` against a recreated service. |
| Bot offline, no login attempt in logs | Token is missing or empty, or a stale Windows env var `DISCORD_BOT_TOKEN` is set in `HKCU\Environment` and shadows the `.env` file (Docker Compose picks up the shell env over `.env`) | Confirm `DISCORD_BOT_TOKEN=` line is non-empty in `.env`. Open a fresh PowerShell window (the old one may have a stale value). If the Windows shell variable persists across reboots, remove it with `reg delete "HKCU\Environment" /v DISCORD_BOT_TOKEN /f`. |
| Bot connects as the wrong bot (e.g. `AscendClaw` instead of `AscendHermes`) when you intended a different one | Same Windows env var shadow: the `DISCORD_BOT_TOKEN` is being read from the PowerShell session or `HKCU\Environment` and that value corresponds to the wrong application | Reset and paste the correct bot's token into `.env`, remove the Windows env var (`reg delete`), run from a fresh terminal window. Verify with `docker compose config` what value will be substituted. |
| Bot never appeared in your server's member list | Invite URL was never opened, or the wrong scopes were selected | Re-open the OAuth2 URL Generator URL with `bot` in Scopes and the required permissions, authorize the bot to the server again |
| "user not in DISCORD_ALLOWED_USERS" in logs | Allowlist set to specific IDs not including yours | Empty the list to allow all, or add your user ID |
| Bot replies to DMs but not server | `DISCORD_REQUIRE_MENTION=true` (default) and you didn't `@mention` | `@mention` it, set `DISCORD_REQUIRE_MENTION=false`, or add channel to `DISCORD_FREE_RESPONSE_CHANNELS` |
| "scopes not valid" warning in Developer Portal | `Requires OAuth2 Code Grant` was enabled in the `Bot` tab, or `Install Link` is set to `None` in the `Installation` tab | Uncheck `Requires OAuth2 Code Grant` in the `Bot` tab (Authorization section), ignore the `Installation` tab (the invite URL comes from `OAuth2 > URL Generator` instead) |
| "You must specify at least one URI for authentication to work" warning | Caused by enabling `Requires OAuth2 Code Grant` for a bot that does not use it | Uncheck it in the `Bot` tab. No URI needed for bot installation. |
| Rebase onto a newer hermes release and the bot stops connecting where it worked before | Upstream changed the strictness of Discord integration. Re-check the new version's `gateway/platforms/discord.py` and the bot's portal configuration against the new requirements | Common ones: new gateway protocol version, new intent requirement, new permission scope. Run the gateway with the latest source, observe the first error in `hermes-data/logs/gateway.log`, then map the error to the portal setting. |
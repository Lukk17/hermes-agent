Hermes Agent has first-class Discord support. The bot ships as a platform plugin at `plugins/platforms/discord/adapter.py`. Each Discord message goes through: authorization → mention/free-response check → session lookup → agent execution → reply delivery.

### Shell variants in this note

Docker and git commands are identical in PowerShell and in a Unix shell, so they appear once, in a block tagged `bash`, and paste unchanged into PowerShell on Windows, into bash or zsh on Linux, and into zsh on macOS. Anything that genuinely differs between the two, file copies, variable assignment, redirection, reading a file, gets one block per shell with a label above it saying which is which. A command that only makes sense on one platform gets a single block and a sentence saying why there is no second variant.

### Bot behavior by context

| Context | Behavior |
|---|---|
| DMs | Responds to every message. No `@mention` needed. Each DM is its own session. |
| Server channels | Only responds to `@mention` by default. Set `require_mention: false` under `discord:` in `hermes-data/config.yaml` to respond to every message. This fork sets it to `false`. |
| Free-response channels | List channel IDs under `discord.free_response_channels` in `hermes-data/config.yaml` to skip the mention requirement. |
| Threads | Replies in the same thread. Isolated session history from parent channel. |
| Shared channels | By default each user gets their own session inside a shared channel. Set the top-level `group_sessions_per_user: false` in `hermes-data/config.yaml` (bind-mounted at `/opt/data/config.yaml` inside the container) for one shared transcript. |

### Discord Developer Portal setup

The Discord UI for bot creation changes regularly. The steps below are current as of August 2026. If a button name differs, look for the equivalent label in the left sidebar.

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and log in.
2. Click `New Application` at the top right. Enter a name for your bot and agree to the terms. Click `Create`.
3. The bot user is auto-created. You do NOT need to click `Add Bot`. Skip directly to the `Bot` tab in the left sidebar.
4. In the `Bot` tab, scroll down to `Privileged Gateway Intents`. This is the most common reason a Hermes bot fails to connect: from hermes-agent v0.20.x onwards (the codebase that this fork now tracks after the v2026.8.27 rebase), the Discord client refuses the WebSocket connection unless these are explicitly enabled. Enable BOTH and click `Save changes`. The bot is silent without them even when online.
   - `Server Members Intent`: ON
   - `Message Content Intent`: ON (required for hermes to read message text, and without this the gateway log shows `discord.errors.PrivilegedIntentsRequired: Shard ID None is requesting privileged intents that have not been explicitly enabled in the developer portal.`)
   - Optional `Presence Intent`: enable only if you plan to use hermes's presence-tracking features.
5. To get the bot token, click `Reset Token` in the `Bot` tab. Discord displays the new token ONCE. Copy it immediately. The old token (if any) is invalidated, so anything still pointing at the old one will stop working. Resetting again invalidates the freshly pasted one, so only reset when you have somewhere ready to paste.
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

Three files carry Discord settings, and one rule decides which:

- `hermes-data/.env` holds credentials, and the handful of settings that have no `config.yaml` key at all. Anything hermes or a process hermes spawns has to read at runtime belongs here.
- `hermes-data/config.yaml`, under `discord:`, holds behaviour. Who may talk to the bot, which channels it answers in, whether it opens threads, the per-channel personas.
- The repo-root `.env` is read by Docker Compose only, for `${VAR}` substitution in `docker-compose.override.yml`. Nothing inside the container opens that file.

Older revisions of this note told you to put the token and the behaviour toggles in the repo-root `.env`. That is no longer how this fork is wired, and following it now gives you a bot that never logs in.

#### The token, and why it is not in the repo-root `.env`

`DISCORD_BOT_TOKEN` goes in `hermes-data/.env`, which is gitignored and sits inside the directory mounted at `/opt/data`:

```
DISCORD_BOT_TOKEN=<bot-token>
```

Compose deliberately does NOT forward it. Two reasons, in the order that matters.

1. Single source of truth. The credential is declared in exactly one file, so there is no precedence question to reason about when the value turns out to be wrong. It is worth knowing which way precedence runs anyway, because it rules out a whole class of guesses: hermes loads `$HERMES_HOME/.env`, which is `hermes-data/.env` here, late and with `override=True` (`hermes_cli/env_loader.py:500`), and `override=True` means values from the file win over whatever the process environment already held. A stale shell variable, a Windows registry entry or an empty compose passthrough cannot beat it.
2. Subprocess stripping, which is the one that actually bites. Hermes removes messaging and provider credentials from the environment of every child process it spawns, so a cron script shelling out to `hermes send` can only see the token because that child re-reads `hermes-data/.env` at startup. A compose passthrough would not help it at all. The blocklist is built in `tools/environments/local.py` from the provider registry plus every `OPTIONAL_ENV_VARS` entry in the `tool` or `messaging` category. Measured against this checkout, it strips `DISCORD_BOT_TOKEN`, `DISCORD_HOME_CHANNEL`, `DISCORD_HOME_CHANNEL_NAME`, `DISCORD_ALLOWED_USERS`, `DISCORD_ALLOW_ALL_USERS`, `DISCORD_REQUIRE_MENTION`, `DISCORD_FREE_RESPONSE_CHANNELS`, `DISCORD_AUTO_THREAD`, `DISCORD_REPLY_TO_MODE` and `MINIMAX_API_KEY`. It does not strip `DISCORD_COMMAND_SYNC_POLICY`, which is exactly why that one is still forwarded and these are not.

The token also decides whether the Discord platform exists at all: `gateway/config.py:2021` enables the adapter only when `DISCORD_BOT_TOKEN` is set. No token means no login attempt in the log, not a failed one.

#### What is actually in `hermes-data/.env`

Four keys, and only four: `DISCORD_BOT_TOKEN`, `DISCORD_HOME_CHANNEL`, `MINIMAX_API_KEY`, `API_SERVER_KEY`.

`DISCORD_HOME_CHANNEL` is the exception to the rule above and worth naming rather than glossing. It is behaviour, not a credential, but there is no `discord.home_channel` key in `config.yaml` to put it in: the gateway reads it from the environment (`gateway/config.py:2026`), and the only file-based route is a `platforms.discord.home_channel` block that `/set-home` writes at runtime. Since `config.yaml` is mounted read-only in this fork, that runtime write cannot happen, so the env var is the route that works here.

#### What is in `hermes-data/config.yaml` under `discord:`

The live values in this fork:

```yaml
discord:
  require_mention: false
  free_response_channels: <four channel IDs, comma-separated>
  allowed_channels: <the same four channel IDs>
  auto_thread: false
  reactions: true
  allow_all_users: true
  channel_prompts:
    '<general-channel-id>': |
      ...
    '<crypto-monitor-channel-id>': |
      ...
    '<osint-channel-id>': |
      ...
    '<research-channel-id>': |
      ...
  server_actions: ''
```

Precedence, so you know which one you are actually changing: the adapter reads the environment first and falls back to the `config.yaml` value (`_gate_raw` in `plugins/platforms/discord/adapter.py`), and the config loader bridges a `config.yaml` value into the matching env var only when that env var is unset. A non-empty env var therefore pins the setting and the YAML edit does nothing. That is the second reason the behavioural keys are not in the compose passthrough.

Access control in this fork is `allow_all_users: true` under `discord:`. The alternative is to drop that and list Discord user IDs under `discord.allow_from` instead. Without one of the two, the gateway denies every sender. `GATEWAY_ALLOW_ALL_USERS` still works as a gateway-wide equivalent, but it is env-only with no `config.yaml` key, so prefer the Discord one.

Standing condition for this deployment: `allow_all_users: true` means anyone who can post in the four channels listed in `discord.allowed_channels` gets an agent with shell and filesystem access inside the container. That is deliberate, and it is only safe while those four channels stay private. If any of them is opened up, or the bot joins another server, switch to `allow_from` with your own user ID first.

#### What compose forwards

One Discord variable, in `docker-compose.override.yml` under `gateway.environment:`:

```yaml
- DISCORD_COMMAND_SYNC_POLICY=${DISCORD_COMMAND_SYNC_POLICY:-off}
```

It is forwarded precisely because it has no `config.yaml` equivalent. It controls how the bot syncs its slash-command list on connect: `safe`, `bulk`, or `off`.

### Optional toggles

Top-level in `hermes-data/config.yaml`, not under `discord:`:

```yaml
group_sessions_per_user: true
```

Default is `true`. Set `false` for one shared transcript per channel.

Settings hermes supports that this fork does not currently set. The first two have a `config.yaml` key and belong under `discord:`. The third has none, so it is one of the env-only exceptions and goes in `hermes-data/.env`:

| Setting | Purpose |
|---|---|
| `discord.allowed_roles` in `config.yaml`, or `DISCORD_ALLOWED_ROLES` | Comma-separated role IDs, OR-semantics with the allowed users |
| `discord.ignored_channels` in `config.yaml`, or `DISCORD_IGNORED_CHANNELS` | Channels the bot never answers in, even when mentioned |
| `DISCORD_IGNORE_NO_MENTION` | Default `true`, the bot stays silent when someone else is mentioned but it is not |

### Bring it up

Which command you need depends on which file you edited.

After editing `hermes-data/.env`, a restart is enough. That file lives inside the directory bind-mounted at `/opt/data`, so the container already sees the new content and hermes re-reads it when the process starts:

```bash
docker compose restart gateway
```

After editing `hermes-data/config.yaml`, recreate. Config is read once at startup and the file is mounted read-only, so nothing picks up a change on its own:

```bash
docker compose up -d --force-recreate gateway
```

After editing the repo-root `.env` or `docker-compose.override.yml`, recreate for a different reason: compose only re-reads those on an `up` against a recreated service, never on a plain `restart`:

```bash
docker compose up -d --force-recreate gateway
```

Tail logs and look for the Discord login line:

```bash
docker compose logs -f gateway
```

### Verification

DM the bot from a Discord account, should reply.

`@mention` it in a server channel, should reply.

```bash
docker compose exec gateway hermes doctor
```

The Discord section should show connected.

### Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Bot offline, gateway log shows `discord.errors.PrivilegedIntentsRequired: Shard ID None is requesting privileged intents that have not been explicitly enabled in the developer portal.` | Privileged Gateway Intents (especially `Message Content Intent`) are not enabled in the Discord Developer Portal `Bot` tab. From hermes-agent v0.20.x onwards this is enforced at connection time; the WebSocket is rejected before any message processing. | Open the Developer Portal, select your bot application, `Bot` tab, scroll to `Privileged Gateway Intents`, enable `Message Content Intent` and `Server Members Intent`, click `Save Changes`, then `docker compose up -d --force-recreate gateway`. |
| Bot online, never replies in channels | Message Content Intent disabled (the legacy failure mode; not usually the cause after v0.20.x because that check now blocks the connection entirely) | Developer Portal, Bot tab, enable, Save |
| Bot online, doesn't see usernames | Server Members Intent disabled | Developer Portal, Bot tab, enable, Save |
| Bot offline, `Improper token has been passed` in logs | The token was `Reset` after you copied it, or `hermes-data/.env` was edited but the gateway process was not restarted | `Reset Token` again and paste the freshly-displayed token into `hermes-data/.env`, NOT the repo-root `.env`, then `docker compose restart gateway`. That file sits inside the bind mount and is read at process start, so a restart is enough and no recreate is needed. The repo-root `.env` is the one that needs a recreate, because compose only re-reads it on `up` against a recreated service. |
| Bot offline, no login attempt in logs at all | `DISCORD_BOT_TOKEN` is missing or empty in `hermes-data/.env`. The token is what enables the platform: `gateway/config.py:2021` only constructs the Discord adapter when it is set, so an absent token produces silence rather than a failed login | Confirm the `DISCORD_BOT_TOKEN=` line is present and non-empty in `hermes-data/.env`. Do not look in the repo-root `.env`, and do not add it there: compose does not forward it, by design |
| Bot connects as the wrong bot (e.g. `AscendClaw` instead of `AscendHermes`) | The token in `hermes-data/.env` belongs to the other application. A shell or Windows-registry `DISCORD_BOT_TOKEN` cannot cause this any more, because hermes loads that file with `override=True` and it wins over anything inherited from the environment | Reset the intended bot's token in the Developer Portal and paste it into `hermes-data/.env`, then restart the gateway. The login line in `hermes-data/logs/gateway.log` names the application it actually connected as, so check that rather than guessing |
| Bot never appeared in your server's member list | Invite URL was never opened, or the wrong scopes were selected | Re-open the OAuth2 URL Generator URL with `bot` in Scopes and the required permissions, authorize the bot to the server again |
| `user not in DISCORD_ALLOWED_USERS / DISCORD_ALLOWED_ROLES` in logs | An allowlist is in force and your ID is not on it. The message names the env var even when the value came from `config.yaml`, because the loader bridges `discord.allow_from` into that variable, so it will send you to the wrong file if you take it literally | In `hermes-data/config.yaml` under `discord:`, either set `allow_all_users: true` (what this fork ships) or add your Discord user ID to `allow_from`. Then recreate, because `config.yaml` is read once at startup and is mounted read-only |
| Bot replies to DMs but not in a server channel | `require_mention` is on (upstream default) and you did not `@mention` it, or the channel is not in `discord.free_response_channels`. This fork sets `require_mention: false` and lists four channels, so the usual cause here is a channel that is not on either list | `@mention` it, or add the channel ID to `discord.free_response_channels` and `discord.allowed_channels` in `hermes-data/config.yaml`, then recreate |
| Bot online and authorized, silent in one specific channel | That channel ID is missing from `discord.allowed_channels`, which is a whitelist: when it is non-empty the bot answers ONLY in the channels it lists | Add the channel ID to `discord.allowed_channels`, and to `discord.free_response_channels` too if you want it to answer without a mention, then recreate |
| "scopes not valid" warning in Developer Portal | `Requires OAuth2 Code Grant` was enabled in the `Bot` tab, or `Install Link` is set to `None` in the `Installation` tab | Uncheck `Requires OAuth2 Code Grant` in the `Bot` tab (Authorization section), ignore the `Installation` tab (the invite URL comes from `OAuth2 > URL Generator` instead) |
| "You must specify at least one URI for authentication to work" warning | Caused by enabling `Requires OAuth2 Code Grant` for a bot that does not use it | Uncheck it in the `Bot` tab. No URI needed for bot installation. |
| Rebase onto a newer hermes release and the bot stops connecting where it worked before | Upstream changed the strictness of the Discord integration. Re-check the new version's `plugins/platforms/discord/adapter.py` and the bot's portal configuration against the new requirements | Common ones: new gateway protocol version, new intent requirement, new permission scope. Run the gateway with the latest source, observe the first error in `hermes-data/logs/gateway.log`, then map the error to the portal setting. |
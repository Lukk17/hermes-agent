The Hermes Agent dashboard has no built-in authentication. Anyone who can reach the URL is instantly admin: read every conversation transcript, exfiltrate every API key (Anthropic, MiniMax, Discord, Gmail OAuth tokens, OSINT keys), run arbitrary tool calls, reconfigure the agent. Upstream's own docs warn that binding the dashboard to anything other than loopback is **dangerous** (`website/docs/user-guide/features/web-dashboard.md:180`).

This fork's approach: don't expose the dashboard. Publish it only to `127.0.0.1:9119` on the host. For remote access, tunnel through SSH.

### Network layout

| Service | Network mode | Listener | Who can reach it |
|---|---|---|---|
| gateway | `network_mode: host` | none (outbound-only) | nobody — outbound only |
| dashboard | `network_mode: host` | `127.0.0.1:9119` | the host's loopback only |

Both services run with `network_mode: host`, so they share the host's network namespace and there is no port publish to configure. The dashboard's own command binds `127.0.0.1` (`["dashboard", "--host", "127.0.0.1", "--port", "9119", "--no-open"]` in `docker-compose.override.yml`), and that bind IS the security boundary. Nothing on the LAN can reach the dashboard.

### There is no `--insecure` flag

Do not add one. `--insecure` is still accepted by `hermes dashboard` and `hermes serve` but it is a documented no-op (`hermes_cli/subcommands/dashboard.py:32-41`): since the June 2026 hardening it no longer disables authentication, and a public bind always requires an auth provider. The dashboard command in `docker-compose.override.yml` is `["dashboard", "--host", "127.0.0.1", "--port", "9119", "--no-open"]`, so it binds loopback directly and never trips the bind-safety check.

The same applies to `--tui`. It is accepted and silently ignored (`hermes_cli/subcommands/dashboard.py:110-124`), a backward-compatibility shim for old desktop-app shells. The embedded chat surface is always on; passing the flag changes nothing.

### Local access (same machine as Docker)

Open in any browser on the host:

```
http://localhost:9119
```

No auth, no tunnel — the loopback bind is the security boundary.

### Remote access via SSH tunnel

From your laptop, with the Hermes host accessible via SSH:

```powershell
ssh -L 9119:localhost:9119 <user>@<host>
```

Replace `<user>` with your Linux account on the host and `<host>` with its LAN IP, hostname, or Tailscale name. Leave that terminal open — closing it tears down the tunnel.

Then in your **local** browser:

```
http://localhost:9119
```

Traffic flow: your browser → your laptop's `localhost:9119` → SSH (encrypted) → host's `localhost:9119` → dashboard. The host's port 9119 is never reachable from anywhere except its own loopback and SSH-tunneled sessions.

### SSH credentials

SSH uses OS-level credentials on the host (Linux user account), not anything from `.env`. Two options:

- **Password auth** — set the host user's password (`passwd` on the host). `ssh user@host` prompts for it each time.
- **Public key auth (recommended)** — generate a key on your laptop once (`ssh-keygen`), copy the public key into the host's `~/.ssh/authorized_keys` (`ssh-copy-id user@host` on macOS/Linux; paste manually on Windows). No password prompt after that.

Harden `sshd` on the remote host (`/etc/ssh/sshd_config`):

```
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
```

### Off-LAN access (optional)

If the Hermes host is behind a router and you want to reach it from outside your home network, two clean options that layer on top of the SSH-tunnel approach:

- **Tailscale** on the host and on each client. Devices in the tailnet reach the host by its tailnet name; the SSH tunnel command then targets that name. Free for personal use, zero port forwarding.
- **Cloudflare Tunnel + Cloudflare Access** — public DNS, Cloudflare's auth proxy in front, no port forwarding. More setup; useful when SSH from the client device isn't viable.

### Other Hermes ports

| Port | What | Default state |
|---|---|---|
| 9119 | Dashboard, loopback only | host loopback only |
| (none) | Gateway is outbound-only | n/a |
| (optional) | Gateway OpenAI-compatible API server, enabled by `API_SERVER_KEY` and `API_SERVER_HOST` | off |

### What not to do

- Bind the dashboard to `0.0.0.0` on the host and rely on the LAN being trusted. Compromised IoT devices on the same subnet can walk in.
- Port-forward `:9119` from your router to the public internet. Even with a tunnel in front, this becomes a Shodan target.
- Use ngrok or similar public tunneling without auth in front. The dashboard has no auth — exposing it publicly is wide-open admin access.

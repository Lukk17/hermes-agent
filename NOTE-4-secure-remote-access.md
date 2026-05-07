# Note 4 — How to access Hermes safely from your LAN (or anywhere)

## The honest threat model

The Hermes dashboard at `:9119` has **no built-in authentication**. Whoever can reach the port can:

- read every conversation transcript ever stored
- exfiltrate every API key the agent holds (Anthropic, MiniMax, OpenAI, Discord, Telegram, Gmail OAuth tokens, all the OSINT keys, etc.)
- run arbitrary tool calls (shell, file ops, Docker, web fetches) against your minipc and any reachable network
- impersonate your Discord/Telegram bot
- reconfigure the agent (change provider, swap models, install skills, edit memory)

Same for `docker compose exec` shell access against the host: anyone on the host can do anything the `hermes` container can do, which is essentially unlimited.

So "secure remote access" really means: **only people you trust should reach those interfaces, and the path they take should be authenticated and encrypted.**

The fork currently binds dashboard to `0.0.0.0:9119` per your earlier request. That is the **least secure** option and should be reverted before any of the recommended paths below.

## Three safe options, ranked

### Option 1 (recommended): Tailscale (or any WireGuard-based mesh)

This is the best fit for a homelab minipc. Tailscale puts you and your minipc on a private encrypted overlay network identified by your Google/GitHub/Microsoft account. The dashboard binds to `127.0.0.1` again (and to the Tailscale interface), and only authenticated Tailscale peers in your "tailnet" can reach it.

**Why this beats SSH tunnels for daily use:**

- works from your laptop, phone (Tailscale apps for iOS/Android), and any other device
- works through CGNAT, behind a router with no port forwarding, on cellular data, on coffee-shop WiFi
- ACLs are written once in the admin panel, no per-user SSH key juggling
- traffic is end-to-end encrypted with WireGuard
- the dashboard is *invisible* to anyone outside your tailnet (no port scan reveals it)

**Setup on the minipc (Linux):**

```bash
# Install
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Authenticate via the URL printed, log in with your provider
tailscale ip -4   # note this IP, e.g. 100.x.y.z
```

**On every client device** (laptop, phone): install the Tailscale app, sign in with the same identity.

**Dashboard config:** revert the override to `--host 127.0.0.1` (see "Revert the LAN exposure" at the bottom). Tailscale has its own interface on the host; if you want to bind only to the Tailscale IP rather than every interface, use `--host 100.x.y.z`. With host networking the container can see the Tailscale interface directly.

**Access:** from any logged-in device:

```
http://<minipc-tailscale-name>:9119
http://100.x.y.z:9119
```

**Shell access** to the host (and from there `docker compose exec`):

```bash
# enable Tailscale SSH on the minipc, no SSH keys to manage
sudo tailscale up --ssh
# then from a client
ssh you@<minipc-tailscale-name>
docker compose exec -it gateway hermes
```

Tailscale SSH uses your tailnet identity (the same Google/GitHub login), so revoking access for a device or person is a one-click action in the Tailscale admin panel.

For a homelab minipc on your LAN, this is the "right answer" by a wide margin.

### Option 2: Plain SSH tunnel (simplest, no extra software)

If you already have OpenSSH installed and don't want another agent running, port-forward the dashboard over SSH. The dashboard stays bound to `127.0.0.1` on the minipc; SSH does the encrypted hop.

**On the minipc (Linux):**

```bash
sudo apt install openssh-server   # if not already
sudo ufw allow ssh                # only SSH is exposed, not 9119
```

Use **public-key auth only** (disable passwords in `/etc/ssh/sshd_config`):

```
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
```

**On a client (laptop/phone with Termius/ConnectBot):**

```bash
ssh -L 9119:localhost:9119 you@<minipc-LAN-ip>
# leave that terminal open, then in a browser:
#   http://localhost:9119
```

The dashboard appears on the *client's* `localhost:9119` while the SSH session is up.

**Shell access:** same SSH session gives you a shell on the minipc, and from there `docker compose exec -it gateway bash` for the container.

**Limitations:** SSH-only access works fine on your LAN, but to use it from outside you either need to expose SSH to the internet (acceptable with key-only auth and `fail2ban`, but more attack surface than Tailscale) or set up port-forwarding on your router.

### Option 3: Caddy reverse proxy with basic-auth (LAN-only, low effort)

If you want a normal `http://hermes.local:9119` on your LAN that asks for a password, run a Caddy reverse proxy in front of the dashboard. The dashboard binds to `127.0.0.1` again; Caddy listens on the LAN interface and requires basic auth.

`Caddyfile`:

```
hermes.local {
    reverse_proxy 127.0.0.1:9119
    basicauth {
        you JDJhJDE0JC5...   # bcrypt hash, generate with: caddy hash-password
    }
    tls internal              # self-signed cert, accept once on each client
}
```

`docker run -d --network host -v /etc/caddy/Caddyfile:/etc/caddy/Caddyfile:ro caddy`

Less convenient than Tailscale (you still have to deal with router DNS or `/etc/hosts` for `hermes.local`), but if you're already running a reverse proxy this is the natural pattern.

## Things you should NOT do

- **Bind `0.0.0.0` and rely on the LAN being trusted.** Smart TVs, IoT devices, and guest Wi-Fi clients live on most home LANs and are routinely compromised. One compromised device on the same VLAN can reach your dashboard and walk away with every API key.
- **Port-forward 9119 from the router to the public internet.** The dashboard has no auth, no rate-limit, no audit. It will be discovered by Shodan within hours.
- **Use Cloudflare Tunnel without an Access policy.** A bare tunnel is the same as a public DNS name with no auth. Add Cloudflare Access (Zero Trust) on top, or use Tailscale instead.

## Revert the LAN exposure (do this before adopting Option 1 or 2 or 3)

Edit `docker-compose.override.yml` and change the dashboard command back to localhost-only:

```yaml
dashboard:
  command: ["dashboard", "--host", "127.0.0.1", "--port", "9119", "--no-open"]
```

Or remove the `command:` override entirely to fall back to upstream's default (which is the same thing).

```powershell
docker compose up -d --force-recreate dashboard
docker compose logs dashboard --tail 10
# Should now say: listening on http://127.0.0.1:9119
```

Then layer on Tailscale (Option 1) or SSH tunneling (Option 2) for actual remote access.

## My recommendation for your minipc setup

1. Revert dashboard binding to `127.0.0.1`.
2. Install Tailscale on the minipc and on every device you want to access from. Enable Tailscale SSH on the minipc.
3. Lock the minipc's regular SSH port behind a firewall (or disable password auth and trust public-key auth only) so even LAN attacks against SSH are limited.
4. Skip port forwarding, skip basic-auth proxies, skip 0.0.0.0 binds. The dashboard is invisible to everything except your authenticated tailnet.

This gets you LAN access, mobile access, off-LAN access from coffee shops, and a single place (Tailscale admin panel) to revoke any device or person, without ever exposing the dashboard's authless interface to a network you don't fully control.

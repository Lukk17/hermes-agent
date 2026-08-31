# Deploying the fork to a minipc (Proxmox VM with Docker Engine)

Assumes you have already followed `fork/NOTE-1-install.md` on a Windows or
Linux dev box, you have built and pushed the images to Docker Hub, and you
have a Proxmox VM with Debian 12+ and Docker Engine plus the Compose plugin
v2.24+ installed and reachable on your LAN via SSH.

The goal of this note is the *minipc-specific* deltas: which files to copy,
how to pull the prebuilt image instead of building from source, how to keep
`.agents/skills/` in sync from your standards repo, the Proxmox networking
gotcha, and the optional nginx reverse proxy if you want LAN browser access
without an SSH tunnel.

### Repo-as-deployable-unit

The intent of this fork is that the GitHub repo IS the deployable unit: a
fresh `git clone` on the minipc gives you everything except secrets and
runtime state. To make that work, the fork splits `hermes-data/` into two
halves: tracked content (config, cron jobs, project workspaces, fork
plugin, per-channel prompts) and gitignored runtime state (OAuth tokens,
sessions database, logs, kanban DB, model cache).

Tracked under `hermes-data/`:

- `SOUL.md` (agent personality)
- `config.yaml` (provider, model, Discord IDs, channel prompts, external_dirs)
- `cron/jobs.yaml` (scheduled jobs)
- `projects/<name>/` (per-project workspaces, e.g. `projects/crypto-monitor/`)
- `plugins/hermes-fork-extras/` (fork-specific plugin)

Gitignored under `hermes-data/`:

- `auth.json`, `auth.lock` (OAuth tokens)
- `state.db*` (sessions SQLite DB)
- `sessions/` (conversation history)
- `logs/` (agent log files)
- `cache/`, `models_dev_cache.json` (provider model lists)
- `discord_threads.json`, `gateway.lock`, `gateway.pid` (process state)
- `kanban.db*` (debatable; keep tracked only if you want the board to survive
  a fresh clone, otherwise gitignore)
- `credentials/` (per-skill OAuth credential files like `google_token.json`)
- `external-skills/` (this is the mount target for `.agents/skills/`,
  never written to from inside the container)
- `.hermes_history`, `.skills_prompt_snapshot.json`, `.npm`, `.local`,
  `bin/` (runtime scratch)

The `.gitignore` at the repo root already excludes `hermes-data/` except
`SOUL.md`. The repo-root `.gitignore` plus the same patterns in
`hermes-data/.gitignore` (a per-directory ignore) achieve the split above.
See the "Tracking hermes-data selectively" section below for the exact
rules.

### Network layout assumed

```
[ Laptop on LAN ] --(LAN)-- [ Proxmox host ] --(bridged)-- [ VM with Docker ] --(host net)-- [ hermes gateway + dashboard ]
```

The VM must use **bridged networking** in Proxmox, not `internal network` or
NAT. NAT gives the VM no LAN IP, which makes SSH from your laptop awkward and
blocks any future nginx reverse proxy.

Verify the VM has a real LAN IP:

```bash
ip -4 addr show | grep -E 'inet '
# expect something like 192.168.1.42/24 on the same subnet as your laptop
```

### Files to copy to the minipc

Because the repo is deployable as-is, the rsync step in earlier revisions is
replaced by a `git clone` (or `git pull` if already cloned). The minipc
needs:

| Path on minipc | Source | Notes |
|---|---|---|
| `/opt/hermes-fork/` (the project root) | `git clone` of this repo | tracked content, including `hermes-data/config.yaml`, `hermes-data/SOUL.md`, `hermes-data/projects/`, `hermes-data/cron/`, `hermes-data/plugins/`, `.agents/skills/`, `fork/`, `docker-compose.yml`, `docker-compose.override.yml` |
| `/opt/hermes-fork/.env` | hand-written, from `.env.fork.example` | secrets, gitignored |

That is it. No rsync, no source tree, no `.venv`, no `node_modules`.

Bootstrap on a fresh minipc:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo mkdir -p /opt/hermes-fork && sudo chown $USER:$USER /opt/hermes-fork
cd /opt/hermes-fork
git clone https://github.com/Lukk17/hermes-agent.git .
cp .env.fork.example .env
# edit .env: paste DISCORD_BOT_TOKEN, fill in API keys
docker compose pull
docker compose up -d
```

### Pin the image tags in docker-compose.yml on the minipc

The upstream `docker-compose.yml` uses `build: .` plus `image: hermes-agent`.
On the minipc you want `image:` only, no `build:`. The override already sets
`image: hermes-agent:fork` for the gateway and `image: hermes-agent:fork-tui`
for the dashboard, but those rely on a local build context which the minipc
does not have.

After `git clone`, edit `docker-compose.yml` so both services come from
Docker Hub:

```yaml
services:
  gateway:
    image: lukk17/hermes-agent:fork
    container_name: hermes
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./hermes-data:/opt/data
    env_file: .env
    command: ["gateway", "run"]

  dashboard:
    image: lukk17/hermes-agent:fork-tui
    container_name: hermes-dashboard
    restart: unless-stopped
    network_mode: host
    depends_on:
      - gateway
    volumes:
      - ./hermes-data:/opt/data
    env_file: .env
    command: ["dashboard", "--host", "127.0.0.1", "--no-open"]
```

Two key changes from the upstream compose on the minipc:

- `image:` replaces `build:`. No `Dockerfile` or `Dockerfile.fork` needed on
  the minipc.
- `env_file: .env` replaces the per-key `environment:` block in
  `docker-compose.override.yml`. Compose auto-loads `.env` for variable
  substitution, but `env_file:` also pushes every variable into the
  container. This avoids maintaining two parallel lists.

The `extra_hosts` and the read-only `.agents/skills` mount stay in the
override (mount `./.agents/skills` to `/opt/data/external-skills`).

### Sync skills from agent-standards

`.agents/skills/` is the single source of truth for user-authored skills
that the hermes container loads. The fork mirrors a curated subset of
`Lukk17/agent-standards/.agents/skills/`. **Skills are not built into the
image** because they are read-only bind-mounted from the host. The same
directory is also where Kilo / OpenCode / Claude Code look for skills
during development, so the production set and the coding-agent set stay in
sync automatically.

For skills that already exist locally, update in place from
agent-standards master. Source path matches destination path, so the
original (correct) git checkout command works without gymnastics:

```powershell
foreach ($d in Get-ChildItem -Directory .agents/skills) {
  git checkout agent-standards/master -- ".agents/skills/$($d.Name)/" 2>$null
}
```

This overwrites local files with the upstream version. It only updates
skills that already exist locally. New skills in `agent-standards` are NOT
pulled. To add a brand new skill, use `git archive` plus `tar` with
`--strip-components` to relocate the tree from `.agents/skills/<new>/` to
the destination:

```powershell
$tmp = "C:\Windows\Temp\new-skill.tar"
git archive agent-standards/master ".agents/skills/<new-skill-name>" -o $tmp
New-Item -ItemType Directory -Force ".agents/skills/<new-skill-name>"
tar -xf $tmp -C ".agents/skills/<new-skill-name>" --strip-components=3
Remove-Item $tmp -Force
```

After either operation, no container restart is needed. Hermes rescans
`external_dirs` on session start; to force a rescan without restarting:

```bash
docker compose exec gateway /opt/hermes/.venv/bin/hermes skills reload
```

### Sync the fork plugin (`hermes-data/plugins/hermes-fork-extras/`)

The fork plugin lives at `hermes-data/plugins/hermes-fork-extras/` and is
picked up by Hermes' plugin manager as `~/.hermes/plugins/hermes-fork-extras/`
inside the container. It is tracked in git (no sync needed beyond `git pull`).

On first boot, Hermes auto-discovers any folder matching
`<hermes_home>/plugins/<name>/plugin.yaml` + `<name>/__init__.py`. No
explicit registration is needed.

If you ever need to install third-party Python deps for the plugin:

```bash
docker compose exec gateway /opt/hermes/.venv/bin/pip install <pkg>
# the .venv lives on the bind-mounted volume, so this survives a recreate
```

### Bring it up

```bash
cd /opt/hermes-fork
HERMES_UID=$(id -u) HERMES_GID=$(id -g) docker compose pull
docker compose up -d
# verify
docker compose logs -f gateway
docker compose exec gateway /opt/hermes/.venv/bin/hermes doctor
docker compose exec gateway /opt/hermes/.venv/bin/hermes skills list
docker compose exec gateway /opt/hermes/.venv/bin/hermes cron list
docker compose exec gateway /opt/hermes/.venv/bin/hermes plugins list
```

The dashboard is at `http://localhost:9119` **on the minipc itself only**.
From your laptop, SSH tunnel (recommended):

```bash
ssh -L 9119:localhost:9119 user@<minipc-lan-ip>
# then open http://localhost:9119 in your laptop browser
```

### LAN access without SSH (nginx, since you already run it)

If you already maintain nginx on this Docker VM for other homelab apps, the
cleanest way to expose Hermes on the LAN is a vhost with HTTP basic auth in
front of the loopback-bound dashboard. Nothing about Hermes changes. nginx
terminates the LAN-facing side; the dashboard still binds only to loopback
inside the container.

nginx site config (e.g. `/etc/nginx/sites-available/hermes.conf`):

```nginx
server {
    listen 80;
    server_name hermes.local;

    # optional LAN-only listener, comment out if you also want it from anywhere
    # listen 192.168.1.42:80;

    # HTTP basic auth against an htpasswd file
    auth_basic "Hermes Agent";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:9119;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Hermes dashboard uses websockets (TUI streaming)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 1800s;   # matches agent.gateway_timeout
    }
}
```

Create the htpasswd file (one-time, replace `you`):

```bash
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd you
```

Point `hermes.local` at the minipc:

- On the laptop's `/etc/hosts` (Linux/macOS) or
  `C:\Windows\System32\drivers\etc\hosts`: `192.168.1.42  hermes.local`
- Or run a local DNS resolver (Pi-hole, dnsmasq) on the LAN so every device
  resolves it without per-host edits.

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/hermes.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Open `http://hermes.local` from the laptop. nginx prompts for the basic-auth
credentials, then forwards to the dashboard. Anyone on the LAN without the
password is blocked at the nginx layer. Anyone outside the LAN cannot
reach nginx at all (unless you also add a public DNS record and TLS, which
is not recommended for this use case).

If you ever want TLS without buying a cert, swap nginx for Caddy and use its
`basicauth` + `auto_https` directives. Same trade-off, slightly more
automation.

### Proxmox-specific gotchas

- **VM must be on a bridged network**, not NAT or internal-only. Without
  bridged networking the VM has no LAN IP and SSH from your laptop requires
  port-forwarding on the Proxmox host.
- **Clock skew.** Proxmox VMs should have NTP enabled (`timedatectl` inside
  the guest, or `enabled=1` in the Proxmox VM config). OAuth tokens and
  session timestamps break with bad clocks.
- **Disk size.** `./hermes-data/` grows over time (sessions, kanban DB,
  logs, agent-created skills). Start the VM disk at 32GB+, monitor with
  `du -sh ./hermes-data/` periodically.
- **Resource caps.** Hermes plus Playwright Chromium can spike to 2GB RAM
  during a `terminal` session. Give the VM 4GB minimum, 8GB comfortable.
- **Backups.** Add `./hermes-fork/hermes-data/` to Proxmox's backup
  schedule (PBS or vzdump). `config.yaml`, `auth.json`, `SOUL.md`,
  `kanban.db`, and `projects/` are the irreplaceable bits.
- **Firewall.** If Proxmox enables a guest firewall by default, open port
  22 (for SSH) and 80 (for nginx) at the Proxmox firewall level. Port 9119
  stays loopback-only and never appears on the VM's interfaces.

### Updating to a new upstream image

After you push a new build to Docker Hub from the dev box:

```bash
# on the minipc
cd /opt/hermes-fork
docker compose pull
docker compose up -d --force-recreate
```

Your `./hermes-data/` is bind-mounted, not copied into the image, so config
and sessions survive. OAuth tokens refresh automatically on next session
start.

### Tracking hermes-data selectively

The fork's root `.gitignore` excludes `hermes-data/` except `SOUL.md`. Add
a `hermes-data/.gitignore` to allow only the tracked content. Drop this
file at `hermes-data/.gitignore`:

```
# allow tracked content
!/.gitignore
!/SOUL.md
!/config.yaml
!/cron/
!/projects/
!/plugins/

# ignore everything else inside hermes-data/
/*
```

The `/*` line ignores every direct child by default, then the `!` lines
un-ignore the ones we want. This pattern matches Git's standard
"gitignore with whitelist" idiom.

If you want kanban state to survive across clones, also un-ignore
`!/kanban.db` (and be aware it will conflict if two clones ever push to the
same remote). Most users prefer to keep `kanban.db*` gitignored and treat it
as runtime state.

### Per-project subdirectories (crypto-monitor, osint)

Hermes does not auto-create per-project directories under `hermes-data/`,
but you can make each Discord channel's agent stick to its own subdir by
encoding the path in `channel_prompts` (see `fork/NOTE-3-discord.md`):

```yaml
discord:
  channel_prompts:
    '1470798824791343317': |
      ... persona ...
      All persistent files for this project go to /opt/data/projects/crypto-monitor/.
      Create that directory on first use; treat it as the project's working tree.
    '1489711334802063552': |
      ... persona ...
      All persistent files for this project go to /opt/data/projects/osint/.
```

This is convention, not enforcement. The agent follows the instruction
because the prompt says so. Agents in other channels do not see or touch
those subdirs unless explicitly asked. For hard isolation you need separate
Hermes profiles (`hermes -p crypto`, `hermes -p osint`) running as
separate containers with separate Discord bot users.

The `hermes-data/projects/<name>/` location is the canonical spot for
project workspaces because it is tracked in git. Drop your OpenClaw
project content there.

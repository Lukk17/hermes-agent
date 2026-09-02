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
runtime state. To make that work, the fork keeps three directories:

- `./fork/hermes-config/` (tracked): `SOUL.md`, `config.yaml`, `cron/jobs.json`. Bind-mounted at `/opt/data/...` inside the container via file-specific overrides.
- `./fork/projects/` (tracked): project workspaces. Bind-mounted at `/opt/projects/`.
- `./hermes-data/` (gitignored, runtime state only): `state.db`, `auth.json`, `logs/`, `sessions/`, `cache/`, `memories/`, `kanban.db`. Bind-mounted at `/opt/data/`.

Plus tracked in repo root:
- `.env` (gitignored): local secrets.
- `.agents/skills/`: curated skills, bind-mounted at `/opt/external-skills/` (read-only).
- `./skills/`: bundled hermes skills, bind-mounted at `/opt/skills/`.
- `docker-compose.override.yml`, `Dockerfile.fork`: container wiring.

The fork is a real rebase target: `git fetch upstream && git rebase v<TAG>`
on `master` does not conflict with any of the above because upstream does
not ship `fork/`, `fork/hermes-config/`, `fork/projects/`, `.agents/skills/`,
or `./skills/`. Upstream has its own `hermes-data/` and we leave it alone.

See `fork/NOTE-7-updating-from-upstream.md` for the rebase procedure.

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
| `/opt/hermes-fork/` (the project root) | `git clone` of this repo | tracked content, including `fork/hermes-config/SOUL.md`, `fork/hermes-config/config.yaml`, `fork/hermes-config/cron/jobs.json`, `fork/projects/`, `.agents/skills/`, `fork/`, `docker-compose.yml`, `docker-compose.override.yml` |
| `/opt/hermes-fork/.env` | hand-written, from `.env.fork.example` | secrets, gitignored |

That is it. No rsync, no source tree, no `.venv`, no `node_modules`.

Bootstrap on a fresh minipc:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
```

```bash
sudo mkdir -p /opt/hermes-fork && sudo chown $USER:$USER /opt/hermes-fork
```

```bash
cd /opt/hermes-fork && git clone https://github.com/Lukk17/hermes-agent.git .
```

```bash
cp .env.fork.example .env
```

Edit `.env`: paste `DISCORD_BOT_TOKEN`, fill in API keys, and set `HERMES_UID=$(id -u)` / `HERMES_GID=$(id -g)` so the container's runtime user matches the host owner of the checkout. Nothing chowns `/opt/projects`, so a mismatch means the agent gets EACCES on every project write.

Then write `docker-compose.minipc.yml` as described in the next section. Only after that file exists can you pull, because pulling before it is in place would try to build or fetch the wrong images:

```bash
docker compose -f docker-compose.yml -f docker-compose.minipc.yml pull
```

```bash
docker compose -f docker-compose.yml -f docker-compose.minipc.yml up -d
```

Every later `docker compose` command on the minipc needs the same `-f` pair. Export it once per shell to avoid repeating it:

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml
```

### Use a minipc-only compose file, not an edit to docker-compose.yml

The minipc pulls prebuilt images instead of building. Do NOT edit
`docker-compose.yml` to achieve that: it is upstream-owned, so every edit to it
becomes a rebase conflict on the next upstream sync. Do not edit
`docker-compose.override.yml` either, because it is what the dev box builds
with.

Instead, add a third file, `docker-compose.minipc.yml`, tracked or hand-written
on the minipc, and select it explicitly with `-f`. Compose applies files
left-to-right, so the minipc file wins. It is NOT auto-merged the way
`docker-compose.override.yml` is, and naming `-f` suppresses the automatic
override merge, which is what you want here: the override carries `build:`
blocks the minipc cannot satisfy.

Local build tags on the dev box are `hermes-agent:upstream` (the untouched
upstream image), `hermes-agent:fork` (gateway) and `hermes-agent:fork-dashboard`
(dashboard). On Docker Hub they are published as
`lukk17/hermes-agent-gateway` and `lukk17/hermes-agent-dashboard`.

`docker-compose.minipc.yml` should:

- Replace `build:` with `image: lukk17/hermes-agent-gateway:<tag>` for the
  gateway and `image: lukk17/hermes-agent-dashboard:<tag>` for the dashboard.
  Pin a versioned tag for anything that must be reproducible; `:latest` only
  for a scratch box.
- Reproduce the volume set the override provides: `./hermes-data:/opt/data`,
  `./fork/projects:/opt/projects`, `./.agents/skills:/opt/external-skills:ro`,
  `./skills:/opt/skills:ro`, plus the three file-level mounts for
  `fork/hermes-config/SOUL.md`, `config.yaml` and `cron/jobs.json`.
- Reproduce `extra_hosts: ["host.docker.internal:host-gateway"]` on the
  gateway.
- Use `env_file: .env` instead of the override's per-key `environment:` block.
  Compose auto-loads `.env` for `${VAR}` substitution, but `env_file:` also
  pushes every variable into the container, which avoids maintaining two
  parallel lists.
- Keep `network_mode: host` and the dashboard command
  `["dashboard", "--host", "127.0.0.1", "--port", "9119", "--no-open"]`.

The skills mount target is `/opt/external-skills`, NOT `/opt/data/external-skills`.
That path is what `skills.external_dirs` in `fork/hermes-config/config.yaml`
points at; getting it wrong means the skills silently do not load.

This file does not exist in the repo yet. Write it once on the minipc from the
bullet list above and keep it there.

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
docker compose exec gateway hermes skills reload
```

### Fork plugin (optional, future use)

The upstream fork layout reserves `hermes-data/plugins/hermes-fork-extras/`
for a fork-specific plugin, but the current fork does NOT use one. The
per-project conventions under `fork/projects/` plus the channel_prompts
in `fork/hermes-config/config.yaml` cover the same needs without a plugin.

If you later decide to add a fork plugin (for example, a custom OSINT tool
or a Discord admin helper), create it at `hermes-data/plugins/<name>/`
with a `plugin.yaml` and `__init__.py`. The container bind-mounts
`hermes-data/` at `/opt/data/`, so the plugin shows up at
`/opt/data/plugins/<name>/` inside the container.

Do NOT `pip install` into `/opt/hermes/.venv`. That tree is immutable by design:
`docker/stage2-hook.sh:256-262` deliberately leaves it root-owned and
non-writable so an agent session cannot self-modify the runtime and brick the
gateway, and `Dockerfile:388` sets `HERMES_DISABLE_LAZY_INSTALLS=1` to seal the
venv. Anything that did land there would be lost on the next image update,
because `/opt/hermes` lives in the image rather than on the `/opt/data` volume.

The sanctioned target is `/opt/data/lazy-packages`, set as
`HERMES_LAZY_INSTALL_TARGET` at `Dockerfile:401`. It is seeded and chowned to
the `hermes` user at every boot (`docker/stage2-hook.sh:250`), appended to the
END of `sys.path` so a package there can only add modules and can never shadow
a core one (`tools/lazy_deps.py:454-481`), wired in at startup by
`activate_durable_lazy_target()` (`tools/lazy_deps.py:483-500`), and it lives on
the data volume so it survives container recreates and image updates.

Declaring `pip_dependencies` in a general plugin's `plugin.yaml` does nothing.
The key is accepted without warning because it sits in `_KNOWN_MANIFEST_FIELDS`
(`hermes_cli/plugins.py:718`), but the only code that consumes it is the
memory-provider path (`hermes_cli/memory_setup.py:133`,
`hermes_cli/web_server.py:6481-6689`). `hermes plugins install` does not help
either: it takes a Git URL, an `owner/repo`, or an index name, and it installs
no dependencies. So a hand-written local plugin's dependencies are a manual
install.

Run it as the `hermes` user, not root, for the same ownership reason as the CLI
shim:

```bash
docker compose exec -u hermes gateway uv pip install --target /opt/data/lazy-packages <pkg>
```

One caveat: hermes' own install path additionally passes `--constraint` from
`_core_constraints_file()` (`tools/lazy_deps.py:727-736`), pinning shared
transitive dependencies to the core venv's versions. A hand-run install skips
that and can pull an incompatible transitive dependency.

Remember that any file in `hermes-data/` is runtime state and not tracked
in git. The plugin is created and configured on each minipc separately.
For a tracked plugin, place it in `fork/hermes-config/plugins/<name>/` and
add a file-specific bind mount for the directory.

### Bring it up

```bash
cd /opt/hermes-fork && export COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml
```

```bash
docker compose pull
```

```bash
docker compose up -d
```

```bash
docker compose logs -f gateway
```

```bash
docker compose exec gateway hermes doctor
```

```bash
docker compose exec gateway hermes skills list
```

```bash
docker compose exec gateway hermes cron list
```

```bash
docker compose exec gateway hermes plugins list
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
- **Backups.** Add `./hermes-fork/hermes-data/` AND `./hermes-fork/fork/hermes-config/` to Proxmox's
  backup schedule (PBS or vzdump). `state.db` (sessions), `auth.json` (OAuth),
  `kanban.db` (board state), and everything in `fork/hermes-config/` (config,
  persona, cron) are the irreplaceable bits.
- **Firewall.** If Proxmox enables a guest firewall by default, open port
  22 (for SSH) and 80 (for nginx) at the Proxmox firewall level. Port 9119
  stays loopback-only and never appears on the VM's interfaces.

### Updating to a new upstream image

After you push a new build to Docker Hub from the dev box:

```bash
cd /opt/hermes-fork && export COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml
```

```bash
docker compose pull
```

```bash
docker compose up -d --force-recreate
```

Your `./hermes-data/` is bind-mounted, not copied into the image, so config
and sessions survive. OAuth tokens refresh automatically on next session
start.

### hermes-data is gitignored entirely

The current fork design treats `hermes-data/` as fully runtime. There is
no per-directory whitelist. The root `.gitignore` excludes the whole
directory. All tracked configuration lives in `./fork/hermes-config/`. The
fork was redesigned this way to make rebase-on-upstream conflict-free.

The `hermes-data/.gitignore` file that used to whitelist `SOUL.md` and
`config.yaml` no longer exists. If you are upgrading from an older fork
branch, delete it:

```powershell
cmd /c "del hermes-data\.gitignore"
```

There is no need to replace it with anything. `hermes-data/` is now a pure
runtime directory.

### Per-project subdirectories (crypto-monitor, osint)

Hermes does not auto-create per-project directories under `hermes-data/`,
but the fork expects projects to live in `fork/projects/<name>/` (mounted
at `/opt/projects/<name>/` inside the container). Configure each
Discord channel's agent to stick to its own subdir via `channel_prompts`
in `fork/hermes-config/config.yaml` (see `fork/NOTE-3-discord.md`):

```yaml
discord:
  channel_prompts:
    '<crypto-monitor-channel-id>': |
      ... persona ...
      All persistent files for this project go to /opt/projects/crypto-monitor/.
      Treat it as the project's working tree.
    '<osint-channel-id>': |
      ... persona ...
      All persistent files for this project go to /opt/projects/osint/.
```

The path is `/opt/projects/<name>/`, from the `./fork/projects:/opt/projects`
bind mount. It is NOT under `/opt/data/`.

This is convention, not enforcement. The agent follows the instruction
because the prompt says so. Agents in other channels do not see or touch
those subdirs unless explicitly asked. For hard isolation you need separate
Hermes profiles (`hermes -p crypto`, `hermes -p osint`) running as
separate containers with separate Discord bot users.

The `fork/projects/<name>/` location is the canonical spot for project
workspaces because it is tracked in git. Mounted at `/opt/projects/<name>/`
inside the container.

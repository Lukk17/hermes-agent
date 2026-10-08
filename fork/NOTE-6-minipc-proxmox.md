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

### Shell variants in this note

Docker and git commands are identical in PowerShell and in a Unix shell, so they appear once, in a block tagged `bash`, and paste unchanged into PowerShell on Windows, into bash or zsh on Linux, and into zsh on macOS.

Most of the rest of this note runs ON the minipc, in an SSH session, on Debian. Those blocks are Linux commands and deliberately have no PowerShell variant, because there is no Windows shell at the other end of the connection. The two places where a command runs on your own machine instead, the skills sync from `agent-standards` and the SSH tunnel, carry both variants.

### Repo-as-deployable-unit

The intent of this fork is that the GitHub repo IS the deployable unit: two
fresh `git clone`s on the minipc, the fork repository and its nested
`hermes-data/` repository, give you everything except secrets and runtime
state.

One host directory carries hermes' own half of it. `./hermes-data/` is
bind-mounted at `/opt/data` inside the container, which is hermes' home
directory, so everything hermes writes about itself lands back there on the
host. It is its own git repository, a clone of the private
`Lukk17/hermes-projects` (branch `master`), not a submodule. Its own
`hermes-data/.gitignore` then splits that one directory in two.

Tracked by `hermes-data/.gitignore`, and therefore in the `hermes-projects`
clone on the minipc:

- `./hermes-data/config.yaml`: model, provider, skills paths, Discord channel prompts.
- `./hermes-data/SOUL.md`: the persona.
- `./hermes-data/cron/jobs.json`: the schedule.
- `./hermes-data/memories/MEMORY.md` and `USER.md`: what hermes has learned.
- `./hermes-data/projects/`: the project workspaces.
- `./hermes-data/scripts/*.sh`: the top-level cron entry scripts.
- `./hermes-data/skills/`: skills hermes installed or wrote at runtime, with `.usage.json` and `.bundled_manifest`.
- `./hermes-data/plugins/`, `hooks/`, `skins/`: plugins, hooks and skins added at runtime.
- `./hermes-data/plans/`, `workspace/`, `local/`: plans, workspace and local folders written at runtime.
- `./hermes-data/.env.example`: the template for `hermes-data/.env`, with placeholders and no real values.

Ignored by `hermes-data/.gitignore`, and therefore per-machine:

- `./hermes-data/state.db`, `sessions/`, `logs/`, `cache/`, `kanban.db`: sessions, logs, caches.
- `./hermes-data/auth.json`: OAuth tokens. Log in again on the minipc.
- `./hermes-data/.env`: runtime secrets hermes and its child processes read.
- `./hermes-data/projects/*/.venv/`: per-project virtualenvs, rebuilt in the container.
- `./hermes-data/skills/.curator_backups/`, `skills/.usage.json.lock`, `skills/.curator_state`, `skills/.hub/audit.log`: curator snapshots, a lock file, the curator's per-machine last-run state and a log.

Plus, tracked in the fork repository's own root:

- `.agents/skills/`: curated skills, mounted read-only at `/opt/data/external-skills/`.
- `./skills/`: bundled hermes skills, mounted read-only at `/opt/data/bundled-skills/`.
- `docker-compose.override.yml`, `Dockerfile.fork`: container wiring.
- `.env` (gitignored): compose-time values, including `HERMES_UID`/`HERMES_GID`.

The fork is a real rebase target: `git fetch upstream && git rebase v<TAG>`
on `master` does not conflict with any of the above because upstream does
not ship `fork/`, `hermes-data/`, `.agents/skills/`, or `./skills/`, and
because `hermes-data/` is now a separate git repository that a rebase of the
fork never touches at all.

See `fork/NOTE-7-updating-from-upstream.md` for the rebase procedure.

### What "pull on the other machine and it is all there" actually means

The dev box and the minipc each hold two clones: the fork repository, and
`hermes-data/` as its own clone of the private `hermes-projects`. On the dev
box, after a session where hermes updated its SOUL, wrote a memory, or added a
cron job, those edits are sitting in the `hermes-data/` working tree as
ordinary modified files, because the container wrote them straight through
the bind mount:

```bash
cd hermes-data
```

```bash
git status
```

Commit and push them like any other change, still from inside `hermes-data/`:

```bash
git add -A
```

```bash
git commit -m "state: soul, memories, cron"
```

```bash
git push
```

On the minipc:

```bash
cd /opt/hermes-fork/hermes-data
```

```bash
git pull
```

```bash
cd ..
```

```bash
docker compose up -d
```

The gateway comes back with the same persona, the same memories, the same cron
schedule and the same project sources. What it does NOT bring across is the
per-machine half listed above: log in to the LLM provider again, put the
runtime secrets in `hermes-data/.env`, and rebuild the two project venvs
inside the container. Conversation history does not travel either, since
`state.db` is ignored.

One thing to watch: the same file being edited on both machines conflicts like
any other tracked file. `SOUL.md` and `memories/MEMORY.md` are the realistic
candidates, because hermes writes them itself on whichever box is running. Keep
one box authoritative, or pull before you start a session on the other.

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
```

Expect something like `192.168.1.42/24` on the same subnet as your laptop. This runs on the minipc, so there is no PowerShell variant.

### Files to copy to the minipc

Because the repo is deployable as-is, the rsync step in earlier revisions is
replaced by two `git clone`s (or `git pull`s if already cloned). The minipc
needs:

| Path on minipc | Source | Notes |
|---|---|---|
| `/opt/hermes-fork/` (the project root) | `git clone` of `hermes-agent` | the fork's own tracked content: `.agents/skills/`, `fork/`, `docker-compose.yml`, `docker-compose.override.yml`, `Dockerfile.fork` |
| `/opt/hermes-fork/hermes-data/` | `git clone` of the private `hermes-projects`, into the `hermes-data` subdirectory, before the first container start | `config.yaml`, `SOUL.md`, `cron/jobs.json`, `memories/`, `projects/`, `scripts/`, `skills/`, `plugins/`, `hooks/`, `skins/`, `plans/`, `workspace/`, `local/`, `.env.example` |
| `/opt/hermes-fork/.env` | hand-written, from `.env.fork.example` | compose-time values and the container uid, gitignored |
| `/opt/hermes-fork/hermes-data/.env` | hand-written | runtime secrets hermes child processes read, gitignored |

That is it. No rsync, no source tree, no `.venv`, no `node_modules`.

Bootstrap on a fresh minipc. Every block below runs on the minipc over SSH, so
each one is Linux-only:

```bash
sudo apt update
```

```bash
sudo apt install -y docker.io docker-compose-plugin git
```

```bash
sudo mkdir -p /opt/hermes-fork
```

```bash
sudo chown $USER:$USER /opt/hermes-fork
```

```bash
cd /opt/hermes-fork
```

```bash
git clone https://github.com/Lukk17/hermes-agent.git .
```

`hermes-data/` is its own git repository, a clone of the private
`Lukk17/hermes-projects` (branch `master`), not a submodule. Clone it next,
before the first container start: `docker compose up` creates `hermes-data/`
itself if it does not exist, and `git clone` refuses to clone into a
directory that already has files in it. `hermes-projects` is private, so
authenticate to GitHub on this machine first, either `gh auth login` or a
credential helper backed by a personal access token:

```bash
gh auth login
```

```bash
git clone https://github.com/Lukk17/hermes-projects.git hermes-data
```

```bash
cp .env.fork.example .env
```

Fill in the API keys in `.env`. The Discord bot token does not belong here, it
goes in `hermes-data/.env`, because hermes strips messaging and provider
credentials from every subprocess it spawns and that file is the one each child
re-reads at startup. Full reasoning in `fork/NOTE-3-discord.md`.

Then pin the container's user id to yours. This matters on the minipc and not
on a Windows dev box, because native Linux is the only host that passes real
file ownership through a bind mount. The container drops to an internal
`hermes` user, uid 10000 by default; if that uid does not own the checkout,
every write the agent makes under `/opt/data` fails with EACCES, which covers
`SOUL.md`, the memories, the cron jobs and every project file. Compose cannot
run a shell, so it cannot work this out for itself. This one is Linux-only in a
stronger sense than the rest of the note: it reads the calling user's numeric
uid and gid, which Windows does not have, so there is no PowerShell version
worth writing. Run it once, from the repo root, and compose reads `.env` on
every `up` from then on:

```bash
printf 'HERMES_UID=%s\nHERMES_GID=%s\n' "$(id -u)" "$(id -g)" >> .env
```

Confirm it took effect after the first `up`:

```bash
docker compose exec gateway id
```

Then write `docker-compose.minipc.yml` as described in the next section. Only after that file exists can you pull, because pulling before it is in place would try to build or fetch the wrong images:

```bash
docker compose -f docker-compose.yml -f docker-compose.minipc.yml pull
```

```bash
docker compose -f docker-compose.yml -f docker-compose.minipc.yml up -d
```

Every later `docker compose` command on the minipc needs the same `-f` pair. Export it once per shell to avoid repeating it. `export` is a Unix shell builtin and this shell is on the minipc, so there is no PowerShell variant:

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
  `./.agents/skills:/opt/data/external-skills:ro`,
  `./skills:/opt/data/bundled-skills:ro`, plus the two read-only re-mounts on
  top of the first one, `./hermes-data/config.yaml:/opt/data/config.yaml:ro`
  and
  `./hermes-data/scripts/crypto-monitor-daily.sh:/opt/data/scripts/crypto-monitor-daily.sh:ro`.
  `SOUL.md`, `cron/jobs.json`, `memories/` and `projects/` need no line of
  their own, they are already inside the directory mount.
- Set `HERMES_SKIP_CONFIG_MIGRATION=1` on both services. Without it the boot
  hook tries to rewrite the read-only `config.yaml` and fails.
- Reproduce `extra_hosts: ["host.docker.internal:host-gateway"]` on the
  gateway.
- Use `env_file: .env` instead of the override's per-key `environment:` block.
  Compose auto-loads `.env` for `${VAR}` substitution, but `env_file:` also
  pushes every variable into the container, which avoids maintaining two
  parallel lists.
- Keep `network_mode: host` and the dashboard command
  `["dashboard", "--host", "127.0.0.1", "--port", "9119", "--no-open"]`.

The skills mount targets are `/opt/data/external-skills` and
`/opt/data/bundled-skills`. Those two paths are what `skills.external_dirs` in
`hermes-data/config.yaml` points at; getting either wrong means the skills
silently do not load.

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
original (correct) git checkout command works without gymnastics. This one
runs on your own machine, in the repo checkout, not on the minipc, so it gets
both variants.

PowerShell:

```powershell
foreach ($d in Get-ChildItem -Directory .agents/skills) { git checkout agent-standards/master -- ".agents/skills/$($d.Name)/" 2>$null }
```

Unix shell:

```bash
for d in .agents/skills/*/; do git checkout agent-standards/master -- "$d" 2>/dev/null; done
```

This overwrites local files with the upstream version. It only updates
skills that already exist locally. New skills in `agent-standards` are NOT
pulled. To add a brand new skill, use `git archive` plus `tar` with
`--strip-components` to relocate the tree from `.agents/skills/<new>/` to
the destination. Also on your own machine, so both variants again.

PowerShell:

```powershell
git archive agent-standards/master ".agents/skills/<new-skill-name>" -o "$env:TEMP\new-skill.tar"
```

```powershell
New-Item -ItemType Directory -Force ".agents/skills/<new-skill-name>"
```

```powershell
tar -xf "$env:TEMP\new-skill.tar" -C ".agents/skills/<new-skill-name>" --strip-components=3
```

```powershell
Remove-Item "$env:TEMP\new-skill.tar" -Force
```

Unix shell:

```bash
git archive agent-standards/master ".agents/skills/<new-skill-name>" -o /tmp/new-skill.tar
```

```bash
mkdir -p ".agents/skills/<new-skill-name>"
```

```bash
tar -xf /tmp/new-skill.tar -C ".agents/skills/<new-skill-name>" --strip-components=3
```

```bash
rm -f /tmp/new-skill.tar
```

After either operation, no container restart is needed. Hermes rescans
`external_dirs` on session start; to force a rescan without restarting:

```bash
docker compose exec gateway hermes skills reload
```

### Fork plugin (optional, future use)

Hermes looks for plugins in its home directory, which is `hermes-data/` on the
host. The fork does NOT ship one. The per-project conventions under
`hermes-data/projects/` plus the channel_prompts in `hermes-data/config.yaml`
cover the same needs without a plugin.

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

`hermes-data/plugins/` is in `hermes-data/.gitignore`'s re-include list, so
a plugin created there is tracked and travels with the `hermes-projects` clone
like `config.yaml`, `SOUL.md` and `projects/`. Commit it from inside
`hermes-data/`. No new bind mount is needed: the directory is already inside
the `/opt/data` mount.

### Bring it up

```bash
cd /opt/hermes-fork
```

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml
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
```

Then open `http://localhost:9119` in the browser on your laptop. This block runs on your laptop rather than on the minipc, and `ssh` is the same command in PowerShell on Windows, in bash or zsh on Linux, and in zsh on macOS, so one block covers all three.

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
```

```bash
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
```

```bash
sudo nginx -t
```

```bash
sudo systemctl reload nginx
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
- **Backups.** Add `./hermes-fork/hermes-data/` to Proxmox's backup schedule
  (PBS or vzdump). One directory covers everything: the tracked half (config,
  persona, cron, memories, projects) is also in `hermes-data`'s own git
  repository (`hermes-projects`), and the untracked half (`state.db`
  sessions, `auth.json` OAuth, `kanban.db` board state, `.env`) exists
  nowhere else.
- **Firewall.** If Proxmox enables a guest firewall by default, open port
  22 (for SSH) and 80 (for nginx) at the Proxmox firewall level. Port 9119
  stays loopback-only and never appears on the VM's interfaces.

### Updating to a new upstream image

After you push a new build to Docker Hub from the dev box:

```bash
cd /opt/hermes-fork
```

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml
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

### hermes-data is its own repository, selectively tracked by its own .gitignore

`hermes-data/` is a separate git repository, a clone of the private
`Lukk17/hermes-projects` (branch `master`), not a submodule. The fork
repository's own `.gitignore` ignores the whole directory with one line:

```
/hermes-data/
```

Inside `hermes-data/`, its own `.gitignore` is what holds two kinds of file
apart. It ignores everything by default and then re-includes the parts worth
carrying between machines:

```
/*
!/.gitignore
!/.env.example
!/config.yaml
!/SOUL.md
!/cron
/cron/*
!/cron/jobs.json
!/memories
/memories/*
!/memories/*.md
!/projects
!/scripts
/scripts/*
!/scripts/*.sh
!/skills
!/plugins
!/hooks
!/skins
!/plans
!/workspace
!/local
/skills/.curator_backups/
/skills/.usage.json.lock
/skills/.curator_state
/skills/.hub/audit.log
data/
```

The re-include pairs look repetitive on purpose. Git will not look inside an
ignored directory, so to reach one file in a subdirectory you have to
un-ignore the directory, re-ignore its contents, then un-ignore the one file.

To see which side of the line any file inside `hermes-data/` falls on, ask
git rather than reading the pattern list, from inside `hermes-data/` so the
check runs against its own repository:

```bash
cd hermes-data
```

```bash
git check-ignore -v <path>
```

No output means the file is tracked and travels with the `hermes-projects`
clone.

### Per-project subdirectories (crypto-monitor, osint)

Projects live in `hermes-data/projects/<name>/` on the host, which the
container sees at `/opt/data/projects/<name>/`. Hermes does not create these
directories on its own. Configure each
Discord channel's agent to stick to its own subdir via `channel_prompts`
in `hermes-data/config.yaml` (see `fork/NOTE-3-discord.md`):

```yaml
discord:
  channel_prompts:
    '<crypto-monitor-channel-id>': |
      ... persona ...
      All persistent files for this project go to /opt/data/projects/crypto-monitor/.
      Treat it as the project's working tree.
    '<osint-channel-id>': |
      ... persona ...
      All persistent files for this project go to /opt/data/projects/osint/.
```

The path inside the container is `/opt/data/projects/<name>/`. There is no
separate bind mount for it: `hermes-data/projects/` sits inside
`hermes-data/`, which is mounted whole at `/opt/data`.

This is convention, not enforcement. The agent follows the instruction
because the prompt says so. Agents in other channels do not see or touch
those subdirs unless explicitly asked. For hard isolation you need separate
Hermes profiles (`hermes -p crypto`, `hermes -p osint`) running as
separate containers with separate Discord bot users.

`hermes-data/projects/<name>/` is the canonical spot for project workspaces
because it is tracked in `hermes-data`'s own git repository, so the sources
travel to the other machine with the `hermes-projects` clone. Each project's
`.venv/` does not, and has to be built inside the container once per machine
(see `fork/NOTE-1-install.md`, step 6b).

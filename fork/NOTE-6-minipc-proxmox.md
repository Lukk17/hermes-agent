# Deploying the fork to a minipc (Proxmox VM with Docker Engine)

Assumes you have already followed `fork/NOTE-1-install.md` on a Windows or
Linux dev box, you have built and pushed the images to Docker Hub, and you
have a Proxmox VM running Ubuntu Server LTS, reachable on your LAN via SSH.
Docker Engine and the Compose plugin are not assumed to be installed yet.
Installing them is the first step of the numbered sequence below.

The goal of this note is the *minipc-specific* deltas: which files to copy,
how to pull the prebuilt image instead of building from source, how to keep
`.agents/skills/` in sync from your standards repo, and the Proxmox networking
gotcha. Access to the minipc and to the dashboard is SSH only, there is no
LAN-facing reverse proxy.

### Shell variants in this note

Docker and git commands are identical in PowerShell and in a Unix shell, so they appear once, in a block tagged `bash`, and paste unchanged into PowerShell on Windows, into bash or zsh on Linux, and into zsh on macOS.

Most of the rest of this note runs ON the minipc, in an SSH session, on Ubuntu. Those blocks are Linux commands and deliberately have no PowerShell variant, because there is no Windows shell at the other end of the connection. The two places where a command runs on your own machine instead, the skills sync from `agent-standards` and the SSH tunnel, carry both variants.

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
- `.env` (gitignored): compose-time values, including `HERMES_UID`/`HERMES_GID`, and on the minipc the `COMPOSE_FILE` line that selects `docker-compose.minipc.yml`.

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

On the minipc. The `docker compose up -d` at the end runs from `/opt/docker-stack/hermes` and takes `docker-compose.yml` plus `docker-compose.minipc.yml` from the `COMPOSE_FILE` line in the minipc's `.env`, see "Every docker compose command on the minipc uses both files" below:

```bash
cd /opt/docker-stack/hermes/hermes-data
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
NAT. NAT gives the VM no LAN IP, which makes SSH from your laptop awkward.

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
| `/opt/docker-stack/hermes/` (the project root) | `git clone` of `hermes-agent` | the fork's own tracked content: `.agents/skills/`, `fork/`, `docker-compose.yml`, `docker-compose.override.yml`, `docker-compose.minipc.yml`, `Dockerfile.fork` |
| `/opt/docker-stack/hermes/hermes-data/` | `git clone` of the private `hermes-projects`, into the `hermes-data` subdirectory, before the first container start | `config.yaml`, `SOUL.md`, `cron/jobs.json`, `memories/`, `projects/`, `scripts/`, `skills/`, `plugins/`, `hooks/`, `skins/`, `plans/`, `workspace/`, `local/`, `.env.example` |
| `/opt/docker-stack/hermes/.env` | hand-written, from `.env.fork.example` | compose-time values, the container uid and the `COMPOSE_FILE` line, gitignored |
| `/opt/docker-stack/hermes/hermes-data/.env` | hand-written, from `hermes-data/.env.example` | runtime secrets hermes child processes read, gitignored |

That is it. No rsync, no source tree, no `.venv`, no `node_modules`.

### Use a minipc-only compose file, not an edit to docker-compose.yml

The minipc pulls prebuilt images instead of building. Do NOT edit
`docker-compose.yml` to achieve that: it is upstream-owned, so every edit to it
becomes a rebase conflict on the next upstream sync. Do not edit
`docker-compose.override.yml` either, because it is what the dev box builds
with.

Instead, a third file, `docker-compose.minipc.yml`, is tracked in the fork
repository and selected explicitly with `-f`. Compose applies files
left-to-right, so the minipc file wins. It is NOT auto-merged the way
`docker-compose.override.yml` is, and naming `-f` suppresses the automatic
override merge, which is what you want here: the override carries `build:`
blocks the minipc cannot satisfy.

Local build tags on the dev box are `hermes-agent:upstream` (the untouched
upstream image), `hermes-agent:fork` (gateway) and `hermes-agent:fork-dashboard`
(dashboard). On Docker Hub they are published as
`lukk17/hermes-agent-gateway` and `lukk17/hermes-agent-dashboard`.

`docker-compose.minipc.yml`:

- Resets `build:` to nothing (`!reset null`) and replaces it with
  `image: lukk17/hermes-agent-gateway:latest` for the gateway and
  `image: lukk17/hermes-agent-dashboard:latest` for the dashboard. Both are
  pinned to `:latest` on purpose, not a versioned tag: the user keeps `:latest`
  always pointing at a working build, so this file never needs an edit on a
  version update, and `docker compose pull` alone picks up the newest image.
- Reproduces the volume set the override provides, with `!override` so the
  list replaces the base file's `~/.hermes:/opt/data` mount instead of
  concatenating with it: `./hermes-data:/opt/data`,
  `./.agents/skills:/opt/data/external-skills:ro`,
  `./skills:/opt/data/bundled-skills:ro`, plus the two read-only re-mounts on
  top of the first one, `./hermes-data/config.yaml:/opt/data/config.yaml:ro`
  and
  `./hermes-data/scripts/crypto-monitor-daily.sh:/opt/data/scripts/crypto-monitor-daily.sh:ro`.
  `SOUL.md`, `cron/jobs.json`, `memories/` and `projects/` need no line of
  their own, they are already inside the directory mount.
- Sets `HERMES_SKIP_CONFIG_MIGRATION=1` on both services. Without it the boot
  hook tries to rewrite the read-only `config.yaml` and fails.
- Reproduces `extra_hosts: ["host.docker.internal:host-gateway"]` on the
  gateway.
- Spells out each secret in the gateway's `environment:` block with `${VAR}`
  substitution, the same keys as `docker-compose.override.yml`, rather than
  `env_file: .env`. `env_file:` would also push `DISCORD_BOT_TOKEN` and
  `MINIMAX_API_KEY` into the gateway's own process environment, which the
  override intentionally keeps out of it, since those two live only in
  `hermes-data/.env`. Keep the two lists in sync when a new secret is added
  (see "Need a new key" in `fork/AGENTS.md`).
- Keeps `network_mode: host` (inherited from `docker-compose.yml`, no line of
  its own needed) and the dashboard command
  `["dashboard", "--host", "127.0.0.1", "--port", "9119", "--no-open"]`.

The skills mount targets are `/opt/data/external-skills` and
`/opt/data/bundled-skills`. Those two paths are what `skills.external_dirs` in
`hermes-data/config.yaml` points at; getting either wrong means the skills
silently do not load.

Verify the merge did what it should before trusting it on a real machine,
comparing against the dev box's override by key name only, never printing
secret values:

```bash
docker compose -f docker-compose.yml -f docker-compose.minipc.yml config --quiet
```

### Every docker compose command on the minipc uses both files

On the minipc the stack always runs as `docker-compose.yml` plus `docker-compose.minipc.yml`, never with `docker-compose.override.yml`. Plain `docker compose` with no `-f` and no `COMPOSE_FILE` would merge the override automatically and try to build images the minipc cannot build, so every compose command there has to name the pair one way or another.

The permanent way is one line in the minipc's repo-root `.env`. Compose v2 reads the `.env` file in the project directory not only for `${VAR}` substitution but also for its own pre-defined settings, `COMPOSE_FILE` among them. With that line in place, a plain `docker compose ...` run from `/opt/docker-stack/hermes` uses the pair in every shell, every SSH session and every one-shot `ssh minipc '...'` command, with nothing to export. Bootstrap step 6 below adds it. Run once, from `/opt/docker-stack/hermes`:

```bash
printf 'COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml\n' >> .env
```

Check that Compose picked it up. The output must list `lukk17/hermes-agent-gateway:latest` and `lukk17/hermes-agent-dashboard:latest`, and not the locally built `hermes-agent:fork` or `hermes-agent:fork-dashboard`:

```bash
docker compose config --images
```

Rules that keep this reliable:

- Run every minipc compose command from `/opt/docker-stack/hermes`. Compose looks for `.env` in the current directory, so from anywhere else the line is not read.
- A `COMPOSE_FILE` exported in the shell wins over the `.env` line. Do not export one on the minipc.
- A line in `~/.bashrc` is the weaker choice: it reaches interactive bash sessions only, not one-shot SSH commands or cron, and it would also apply to every other Compose project that user runs.
- Without the `.env` line, name the pair on each command instead, for example `docker compose -f docker-compose.yml -f docker-compose.minipc.yml up -d`. Explicit `-f` flags always override `COMPOSE_FILE`.

The dev box never gets this line. Its `.env` has no `COMPOSE_FILE`, so Compose there uses `docker-compose.yml` plus the automatically merged `docker-compose.override.yml`, which builds the images locally. The commands in `fork/NOTE-1-install.md`, `fork/NOTE-5-operations.md` and the build steps of `fork/NOTE-7-updating-from-upstream.md` rely on that.

### Bootstrap on a fresh minipc

Every block below runs on the minipc over SSH, so each one is Linux-only.

1. Install Docker Engine from Docker's official repository, not the `docker.io`
   package (it lags badly and ships no Compose plugin):

   ```bash
   sudo install -m 0755 -d /etc/apt/keyrings
   ```

   ```bash
   sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
   ```

   ```bash
   sudo chmod a+r /etc/apt/keyrings/docker.asc
   ```

   ```bash
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   ```

   ```bash
   sudo apt update
   ```

   ```bash
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin git
   ```

   ```bash
   sudo usermod -aG docker $USER
   ```

   ```bash
   newgrp docker
   ```

2. Authenticate to GitHub. `hermes-projects` is private, so this has to happen
   before the clone in step 4:

   ```bash
   gh auth login
   ```

3. Create `/opt/docker-stack/hermes` and clone the fork into it:

   ```bash
   sudo mkdir -p /opt/docker-stack/hermes
   ```

   ```bash
   sudo chown $USER:$USER /opt/docker-stack/hermes
   ```

   ```bash
   cd /opt/docker-stack/hermes
   ```

   ```bash
   git clone https://github.com/Lukk17/hermes-agent.git .
   ```

4. Clone `hermes-data` next, before the first container start: `docker compose
   up` creates `hermes-data/` itself if it does not exist, and `git clone`
   refuses to clone into a directory that already has files in it.
   `hermes-data/` is its own git repository, a clone of the private
   `Lukk17/hermes-projects` (branch `master`), not a submodule:

   ```bash
   git clone https://github.com/Lukk17/hermes-projects.git hermes-data
   ```

5. Copy both env templates and fill them in. `.env` at the repo root holds
   compose-time values and the container uid. `hermes-data/.env` holds the
   runtime secrets hermes and every child process it spawns re-reads at
   startup, including the Discord bot token. Full reasoning in
   `fork/NOTE-3-discord.md`:

   ```bash
   cp .env.fork.example .env
   ```

   ```bash
   cp hermes-data/.env.example hermes-data/.env
   ```

   Fill in the values in both files, then pin the container's user id to
   yours. This matters on the minipc and not on a Windows dev box, because
   native Linux is the only host that passes real file ownership through a
   bind mount. The container drops to an internal `hermes` user, uid 10000 by
   default. If that uid does not own the checkout, every write the agent
   makes under `/opt/data` fails with EACCES, which covers `SOUL.md`, the
   memories, the cron jobs and every project file. Compose cannot run a
   shell, so it cannot work this out for itself. Run it once, from the repo
   root, and compose reads `.env` on every `up` from then on:

   ```bash
   printf 'HERMES_UID=%s\nHERMES_GID=%s\n' "$(id -u)" "$(id -g)" >> .env
   ```

6. Make every later `docker compose` command on the minipc use `docker-compose.yml` plus `docker-compose.minipc.yml`, permanently, by adding the `COMPOSE_FILE` line to the same `.env`. Why this and not an `export`, see "Every docker compose command on the minipc uses both files" above:

   ```bash
   printf 'COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml\n' >> .env
   ```

   Confirm it took effect. The output must list the two `lukk17/` images and not the locally built `hermes-agent:fork` or `hermes-agent:fork-dashboard`:

   ```bash
   docker compose config --images
   ```

   Every block from here to the end of this sequence runs from `/opt/docker-stack/hermes`, where Compose finds that `.env`.

7. Pull the prebuilt images:

   ```bash
   docker compose pull
   ```

8. Start the containers:

   ```bash
   docker compose up -d
   ```

   Confirm the uid mapping took effect:

   ```bash
   docker compose exec gateway id
   ```

9. Build each project's venv inside the container. Required, not optional:
   see `fork/NOTE-1-install.md` step 6b for the exact commands, run them
   against this container the same way.

10. Configure an LLM provider and log in: see `fork/NOTE-2-llm-providers.md`.
    Come back here once `hermes doctor` shows it logged in.

11. Verify end to end:

    ```bash
    docker compose exec gateway hermes doctor
    ```

    ```bash
    docker compose exec gateway hermes cron list
    ```

    Then send a real message to the bot from Discord and confirm it replies,
    and check for errors:

    ```bash
    docker compose logs -f gateway
    ```

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

Run it from the repo root. On the dev box that is all it needs. On the minipc, run it from `/opt/docker-stack/hermes` after a `git pull` of the fork has brought the new skills across, and the `COMPOSE_FILE` line in the minipc's `.env` supplies the compose pair.

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

On the minipc, run it from `/opt/docker-stack/hermes` so the `COMPOSE_FILE` line in its `.env` applies.

One caveat: hermes' own install path additionally passes `--constraint` from
`_core_constraints_file()` (`tools/lazy_deps.py:727-736`), pinning shared
transitive dependencies to the core venv's versions. A hand-run install skips
that and can pull an incompatible transitive dependency.

`hermes-data/plugins/` is in `hermes-data/.gitignore`'s re-include list, so
a plugin created there is tracked and travels with the `hermes-projects` clone
like `config.yaml`, `SOUL.md` and `projects/`. Commit it from inside
`hermes-data/`. No new bind mount is needed: the directory is already inside
the `/opt/data` mount.

### Opening the dashboard

Access to the minipc is SSH only. There is no LAN-facing reverse proxy and no
port 80 listener. The dashboard is at `http://localhost:9119` **on the minipc
itself only**. From your laptop, SSH tunnel:

```bash
ssh -L 9119:localhost:9119 user@<minipc-lan-ip>
```

Then open `http://localhost:9119` in the browser on your laptop. This block
runs on your laptop rather than on the minipc, and `ssh` is the same command
in PowerShell on Windows, in bash or zsh on Linux, and in zsh on macOS, so one
block covers all three. See `fork/NOTE-4-secure-remote-access.md` for the
general version of this tunnel and why `--insecure --host 0.0.0.0` is never
the alternative.

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
- **Backups.** Add `/opt/docker-stack/hermes/hermes-data/` to Proxmox's backup
  schedule (PBS or vzdump). One directory covers everything: the tracked half
  (config, persona, cron, memories, projects) is also in `hermes-data`'s own
  git repository (`hermes-projects`), and the untracked half (`state.db`
  sessions, `auth.json` OAuth, `kanban.db` board state, `.env`) exists
  nowhere else.
- **Firewall.** If Proxmox enables a guest firewall by default, open port 22
  (for SSH) at the Proxmox firewall level. Port 9119 stays loopback-only,
  reached only through the SSH tunnel above, and never appears on the VM's
  interfaces.

### Updating to a new upstream image

After you push a new build to Docker Hub from the dev box, on the minipc. Both compose commands take `docker-compose.yml` plus `docker-compose.minipc.yml` from the `COMPOSE_FILE` line in the minipc's `.env`, see "Every docker compose command on the minipc uses both files" above:

```bash
cd /opt/docker-stack/hermes
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
**/data/*
!projects/crypto-monitor/data/reports/
!projects/crypto-monitor/data/reports/**
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

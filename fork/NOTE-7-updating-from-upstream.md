# Updating the fork from upstream hermes-agent

This note describes how to pull the latest upstream code into this fork, resolve conflicts, rebuild the Docker images, tag them, and push to Docker Hub. The workflow mirrors what `NOTE-6-minipc-proxmox.md` does for deployments, but for source-level syncs.

## Branches in this fork

| Branch | Purpose | Workflow |
|---|---|---|
| `main` | Auto-tracks `upstream/main`. You never commit here locally. Safe to delete if you want; re-create with `git branch main upstream/main`. | Receives upstream commits only, used as a reference for `git diff upstream/main..master`. |
| `master` | The production build branch. Carries fork-specific files on top of an upstream release tag. | Rebased onto the latest upstream release tag each update cycle. |

Hermes upstream uses `main` (not `master`) since late 2025. This fork was originally cloned from a `master`-named upstream and stays on `master` by choice.

## Image tag layout

After each update cycle, the built images carry these names:

| Local tag | Pushed as | Built from |
|---|---|---|
| `hermes-agent:upstream` | not pushed | the untouched upstream `Dockerfile`, via the build-only `upstream-base` service in `docker-compose.override.yml` |
| `hermes-agent:fork` | `lukk17/hermes-agent-gateway:latest`<br>`lukk17/hermes-agent-gateway:v<UPSTREAM_TAG>-lukk` | `Dockerfile.fork` with `BASE_IMAGE=hermes-agent:upstream` (gateway service) |
| `hermes-agent:fork-dashboard` | `lukk17/hermes-agent-dashboard:latest`<br>`lukk17/hermes-agent-dashboard:v<UPSTREAM_TAG>-lukk` | the same `Dockerfile.fork` and the same base (dashboard service) |

`Dockerfile.fork` is the fork's tools layer: OSINT apt dependencies, pyenv with
Python 3.11 (crypto-monitor) and 3.12 (osint), the
`chown -R hermes:hermes /opt/hermes/ui-tui` fix, and a
`/opt/data/.local/bin/hermes` symlink. It takes `BASE_IMAGE` as a build arg so
the upstream image keeps its own tag and is never rebuilt by the fork's
Dockerfile. Both the gateway and the dashboard build from it; the only
difference between them is the runtime command in compose.

Two older names are retired. The dashboard image was `:fork-tui`, renamed to
`:fork-dashboard` because the image is the dashboard service, not a TUI. On
Docker Hub the gateway repository was `lukk17/hermes-agent`, now
`lukk17/hermes-agent-gateway`, so the two published repositories are symmetric.

## Pre-flight

```powershell
# Verify the upstream remote exists
git remote -v
# expect: upstream  https://github.com/NousResearch/hermes-agent.git  (fetch)
#          upstream  https://github.com/NousResearch/hermes-agent.git  (push)

# If upstream is missing:
git remote add upstream https://github.com/NousResearch/hermes-agent.git
```

If you forked your repository directly from `NousResearch/hermes-agent`, `origin` already points to upstream. Add your own fork as `origin` and use `upstream` for the NousResearch one if needed:

```powershell
git remote set-url origin https://github.com/Lukk17/hermes-agent.git
```

## Update workflow (assume the current target release is `v2026.8.27`)

### 1. Sync metadata, list available tags

```powershell
git fetch upstream
git fetch upstream --tags
git tag -l "v20*" --sort=-v:refname
```

The output is the list of released versions, newest first, for example:

```
v2026.8.27
v2026.8.19
v2026.8.16.2
v2026.8.13
v2026.7.30
v2026.7.20
v2026.7.7.2
v2026.7.7
...
```

Pick the one you want to consume. The date format embedded in the tag is `vYYYY.M.D` (year.month.day), with optional `.2` patch suffix.

### 2. Switch to master and rebase onto the chosen tag

```powershell
git checkout master
git rebase v2026.8.27
```

`git rebase` walks every commit upstream made between your fork base and `v2026.8.27` and replays your fork commits on top. With this fork's history being a few small commits and `v2026.8.27` being thousands of upstream commits ahead, expect conflicts only on files the fork actually modifies (`docker-compose.override.yml`, `Dockerfile.fork`, `.gitignore`, `fork/NOTE-*.md`, anything under `.agents/skills/`, etc.). Files the fork never touches will replay cleanly.

### 3. Resolve conflicts

For each file flagged by git, decide one of:

| Decision | Command | When |
|---|---|---|
| Keep upstream version entirely | `git checkout --theirs path` | Upstream renamed or restructured the file, and your fork change is obsolete |
| Keep fork version entirely | `git checkout --ours path` | Upstream deleted the file, or the fork change is canonical (most of your fork NOTES fall here) |
| Manual merge | open in editor, resolve hunks, `git add path` | Both sides made changes you need to keep |

After each file:

```powershell
git add resolved-path
git rebase --continue
```

If you get stuck at any point:

```powershell
git rebase --abort    # back to where you started
git rebase --skip     # drop the upstream commit entirely (last resort)
```

### 4. Sanity-check the resolved tree

```powershell
git diff --stat upstream/v2026.8.27..master
# expect: only the fork-specific files differ

git diff upstream/v2026.8.27..master -- docker-compose.override.yml Dockerfile.fork .gitignore fork/
# eyeball each diff to confirm overrides and NOTES still make sense with new upstream base
```

### 5. Build the images

```powershell
docker compose --profile build build upstream-base
```

```powershell
docker compose build gateway
```

```powershell
docker compose build dashboard
```

Build order matters only for the first command: `upstream-base` produces
`hermes-agent:upstream`, which is the `BASE_IMAGE` both fork images sit on.
`gateway` and `dashboard` are independent of each other.

### 6. Tag and push to Docker Hub

```powershell
$tag = "v2026.8.27-lukk"
```

```powershell
docker tag hermes-agent:fork lukk17/hermes-agent-gateway:$tag
```

```powershell
docker tag hermes-agent:fork lukk17/hermes-agent-gateway:latest
```

```powershell
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:$tag
```

```powershell
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:latest
```

```powershell
docker push lukk17/hermes-agent-gateway:$tag
```

```powershell
docker push lukk17/hermes-agent-gateway:latest
```

```powershell
docker push lukk17/hermes-agent-dashboard:$tag
```

```powershell
docker push lukk17/hermes-agent-dashboard:latest
```

`hermes-agent:upstream` is a local build artifact and is never pushed. Each
fork-built image carries two Docker Hub tags. Use the versioned one
(`v2026.8.27-lukk`) for any deployment that should be reproducible, and
`:latest` for the most recent build.

### 7. Update the minipc to consume the new image

On the dev box the minipc pulls from:

```bash
ssh user@minipc
```

```bash
cd /opt/hermes-fork && export COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml
```

```bash
git pull
```

```bash
docker compose pull
```

```bash
docker compose up -d --force-recreate gateway dashboard
```

```bash
docker compose exec gateway hermes doctor
```

```bash
docker compose exec gateway hermes cron list
```

The `COMPOSE_FILE` pair matters: `docker-compose.minipc.yml` is what replaces the
`build:` blocks with registry images. See `fork/NOTE-6-minipc-proxmox.md`.

If anything fails after the upgrade, roll back by pinning the previous image tag:

Edit `docker-compose.minipc.yml` on the minipc, set the gateway's `image:` to
`lukk17/hermes-agent-gateway:v2026.8.19-lukk`, then:

```bash
docker compose pull gateway
```

```bash
docker compose up -d --force-recreate gateway
```

Revert the `image:` line once the newer build is fixed.

## Conflict resolution cheatsheet

Patterns you will hit most often during a rebase:

### Upstream renamed an env var the fork override passes

Example: upstream `docker-compose.yml` exposes `DISCORD_GATEWAY_TOKEN`, your override still uses `DISCORD_BOT_TOKEN`.

- Update your override to the new env var name
- Update `fork/hermes-config/config.yaml` if it referenced the old name
- Leave a one-line comment in the override explaining the rename

### Upstream split a service in two

Example: upstream `dashboard` service now becomes `dashboard` plus `dashboard-assets`.

- Add the new services to your override
- Replicate your port mapping, volumes, and env wiring across both

### Upstream dropped a tool your fork relies on

Example: upstream removed `blockscout_query`, your crypto-monitor cron still calls it.

- Reimplement the dropped tool as a fork plugin under `hermes-data/plugins/hermes-fork-extras/` (per the plugin-authoring guidelines; see `fork/NOTE-7` followups for a template)
- Keep the cron job pointing at the new tool name
- Document the dependency in `fork/NOTE-<n>-<project>.md`

### Upstream added a new env var the fork should pass

Example: upstream introduced `HERMES_RUST_TOOLCHAIN_ENABLED`, your override does not pass it.

- Add it to the override, default to `false` if it is off by default
- Document the new env var in the relevant NOTE so you remember why it is in the override

### Upstream changed the TUI build path

The dashboard rebuilds the React UI on startup and needs to write into
`/opt/hermes/ui-tui`, which the upstream image seals read-only for the hermes
user. That is the whole reason `Dockerfile.fork` chowns it. There is no `--tui`
flag involved: the embedded chat surface is always on, and `--tui` is an
accepted-and-ignored compat shim
(`hermes_cli/subcommands/dashboard.py:110-124`).

If the build path moves off `/opt/hermes/ui-tui`:

- Check upstream's new `Dockerfile` for how they handle that directory's permissions
- Update `Dockerfile.fork` accordingly, rebuild, verify with `docker compose logs dashboard` that the UI build succeeds

## First-time import from an old fork

If you start with a fork that pre-dates the `master`/tag workflow above (this fork was one of them until 2026-08-31, with the original fork point on 2026-05-11), do **NOT** try to rebase 18 000 commits of upstream drift onto the tag. Two simpler paths:

### Path 1 — keep what you have, tag the current state

```powershell
git checkout master
git tag v2026.5.11-lukk fc94e319d10a4852c856dd617af4b7f8981ff5d6
# build, push, and treat v2026.5.11-lukk as your first "release"
```

This locks the fork state to the day the workflow was introduced. Future updates rebase onto upstream release tags from this baseline; the rebase deltas are then bounded by however many upstream commits land between the new tag and the current baseline.

### Path 2 — fresh re-fork from the latest tag

```powershell
git checkout v2026.8.27
git checkout -b master
# port the fork-specific files from the old branch manually:
git checkout <old-master> -- docker-compose.override.yml Dockerfile.fork .gitignore fork/ .agents/skills/
# commit
git add -A
git commit -m "feat(fork): re-fork on v2026.8.27 baseline"
# build and push as above
```

This skips the painful rebase. Future cycles are short.

## Quick reference card

```
# fetch
git fetch upstream --tags
git tag -l "v20*" --sort=-v:refname

# rebase
git checkout master
git rebase v<TAG>
# resolve conflicts, git add ..., git rebase --continue

# build + tag + push
docker compose --profile build build upstream-base
docker compose build gateway
docker compose build dashboard
docker tag hermes-agent:fork           lukk17/hermes-agent-gateway:v<TAG>-lukk
docker tag hermes-agent:fork           lukk17/hermes-agent-gateway:latest
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:v<TAG>-lukk
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:latest
docker push lukk17/hermes-agent-gateway:v<TAG>-lukk
docker push lukk17/hermes-agent-gateway:latest
docker push lukk17/hermes-agent-dashboard:v<TAG>-lukk
docker push lukk17/hermes-agent-dashboard:latest

# consume on minipc
ssh user@minipc
cd /opt/hermes-fork
export COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml
git pull
docker compose pull
docker compose up -d --force-recreate gateway dashboard
```

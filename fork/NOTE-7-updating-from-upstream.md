# Updating the fork from upstream hermes-agent

This note describes how to pull the latest upstream code into this fork, resolve conflicts, rebuild the Docker images, tag them, and push to Docker Hub. The workflow mirrors what `NOTE-6-minipc-proxmox.md` does for deployments, but for source-level syncs.

## Branches in this fork

| Branch | Purpose | Workflow |
|---|---|---|
| `main` | Auto-tracks `upstream/main`. You never commit here locally. Safe to delete if you want; re-create with `git branch main upstream/main`. | Receives upstream commits only, used as a reference for `git diff upstream/main..master`. |
| `master` | The production build branch. Carries fork-specific files on top of an upstream release tag. | Rebased onto the latest upstream release tag each update cycle. |

Hermes upstream uses `main` (not `master`) since late 2025. This fork was originally cloned from a `master`-named upstream but we keep the fork on `master` to match your openclaw convention.

## Image tag layout

After each update cycle, the built images carry these names:

| Docker image | Pushed as | Built from |
|---|---|---|
| `hermes-agent:fork` | `lukk17/hermes-agent:latest`<br>`lukk17/hermes-agent:v<UPSTREAM_TAG>-lukk` | upstream `Dockerfile` (gateway service, plain python image) |
| `hermes-agent:fork-dashboard` | `lukk17/hermes-agent-dashboard:latest`<br>`lukk17/hermes-agent-dashboard:v<UPSTREAM_TAG>-lukk` | `Dockerfile.fork` (dashboard service, adds `chown -R hermes:hermes /opt/hermes/ui-tui` so the runtime user can rebuild the TUI bundle on startup) |

The dashboard image was previously tagged `:fork-tui`. Renamed to `:fork-dashboard` because the image is the **dashboard** service, not a TUI. The dashboard page does render a TUI-like Ink/React console inside it, but the service name and the image are the dashboard. New tags drop the old `:fork-tui` alias.

If you want a single combined image, build the gateway with the dashboard `Dockerfile.fork` chained on and stop maintaining the dashboard service in compose. Two-image setup is what this fork currently uses.

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

### 5. Build both images

```powershell
docker compose build gateway
docker compose build dashboard
```

Build order matters: gateway must finish first (it produces the `:fork` tag that `Dockerfile.fork` builds on top of).

### 6. Tag and push to Docker Hub

```powershell
$tag = "v2026.8.27-lukk"

docker tag hermes-agent:fork           lukk17/hermes-agent:$tag
docker tag hermes-agent:fork           lukk17/hermes-agent:latest
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:$tag
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:latest

docker push lukk17/hermes-agent:$tag
docker push lukk17/hermes-agent:latest
docker push lukk17/hermes-agent-dashboard:$tag
docker push lukk17/hermes-agent-dashboard:latest
```

Each fork-built image carries two Docker Hub tags. Use the versioned one (`v2026.8.27-lukk`) for any deployment that should be reproducible, and `:latest` for the most recent build.

### 7. Update the minipc to consume the new image

On the dev box the minipc pulls from:

```powershell
ssh user@minipc
cd /opt/hermes-fork
git pull
docker compose pull
docker compose up -d --force-recreate gateway dashboard
docker compose exec gateway hermes doctor
docker compose exec gateway hermes cron list
```

If anything fails after the upgrade, roll back by pinning the previous image tag:

```powershell
# On the minipc
docker compose pull lukk17/hermes-agent:v2026.8.19-lukk
docker compose up -d --force-recreate gateway
```

(Adjust the gateway service compose to `image: lukk17/hermes-agent:v2026.8.19-lukk` temporarily, then revert.)

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

The dashboard runs `dashboard --tui` which rebuilds the React UI on startup. If the build path moved from `/opt/hermes/ui-tui` to something else, `Dockerfile.fork` needs updating to chown the new path or the runtime user hits EACCES.

- Check upstream's new `Dockerfile` for how they handle the TUI directory permission
- Update `Dockerfile.fork` accordingly, regenerate the image, verify with `docker compose logs dashboard` that the TUI build succeeds

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
docker compose build gateway
docker compose build dashboard
docker tag hermes-agent:fork           lukk17/hermes-agent:v<TAG>-lukk
docker tag hermes-agent:fork           lukk17/hermes-agent:latest
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:v<TAG>-lukk
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:latest
docker push lukk17/hermes-agent:v<TAG>-lukk
docker push lukk17/hermes-agent:latest
docker push lukk17/hermes-agent-dashboard:v<TAG>-lukk
docker push lukk17/hermes-agent-dashboard:latest

# consume on minipc
ssh user@minipc
cd /opt/hermes-fork
git pull
docker compose pull
docker compose up -d --force-recreate gateway dashboard
```

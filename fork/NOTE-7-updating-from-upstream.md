# Updating the fork from upstream hermes-agent

This note describes how to pull the latest upstream code into this fork, resolve conflicts, rebuild the Docker images, tag them, and push to Docker Hub. The workflow mirrors what `NOTE-6-minipc-proxmox.md` does for deployments, but for source-level syncs.

## Shell variants in this note

Docker and git commands are identical in PowerShell and in a Unix shell, so they appear once, in a block tagged `bash`, and paste unchanged into PowerShell on Windows, into bash or zsh on Linux, and into zsh on macOS. That covers nearly every command here.

The exception is the image tag in step 6, which is held in a shell variable, and variable assignment is the one piece of syntax the two shells do not share. That step carries a block per shell. The blocks in step 7 run on the minipc over SSH and are Linux-only, which is stated where they appear.

## Branches in this fork

| Branch | Purpose | Workflow |
|---|---|---|
| `main` | Auto-tracks `upstream/main`. You never commit here locally. Safe to delete if you want; re-create with `git branch main upstream/main`. | Receives upstream commits only, used as a reference for `git diff upstream/main..master`. |
| `master` | The production build branch. Carries fork-specific files on top of an upstream release tag. | Rebased onto the latest upstream release tag each update cycle. |

Hermes upstream uses `main` (not `master`) since late 2025. This fork was originally cloned from a `master`-named upstream and stays on `master` by choice.

`docker-compose.windows.yml` is unrelated to this workflow. It is upstream's own Windows Docker Desktop compose variant and is untouched by a rebase.

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

Verify the upstream remote exists:

```bash
git remote -v
```

Expect two lines for `upstream`, a fetch and a push, both pointing at `https://github.com/NousResearch/hermes-agent.git`. If `upstream` is missing, add it:

```bash
git remote add upstream https://github.com/NousResearch/hermes-agent.git
```

If you forked your repository directly from `NousResearch/hermes-agent`, `origin` already points to upstream. Add your own fork as `origin` and use `upstream` for the NousResearch one if needed:

```bash
git remote set-url origin https://github.com/Lukk17/hermes-agent.git
```

## Update workflow (assume the current target release is `v2026.8.27`)

### 1. Sync metadata, list available tags

```bash
git fetch upstream
```

```bash
git fetch upstream --tags
```

```bash
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

### 2. Back up master, then rebase in a worktree

Create a backup branch before touching anything. A rebase that goes wrong is
then one `git reset` away from undone:

```bash
git branch backup/master-pre-v2026.8.27 master
```

Older commits on this fork's history still touch paths under `hermes-data/`,
from before that directory became its own nested git repository. Rebasing
those commits in the main checkout fails with "untracked working tree files
would be overwritten," because the checkout's real `hermes-data/` (a separate
git repository, ignored by this repo's own `.gitignore`) sits exactly where
the old commit wants to write. Do the rebase in a `git worktree` instead, a
second checkout of the same repository with its own working directory and no
`hermes-data/` clone inside it, so there is nothing in the way. `master` is
already checked out in the main worktree, so give the worktree a new branch
name rather than reusing `master`:

```bash
git worktree add ../hermes-agent-rebase -b rebase/v2026.8.27 master
```

```bash
cd ../hermes-agent-rebase
```

`git rebase` walks every commit upstream made between your fork base and
`v2026.8.27` and replays your fork commits on top. With this fork's history
being a few small commits and `v2026.8.27` being thousands of upstream commits
ahead, expect conflicts only on files the fork actually modifies.

Rebase also rewrites the committer date of every replayed commit to the
current time, which conflicts with this project's backdating rule (author
date and committer date must match). Pass `--committer-date-is-author-date`
so each replayed commit keeps its original committer date instead of picking
up the time the rebase ran:

```bash
git rebase --committer-date-is-author-date v2026.8.27
```

If a commit's committer date was already wrong before this rebase (for
example, rewritten by an earlier tool that did not carry this flag), fix it
after the fact instead, on that one commit, with a filter rather than by
rebasing again:

```bash
git filter-branch --env-filter 'if [ "$GIT_COMMIT" = "<sha>" ]; then export GIT_COMMITTER_DATE="$GIT_AUTHOR_DATE"; fi' -- <sha>^..<sha>
```

Resolve conflicts below in this worktree, same as in the main checkout. Once
`git rebase --continue` finishes cleanly, go back to the main checkout,
fast-forward `master` onto `rebase/v2026.8.27`, then remove the worktree and
the temporary branch:

```bash
cd ../hermes-agent
```

```bash
git merge --ff-only rebase/v2026.8.27
```

```bash
git worktree remove ../hermes-agent-rebase
```

```bash
git branch -d rebase/v2026.8.27
```

The full fork-owned set, the files a conflict can actually appear in, is:

- `docker-compose.override.yml`, `Dockerfile.fork`
- `.gitignore` (the fork appends one line ignoring `/hermes-data/` wholesale, on top of upstream's)
- `FORK.md`, `fork/AGENTS.md`, `fork/NOTE-*.md`
- `.agents/`, `.claude/`, `.codex/`, `.kilo/`, `.opencode/`

Only `.gitignore` is a file upstream also owns, so in practice it is the one that conflicts. Upstream ships neither `fork/` nor `hermes-data/`, so `fork/` replays cleanly however much has changed inside it, and files the fork never touches replay cleanly too. `hermes-data/` is its own git repository now, entirely ignored by this repo's `.gitignore`, so a rebase here never touches it at all.

Two directories that used to be listed here are gone. `fork/hermes-config/` no longer exists: its three files moved into `hermes-data/` and are tracked there. `fork/projects/` no longer exists either, it moved to `hermes-data/projects/`. If a rebase surfaces either path, you are replaying a fork commit from before that move and should take the newer side.

### 3. Resolve conflicts

For each file flagged by git, decide one of:

| Decision | Command | When |
|---|---|---|
| Keep upstream version entirely | `git checkout --theirs path` | Upstream renamed or restructured the file, and your fork change is obsolete |
| Keep fork version entirely | `git checkout --ours path` | Upstream deleted the file, or the fork change is canonical (most of your fork NOTES fall here) |
| Manual merge | open in editor, resolve hunks, `git add path` | Both sides made changes you need to keep |

After each file:

```bash
git add resolved-path
```

```bash
git rebase --continue
```

If you get stuck at any point, both commands below run in the worktree, not
the main checkout, so `master` itself has not moved yet either way:

Back to where you started:

```bash
git rebase --abort
```

Drop the upstream commit entirely, a last resort:

```bash
git rebase --skip
```

If the worktree is unrecoverable, delete it and start over from step 2. The
`backup/master-pre-v2026.8.27` branch and the untouched `master` are both
still there:

```bash
cd ../hermes-agent
```

```bash
git worktree remove --force ../hermes-agent-rebase
```

```bash
git branch -D rebase/v2026.8.27
```

### 4. Sanity-check the resolved tree

Expect only the fork-specific files to differ:

```bash
git diff --stat v2026.8.27..master
```

Then eyeball each diff to confirm the overrides and the notes still make sense against the new upstream base:

```bash
git diff v2026.8.27..master -- docker-compose.override.yml Dockerfile.fork .gitignore FORK.md fork/
```

The revision is the bare tag `v2026.8.27`, not `upstream/v2026.8.27`. Tags are not namespaced per remote the way branches are, so the `upstream/` form fails with an unknown-revision error.

### 5. Build the images

```bash
docker compose --profile build build upstream-base
```

```bash
docker compose build gateway dashboard
```

Build order matters only for the first command: `upstream-base` produces
`hermes-agent:upstream`, which is the `BASE_IMAGE` both fork images sit on.
`gateway` and `dashboard` are independent of each other.

### 6. Tag and push to Docker Hub

Hold the tag in a shell variable. This is the one command in the note whose syntax differs between the two shells.

PowerShell:

```powershell
$tag = "v2026.8.27-lukk"
```

Unix shell:

```bash
tag="v2026.8.27-lukk"
```

Every `docker tag` and `docker push` below reads it as `$tag`, which expands the same way in both shells, so those blocks are shared.

```bash
docker tag hermes-agent:fork lukk17/hermes-agent-gateway:$tag
```

```bash
docker tag hermes-agent:fork lukk17/hermes-agent-gateway:latest
```

```bash
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:$tag
```

```bash
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:latest
```

```bash
docker push lukk17/hermes-agent-gateway:$tag
```

```bash
docker push lukk17/hermes-agent-gateway:latest
```

```bash
docker push lukk17/hermes-agent-dashboard:$tag
```

```bash
docker push lukk17/hermes-agent-dashboard:latest
```

`hermes-agent:upstream` is a local build artifact and is never pushed. Each
fork-built image carries two Docker Hub tags. Use the versioned one
(`v2026.8.27-lukk`) for any deployment that should be reproducible, and
`:latest` for the most recent build.

### 7. Update the minipc to consume the new image

The minipc needs no compose change for this. `docker-compose.minipc.yml`
pins both services to `:latest`, and step 6 just moved that tag to the new
build, so `git pull` on the minipc is only there to pick up a fork doc or
compose-file change, never to touch an image reference.

Open a session on the minipc. `ssh` is the same command in PowerShell and in a Unix shell:

```bash
ssh user@minipc
```

Everything from here to the end of this step runs inside that SSH session, on Ubuntu, so those blocks are Linux-only and have no PowerShell variant:

```bash
cd /opt/docker-stack/hermes
```

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml
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

If anything fails after the upgrade, roll back by moving `:latest` itself back
to the previous good build, on the dev box, not by editing
`docker-compose.minipc.yml` on the minipc. The file stays pinned to `:latest`
either way, which is the point of pinning it there in the first place:

```bash
docker pull lukk17/hermes-agent-gateway:v2026.8.19-lukk
```

```bash
docker tag lukk17/hermes-agent-gateway:v2026.8.19-lukk lukk17/hermes-agent-gateway:latest
```

```bash
docker push lukk17/hermes-agent-gateway:latest
```

Repeat the same three commands for `lukk17/hermes-agent-dashboard` if the
dashboard image also needs rolling back. Then on the minipc:

```bash
docker compose pull gateway dashboard
```

```bash
docker compose up -d --force-recreate gateway dashboard
```

Push the fixed build's `:latest` once it is ready, the same way step 6 does,
and the minipc picks it up on its next `docker compose pull`.

## Conflict resolution cheatsheet

Patterns you will hit most often during a rebase:

### Upstream renamed an env var the fork override passes

Example: upstream `docker-compose.yml` exposes `DISCORD_GATEWAY_TOKEN`, your override still uses `DISCORD_BOT_TOKEN`.

- Update your override to the new env var name
- Update `hermes-data/config.yaml` if it referenced the old name, then recreate the gateway, because that file is read-only inside the container and is read once at startup
- Leave a one-line comment in the override explaining the rename

### Upstream split a service in two

Example: upstream `dashboard` service now becomes `dashboard` plus `dashboard-assets`.

- Add the new services to your override
- Replicate your port mapping, volumes, and env wiring across both

### Upstream dropped a tool your fork relies on

Example: upstream removed `blockscout_query`, your crypto-monitor cron still calls it.

- Reimplement the dropped tool as a plugin under `hermes-data/plugins/<name>/`, which the container already sees at `/opt/data/plugins/<name>/` because `hermes-data/` is mounted whole. That directory is re-included by `hermes-data`'s own `.gitignore`, so the plugin is tracked and travels with the `hermes-projects` clone. Commit it from inside `hermes-data/`
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

```bash
git checkout master
```

```bash
git tag v2026.5.11-lukk fc94e319d10a4852c856dd617af4b7f8981ff5d6
```

Then build and push as in steps 5 and 6, and treat `v2026.5.11-lukk` as your first release.

This locks the fork state to the day the workflow was introduced. Future updates rebase onto upstream release tags from this baseline; the rebase deltas are then bounded by however many upstream commits land between the new tag and the current baseline.

### Path 2 — fresh re-fork from the latest tag

```bash
git checkout v2026.8.27
```

```bash
git checkout -b master
```

Port the fork-specific files over from the old branch:

```bash
git checkout <old-master> -- docker-compose.override.yml Dockerfile.fork .gitignore FORK.md fork/ .agents/skills/
```

`hermes-data/` is not part of this checkout any more. It is its own git repository, a clone of the private `Lukk17/hermes-projects`, set up separately per `fork/NOTE-1-install.md`.

```bash
git add -A
```

```bash
git commit -m "feat(fork): re-fork on v2026.8.27 baseline"
```

Then build and push as in steps 5 and 6.

This skips the painful rebase. Future cycles are short.

## Quick reference card

A reference listing, not a paste-in-one-go block. Each line has its own copyable block in the step above it, and the `v<TAG>` placeholders have to be filled in anyway.

```
# fetch
git fetch upstream --tags
git tag -l "v20*" --sort=-v:refname

# back up, then rebase in a worktree
git branch backup/master-pre-v<TAG> master
git worktree add ../hermes-agent-rebase -b rebase/v<TAG> master
cd ../hermes-agent-rebase
git rebase --committer-date-is-author-date v<TAG>
# resolve conflicts, git add ..., git rebase --continue
cd ../hermes-agent
git merge --ff-only rebase/v<TAG>
git worktree remove ../hermes-agent-rebase
git branch -d rebase/v<TAG>

# build + tag + push
docker compose --profile build build upstream-base
docker compose build gateway dashboard
docker tag hermes-agent:fork           lukk17/hermes-agent-gateway:v<TAG>-lukk
docker tag hermes-agent:fork           lukk17/hermes-agent-gateway:latest
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:v<TAG>-lukk
docker tag hermes-agent:fork-dashboard lukk17/hermes-agent-dashboard:latest
docker push lukk17/hermes-agent-gateway:v<TAG>-lukk
docker push lukk17/hermes-agent-gateway:latest
docker push lukk17/hermes-agent-dashboard:v<TAG>-lukk
docker push lukk17/hermes-agent-dashboard:latest

# consume on minipc, no compose change, docker-compose.minipc.yml stays on :latest
ssh user@minipc
cd /opt/docker-stack/hermes
export COMPOSE_FILE=docker-compose.yml:docker-compose.minipc.yml
git pull
docker compose pull
docker compose up -d --force-recreate gateway dashboard
```

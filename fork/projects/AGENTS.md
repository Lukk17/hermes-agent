# Shared conventions for all hermes projects (Lukk17 fork)

This file is read by every hermes agent at session start when its working directory is `/opt/projects/` or any descendant. Treat it as the canonical user-pinned instructions across projects. Per-project overrides live in each project's own `AGENTS.md` and layer on top.

## Path layout inside the container

```
/opt/
├── hermes/                         # upstream source (image internal, do not write here)
├── data/                           # hermes runtime state (from ./hermes-data on host)
├── projects/                       # YOUR project code (from ./fork/projects on host)
│   ├── AGENTS.md                   # this file (shared)
│   ├── crypto-monitor/
│   └── osint/
├── external-skills/                # shared skills (from ./.agents/skills on host, read-only)
└── skills/                         # secondary skills location (from ./skills on host, read-only)
```

The agent's cwd is `/opt/projects/` by default unless the channel persona explicitly asks it to `cd` into a project subdirectory. Read files with absolute paths. Never assume the host filesystem layout.

## Per-project conventions

- Every project under `/opt/projects/<name>/` has its own Python virtualenv at `<name>/venv/` (NOT tracked, built once per machine via `uv venv venv --python python3.11` then `./venv/bin/pip install -r requirements.txt`).
- Project scripts that need network access run through the project venv.
- Project artifacts (data/, reports/, cache/, venv/) live INSIDE the project dir but are gitignored.
- Project source code (scripts/, src/, AGENTS.md, requirements.txt, *.md docs) is tracked in git.

## Discord channel mapping

| Channel | Working dir | Persona file |
|---|---|---|
| `#hermes-general` | `/opt/projects/` | reads this file + ambient context |
| `#hermes-crypto-monitor` | `/opt/projects/crypto-monitor/` | reads project AGENTS.md + USER_REQUIREMENTS.md + SUMMARY_GUIDE.md + AGENT.md |
| `#hermes-osint` | `/opt/projects/osint/` | reads project AGENTS.md + README.md + ARCHITECTURE.md |

The agent switches working directory at the start of each turn based on the active channel's persona prompt. It does NOT carry session state from one channel to another.

## Skill mounting

Two skill locations are mounted read-only:

- `/opt/external-skills/` ← `./.agents/skills/` (curated subset of `Lukk17/agent-standards/.agents/skills/`, mirrored via the `git checkout agent-standards/master` loop described in `fork/NOTE-6-minipc-proxmox.md`)
- `/opt/skills/` ← `./skills/` (any extra per-project skills you want to share)

Both appear in `hermes-data/config.yaml` under `skills.external_dirs`. The agent discovers skills from both. Add skills to one or the other; do not duplicate.

## Tool conventions

- For scheduled work, every project gets a cron entry in `hermes-data/cron/jobs.json` (the v2026.8.27+ format is JSON, NOT the old YAML). Schedules must be cron expressions (e.g. `0 10 * * *` for 10:00 UTC daily). Cron runs as the hermes container user, which means scripts can use `/opt/projects/<name>/venv/bin/python` directly.
- For Discord output, use the `discord.send` tool (provided by the gateway). Do NOT call Discord REST API directly from project scripts.
- For OSINT and crypto lookups, use the env vars from `.env` (`HUNTER_API_KEY`, `ALCHEMY_API_KEY`, etc.). Never bake keys into project scripts.

## Permissions and host/container mapping

The Docker container runs as the user specified by `HERMES_UID`/`HERMES_GID` (defaults to 10000). Files bind-mounted from the host inherit the host's permissions as seen through the WSL2 layer on Docker Desktop, or the regular Linux permissions on a Linux host. If a project writes files to its workspace, the host user can read them as long as your Windows uid matches `HERMES_UID`. On Linux, run `chown -R $(id -u):$(id -g) fork/projects/` after a fresh clone.

## What this file is NOT

- It is not a replacement for per-project `AGENTS.md` files. Each project has its own and the project file wins for project-specific questions.
- It is not hermes system prompt. Hermes' actual system prompt is built from `hermes-data/SOUL.md` plus `channel_prompts` plus this file when cwd matches `/opt/projects/`.
- It is not the AGI manifesto. It is just the operating instructions that keep the three channels consistent.
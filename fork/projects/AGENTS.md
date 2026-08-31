# Shared conventions for all hermes projects (Lukk17 fork)

This file is read by every hermes agent at session start when its working directory is `/opt/projects/` or any descendant. Treat it as the canonical user-pinned instructions across projects. Per-project overrides live in each project's own `AGENTS.md` and layer on top.

## Runtime model: Docker container, host-mounted sources

This hermes stack runs in a Docker container. The mapping between host and container is:

| Host | Container | Contents | Writable from container? |
|---|---|---|---|
| `./hermes-data/` | `/opt/data/` | runtime state (state.db, logs/, sessions/, cache/, auth.json, ...) | yes |
| `./fork/projects/` | `/opt/projects/` | project workspaces (tracked source) | yes |
| `./.agents/skills/` | `/opt/external-skills/` | curated skill set (read-only) | no |
| `./skills/` | `/opt/skills/` | bundled hermes skills (read-only) | no |
| `./fork/hermes-config/SOUL.md` | `/opt/data/SOUL.md` | agent persona (override of hermes-data default) | yes |
| `./fork/hermes-config/config.yaml` | `/opt/data/config.yaml` | hermes runtime config | yes |
| `./fork/hermes-config/cron/jobs.json` | `/opt/data/cron/jobs.json` | scheduled jobs | yes |

The hermes-data/ host directory is the bind mount for runtime state. The three tracked files (SOUL.md, config.yaml, cron/jobs.json) are sourced from fork/hermes-config/ via file-specific overrides, so rebase-on-upstream does not conflict with our local changes.

Critical consequences of this layout:

- Any change made INSIDE the container to a file under `/opt/data/` that is sourced from `fork/hermes-config/` is lost on the next container recreate.
- The agent must NEVER modify `/opt/data/SOUL.md`, `/opt/data/config.yaml`, `/opt/data/cron/jobs.json`, `/opt/projects/...`, or `/opt/external-skills/...` directly. It edits the host-side source file via the editor or by asking the user to run a `Write` or `Edit` tool call on the host path.
- After any change to a tracked file under `fork/hermes-config/`, `fork/projects/`, or `fork/NOTE-*.md`, the agent tells the user: "edit X to Y, then run `docker compose up -d --force-recreate gateway dashboard`" (and waits for confirmation, never recreates itself).
- After any change to `./hermes-data/` runtime state (logs, sessions, cache), no recreate is needed. The change is already on the host. The container will read it on next restart.

When the agent needs to make a configuration change, the protocol is:

1. Identify the file (path on host, e.g. `fork/hermes-config/config.yaml`).
2. Identify the exact line and the exact value to change.
3. Tell the user: "Open `fork/hermes-config/config.yaml`. Change line N from X to Y. Save. Then run `docker compose up -d --force-recreate gateway dashboard` from the repo root."
4. Wait for the user to confirm the edit landed and the recreate happened.

The agent does NOT edit these files itself and does NOT recreate the container itself. Both are user actions.

---

## Channel to workspace mapping (no platform prefix)

Each Discord channel maps to exactly one directory under `/opt/projects/`. The channel name is slugified directly:

- `#hermes-general` → `/opt/projects/`
- `#hermes-crypto-monitor` → `/opt/projects/crypto-monitor/`
- `#hermes-osint` → `/opt/projects/osint/`
- `#hermes-research` → `/opt/projects/research/`

There is no platform prefix to strip. Use the channel name slug directly. If a channel name has invalid filename characters (rare, but Discord allows some Unicode), sanitize and tell the user.

When the user runs a project for the first time in a new channel, the agent creates the directory at the appropriate path. After that, all subsequent work in that channel operates inside the existing directory.

---

## Discord formatting rules (mirror of SOUL.md)

- No tables. Use bullet lists.
- No em dash. Use hyphen-minus.
- Comments about code blocks go BELOW, never inside.
- Every list item on its own line. No inline comma-separated items.
- Wrap multiple bare links in `<>` to suppress embeds.
- For code snippets, use a single triple-backtick block.

---

## Secret handling

- No `.env` files inside any project dir. Secrets live in the host repo `.env` at the repo root, exposed to the container via `docker-compose.override.yml` environment passthrough.
- The hermes runtime reads secrets via `os.getenv("KEY_NAME")`. The container process env is populated from `docker-compose.override.yml`.
- The agent NEVER embeds real API keys, tokens, or credentials in code, comments, README files, or any committed file. Always use placeholders like `<YOUR_KEY>` in docs.

---

## Skill usage is mandatory

Two skill locations are mounted read-only into every hermes session:

- `/opt/external-skills/` ← `./.agents/skills/` (curated subset of `Lukk17/agent-standards/.agents/skills/`, mirrored via the `git checkout agent-standards/master` loop described in `fork/NOTE-6-minipc-proxmox.md`)
- `/opt/skills/` ← `./skills/` (any extra per-project skills you want to share)

Skills appear in `fork/hermes-config/config.yaml` (bind-mounted at `/opt/data/config.yaml` inside the container) under `skills.external_dirs`. The agent discovers skills from both at session start.

### Rules

- Skill usage is MANDATORY for every task that has a relevant skill.
- For each user task, list every skill that could apply and use ALL of them. Do not pick a single skill when two or three fit.
- Even if the task looks trivial (formatting a file, drafting a short note), check `skills list` mentally against the request and pull in anything that adds value (e.g. `coding-standards` for any code edit, `docker-patterns` for any compose change, `security-review` for any auth/secret handling, `review-duplication` for any code review, `observability-and-logging` for any monitoring/logging change).
- If a skill is not in the catalog yet but would obviously apply, say so in the channel and add it to `.agents/skills/` rather than improvising.
- When in doubt, prefer the more thorough set. Wasted skill calls are cheap, missed skills cause real mistakes.

---

## Path layout inside the container

```
/opt/
├── hermes/                         # upstream source (image internal, do not write here)
├── data/                           # hermes runtime state (from ./hermes-data on host)
│   ├── SOUL.md                      # persona (override from ./fork/hermes-config/SOUL.md)
│   ├── config.yaml                  # runtime config (override from ./fork/hermes-config/config.yaml)
│   ├── memories/                    # agent memory (MEMORY.md, USER.md) - private
│   ├── logs/                        # gateway / agent / skill logs
│   ├── sessions/                    # SQLite session files
│   ├── state.db*                    # live SQLite (do not commit)
│   ├── skills/                      # bundled skills installed at runtime
│   └── cron/
│       └── jobs.json                # scheduled jobs (override from ./fork/hermes-config/cron/jobs.json)
├── projects/                       # YOUR project code (from ./fork/projects on host)
│   ├── AGENTS.md                      # this file (shared)
│   ├── AGENTS.user.md                # user-specific notes (private to the user, gitignored)
│   ├── crypto-monitor/               # has its own .venv/, AGENTS.md, pipeline
│   ├── osint/                        # has its own .venv/, AGENTS.md, cascade engine
│   └── research/                     # topic subdirs + README.md index
├── external-skills/                # shared skills (from ./.agents/skills on host, read-only)
└── skills/                         # secondary skills (from ./skills on host, read-only)
```

The agent's cwd is `/opt/projects/` by default unless the channel persona explicitly asks it to `cd` into a project subdirectory. Read files with absolute paths. Never assume the host filesystem layout.

### `AGENTS.user.md` (private user notes)

Each project can optionally ship an `AGENTS.user.md` (not `AGENTS.md`) at its root for notes that are private to the user and never part of the agent's persona. It is gitignored by the per-project `.gitignore`. Use it for things like personal reminders, experiment drafts, machine-local paths. The agent never auto-reads `AGENTS.user.md`. The user references it explicitly when they want the agent to see those notes.

---

## Per-project conventions

- Every project under `/opt/projects/<name>/` has its own Python virtualenv at `.venv/` (with leading dot, NOT tracked, built once per machine). Use `uv venv .venv --python python3.11` (or 3.12 for OSINT, which needs newer Python for some libraries), then `./.venv/bin/pip install -r requirements.txt` (or `uv pip install -e .` if the project ships a `pyproject.toml`).
- Project scripts that need network access run through the project venv (`.venv/bin/python`).
- Project artifacts (data/, reports/, cache/, .venv/) live INSIDE the project dir but are gitignored via `fork/projects/.gitignore`.
- Project source code (scripts/, src/, AGENTS.md, requirements.txt, *.md docs) is tracked in git.

---

## Discord channel mapping

| Channel | Working dir | Persona file |
|---|---|---|
| `#hermes-general` | `/opt/projects/` | reads this file + ambient context |
| `#hermes-crypto-monitor` | `/opt/projects/crypto-monitor/` | reads project AGENTS.md + USER_REQUIREMENTS.md + SUMMARY_GUIDE.md + AGENT.md |
| `#hermes-osint` | `/opt/projects/osint/` | reads project AGENTS.md + README.md + ARCHITECTURE.md |
| `#hermes-research` | `/opt/projects/research/` | reads project AGENTS.md for topic subdir convention |

The agent switches working directory at the start of each turn based on the active channel's persona prompt. It does NOT carry session state from one channel to another.

---

## Tool conventions

- For scheduled work, every project gets a cron entry in `fork/hermes-config/cron/jobs.json` (bind-mounted at `/opt/data/cron/jobs.json` inside the container) (the v2026.8.27+ format is JSON, NOT the old YAML). Schedules must be cron expressions (e.g. `0 10 * * *` for 10:00 UTC daily). Cron runs as the hermes container user, which means scripts can use `/opt/projects/<name>/.venv/bin/python` directly.
- For Discord output, use the `discord.send` tool (provided by the gateway). Do NOT call Discord REST API directly from project scripts.
- For OSINT and crypto lookups, use the env vars from `.env` (`HUNTER_API_KEY`, `ALCHEMY_API_KEY`, etc.). Never bake keys into project scripts.
- For web scraping across projects, prefer the ascend scraper at `$ASCEND_SCRAPPER_URL`. Skip Playwright / Selenium unless the project explicitly says otherwise.

---

## Permissions and host/container mapping

The Docker container runs as the user specified by `HERMES_UID`/`HERMES_GID` (defaults to 10000). Files bind-mounted from the host inherit the host's permissions as seen through the WSL2 layer on Docker Desktop, or the regular Linux permissions on a Linux host. If a project writes files to its workspace, the host user can read them as long as your Windows uid matches `HERMES_UID`. On Linux, run `chown -R $(id -u):$(id -g) fork/projects/` after a fresh clone.

---

## What this file is NOT

- It is not a replacement for per-project `AGENTS.md` files. Each project has its own and the project file wins for project-specific questions.
- It is not the AGENTS.user.md private notes file. That lives at `/opt/projects/AGENTS.user.md` if the user creates it.
- It is not hermes system prompt. Hermes' actual system prompt is built from `fork/hermes-config/SOUL.md` (bind-mounted at `/opt/data/SOUL.md` inside the container) plus `channel_prompts` plus this file when cwd matches `/opt/projects/`.
- It is not a config file. Persistent settings live in `fork/hermes-config/config.yaml`. Cron schedules live in `fork/hermes-config/cron/jobs.json`. Persona lives in `fork/hermes-config/SOUL.md` and `hermes-data/memories/`.
- It is not a place to track historical OpenClaw files. Historical context belongs in git history, not in the working tree. If a file is no longer relevant, delete it.
- It is not the AGI manifesto. It is just the operating instructions that keep the four channels consistent.
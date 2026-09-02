# Shared conventions for all hermes projects (Lukk17 fork)

This file is read by every hermes agent at session start when its working directory is `/opt/data/projects/` or any descendant. Treat it as the canonical user-pinned instructions across projects. Per-project overrides live in each project's own `AGENTS.md` and layer on top.

## Runtime model: Docker container, host-mounted sources

This hermes stack runs in a Docker container, and one host directory carries everything. `./hermes-data/` on the user's machine is bind-mounted at `/opt/data` inside this container, which is this agent's home directory. So `/opt/data/anything` and `hermes-data/anything` are the same file seen from two sides, and a write on either side is immediately visible on the other. The full mapping:

| Host | Container | Contents | Writable from here? |
|---|---|---|---|
| `./hermes-data/` | `/opt/data/` | everything below, plus runtime state (state.db, logs/, sessions/, cache/, auth.json, .env) | yes |
| `./hermes-data/SOUL.md` | `/opt/data/SOUL.md` | agent persona | yes |
| `./hermes-data/cron/jobs.json` | `/opt/data/cron/jobs.json` | scheduled jobs | yes |
| `./hermes-data/memories/*.md` | `/opt/data/memories/*.md` | MEMORY.md, USER.md | yes |
| `./hermes-data/projects/` | `/opt/data/projects/` | project workspaces | yes |
| `./hermes-data/config.yaml` | `/opt/data/config.yaml` | hermes runtime config | NO, re-mounted read-only |
| `./hermes-data/scripts/crypto-monitor-daily.sh` | `/opt/data/scripts/crypto-monitor-daily.sh` | cron entry point | NO, re-mounted read-only |
| `./.agents/skills/` | `/opt/data/external-skills/` | curated skill set | NO, read-only mount |
| `./skills/` | `/opt/data/bundled-skills/` | bundled hermes skills | NO, read-only mount |

Critical consequences of this layout:

- Nothing written under `/opt/data/` is lost on a container recreate. It is already a file on the host. This is the opposite of the old layout, where in-container edits to the config files were discarded.
- Which of those host files travel to the user's other machines is decided by `.gitignore`, not by where they sit. Tracked: `config.yaml`, `SOUL.md`, `cron/jobs.json`, `memories/*.md`, everything under `projects/`, `scripts/crypto-monitor-daily.sh`. Ignored: the databases, logs, caches, `auth.json` and `.env` beside them.
- `/opt/data/config.yaml` and `/opt/data/scripts/crypto-monitor-daily.sh` cannot be written from here at all. A write fails with a read-only filesystem error. Changing either one is a user action on the host followed by a container recreate, so surface it as a request rather than attempting the write.
- `/opt/data/external-skills/` and `/opt/data/bundled-skills/` are also read-only. New skills go in `.agents/skills/` on the host.

When the agent needs a change it cannot make itself, the protocol is:

1. Name the file by its host path, for example `hermes-data/config.yaml`.
2. Name the exact line and the exact value to change.
3. Tell the user: "Open `hermes-data/config.yaml`. Change line N from X to Y. Save. Then run `docker compose up -d --force-recreate gateway dashboard` from the repo root."
4. Wait for the user to confirm the edit landed and the recreate happened.

The agent does not recreate the container itself. That is a user action.

---

## Channel to workspace mapping (no platform prefix)

Each Discord channel maps to exactly one directory under `/opt/data/projects/`. The channel name is slugified directly:

- `#hermes-general` → `/opt/data/projects/`
- `#hermes-crypto-monitor` → `/opt/data/projects/crypto-monitor/`
- `#hermes-osint` → `/opt/data/projects/osint/`
- `#hermes-research` → `/opt/data/projects/research/`

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

- `/opt/data/external-skills/` ← `./.agents/skills/` (curated subset of `Lukk17/agent-standards/.agents/skills/`, mirrored via the `git checkout agent-standards/master` loop described in `fork/NOTE-6-minipc-proxmox.md`)
- `/opt/data/bundled-skills/` ← `./skills/` (any extra per-project skills you want to share)

Both paths are listed under `skills.external_dirs` in `/opt/data/config.yaml` (`hermes-data/config.yaml` on the host). The agent discovers skills from both at session start.

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
└── data/                        # this agent's home, the whole of ./hermes-data on host
    ├── SOUL.md                  # persona, writable
    ├── config.yaml              # runtime config, READ-ONLY here
    ├── memories/                # agent memory (MEMORY.md, USER.md), writable
    ├── cron/jobs.json           # scheduled jobs, writable
    ├── scripts/                 # cron entry points; crypto-monitor-daily.sh is READ-ONLY
    ├── logs/                    # gateway / agent / skill logs
    ├── sessions/  state.db*     # live SQLite, never commit
    ├── skills/                  # skills installed at runtime
    ├── external-skills/         # curated skills (from ./.agents/skills on host, READ-ONLY)
    ├── bundled-skills/          # upstream skills (from ./skills on host, READ-ONLY)
    └── projects/                # project code (from ./hermes-data/projects on host)
        ├── AGENTS.md            # this file (shared)
        ├── AGENTS.user.md       # user-specific notes (private to the user, gitignored)
        ├── crypto-monitor/      # has its own .venv/, AGENTS.md, pipeline
        ├── osint/               # has its own .venv/, AGENTS.md, cascade engine
        └── research/            # topic subdirs + README.md index
```

The agent's cwd is `/opt/data/projects/` by default unless the channel persona explicitly asks it to `cd` into a project subdirectory. Read files with absolute paths. Never assume the host filesystem layout.

### `AGENTS.user.md` (private user notes)

Each project can optionally ship an `AGENTS.user.md` (not `AGENTS.md`) at its root for notes that are private to the user and never part of the agent's persona. It is gitignored by the per-project `.gitignore`. Use it for things like personal reminders, experiment drafts, machine-local paths. The agent never auto-reads `AGENTS.user.md`. The user references it explicitly when they want the agent to see those notes.

---

## Per-project conventions

- Every project under `/opt/data/projects/<name>/` has its own Python virtualenv at `.venv/` (with leading dot, NOT tracked, built once per machine). Neither project's `.venv/` exists in a fresh clone or in the image, so building it is a REQUIRED first-run step, not an optional one: the crypto-monitor pipeline exits 2 without it. Use `uv venv .venv --python python3.11` (or 3.12 for OSINT, which needs newer Python for some libraries), then `uv pip install --python ./.venv/bin/python -e .`. Always pass `--python` explicitly: osint's `pyproject.toml` has no upper bound on `requires-python`, so nothing else stops the venv being built on 3.13. Both current projects declare their dependencies in `pyproject.toml`; neither ships a `requirements.txt`. `uv` is at `/usr/local/bin/uv` in the image, and pyenv provides 3.11 and 3.12 under `/opt/pyenv/`.
- Project scripts that need network access run through the project venv (`.venv/bin/python`).
- Project artifacts (data/, reports/, cache/, .venv/) live INSIDE the project dir but are gitignored via `hermes-data/projects/.gitignore`. Project sources are tracked and travel to the user's other machines; the artifacts do not.
- Project source code (scripts/, src/, AGENTS.md, pyproject.toml, *.md docs) is tracked in git.

---

## Discord channel mapping

| Channel | Working dir | Persona file |
|---|---|---|
| `#hermes-general` | `/opt/data/projects/` | reads this file + ambient context |
| `#hermes-crypto-monitor` | `/opt/data/projects/crypto-monitor/` | reads project AGENTS.md + USER_REQUIREMENTS.md + SUMMARY_GUIDE.md |
| `#hermes-osint` | `/opt/data/projects/osint/` | reads project AGENTS.md + README.md + ARCHITECTURE.md |
| `#hermes-research` | `/opt/data/projects/research/` | reads project AGENTS.md for topic subdir convention |

The agent switches working directory at the start of each turn based on the active channel's persona prompt. It does NOT carry session state from one channel to another.

---

## Tool conventions

- For scheduled work, every project gets a cron entry in `/opt/data/cron/jobs.json` (`hermes-data/cron/jobs.json` on the host; the v2026.8.27+ format is JSON, NOT the old YAML). Schedules must be cron expressions (e.g. `0 10 * * *` for 10:00 UTC daily). Cron runs as the hermes container user, which means scripts can use `/opt/data/projects/<name>/.venv/bin/python` directly.
- Discord output is the agent's own reply, not a tool call. There is NO agent-callable Discord send tool. `tools/discord_tool.py` registers only `discord` (read and moderate: fetch messages, list channels, pin, thread) and `discord_admin` (roles, deletes). `send_message` exists in `tools/send_message_tool.py` but is deliberately NOT registered as a model tool, so the agent cannot call it. Write the message as the final response and the gateway delivers it to the channel the turn came from. For a scheduled job that runs an agent turn, the job's `deliver` field in `/opt/data/cron/jobs.json` routes the final response to the target channel. A job can also skip the agent entirely with `no_agent: true` and no `deliver`, in which case cron runs only its script and that script publishes for itself. `crypto-monitor-daily` works that way: the pipeline owns the structure and calls the agent only for the pieces that need a model.
- To attach a file to that reply, put one line per file of the form `MEDIA:` followed by an absolute path in the final response, in plain text outside any code block, inline backticks or blockquote, and only for files that exist on disk. The platform adapter strips those lines and uploads the files. Anything else (a bare mention of a path, a link) is not an attachment.
- Do NOT call the Discord REST API directly from project scripts.
- For OSINT and crypto lookups, read the container process environment (`os.getenv("HUNTER_API_KEY")`, `os.getenv("ALCHEMY_API_KEY")`, and so on). Those values are injected by `docker-compose.override.yml` from the gitignored repo-root `.env` on the host. Never bake keys into project scripts and never create a `.env` inside a project directory.
- For web scraping across projects, prefer the ascend scraper. Its base URL comes from the `ASCEND_SCRAPPER_URL` environment variable, falling back to `http://host.docker.internal:7021` when the variable is unset. Skip Playwright / Selenium unless the project explicitly says otherwise.

---

## Permissions and host/container mapping

The container runs as the user given by `HERMES_UID`/`HERMES_GID`, defaulting to 10000. Only native Linux enforces host file ownership through a bind mount. Docker Desktop on Windows squashes it, so any container uid can write there.

On a Linux host the user pins the container uid to their own with one command in the repo root, `printf 'HERMES_UID=%s\nHERMES_GID=%s\n' "$(id -u)" "$(id -g)" >> .env`, and compose reads it on every `up`. If that was never done, every write under `/opt/data` fails with a permission error: SOUL.md, memories, cron jobs and project files alike. A blanket permission-denied on writes that used to work is the signature, and the fix belongs on the host, not in the agent's code.

---

## What this file is NOT

- It is not a replacement for per-project `AGENTS.md` files. Each project has its own and the project file wins for project-specific questions.
- It is not the AGENTS.user.md private notes file. That lives at `/opt/data/projects/AGENTS.user.md` if the user creates it.
- It is not hermes system prompt. Hermes' actual system prompt is built from `/opt/data/SOUL.md` plus `channel_prompts` plus this file when cwd matches `/opt/data/projects/`.
- It is not a config file. Persistent settings live in `/opt/data/config.yaml`, cron schedules in `/opt/data/cron/jobs.json`, persona in `/opt/data/SOUL.md` and `/opt/data/memories/`. On the user's machine those are `hermes-data/config.yaml`, `hermes-data/cron/jobs.json`, `hermes-data/SOUL.md` and `hermes-data/memories/`.
- It is not a place to track files from the projects' previous runtime. Historical context belongs in git history, not in the working tree. If a file is no longer relevant, delete it.
- It is not the AGI manifesto. It is just the operating instructions that keep the four channels consistent.
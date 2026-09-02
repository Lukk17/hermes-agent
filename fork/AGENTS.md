# Hermes Agent fork (Lukk17) — Coding Agent Guide

This file is read by every coding agent (Kilo Code, Claude Code, OpenCode, GitHub Copilot, Cursor, Gemini CLI, Zed) working on this repository. It layers on top of the upstream `AGENTS.md` at the repo root, which describes the hermes-agent project itself. The coding agent reads BOTH and follows both. The upstream rules govern the underlying codebase; the rules here govern the fork overlay and the way this repository is operated.

If a rule here contradicts an upstream rule, the upstream rule wins (this repository is a hermes-agent fork and ships upstream code). If a rule here contradicts what the user has typed in chat, the user wins (always).

## Repository structure

```
/
├── AGENTS.md                          # upstream hermes-agent coding guide (read-only for the fork)
├── .claude/CLAUDE.md                  # Claude Code's entry point; @-imports ../AGENTS.md + ../fork/AGENTS.md
├── .agents/                           # AI tooling config (agent defs, hooks, skills for Kilo)
├── .claude/ .codex/ .kilo/ .opencode/ # per-tool entries; each has its own AGENTS/CLAUDE config
│
├── docker-compose.yml                 # upstream hermes service definitions
├── docker-compose.override.yml        # fork-only overrides (image tags, env passthrough, mounts)
├── Dockerfile                         # upstream hermes image build
├── Dockerfile.fork                    # fork tools layer on hermes-agent:upstream:
│                                      #   OSINT apt deps, pyenv + Python 3.11 and 3.12,
│                                      #   ui-tui chown, /opt/data/.local/bin/hermes symlink
├── .gitignore                         # fork additions on top of upstream's
│
│   # The repository root IS the hermes-agent checkout. There is no
│   # hermes-agent/ subdirectory. Everything below is upstream source.
├── run_agent.py cli.py model_tools.py toolsets.py utils.py
│                                      #   ... and every other top-level *.py
├── agent/                             # upstream agent internals
├── gateway/                           # upstream gateway source
├── tools/                             # upstream tool source
├── skills/                            # upstream bundled skills (read-only mount source)
├── optional-skills/                   # upstream optional skills
├── plugins/                           # upstream plugin tree
├── providers/                         # upstream provider profiles
├── web/                               # upstream web UI source
├── ui-tui/                            # upstream TUI source
├── tui_gateway/                       # upstream TUI backend
├── apps/                              # upstream desktop app
├── acp_adapter/                       # upstream ACP adapter source
├── cron/                              # upstream cron subsystem source
├── hermes_cli/                        # upstream CLI source
├── scripts/ tests/ tests-js/ website/ docs/ evals/ native/ nix/ locales/
│                                      # upstream, all of it
│
├── fork/                              # fork documentation only, nothing the container reads
│   ├── AGENTS.md                      # this file (coding agent guide for the fork overlay)
│   └── NOTE-*.md                      # fork docs
│
├── hermes-data/                       # the container's whole home directory, mounted at /opt/data
│   │                                  # TRACKED (travels between machines):
│   ├── config.yaml                    #   runtime config, re-mounted read-only in the container
│   ├── SOUL.md                        #   agent persona, hermes may rewrite it at runtime
│   ├── cron/jobs.json                 #   scheduled jobs
│   ├── memories/*.md                  #   MEMORY.md, USER.md
│   ├── projects/                      #   project workspaces, one subdir per Discord channel
│   │   ├── AGENTS.md                  #     shared hermes-runtime conventions
│   │   ├── AGENTS.user.md             #     (optional) private user notes, never read by hermes
│   │   ├── crypto-monitor/            #     one Discord channel worth of project
│   │   ├── osint/                     #     one Discord channel worth of project
│   │   └── research/                  #     one Discord channel worth of project
│   ├── scripts/crypto-monitor-daily.sh  # cron entry point, re-mounted read-only
│   │                                  # IGNORED (per-machine, never enters git):
│   ├── .env                           #   secrets that hermes child processes need
│   ├── state.db*                      #   SQLite sessions
│   ├── auth.json                      #   OAuth tokens
│   ├── logs/  sessions/  cache/       #   logs, session files, model catalog cache
│   ├── skills/                        #   skills installed at runtime
│   └── ...                            #   everything else under hermes-data/ is ignored
│
└── .agents/skills/                    # curated user-authored skills (mirror of agent-standards)
```

The rule that makes this layout readable: `hermes-data/` is the container's home directory, bind-mounted whole at `/opt/data`. There is no Docker volume and no per-file mount of a config directory. `.gitignore` is what decides which files inside that one directory travel between machines: it ignores `hermes-data/*` and then re-includes `config.yaml`, `SOUL.md`, `cron/jobs.json`, `memories/*.md`, `projects/`, and `scripts/crypto-monitor-daily.sh`. So the agent writes wherever it likes under its own home, and git picks up only the parts worth carrying to another machine.

Two files inside that mount are re-mounted read-only on top of it, `hermes-data/config.yaml` and `hermes-data/scripts/crypto-monitor-daily.sh`. A running hermes cannot rewrite either one. Changing them means editing the host file and recreating the container.

The fork overlay is everything under `fork/`, `Dockerfile.fork`, `docker-compose.override.yml`, `.gitignore` additions, `FORK.md`, and the tracked files inside `hermes-data/`. The rest is upstream hermes-agent code that we do not modify.

## Engineering principles for the fork

These apply to every code change the fork makes. They restate the user's global engineering rules alongside the upstream `AGENTS.md`. Treat them as non-negotiable.

- **SOLID** (Single responsibility, Open/closed, Liskov, Interface segregation, Dependency inversion). One reason to change per module. Add behavior by extending, not by editing working code. Subtypes work anywhere their base type is expected. Many small focused interfaces. Depend on abstractions.
- **DRY**. Every piece of knowledge has one source of truth. No copy-and-paste programming. If we find ourselves duplicating, extract.
- **KISS**. Simplest solution that fully works wins. If a more elaborate solution is not justified by a measured need, drop it.
- **YAGNI**. Build only what is needed now. Speculative features are technical debt from day one.
- **FIRST** (testing). Tests are fast, isolated, repeatable, self-validating. Written together with the code, not after.
- **Composition over inheritance, immutable data over mutable state, pure functions over side effects**.
- **Surgical changes**. Touch only what the task needs. Do not reformat unrelated code. Match existing style.
- **Best version, not fastest**. If doing it properly means fixing every affected place, doing a real migration, or splitting into several commits, do that. Never reduce scope without asking.
- **Plan first, wait for approval**. Present a one-line plan and wait for an explicit yes before editing anything that touches more than one file. Number open questions and wait for answers.
- **Never invent facts**. If a value, identifier, path, name, or rule is genuinely unknown, ask. A confident guess is worse than admitting you do not know, especially for commit timestamps, issue-tracker IDs, server addresses, ports, secret names, environment variable names. Remember the answer once it is given.
- **Verify before reporting success**. Run the build, run the tests, do a manual check. Read the file back after editing to confirm the change is saved. If a measurement contradicts what was said earlier, correct it in one sentence with new evidence. Never blame an external cause without measuring it first.
- **Real end-to-end flow, not just green build**. For user-facing changes, exercise the actual end-to-end flow. For hermes, that means: build image, push to Docker Hub, pull on the minipc, recreate, send a real Discord message, confirm the bot replies, check the log file for errors.
- **No throwaway scripts**. Validate work by running real hermes / docker / git commands, not by writing one-off Python helpers that mock the same thing.
- **Ask before destructive action**. Never delete files, drop or truncate data, or rewrite history without explicit confirmation.
- **Implement only what was requested**. If something else looks broken, mention it in the report, do not silently fix it.

## Credential safety (overrides any older `.env`-in-workspace habits)

- NEVER create `.env` files in the workspace (root or subfolders). Workspace is reachable by every skill, subagent, sandbox, so secrets leak across contexts.
- Where secrets live: host repo `.env` at the repo root, gitignored, loaded into the container process env via `docker-compose.override.yml` env passthrough.
- Reading in scripts: Python `os.getenv("KEY")`; Node/TS `process.env.KEY`. Do NOT use a workspace `.env` file as a side-channel.
- Need a new key: tell the user. They add `KEY=value` to repo `.env` AND `KEY: ${KEY:-}` under `gateway.environment:` in `docker-compose.override.yml`.
- Per script/app: create `README.md` listing required env vars with placeholders like `<YOUR_KEY>`. Real values via env. Never hardcode in code or comments.
- Found a workspace `.env`: stop. Surface the path to the user. Do not read, copy, or extend.

## Heartbeat vs cron

- Heartbeat: conversational batched periodic checks, drift-tolerant, fewer API calls. Used for things like email/calendar/social background checks.
- Cron: exact timing, isolated session, different model/thinking, one-shot, direct-to-channel delivery. Used for scheduled reports, batch investigations.

Hermes uses cron (`hermes-data/cron/jobs.json`), NOT heartbeat. Do not invent heartbeats inside hermes.

## Confirmation protocol (no silent edits)

- No edits, scripts, tool calls, API calls, or external actions without explicit user approval.
- Before any tool: parse the full message, then plan. Number every open question.
- Promises: any behavioral promise gets written to MEMORY.md first, print the diff, then confirm.
- Re-read first: before any edit, read the target file. State latest disk state in reasoning.

## Conventions for changes to the fork

### Where things go

| Change | Edit |
|---|---|
| Cron schedule for a project | `hermes-data/cron/jobs.json` |
| Discord channel persona | `hermes-data/config.yaml` under `discord.channel_prompts` plus `discord.free_response_channels` / `discord.allowed_channels` |
| Agent persona / SOUL | `hermes-data/SOUL.md` |
| Per-project conventions | `hermes-data/projects/<name>/AGENTS.md` (and per-project docs in the same dir) |
| Cron entry-point script | `hermes-data/scripts/crypto-monitor-daily.sh` (read-only inside the container, so a recreate is required) |
| Agent memory | `hermes-data/memories/MEMORY.md` and `USER.md`. Hermes writes these itself at runtime, they are tracked, so commit them like any other change |
| Skills catalog | `.agents/skills/<skill>/SKILL.md` (mirrored from `Lukk17/agent-standards/.agents/skills/` via `git checkout agent-standards/master -- ".agents/skills/<skill>/"`) |
| Docker compose / image | `docker-compose.override.yml` plus `Dockerfile.fork` |
| Fork docs | `fork/NOTE-*.md` (one per topic: install, operations, minipc, updating, discord) |
| Coding-agent instructions | `fork/AGENTS.md` (this file) plus `.claude/CLAUDE.md` (Claude Code entry point) |

### What NOT to edit

- `AGENTS.md` at repo root: upstream hermes-agent guide. Do not modify.
- Everything at the repository root that is not fork-owned is upstream code, because the repository root IS the hermes-agent checkout. There is no `hermes-agent/` subdirectory to fence off. Concretely, do not patch: every top-level `*.py` (`run_agent.py`, `cli.py`, `model_tools.py`, `toolsets.py`, `hermes_constants.py`, `hermes_state*.py`, `utils.py`, `batch_runner.py`, `mcp_serve.py`, `setup.py`, and the rest), nor `agent/`, `gateway/`, `tools/`, `hermes_cli/`, `cron/`, `tui_gateway/`, `acp_adapter/`, `plugins/`, `providers/`, `skills/`, `optional-skills/`, `optional-mcps/`, `web/`, `ui-tui/`, `apps/`, `website/`, `docs/`, `scripts/`, `tests/`, `tests-js/`, `evals/`, `native/`, `nix/`, `locales/`, `docker/`, `assets/`, `contributors/`, `Dockerfile`, `docker-compose.yml`, `pyproject.toml`, `uv.lock`. Rebasing onto upstream merges their changes; we do not patch them in place unless the fork is the only way.
- Fork-owned, and therefore editable: `fork/`, `Dockerfile.fork`, `docker-compose.override.yml`, the fork's additions to `.gitignore`, `.agents/`, `.claude/`, `.codex/`, `.kilo/`, `.opencode/`, `FORK.md`, and the tracked files inside `hermes-data/`.
- `hermes-data/` is not a fenced-off directory any more. It is the container's home directory and it holds both tracked config and untracked runtime state side by side. Which is which is decided by `.gitignore`, not by the directory name, so check `git status` before assuming a file there is throwaway.
- Tracked and editable inside it: `config.yaml`, `SOUL.md`, `cron/jobs.json`, `memories/*.md`, everything under `projects/`, and `scripts/crypto-monitor-daily.sh`.
- Ignored, and never to be committed or hand-edited: `hermes-data/state.db*` (SQLite sessions), `hermes-data/auth.json` (OAuth tokens), `hermes-data/.env` (secrets that hermes child processes read), and every log, cache, lock and session file beside them.
- `hermes-data/config.yaml` and `hermes-data/scripts/crypto-monitor-daily.sh` are re-mounted read-only inside the container. Hermes cannot rewrite them at runtime, and `HERMES_SKIP_CONFIG_MIGRATION=1` stops the boot hook trying. Edit them on the host and recreate the container.

### Editing protocol

1. Identify the file path on the host (e.g. `hermes-data/config.yaml`).
2. Identify the exact line(s) and value(s) to change.
3. Tell the user: "Open `<path>`. Change line N from X to Y. Save." or do the edit yourself via `Write` / `Edit` tool if the user has authorized the change.
4. `hermes-data/` is bind-mounted whole, so a host-side edit is visible inside the container the moment it is saved. A recreate is needed only when the change is one the running process will not re-read: `config.yaml` (read once at startup, and read-only in the container), `scripts/crypto-monitor-daily.sh` (same), or anything in `docker-compose.override.yml` / `.env`. Say which of the two cases applies rather than reflexively asking for a recreate.
5. When a recreate is needed, tell the user to run `docker compose up -d --force-recreate gateway dashboard` from the repo root, then wait for them to confirm. Do NOT recreate the container yourself. Do NOT modify container-side files under `/opt/data`; always edit the host-side file in `hermes-data/`.

### Rebasing onto upstream hermes

The fork tracks `NousResearch/hermes-agent` upstream. To sync:

```
git fetch upstream --tags
git tag -l "v20*" --sort=-v:refname   # pick the newest release tag
git checkout master
git rebase v<TAG>
```

Conflicts will appear in files the fork actually modifies. Expected conflict files:

- `docker-compose.yml` (upstream may add services, the override handles our customizations)
- `Dockerfile` (upstream changes, we use Dockerfile.fork instead)
- `.gitignore` (we have fork additions)
- `AGENTS.md` (we do not edit, accept upstream)
- Any upstream file we have touched directly (avoid this)

Files that should NOT conflict because the fork's modifications live elsewhere:

- Anything under `fork/` (we own this namespace)
- `hermes-data/` (upstream does not ship this directory, so its tracked files replay cleanly and its ignored files are invisible to git)
- `.agents/skills/`, `.claude/`, `.codex/`, `.kilo/`, `.opencode/` (fork AI tooling, not upstream)

See `fork/NOTE-7-updating-from-upstream.md` for the full procedure including image tag rename, build, push, and minipc pull.

### Layered AGENTS.md convention

This fork uses a layered AGENTS.md convention:

- `AGENTS.md` (repo root): upstream hermes-agent coding agent guide. Read first.
- `fork/AGENTS.md` (this file): fork-specific overlay for the coding agent. Read second.
- `hermes-data/projects/AGENTS.md`: shared runtime conventions for the hermes agent. Read when working on project files.
- `hermes-data/projects/<name>/AGENTS.md`: per-project conventions. Read when working in a specific project.
- `hermes-data/projects/AGENTS.user.md` (per project, optional): private user notes. Never read by the hermes agent. Read only if the user references it explicitly.

## Communication

- Reply in the user's language.
- Put the direct answer or final command at the end of the response.
- Number questions and findings so the user can answer in order.
- Use absolute paths when referencing files.
- After editing a file, say what you changed in one sentence.
- Never restate things the user already knows.

## What this file is NOT

- It is not a replacement for the upstream `AGENTS.md`. Read both.
- It is not a config file. Persistent settings live in `hermes-data/config.yaml` and similar.
- It is not a cron schedule. Cron jobs go in `hermes-data/cron/jobs.json`.
- It is not the hermes agent's instructions inside the container. Those are at `hermes-data/projects/AGENTS.md` and per-project AGENTS.md files.
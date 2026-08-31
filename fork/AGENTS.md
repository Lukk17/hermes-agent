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
├── Dockerfile.fork                    # fork-only chown fix for the dashboard TUI build
├── .gitignore                         # fork additions on top of upstream's
│
├── hermes-agent/                      # upstream Python source (NOT modified by the fork)
├── gateway/                           # upstream gateway source
├── tools/                             # upstream tool source
├── skills/                            # upstream bundled skills (read-only mount source)
├── web/                               # upstream web UI source
├── ui-tui/                            # upstream TUI source
├── acp_adapter/                       # upstream ACP adapter source
├── cron/                              # upstream cron subsystem source
├── hermes_cli/                        # upstream CLI source
│
├── fork/                              # everything fork-specific lives here
│   ├── AGENTS.md                      # this file (coding agent guide for the fork overlay)
│   ├── projects/                      # project workspaces mounted into the hermes container
│   │   ├── AGENTS.md                  # shared hermes-runtime conventions
│   │   ├── AGENTS.user.md             # (optional) private user notes, never read by hermes
│   │   ├── crypto-monitor/            # one Discord channel worth of project
│   │   ├── osint/                     # one Discord channel worth of project
│   │   └── research/                  # one Discord channel worth of project
│   ├── hermes-config/                 # tracked hermes config (file-specific bind mounts)
│   │   ├── SOUL.md                    # agent persona
│   │   ├── config.yaml                # runtime config
│   │   └── cron/jobs.json             # scheduled jobs
│   ├── claw-import/                   # (gitignored) reference files copied from OpenClaw for review
│   └── NOTE-*.md                      # fork docs
│
├── hermes-data/                       # runtime state ONLY (gitignored)
│   ├── state.db*                      # SQLite sessions
│   ├── auth.json                      # OAuth tokens
│   ├── logs/                          # gateway / agent / skill logs
│   ├── sessions/                      # additional SQLite files
│   ├── skills/                        # bundled skills installed at runtime
│   ├── memories/                      # MEMORY.md, USER.md (memory subsystem)
│   └── cache/                         # model catalog cache
│
└── .agents/skills/                    # curated user-authored skills (mirror of agent-standards)
```

The fork overlay is everything under `fork/`, `Dockerfile.fork`, `docker-compose.override.yml`, `.gitignore` additions, and `hermes-data/` runtime state. The rest is upstream hermes-agent code that we do not modify.

## Engineering principles for the fork

These apply to every code change the fork makes. They come from `fork/claw-import/CLAUDE.md` and the upstream `AGENTS.md`. Treat them as non-negotiable.

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

## Conventions for changes to the fork

### Where things go

| Change | Edit |
|---|---|
| Cron schedule for a project | `fork/hermes-config/cron/jobs.json` |
| Discord channel persona | `fork/hermes-config/config.yaml` under `discord.channel_prompts` plus `discord.free_response_channels` / `discord.allowed_channels` |
| Agent persona / SOUL | `fork/hermes-config/SOUL.md` |
| Per-project conventions | `fork/projects/<name>/AGENTS.md` (and per-project docs in the same dir) |
| Skills catalog | `.agents/skills/<skill>/SKILL.md` (mirrored from `Lukk17/agent-standards/.agents/skills/` via `git checkout agent-standards/master -- ".agents/skills/<skill>/"`) |
| Docker compose / image | `docker-compose.override.yml` plus `Dockerfile.fork` |
| Fork docs | `fork/NOTE-*.md` (one per topic: install, operations, minipc, updating, discord) |
| Coding-agent instructions | `fork/AGENTS.md` (this file) plus `.claude/CLAUDE.md` (Claude Code entry point) |

### What NOT to edit

- `AGENTS.md` at repo root: upstream hermes-agent guide. Do not modify.
- `hermes-agent/`, `gateway/`, `tools/`, `skills/` (the upstream version), `web/`, `ui-tui/`, `acp_adapter/`, `cron/` (the upstream version), `hermes_cli/`: upstream code. Rebase onto upstream merges the changes; we do not patch these in place unless the fork is the only way.
- Anything inside `hermes-data/` runtime state: that is bind-mounted from the host for hermes runtime. Runtime data lives there. The tracked files that USED to be in hermes-data/ are now in `fork/hermes-config/` and bind-mounted into the container at the same paths.
- `hermes-data/state.db*`: SQLite session files. Never commit.
- `hermes-data/auth.json`: OAuth tokens. Never commit.
- `hermes-data/memories/MEMORY.md` and `USER.md`: per-machine memory. Default to gitignored unless explicitly tracked.

### Editing protocol

1. Identify the file path on the host (e.g. `fork/hermes-config/config.yaml`).
2. Identify the exact line(s) and value(s) to change.
3. Tell the user: "Open `<path>`. Change line N from X to Y. Save." or do the edit yourself via `Write` / `Edit` tool if the user has authorized the change.
4. If the change is in a file the container reads at runtime (anything in `fork/hermes-config/` or `fork/projects/`), the container will pick up the change on its next restart. Tell the user to run `docker compose up -d --force-recreate gateway dashboard` from the repo root.
5. Wait for the user to confirm the edit landed and the recreate happened. Do NOT recreate the container yourself. Do NOT modify container-side files; always edit the host-side source.

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
- `hermes-data/` (gitignored, never conflicts)
- `.agents/skills/`, `.claude/`, `.codex/`, `.kilo/`, `.opencode/` (fork AI tooling, not upstream)

See `fork/NOTE-7-updating-from-upstream.md` for the full procedure including image tag rename, build, push, and minipc pull.

### Layered AGENTS.md convention

This fork uses a layered AGENTS.md convention:

- `AGENTS.md` (repo root): upstream hermes-agent coding agent guide. Read first.
- `fork/AGENTS.md` (this file): fork-specific overlay for the coding agent. Read second.
- `fork/projects/AGENTS.md`: shared runtime conventions for the hermes agent. Read when working on project files.
- `fork/projects/<name>/AGENTS.md`: per-project conventions. Read when working in a specific project.
- `fork/projects/AGENTS.user.md` (per project, optional): private user notes. Never read by the hermes agent. Read only if the user references it explicitly.

## Communication

- Reply in the user's language.
- Put the direct answer or final command at the end of the response.
- Number questions and findings so the user can answer in order.
- Use absolute paths when referencing files.
- After editing a file, say what you changed in one sentence.
- Never restate things the user already knows.

## What this file is NOT

- It is not a replacement for the upstream `AGENTS.md`. Read both.
- It is not a config file. Persistent settings live in `fork/hermes-config/config.yaml` and similar.
- It is not a cron schedule. Cron jobs go in `fork/hermes-config/cron/jobs.json`.
- It is not the hermes agent's instructions inside the container. Those are at `fork/projects/AGENTS.md` and per-project AGENTS.md files.
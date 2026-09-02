# Research project conventions

This file is read by the hermes agent when its working directory is `/opt/projects/research/`. It layers on top of `/opt/projects/AGENTS.md`. When the two conflict, the project-specific instruction here wins.

## Skill usage in this project

For every research turn, list every relevant skill and use ALL of them:

- `agentic-engineering` for breaking down research questions into eval-first subtasks
- `automation-audit-ops` for documenting what is currently live before proposing changes
- `coding-standards` for any code or config snippet embedded in findings.md
- `docker-patterns` for any deployment / compose snippet that appears in a proposition
- `observability-and-logging` for any logging / monitoring proposal that comes out of research
- `python-patterns` for any code in `prototype/`
- `review-duplication` before recommending a new feature; check whether the answer already exists in another channel or project
- `security-review` for any research that touches auth, secrets, network, or PII
- `api-design` for any research that proposes a new endpoint shape

Run `skills list` mentally before each turn and pull in every skill that fits.

## Purpose

The research channel (`#hermes-research`, Discord id `1543950705776398378`) is for ad-hoc investigations the user wants to run on various topics. Each topic is a self-contained subdirectory with its own findings, propositions, prototypes, and supporting documentation.

A topic is NOT a long-running service. It is a one-shot research effort that produces a written deliverable. When the user moves on, the topic sits as a permanent reference.

## What lives here

Each topic gets its own subdirectory named in `kebab-case`. The topic directory contains the investigation artifacts. No fixed schema, but a typical topic ends up with:

```
research/
├── AGENTS.md                          # this file
├── README.md                          # topic index, written and maintained by the agent
└── <topic-kebab-case>/                # one subdirectory per investigation
    ├── findings.md                     # what the agent learned (conclusions, evidence)
    ├── proposition.md                  # what to do with the findings (proposal)
    ├── prototype/                      # optional, only if a runnable artifact exists
    │   ├── README.md
    │   ├── <files>
    │   └── .venv/                      # per-prototype, gitignored, with leading dot
    └── docs/                           # supporting documentation, links, raw notes
```

Conventions:

- The topic subdirectory name is a slug, not a number. `discord-gateway-rate-limits` not `topic-001`.
- `findings.md` is the main deliverable. It is what the agent reports back to the user with. Keep it skimmable.
- `proposition.md` is optional. Use it when the findings imply an action. Skip it for pure research questions.
- `prototype/` is for runnable artifacts only. README explains how to run. `.venv/` is gitignored.
- `docs/` is for raw notes, external links, transcripts, anything you do not want to consolidate into `findings.md` but want to keep.
- Do not put binary files (images, PDFs, archives) directly in `research/<topic>/`. Reference them from `docs/` with relative paths or external URLs.

## Workflow

When the user types something like `research <topic description>` in `#hermes-research`:

1. Slugify the topic: lowercase, replace spaces and special characters with hyphens, dedupe hyphens, max 80 chars.
2. `mkdir -p /opt/projects/research/<topic-slug>/{prototype,docs}` if a prototype is anticipated, else just the topic dir.
3. Do the research. Use the appropriate tools (web search, ascend scraper, project subagents, etc.).
4. Write `findings.md` (and optionally `proposition.md`).
5. Write the Discord-friendly summary as the FINAL RESPONSE of the turn. There is no Discord send tool: the gateway delivers the final response to `#hermes-research` by itself. Keep it short (3-5 paragraphs max). To attach `findings.md`, add a line of the form `MEDIA:` followed by its absolute path, in plain text outside any code block, inline backticks or blockquote.
6. Update `research/README.md` (the topic index) with a new entry under "Active topics" or "Completed topics". Create the file on the first research turn if it does not exist yet.

## Index maintenance

`research/README.md` is the index of every topic. Nothing generates it: the agent creates it on first use and updates it at the end of every research turn. Keep it small. Two sections:

- "Active topics": topics where the user is still iterating or expecting more work.
- "Completed topics": topics that have a final `findings.md` and the user has moved on.

Format per entry:

```
- **<topic-slug>** (started YYYY-MM-DD): one-line description. Status: active | complete. Last update YYYY-MM-DD.
```

## Per-project conventions inherited

This project follows the same conventions as every other project in `/opt/projects/`:

- Python dependencies live in a per-prototype venv at `/opt/projects/research/<topic-slug>/prototype/.venv/` (with leading dot, gitignored). Build it in the prototype directory when a topic needs one: `uv venv .venv --python python3.12`, then invoke `./.venv/bin/python` directly. There is no project-level venv, and most topics need none at all.
- Cron-scheduled research is not the default. If a recurring research task is needed (e.g. weekly market scan), add a `fork/hermes-config/cron/jobs.json` entry (bind-mounted at `/opt/data/cron/jobs.json` inside the container) pointing at a topic-specific script.
- Skill mounting: `/opt/external-skills/` and `/opt/skills/` are both available. Use them when appropriate. The user's earlier decision was that all skills go in the shared skills mount, not per-project. Stay consistent with that.

## What this project is NOT

- It is NOT a note-taking system. Topics that the user wants to think about without an output are SOUL.md / MEMORY.md territory, not research topics.
- It is NOT a Kanban. Tasks go in the kanban board, not as research topics. Inside the container that board is `/opt/data/kanban.db` (`HERMES_HOME` is `/opt/data`); on the host it is `hermes-data/kanban.db`, runtime state only and gitignored.

## Channel persona expectations

The `#hermes-research` channel is for open-ended investigation, not just answering questions. Tone: thorough, with citations, willing to dig. The agent must:

- Always cite sources (URLs, paper titles, API names).
- Distinguish between confirmed facts, derived inferences, and speculations.
- Prefer Markdown deliverable. Only switch to other formats if the user asks.
- Avoid making changes to code outside `/opt/projects/research/` unless explicitly asked.
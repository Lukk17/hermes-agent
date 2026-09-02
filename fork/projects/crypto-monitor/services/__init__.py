"""
services/agent_bridge.py - the only place the project crosses its own
process boundary.

What this module is for
-----------------------
Calls that leave our Python code and talk to OUTSIDE SYSTEMS:

  - posting to Discord via the host-side hermes gateway
  - (future) firing cron jobs from inside the pipeline
  - (future) pushing to webhooks / Slack / Telegram / etc.

What this module is NOT for
---------------------------
Wrapping Python libraries. If you want to call `requests`, `subprocess`,
`urllib`, or any other stdlib / third-party package, do it directly in the
file that needs it. Do NOT add a wrapper here. The bridge is for crossing
out of our process, not for hiding imports.

When to add a function here
---------------------------
When the call goes to a process or service we do not own (the hermes CLI,
a future MCP server, an external webhook). When we own the receiver (a
local file, an in-memory cache, a sibling Python module), call it directly.
"""

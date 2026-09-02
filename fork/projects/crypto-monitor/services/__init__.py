"""Driven adapters: the project's only process boundaries.

`agent_bridge` is the port to the agent runtime. Add a module here only for a
call that leaves this process; call libraries directly from the file that
needs them.
"""

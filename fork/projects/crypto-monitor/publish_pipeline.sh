#!/bin/bash
# Publish Report - Step 3
# Runs discord_messages_generator.py then sends to Discord

set -e

cd /home/node/.openclaw/workspace/crypto-monitor

# Use venv Python explicitly (required for matplotlib)
PYTHON=/home/node/.openclaw/workspace/crypto-monitor/venv/bin/python

if ! $PYTHON scripts/discord_messages_generator.py; then
    echo "discord_messages_generator failed"
    exit 1
fi

if ! $PYTHON scripts/publish_report.py; then
    echo "publish_report failed"
    exit 1
fi

echo "Step 3 complete. Report sent to Discord."

#!/bin/bash
# Daily Report Pipeline (hermes-compatible)
# Runs report_generator.py which runs all collectors, analyzers, and creates report.
# Designed for the hermes-agent fork; runs as the hermes container user.

set -e

cd /opt/projects/crypto-monitor

# Use project venv Python explicitly (required for matplotlib and pandas).
PYTHON=/opt/projects/crypto-monitor/.venv/bin/python

echo "Running report_generator.py..."
$PYTHON scripts/report_generator.py

echo "Step 1 complete. Report with placeholders created."
echo "Next: hermes agent generates news_summary.md and market_summary.md, then posts via discord.send."
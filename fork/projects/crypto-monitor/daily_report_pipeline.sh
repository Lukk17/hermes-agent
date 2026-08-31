#!/bin/bash
# Daily Report - Step 1
# Runs report_generator.py which runs all collectors, analyzers, and creates report

set -e

cd /home/node/.openclaw/workspace/crypto-monitor

# Use venv Python explicitly (required for matplotlib)
PYTHON=/home/node/.openclaw/workspace/crypto-monitor/venv/bin/python

echo "Running report_generator.py..."
$PYTHON scripts/report_generator.py

echo "Step 1 complete. Report with placeholders created."
echo "Next: Agent generates summaries (step 2)"

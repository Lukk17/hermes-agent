#!/usr/bin/env bash
set -euo pipefail

# cron/scheduler.py refuses any script resolving outside HERMES_HOME/scripts, and
# the pipeline derives its own venv path from BASH_SOURCE, so it must be invoked
# by its real project path rather than mounted into the scripts dir under an alias.
exec bash /opt/data/projects/crypto-monitor/daily_report_pipeline.sh

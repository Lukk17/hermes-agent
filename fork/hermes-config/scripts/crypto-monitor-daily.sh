#!/bin/bash
set -euo pipefail

# The cron scheduler refuses any script path resolving outside HERMES_HOME/scripts,
# so the real pipeline is reached through this in-sandbox wrapper.
exec bash /opt/projects/crypto-monitor/daily_report_pipeline.sh

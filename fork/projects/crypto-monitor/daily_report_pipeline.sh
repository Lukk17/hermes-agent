#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Script: daily_report_pipeline.sh
# Description: Builds the daily crypto report and publishes it to the configured chat.
# Usage: ./daily_report_pipeline.sh [-h]
# Options:
#   -h, --help    Show this help message and exit
# Exit codes:
#   0  report built and published
#   2  bad usage, or the project venv Python is missing
#   3  the report generator failed
#   4  report_latest.json was not rewritten by this run
#   5  publishing failed
#   6  the agent could not write the summaries
# Requires: bash 4.x or newer
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

# --- Constants ---------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# The venv Python is mandatory: matplotlib and pandas live only there.
readonly PYTHON="${SCRIPT_DIR}/.venv/bin/python"
readonly REPORT="${SCRIPT_DIR}/data/reports/report_latest.json"
STARTED_AT="$(date -u +%s)"
readonly STARTED_AT

# --- Logging -----------------------------------------------------------------
log_info()  { echo "[INFO]  $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }
log_error() { echo "[ERROR] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >&2; }

# --- Steps -------------------------------------------------------------------
usage() {
  grep '^#' "$0" | sed 's/^# \?//'
}

require_python() {
  if [[ ! -x "$PYTHON" ]]; then
    log_error "project venv Python is missing or not executable: ${PYTHON}"
    exit 2
  fi
}

assert_report_is_fresh() {
  if [[ ! -f "$REPORT" ]]; then
    log_error "report not found: ${REPORT}"
    exit 4
  fi

  local mtime
  mtime="$(stat -c %Y "$REPORT")"
  if (( mtime < STARTED_AT )); then
    log_error "report was not rewritten by this run, refusing to publish: ${REPORT}"
    exit 4
  fi
}

main() {
  if [[ $# -gt 0 ]]; then
    case "$1" in
      -h|--help)
        usage
        exit 0
        ;;
      *)
        log_error "unknown argument: $1"
        usage
        exit 2
        ;;
    esac
  fi

  require_python
  cd "$SCRIPT_DIR"

  log_info "generating report"
  "$PYTHON" scripts/report_generator.py || { log_error "report generator failed (exit $?)"; exit 3; }

  assert_report_is_fresh

  log_info "generating summaries"
  "$PYTHON" scripts/generate_summaries.py || { log_error "summary generation failed (exit $?)"; exit 6; }

  log_info "publishing report"
  "$PYTHON" scripts/post_to_discord.py || { log_error "publish failed (exit $?)"; exit 5; }

  log_info "pipeline complete"
}

main "$@"

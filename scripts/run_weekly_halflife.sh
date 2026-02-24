#!/usr/bin/env bash
# Weekly cron entry point for code half-life analysis.
# Add to crontab: 0 4 * * 0 /path/to/ai-code-metrics/scripts/run_weekly_halflife.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/halflife_$TIMESTAMP.log"

echo "Starting weekly half-life analysis at $(date)" | tee "$LOG_FILE"

cd "$PROJECT_DIR"
python -m collector.halflife_runner 2>&1 | tee -a "$LOG_FILE"

echo "Half-life analysis finished at $(date)" | tee -a "$LOG_FILE"

# Clean up logs older than 90 days
find "$LOG_DIR" -name "halflife_*.log" -mtime +90 -delete 2>/dev/null || true

#!/usr/bin/env bash
# Daily cron entry point for AI code metrics collection.
# Add to crontab: 0 2 * * * /path/to/ai-code-metrics/scripts/run_daily.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/daily_$TIMESTAMP.log"

echo "Starting daily collection at $(date)" | tee "$LOG_FILE"

cd "$PROJECT_DIR"
python -m collector.metrics_aggregator 2>&1 | tee -a "$LOG_FILE"

echo "Daily collection finished at $(date)" | tee -a "$LOG_FILE"

# Clean up logs older than 30 days
find "$LOG_DIR" -name "daily_*.log" -mtime +30 -delete 2>/dev/null || true

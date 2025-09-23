#!/bin/bash
# Setup cron jobs for automatic log management
# This script sets up cron jobs for:
# 1. Daily log rotation and S3 upload (keep local logs for 30 days)
# 2. Weekly S3 log cleanup (keep S3 logs for 6 months)

# Make the log cleanup scripts executable
chmod +x log_cleanup.py
chmod +x s3_log_cleanup.py

# Get the current directory (where the script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Warning: Virtual environment not found at .venv/bin/activate"
fi

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo "Warning: .env file not found"
fi

# Get S3 bucket from environment or prompt
S3_BUCKET=${S3_LOG_BUCKET:-${S3_BUCKET}}
if [ -z "$S3_BUCKET" ]; then
    echo "Error: S3_LOG_BUCKET or S3_BUCKET environment variable not set"
    echo "Please set S3_LOG_BUCKET in your .env file or environment"
    echo "Current environment variables:"
    echo "  S3_LOG_BUCKET: $S3_LOG_BUCKET"
    echo "  S3_BUCKET: $S3_BUCKET"
    exit 1
fi

echo "Setting up cron jobs for log management..."
echo "S3 Bucket: $S3_BUCKET"
echo ""

# Create cron job entries
# Daily log rotation and S3 upload (runs every day at 1 AM)
DAILY_CRON="0 1 * * * cd $SCRIPT_DIR && python3 log_cleanup.py --rotate >> logs/cron.log 2>&1 && python3 s3_log_cleanup.py --bucket $S3_BUCKET --upload >> logs/cron.log 2>&1"

# Weekly local log cleanup (runs every Sunday at 2 AM, keeps logs for 30 days)
WEEKLY_LOCAL_CRON="0 2 * * 0 cd $SCRIPT_DIR && python3 log_cleanup.py --cleanup --retention-days 30 >> logs/cron.log 2>&1"

# Monthly S3 log cleanup (runs on 1st of every month at 3 AM, keeps S3 logs for 6 months)
MONTHLY_S3_CRON="0 3 1 * * cd $SCRIPT_DIR && python3 s3_log_cleanup.py --bucket $S3_BUCKET --cleanup --retention-days 180 >> logs/cron.log 2>&1"

# Combine all cron jobs
CRON_JOBS="$DAILY_CRON
$WEEKLY_LOCAL_CRON
$MONTHLY_S3_CRON"

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_JOBS") | crontab -

echo "✅ Cron jobs added for automatic log management:"
echo ""
echo "📅 Daily (1:00 AM): Log rotation and S3 upload"
echo "   - Rotates current logs to archives"
echo "   - Uploads logs to S3 for centralized storage"
echo ""
echo "🗑️  Weekly (Sunday 2:00 AM): Local log cleanup"
echo "   - Deletes local logs older than 30 days"
echo "   - Keeps server disk usage low"
echo ""
echo "☁️  Monthly (1st 3:00 AM): S3 log cleanup"
echo "   - Deletes S3 logs older than 6 months (180 days)"
echo "   - Maintains compliance with retention requirements"
echo ""
echo "📊 Log Retention Policy:"
echo "   - Local logs: 30 days maximum"
echo "   - S3 logs: 6 months maximum"
echo "   - Daily uploads ensure no log loss"
echo ""
echo "🔧 Management Commands:"
echo "   crontab -l                    # View current cron jobs"
echo "   crontab -e                    # Edit cron jobs"
echo "   python3 log_cleanup.py --stats    # View local log statistics"
echo "   python3 s3_log_cleanup.py --bucket $S3_BUCKET --stats  # View S3 log statistics"
echo ""
echo "⚠️  Note: This script sets up cron jobs on the current server."
echo "   For local development, run manual commands instead."

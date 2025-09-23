#!/bin/bash
# Setup cron job for automatic log cleanup
# This script sets up a cron job to clean up logs older than 6 months

# Make the log cleanup script executable
chmod +x log_cleanup.py

# Get the current directory (where the script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create cron job entry
CRON_JOB="0 2 * * 0 cd $SCRIPT_DIR && python3 log_cleanup.py --cleanup --retention-days 180 >> logs/cron.log 2>&1"

# Add to crontab (runs every Sunday at 2 AM)
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron job added for automatic log cleanup"
echo "Job will run every Sunday at 2 AM"
echo "Logs older than 180 days (6 months) will be automatically deleted"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To remove this cron job: crontab -e (then delete the line)"
echo ""
echo "Manual log cleanup commands:"
echo "  python3 log_cleanup.py --stats          # View log statistics"
echo "  python3 log_cleanup.py --cleanup        # Clean up old logs"
echo "  python3 log_cleanup.py --rotate          # Rotate current logs"

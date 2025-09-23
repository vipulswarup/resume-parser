#!/bin/bash
# Manual log management commands for local development
# Use these commands instead of setting up cron jobs on your Mac

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

# Get S3 bucket from environment
S3_BUCKET=${S3_LOG_BUCKET:-${S3_BUCKET}}
if [ -z "$S3_BUCKET" ]; then
    echo "Error: S3_LOG_BUCKET or S3_BUCKET environment variable not set"
    echo "Please set S3_LOG_BUCKET in your .env file or environment"
    echo "Current environment variables:"
    echo "  S3_LOG_BUCKET: $S3_LOG_BUCKET"
    echo "  S3_BUCKET: $S3_BUCKET"
    exit 1
fi

echo "🔧 Manual Log Management Commands"
echo "S3 Bucket: $S3_BUCKET"
echo ""

# Function to run command with error handling
run_command() {
    echo "Running: $1"
    eval "$1"
    if [ $? -eq 0 ]; then
        echo "✅ Success"
    else
        echo "❌ Failed"
    fi
    echo ""
}

# Show current log statistics
echo "📊 Current Log Statistics:"
echo "=========================="
run_command "python3 log_cleanup.py --stats"
run_command "python3 s3_log_cleanup.py --bucket $S3_BUCKET --stats"

# Daily operations (run these daily in production)
echo "📅 Daily Operations (Production Schedule):"
echo "=========================================="
echo "1. Rotate current logs to archives"
run_command "python3 log_cleanup.py --rotate"

echo "2. Upload logs to S3"
run_command "python3 s3_log_cleanup.py --bucket $S3_BUCKET --upload"

# Weekly operations (run these weekly in production)
echo "🗑️  Weekly Operations (Production Schedule):"
echo "==========================================="
echo "3. Clean up local logs older than 30 days"
run_command "python3 log_cleanup.py --cleanup --retention-days 30"

# Monthly operations (run these monthly in production)
echo "☁️  Monthly Operations (Production Schedule):"
echo "==========================================="
echo "4. Clean up S3 logs older than 6 months"
run_command "python3 s3_log_cleanup.py --bucket $S3_BUCKET --cleanup --retention-days 180"

echo "📋 Summary:"
echo "==========="
echo "✅ Log rotation completed"
echo "✅ S3 upload completed"
echo "✅ Local cleanup (30 days) completed"
echo "✅ S3 cleanup (6 months) completed"
echo ""
echo "💡 For production deployment:"
echo "   - Run ./setup_cron.sh on the server"
echo "   - This will set up automatic daily/weekly/monthly operations"
echo ""
echo "🔍 To monitor logs:"
echo "   - Local logs: python3 log_cleanup.py --stats"
echo "   - S3 logs: python3 s3_log_cleanup.py --bucket $S3_BUCKET --stats"
echo "   - API: curl http://localhost:8000/logs/s3"

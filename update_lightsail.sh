#!/bin/bash
# Update script for Amazon Lightsail deployment
# Run this script to update the application on your Lightsail instance

set -e  # Exit on any error

echo "🔄 Updating Resume Parser on Lightsail"
echo "====================================="

APP_DIR="/opt/resume-parser"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please run this script as a regular user, not root"
    exit 1
fi

# Navigate to application directory
cd $APP_DIR

# Stop the application
echo "⏹️  Stopping application..."
sudo systemctl stop resume-parser

# Backup current version
echo "💾 Creating backup..."
BACKUP_DIR="/opt/backups/$(date +%Y%m%d_%H%M%S)"
sudo mkdir -p $BACKUP_DIR
sudo cp -r $APP_DIR $BACKUP_DIR/
echo "Backup created at: $BACKUP_DIR"

# Update from Git (if using Git)
echo "📥 Updating from repository..."
# git pull origin main

# Or update files manually (if not using Git)
echo "📁 Updating application files..."
# Copy your updated files here

# Activate virtual environment and update dependencies
echo "📦 Updating dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations (if any)
echo "🗄️  Running database migrations..."
python3 create_tables.py

# Set up log management
echo "📝 Setting up log management..."
./setup_cron.sh

# Restart services
echo "🔄 Restarting services..."
sudo systemctl start resume-parser
sudo systemctl reload nginx

# Check service status
echo "✅ Checking service status..."
sleep 5
sudo systemctl status resume-parser --no-pager

# Test application
echo "🧪 Testing application..."
curl -f http://localhost:8000/health || echo "⚠️  Health check failed"

echo ""
echo "✅ Update completed successfully!"
echo ""
echo "📊 Application Status:"
echo "  Service: $(sudo systemctl is-active resume-parser)"
echo "  Health: $(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo 'Unknown')"
echo ""
echo "🔧 Management Commands:"
echo "  sudo systemctl status resume-parser    # Check status"
echo "  sudo journalctl -u resume-parser -f   # View logs"
echo "  curl http://localhost:8000/stats      # View statistics"

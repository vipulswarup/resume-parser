#!/bin/bash
# DigitalOcean VM deployment script for Resume Parser
# Run this script on your DigitalOcean droplet

set -e  # Exit on any error

echo "🚀 Deploying Resume Parser to DigitalOcean VM"
echo "=============================================="

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.12 and pip (Ubuntu 24.04 default)
echo "🐍 Installing Python 3.12..."
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip

# Install PostgreSQL server and client
echo "🐘 Installing PostgreSQL..."
sudo apt install -y postgresql postgresql-contrib postgresql-client

# Install system dependencies
echo "📚 Installing system dependencies..."
sudo apt install -y build-essential libpq-dev libmagic1

# Create application directory
echo "📁 Setting up application directory..."
APP_DIR="/opt/resume-parser"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR
cd $APP_DIR

# Clone repository (replace with your Git URL)
echo "📥 Cloning repository..."
# git clone https://github.com/vipulswarup/resume-parser.git .
# For now, we'll assume files are already uploaded

# Copy files from current directory to app directory
echo "📋 Copying application files..."
CURRENT_DIR=$(pwd)
# Copy all files and directories
cp -r $CURRENT_DIR/* $APP_DIR/ 2>/dev/null || true
# Copy hidden files (like .env)
cp -r $CURRENT_DIR/.* $APP_DIR/ 2>/dev/null || true
# Ensure we have the requirements.txt file
if [ ! -f "$APP_DIR/requirements.txt" ]; then
    echo "⚠️  requirements.txt not found, copying from current directory..."
    cp $CURRENT_DIR/requirements.txt $APP_DIR/
fi

# Set up PostgreSQL database
echo "🗄️  Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE resume_parser_db;"
sudo -u postgres psql -c "CREATE USER resume_user WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE resume_parser_db TO resume_user;"
sudo -u postgres psql -c "ALTER USER resume_user CREATEDB;"

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3.12 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/resume-parser.service > /dev/null <<EOF
[Unit]
Description=Resume Parser FastAPI Application
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/.venv/bin
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create nginx configuration
echo "🌐 Setting up Nginx reverse proxy..."
sudo apt install -y nginx

sudo tee /etc/nginx/sites-available/resume-parser > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/resume-parser /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Install SSL certificate (Let's Encrypt)
echo "🔒 Setting up SSL certificate..."
sudo apt install -y certbot python3-certbot-nginx

# Create log directories
echo "📝 Creating log directories..."
mkdir -p logs
chmod 755 logs

# Set up log rotation
echo "🔄 Setting up log rotation..."
sudo tee /etc/logrotate.d/resume-parser > /dev/null <<EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload resume-parser
    endscript
}
EOF

# Create environment file template
echo "⚙️  Creating environment configuration..."
cat > .env.template <<EOF
# Database Configuration (Local PostgreSQL)
DATABASE_URL=postgresql://resume_user:your_secure_password@localhost:5432/resume_parser_db

# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET=your-s3-bucket
S3_LOG_BUCKET=your-logs-bucket

# LLM Configuration
OPENAI_API_KEY=sk-your-openai-key
GROQ_API_KEY=gsk-your-groq-key

# Logging Configuration
ENABLE_S3_LOGGING=true
S3_LOG_PREFIX=logs
EOF

echo "✅ Deployment script completed!"
echo ""
echo "📋 Next Steps:"
echo "1. Copy your .env file to $APP_DIR/.env"
echo "2. Update database password in .env file"
echo "3. Run: sudo systemctl enable resume-parser"
echo "4. Run: sudo systemctl start resume-parser"
echo "5. Run: sudo systemctl enable nginx"
echo "6. Run: sudo systemctl start nginx"
echo "7. Set up SSL (optional): sudo certbot --nginx -d yourdomain.com"
echo "8. Access your app at: http://167.71.237.11"
echo ""
echo "🔧 Management Commands:"
echo "  sudo systemctl status resume-parser    # Check service status"
echo "  sudo systemctl restart resume-parser  # Restart service"
echo "  sudo journalctl -u resume-parser -f   # View logs"
echo "  sudo systemctl status postgresql      # Check database status"
echo ""
echo "📊 Monitoring:"
echo "  curl http://167.71.237.11/health     # Health check"
echo "  curl http://167.71.237.11/stats      # System statistics"
echo "  curl http://167.71.237.11/ui/upload # Upload page"
echo "  curl http://167.71.237.11/ui/candidates # Candidates page"

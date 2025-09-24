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
# Start PostgreSQL if not running
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Generate secure password for database
echo "🔐 Generating secure database password..."
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
echo "✅ Generated secure password for resume_user"

# Create database and user with proper authentication
echo "📊 Creating database..."
sudo -u postgres psql -c "CREATE DATABASE resume_parser_db;" 2>/dev/null || echo "✅ Database already exists"

echo "👤 Setting up database user..."
sudo -u postgres psql -c "DROP USER IF EXISTS resume_user;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER resume_user WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "✅ User already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE resume_parser_db TO resume_user;" 2>/dev/null || true
sudo -u postgres psql -c "ALTER USER resume_user CREATEDB;" 2>/dev/null || true

# Update password for existing user
sudo -u postgres psql -c "ALTER USER resume_user PASSWORD '$DB_PASSWORD';" 2>/dev/null || true

# Configure PostgreSQL for local connections
echo "🔧 Configuring PostgreSQL authentication..."
# Check if configuration already exists
if ! grep -q "resume_parser_db" /etc/postgresql/16/main/pg_hba.conf; then
    sudo tee -a /etc/postgresql/16/main/pg_hba.conf > /dev/null <<EOF
# Resume Parser local connections
local   resume_parser_db    resume_user                    md5
host    resume_parser_db    resume_user    127.0.0.1/32    md5
host    resume_parser_db    resume_user    ::1/128         md5
EOF
    echo "✅ PostgreSQL authentication configured"
else
    echo "✅ PostgreSQL authentication already configured"
fi

# Restart PostgreSQL to apply changes
sudo systemctl restart postgresql

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3.12 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Kill any existing processes using port 8000
echo "🔄 Stopping any existing services..."
sudo pkill -f "uvicorn" 2>/dev/null || true
sudo pkill -f "port 8000" 2>/dev/null || true
sleep 2

# Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/resume-parser.service > /dev/null <<EOF
[Unit]
Description=Resume Parser FastAPI Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
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

# Update .env file with correct database URL
echo "📝 Updating .env file with database configuration..."
DB_URL="postgresql://resume_user:$DB_PASSWORD@localhost:5432/resume_parser_db"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating new .env file..."
    cp .env.template .env
fi

# Update or add DATABASE_URL in .env file
if grep -q "DATABASE_URL=" .env; then
    # Update existing DATABASE_URL
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=$DB_URL|" .env
    echo "✅ Updated existing DATABASE_URL in .env file"
else
    # Add DATABASE_URL to .env file
    echo "DATABASE_URL=$DB_URL" >> .env
    echo "✅ Added DATABASE_URL to .env file"
fi

echo "🔐 Database password saved to .env file"
echo "⚠️  Please update other values in .env file with your actual API keys and credentials"

# Test database connection
echo "🧪 Testing database connection..."
sudo -u postgres psql -c "SELECT 1;" > /dev/null && echo "✅ PostgreSQL connection successful" || echo "❌ PostgreSQL connection failed"

# Test database connection with application credentials
echo "🧪 Testing application database connection..."
if psql "$DB_URL" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Application database connection successful"
else
    echo "❌ Application database connection failed"
    echo "🔧 Troubleshooting: Check if PostgreSQL is running and credentials are correct"
fi

# Create database tables
echo "🗄️  Creating database tables..."
cd $APP_DIR
source .venv/bin/activate
python3 create_tables.py
if [ $? -eq 0 ]; then
    echo "✅ Database tables created successfully"
else
    echo "❌ Failed to create database tables"
    echo "🔧 You may need to run: python3 create_tables.py manually"
fi

# Reload systemd and start services
echo "🔄 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable resume-parser
sudo systemctl start resume-parser
sudo systemctl enable nginx
sudo systemctl start nginx

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 5

# Test the application
echo "🧪 Testing application..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Application is running successfully!"
    echo "🌐 Your app is available at: http://167.71.237.11"
else
    echo "❌ Application failed to start. Check logs with: sudo journalctl -u resume-parser -f"
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Your Resume Parser is now running at:"
echo "  🌐 Main App: http://167.71.237.11"
echo "  📤 Upload: http://167.71.237.11/ui/upload"
echo "  👥 Candidates: http://167.71.237.11/ui/candidates"
echo "  ❤️  Health: http://167.71.237.11/health"
echo ""
echo "🔧 Management Commands:"
echo "  sudo systemctl status resume-parser    # Check service status"
echo "  sudo systemctl restart resume-parser  # Restart service"
echo "  sudo journalctl -u resume-parser -f   # View logs"
echo "  sudo systemctl status postgresql      # Check database status"
echo ""
echo "📊 Quick Tests:"
echo "  curl http://167.71.237.11/health     # Health check"
echo "  curl http://167.71.237.11/stats      # System statistics"
echo ""
echo "⚠️  Remember to update your .env file with real API keys!"

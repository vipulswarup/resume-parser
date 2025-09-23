# DigitalOcean VM Deployment Guide

## 🚀 Quick Setup (5-10 minutes)

### **1. Create DigitalOcean Droplet**
- Go to [DigitalOcean Console](https://cloud.digitalocean.com/)
- Click "Create Droplet"
- **OS**: Ubuntu 22.04 LTS
- **Plan**: $6/month (1GB RAM) or $12/month (2GB RAM)
- **Add-ons**: 
  - ✅ PostgreSQL Database (self-hosted)
  - ✅ Public IP (included)
  - ✅ Firewall (optional)

### **Your Server Details**
- **Public IP**: 167.71.237.11
- **Access URL**: http://167.71.237.11

### **2. Connect to DigitalOcean Droplet**
```bash
# Connect via SSH (use your SSH key)
ssh root@167.71.237.11
# OR if using ubuntu user:
ssh ubuntu@167.71.237.11
```

### **3. Run Deployment Script**
```bash
# Upload your project files to the droplet
# Then run:
chmod +x deploy_lightsail.sh
./deploy_lightsail.sh
```

### **4. Configure Environment**
```bash
# Copy your .env file to the droplet
cp .env /opt/resume-parser/.env

# Edit database URL to point to local PostgreSQL
nano /opt/resume-parser/.env
# Set DATABASE_URL=postgresql://username:password@localhost:5432/resume_parser_db
```

### **5. Start Services**
```bash
# Enable and start the application
sudo systemctl enable resume-parser
sudo systemctl start resume-parser
sudo systemctl enable nginx
sudo systemctl start nginx

# Set up SSL (optional - for domain)
sudo certbot --nginx -d yourdomain.com
# OR access directly via IP: http://167.71.237.11
```

## 💰 **Cost Breakdown**

| Component | Monthly Cost |
|-----------|---------------|
| **DigitalOcean Droplet** | $6-12 |
| **PostgreSQL Database** | Free (self-hosted) |
| **Public IP** | Free |
| **S3 Storage** | ~$1-5 |
| **Total** | **$7-17/month** |

## 🔧 **Management Commands**

### **Application Management**
```bash
# Check service status
sudo systemctl status resume-parser

# Restart application
sudo systemctl restart resume-parser

# View application logs
sudo journalctl -u resume-parser -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### **Log Management**
```bash
# Run manual log management
cd /opt/resume-parser
./manual_log_management.sh

# Set up automatic log cleanup
./setup_cron.sh
```

### **Database Management**
```bash
# Connect to local database
psql -U postgres -d resume_parser_db

# Create tables
python3 create_tables.py
```

## 📊 **Monitoring & Health Checks**

### **Health Endpoints**
- `http://167.71.237.11/health` - Basic health check
- `http://167.71.237.11/stats` - System statistics
- `http://167.71.237.11/logs/s3` - S3 log statistics

### **Application URLs**
- `http://167.71.237.11/ui/upload` - Upload resumes
- `http://167.71.237.11/ui/candidates` - View candidates
- `http://167.71.237.11/docs` - API documentation

## 🔒 **Security Considerations**

### **Firewall Setup**
```bash
# Configure DigitalOcean firewall
# Allow: HTTP (80), HTTPS (443), SSH (22)
# Block: All other ports
```

### **SSL Certificate**
```bash
# Automatic SSL renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### **Environment Security**
- Keep `.env` file secure (600 permissions)
- Use strong database passwords
- Rotate API keys regularly

## 📈 **Scaling Options**

### **Upgrade Instance**
- DigitalOcean: $6 → $12 → $24 → $48
- Easy one-click upgrade in console

### **Database Scaling**
- Start with self-hosted PostgreSQL (free)
- Upgrade to managed database if needed

### **Load Balancing**
- Add multiple droplets behind load balancer
- Use DigitalOcean load balancer ($12/month)

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Application Won't Start**
```bash
# Check logs
sudo journalctl -u resume-parser -f

# Check environment
cat /opt/resume-parser/.env

# Test manually
cd /opt/resume-parser
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### **Database Connection Issues**
```bash
# Test database connection
psql -U postgres -d resume_parser_db

# Check database status
sudo systemctl status postgresql
```

#### **Nginx Issues**
```bash
# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### **Performance Monitoring**
```bash
# Check system resources
htop
df -h
free -h

# Check application performance
curl http://localhost:8000/stats
```

## 🔄 **Backup & Recovery**

### **Database Backup**
```bash
# Create backup
pg_dump -U postgres resume_parser_db > backup.sql

# Restore backup
psql -U postgres resume_parser_db < backup.sql
```

### **Application Backup**
```bash
# Backup application files
tar -czf resume-parser-backup.tar.gz /opt/resume-parser

# Backup logs
tar -czf logs-backup.tar.gz /opt/resume-parser/logs
```

## 📞 **Support**

- **DigitalOcean Documentation**: [DigitalOcean Docs](https://docs.digitalocean.com/)
- **Application Logs**: `sudo journalctl -u resume-parser -f`
- **System Logs**: `/var/log/syslog`
- **Nginx Logs**: `/var/log/nginx/`

---

**Total Setup Time**: 5-10 minutes  
**Monthly Cost**: $7-17  
**Scalability**: Easy upgrade path  
**Maintenance**: Minimal with automated scripts

# Amazon Lightsail Deployment Guide

## 🚀 Quick Setup (5-10 minutes)

### **1. Create Lightsail Instance**
- Go to [Amazon Lightsail Console](https://lightsail.aws.amazon.com/)
- Click "Create instance"
- **OS**: Ubuntu 22.04 LTS
- **Instance plan**: $5/month (512MB RAM) or $10/month (1GB RAM)
- **Add-ons**: 
  - ✅ Database (PostgreSQL) - $15/month
  - ✅ Static IP (free)
  - ✅ DNS zone (optional)

### **2. Connect to Instance**
```bash
# Download SSH key from Lightsail console
# Connect via SSH
ssh -i LightsailDefaultKey-us-east-1.pem ubuntu@your-instance-ip
```

### **3. Run Deployment Script**
```bash
# Upload your project files to the instance
# Then run:
chmod +x deploy_lightsail.sh
./deploy_lightsail.sh
```

### **4. Configure Environment**
```bash
# Copy your .env file to the instance
cp .env /opt/resume-parser/.env

# Edit database URL to point to Lightsail database
nano /opt/resume-parser/.env
```

### **5. Start Services**
```bash
# Enable and start the application
sudo systemctl enable resume-parser
sudo systemctl start resume-parser
sudo systemctl enable nginx
sudo systemctl start nginx

# Set up SSL (replace with your domain)
sudo certbot --nginx -d yourdomain.com
```

## 💰 **Cost Breakdown**

| Component | Monthly Cost |
|-----------|---------------|
| **Lightsail Instance** | $5-10 |
| **PostgreSQL Database** | $15 |
| **Static IP** | Free |
| **S3 Storage** | ~$1-5 |
| **Total** | **$21-30/month** |

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
# Connect to database
psql -h your-db-host -U username -d resume_parser_db

# Create tables
python3 create_tables.py
```

## 📊 **Monitoring & Health Checks**

### **Health Endpoints**
- `http://your-domain/health` - Basic health check
- `http://your-domain/stats` - System statistics
- `http://your-domain/logs/s3` - S3 log statistics

### **Application URLs**
- `http://your-domain/ui/upload` - Upload resumes
- `http://your-domain/ui/candidates` - View candidates
- `http://your-domain/docs` - API documentation

## 🔒 **Security Considerations**

### **Firewall Setup**
```bash
# Configure Lightsail firewall
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
- Lightsail: $5 → $10 → $20 → $40
- Easy one-click upgrade in console

### **Database Scaling**
- Start with $15/month PostgreSQL
- Upgrade to RDS for production (if needed)

### **Load Balancing**
- Add multiple instances behind load balancer
- Use Lightsail load balancer ($18/month)

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
psql -h your-db-host -U username -d resume_parser_db

# Check database status in Lightsail console
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
pg_dump -h your-db-host -U username resume_parser_db > backup.sql

# Restore backup
psql -h your-db-host -U username resume_parser_db < backup.sql
```

### **Application Backup**
```bash
# Backup application files
tar -czf resume-parser-backup.tar.gz /opt/resume-parser

# Backup logs
tar -czf logs-backup.tar.gz /opt/resume-parser/logs
```

## 📞 **Support**

- **Lightsail Documentation**: [AWS Lightsail Docs](https://docs.aws.amazon.com/lightsail/)
- **Application Logs**: `sudo journalctl -u resume-parser -f`
- **System Logs**: `/var/log/syslog`
- **Nginx Logs**: `/var/log/nginx/`

---

**Total Setup Time**: 5-10 minutes  
**Monthly Cost**: $21-30  
**Scalability**: Easy upgrade path  
**Maintenance**: Minimal with automated scripts

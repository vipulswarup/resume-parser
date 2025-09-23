# Render.com Deployment Guide

## 🚀 Quick Deploy to Render (5 minutes)

### **Step 1: Prepare Your Repository**

1. **Push your code to GitHub** (if not already done):
   ```bash
   git add .
   git commit -m "Add Render deployment configuration"
   git push origin main
   ```

2. **Make sure you have these files**:
   - ✅ `render.yaml` (deployment configuration)
   - ✅ `requirements.txt` (Python dependencies)
   - ✅ `app/main.py` (FastAPI application)
   - ✅ All your application files

### **Step 2: Create Database on Render**

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"PostgreSQL"**
3. **Configure Database**:
   - **Name**: `resume-parser-db`
   - **Plan**: Free (shared)
   - **Database Name**: `resume_parser_db`
   - **User**: `resume_parser_user`
4. **Click "Create Database"**
5. **Wait for database to be ready** (2-3 minutes)
6. **Copy the connection string** (you'll need this later)

### **Step 3: Deploy Web Service**

1. **Go to Render Dashboard** → **"New +"** → **"Web Service"**
2. **Connect Repository**:
   - **Build and deploy from a Git repository**
   - **Connect your GitHub account**
   - **Select your repository**: `resume-parser`
   - **Branch**: `main`

3. **Configure Service**:
   - **Name**: `resume-parser`
   - **Environment**: `Python 3`
   - **Plan**: Free
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Environment Variables**:
   ```
   DATABASE_URL = [Your PostgreSQL connection string from Step 2]
   AWS_ACCESS_KEY_ID = your_aws_access_key
   AWS_SECRET_ACCESS_KEY = your_aws_secret_key
   S3_BUCKET = your-s3-bucket-name
   S3_LOG_BUCKET = your-logs-bucket-name
   OPENAI_API_KEY = sk-your-openai-key
   GROQ_API_KEY = gsk-your-groq-key
   ENABLE_S3_LOGGING = true
   S3_LOG_PREFIX = logs
   ```

5. **Click "Create Web Service"**

### **Step 4: Initialize Database**

1. **Wait for deployment to complete** (5-10 minutes)
2. **Go to your service URL** (e.g., `https://resume-parser.onrender.com`)
3. **Check if it's working**: Visit `/health` endpoint
4. **Initialize database tables**:
   - Go to **Render Dashboard** → **Your Service** → **Shell**
   - Run: `python3 create_tables.py`

### **Step 5: Test Your Application**

1. **Health Check**: `https://your-app.onrender.com/health`
2. **Upload Page**: `https://your-app.onrender.com/ui/upload`
3. **Candidates Page**: `https://your-app.onrender.com/ui/candidates`
4. **API Docs**: `https://your-app.onrender.com/docs`

## 💰 **Render.com Pricing**

### **Free Tier (Perfect for Development)**
- ✅ **Web Service**: 750 hours/month (free)
- ✅ **PostgreSQL Database**: 1GB storage (free)
- ✅ **SSL Certificate**: Included
- ✅ **Custom Domain**: Supported
- ⚠️ **Limitations**: 
  - Service sleeps after 15 minutes of inactivity
  - Cold start takes 30-60 seconds
  - 1GB database storage limit

### **Paid Plans (When You Need More)**
- **Starter Plan**: $7/month
  - Always-on service (no sleep)
  - 1GB RAM
  - 1GB database storage
- **Standard Plan**: $25/month
  - 2GB RAM
  - 10GB database storage
  - Better performance

## 🔧 **Management & Monitoring**

### **Render Dashboard Features**
- **Real-time logs**: View application logs in real-time
- **Metrics**: CPU, memory, and request metrics
- **Environment variables**: Easy management
- **Database management**: Built-in PostgreSQL admin
- **SSL certificates**: Automatic renewal

### **Useful Commands**
```bash
# Access your service shell
# Go to Dashboard → Your Service → Shell

# Check application status
curl https://your-app.onrender.com/health

# View logs
# Use Render Dashboard → Logs tab

# Database operations
psql $DATABASE_URL
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Service Won't Start**
1. **Check logs** in Render Dashboard
2. **Verify environment variables** are set correctly
3. **Check build command** is correct
4. **Ensure all dependencies** are in requirements.txt

#### **Database Connection Issues**
1. **Verify DATABASE_URL** is correct
2. **Check database is running** in Render Dashboard
3. **Run database initialization**: `python3 create_tables.py`

#### **Cold Start Issues (Free Tier)**
- **First request** after inactivity takes 30-60 seconds
- **Solution**: Upgrade to paid plan for always-on service
- **Workaround**: Set up uptime monitoring to ping your service

#### **Memory Issues**
- **Free tier**: 512MB RAM limit
- **Monitor usage** in Render Dashboard
- **Optimize**: Reduce memory usage or upgrade plan

### **Performance Optimization**

#### **For Free Tier**
```python
# Add to your app/main.py
import os
from fastapi import FastAPI

# Optimize for Render free tier
if os.getenv("RENDER"):
    # Disable some features that use more memory
    ENABLE_S3_LOGGING = False  # Reduce memory usage
```

#### **Database Optimization**
```sql
-- Add indexes for better performance
CREATE INDEX idx_candidates_processing_date ON candidates(processing_date);
CREATE INDEX idx_resumes_uploaded_at ON resumes(uploaded_at);
```

## 📊 **Monitoring Your Application**

### **Health Checks**
- **Basic**: `https://your-app.onrender.com/health`
- **Detailed**: `https://your-app.onrender.com/stats`
- **Logs**: `https://your-app.onrender.com/logs/s3`

### **Uptime Monitoring (Recommended)**
- **UptimeRobot**: Free uptime monitoring
- **Pingdom**: Alternative monitoring service
- **Set up**: Ping your `/health` endpoint every 5 minutes

## 🔄 **Updates & Maintenance**

### **Automatic Deployments**
- **Push to GitHub** → **Automatic deployment** on Render
- **No manual intervention** needed
- **Rollback**: Available in Render Dashboard

### **Database Backups**
- **Render handles backups** automatically
- **Manual backup**: Use Render Dashboard → Database → Backup
- **Restore**: Available in Render Dashboard

## 🎯 **Next Steps After Deployment**

1. **Set up custom domain** (optional)
2. **Configure uptime monitoring**
3. **Set up log management** (S3 logging)
4. **Test all features** thoroughly
5. **Monitor performance** and upgrade if needed

---

**Total Setup Time**: 5 minutes  
**Monthly Cost**: $0 (free tier)  
**Scalability**: Easy upgrade path  
**Maintenance**: Minimal with automatic deployments

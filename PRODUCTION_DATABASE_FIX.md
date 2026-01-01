# Production Database Not Recognized - Troubleshooting Guide

## Problem
Your bot crashes in production with:
```
command finished with error [python production_start.py]: exit status 1
crash loop detected
```

The error message `"Database is not recognized on production"` indicates DATABASE_URL is missing or the bot code needs to be updated.

---

## ✅ Solution 1: Verify DATABASE_URL is Set in Production

### Step 1: Check Your Production Secrets

1. **Go to your Replit Reserved VM deployment**
2. **Navigate to: Deployments → Your Active Deployment → Secrets**
3. **Look for the `DATABASE_URL` secret**

### Step 2: If DATABASE_URL is Missing

Add it with your Neon PostgreSQL connection string:
```
DATABASE_URL=postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/lockbay_db
```

**Where to get this:**
- Go to your Neon dashboard
- Select your "lockbay_db" database
- Copy the connection string (should start with `postgresql://`)
- Paste it as the `DATABASE_URL` secret value

### Step 3: Redeploy

After adding DATABASE_URL:
1. Save the secret
2. Click "Redeploy" or "Restart Deployment"
3. Wait for the bot to start

---

## ✅ Solution 2: Deploy Latest Code with Database Fix

If DATABASE_URL is already set, you may need to deploy the latest code that includes the database validation fix.

### How to Deploy Latest Code

**From your Replit development environment:**

1. **Commit the latest changes:**
   ```bash
   # View what changed
   git status
   
   # Add all changes
   git add .
   
   # Commit with message
   git commit -m "Fix: Database validation for unified Neon PostgreSQL in production"
   ```

2. **Push to your deployment branch:**
   ```bash
   # If using main branch
   git push origin main
   
   # If using production branch
   git push origin production
   ```

3. **Trigger redeployment:**
   - Go to Replit Deployments
   - Click "Redeploy" to pull latest code
   - Or use auto-deploy if enabled

---

## 🐛 Debug: See Actual Error Message

To see the EXACT error (not just "exit status 1"), run this in your Replit shell:

```bash
# Set production environment
export ENVIRONMENT=production

# Run the bot startup script
python production_start.py
```

This will show you the specific error message like:
- `❌ DATABASE_URL not configured! Please set DATABASE_URL environment variable.`
- `🚨 CRITICAL: Database not configured!`
- `❌ STARTUP ERROR: Missing webhook secrets: ...`

---

## 📋 Complete Production Secrets Checklist

Make sure ALL these secrets are configured in your production deployment:

### Database
- ✅ **DATABASE_URL** - Your Neon PostgreSQL connection string
- ✅ **RAILWAY_BACKUP_DB_URL** - Backup database (optional but recommended)
- ✅ **REDIS_URL** - Redis connection string

### Email & Notifications  
- ✅ **BREVO_API_KEY** - Brevo/Sendinblue API key (CRITICAL)
- ✅ **ADMIN_EMAIL** - Admin email address

### Webhook Security
- ✅ **FINCRA_WEBHOOK_ENCRYPTION_KEY** - From Fincra dashboard
- ✅ **DYNOPAY_WEBHOOK_SECRET** - From DynoPay dashboard
- ✅ **BLOCKBEE_WEBHOOK_SECRET** - From BlockBee dashboard

### Bot Security
- ✅ **TELEGRAM_BOT_TOKEN** - Your Telegram bot token
- ✅ **ADMIN_EMAIL_SECRET** - 32+ character random string
- ✅ **CASHOUT_HMAC_SECRET** - 32+ character random string

### URLs
- ✅ **WEBHOOK_URL** - Your deployment URL + /webhook (e.g., https://lockbay.replit.app/webhook)
- ✅ **ADMIN_ACTION_BASE_URL** - Your deployment URL (e.g., https://lockbay.replit.app)

---

## 🎯 Quick Fix Commands

**If you just need to regenerate secrets:**

```bash
# Generate ADMIN_EMAIL_SECRET
python3 -c "import secrets; print('ADMIN_EMAIL_SECRET=' + secrets.token_urlsafe(32))"

# Generate CASHOUT_HMAC_SECRET
python3 -c "import secrets; print('CASHOUT_HMAC_SECRET=' + secrets.token_urlsafe(32))"
```

---

## ✅ Success Indicators

After fixing, your bot should log:
```
✅ Database: Neon PostgreSQL (Unified) - configured and ready for production
✅ All webhook secrets configured
🚀 Starting Telegram Bot - Production Mode
```

---

## 🆘 Still Not Working?

Run this diagnostic command and share the output:

```bash
python3 -c "
import os
print('=== Environment Check ===')
print('ENVIRONMENT:', os.getenv('ENVIRONMENT', 'not set'))
print('DATABASE_URL:', 'SET' if os.getenv('DATABASE_URL') else 'NOT SET')
print('BREVO_API_KEY:', 'SET' if os.getenv('BREVO_API_KEY') else 'NOT SET')
print('FINCRA_WEBHOOK_ENCRYPTION_KEY:', 'SET' if os.getenv('FINCRA_WEBHOOK_ENCRYPTION_KEY') else 'NOT SET')
print('DYNOPAY_WEBHOOK_SECRET:', 'SET' if os.getenv('DYNOPAY_WEBHOOK_SECRET') else 'NOT SET')
"
```

This will show which secrets are missing without exposing their values.

# LockBay Production Deployment Checklist

## Overview
This checklist ensures your LockBay Telegram bot deploys successfully to production on Replit. Production deployments require specific environment variables and configurations that differ from development.

---

## 🚨 Critical Production Environment Variables

### **1. Dual-Domain Configuration (REQUIRED)**

LockBay uses a **dual-domain strategy** for optimal functionality:
- **`lockbay.replit.app`** → Technical server (webhooks, admin actions)
- **`lockbay.io`** → Branded customer-facing URLs (public profiles, referrals)

```bash
# ===== SERVER DOMAIN (for webhooks - points to actual server) =====
# REQUIRED: Primary webhook URL - auto-configures ALL webhook endpoints
WEBHOOK_URL=https://lockbay.replit.app/webhook

# OPTIONAL: Admin action base URL (for email action buttons)
# Only set if different from server domain (rare)
ADMIN_ACTION_BASE_URL=https://lockbay.replit.app

# ===== BRANDED DOMAIN (for customer-facing links) =====
# REQUIRED: Public profile base URL (for shareable reputation pages)
PUBLIC_PROFILE_BASE_URL=https://lockbay.io
```

**Important: What you DON'T need to set:**
```bash
# ❌ NOT NEEDED - These are auto-generated from WEBHOOK_URL:
# DYNOPAY_WEBHOOK_URL        → Auto: https://lockbay.replit.app/dynopay/*
# BLOCKBEE_CALLBACK_URL      → Auto: https://lockbay.replit.app/blockbee/callback/*
# FINCRA_WEBHOOK_URL         → Auto: https://lockbay.replit.app/webhook/api/fincra/webhook
# TELEGRAM_WEBHOOK_URL       → Auto: https://lockbay.replit.app/webhook
```

**How it works:**
Setting `WEBHOOK_URL=https://lockbay.replit.app/webhook` automatically configures:
- ✅ Telegram bot webhook
- ✅ DynoPay payment callbacks  
- ✅ BlockBee payment callbacks
- ✅ Fincra bank webhooks
- ✅ Twilio SMS webhooks

**Why dual domains?**
- **Webhooks need the actual server** → External services POST to `lockbay.replit.app`
- **Public profiles need branding** → Users share `lockbay.io/u/username` (better trust/SEO)

**CRITICAL: DNS Requirement**
For branded public profiles to work, you MUST configure DNS:

**Option 1: DNS CNAME Record** (Recommended)
```
CNAME: lockbay.io → lockbay.replit.app
```

**Option 2: Reverse Proxy** (Advanced)
Use Cloudflare, Nginx, or similar to route:
```
https://lockbay.io/* → https://lockbay.replit.app/*
```

**Common mistakes:**
- ❌ **Wrong:** `WEBHOOK_URL=https://lockbay.io/webhook` → Webhooks NEVER arrive!
- ❌ **Wrong:** `ADMIN_ACTION_BASE_URL=https://lockbay.io` → Email buttons break!
- ✅ **Correct:** Webhooks use `lockbay.replit.app`, profiles use `lockbay.io`

---

### **2. Webhook Security Secrets (REQUIRED)**
These secrets validate incoming webhooks from payment processors. **Get these from your provider dashboards.**

```bash
# DynoPay webhook signature verification
DYNOPAY_WEBHOOK_SECRET=your_dynopay_secret_here

# BlockBee webhook signature verification  
BLOCKBEE_WEBHOOK_SECRET=your_blockbee_secret_here

# Fincra webhook encryption/signature verification
FINCRA_WEBHOOK_ENCRYPTION_KEY=your_fincra_encryption_key_here
```

**How to get these:**
- DynoPay: Dashboard → Settings → Webhook Secret
- BlockBee: Dashboard → API Settings → Webhook Secret
- Fincra: Dashboard → Developers → Webhook Encryption Key

**What happens if missing:**
- Production webhook validation **rejects** all incoming webhooks
- Crypto payments fail even if webhook URL is correct
- Bank payouts fail to process

---

### **3. Database Configuration (AUTO-CONFIGURED)**

```bash
# Replit automatically sets this for you
DATABASE_URL=postgresql://user:password@host:port/database
```

**Note:** Replit's built-in PostgreSQL is automatically configured. No action needed.

---

### **4. Redis Configuration (REQUIRED if using external Redis)**

```bash
# Redis connection URL
REDIS_URL=redis://your-redis-host:6379/0

# Optional: Redis authentication
REDIS_PASSWORD=your_redis_password
REDIS_USERNAME=default
```

**What uses Redis:**
- Wallet cashout flow session storage
- Rate limiting
- Temporary state management

**Fallback behavior:**
- If not set, defaults to `redis://localhost:6379/0` (will fail in production)
- Set `REDIS_FALLBACK_MODE=FAIL_CLOSED` for financial safety

---

## ⚙️ Important Production Settings

### **5. Payment Processor API Keys (REQUIRED)**

```bash
# DynoPay (Primary payment processor)
DYNOPAY_API_KEY=your_dynopay_api_key
DYNOPAY_WALLET_TOKEN=your_dynopay_wallet_token

# BlockBee (Backup payment processor)
BLOCKBEE_API_KEY=your_blockbee_api_key

# Kraken (Crypto withdrawals)
KRAKEN_API_KEY=your_kraken_api_key
KRAKEN_PRIVATE_KEY=your_kraken_private_key
```

---

### **6. Banking/Fincra Configuration (REQUIRED for NGN payouts)**

```bash
# Fincra API credentials
FINCRA_SECRET_KEY=your_fincra_secret_key
FINCRA_PUBLIC_KEY=your_fincra_public_key
FINCRA_BUSINESS_ID=your_fincra_business_id

# Production mode (set to "false" for real payments)
FINCRA_TEST_MODE=false
```

---

### **7. Email Configuration (REQUIRED)**

```bash
# Brevo (formerly SendinBlue) API
BREVO_API_KEY=your_brevo_api_key

# Brevo webhook authentication
BREVO_WEBHOOK_SECRET=your_brevo_webhook_secret

# Sender email (must be verified in Brevo)
FROM_EMAIL=hi@lockbay.io
FROM_NAME=LockBay

# Admin email for alerts
ADMIN_EMAIL=moxxcompany@gmail.com
```

---

### **8. SMS Configuration (OPTIONAL but recommended)**

```bash
# Twilio credentials (for SMS notifications)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

---

### **9. Security Secrets (REQUIRED)**

```bash
# Admin email action token secret (for secure email action buttons)
ADMIN_EMAIL_SECRET=generate_random_secret_here

# Cashout HMAC token secret (for secure cashout links)
CASHOUT_HMAC_SECRET=generate_random_secret_here
```

**Generate random secrets:**
```bash
# Use this command to generate secure secrets:
openssl rand -hex 32
```

---

### **10. Telegram Bot Configuration (REQUIRED)**

```bash
# Your Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789

# Admin user IDs (comma-separated)
ADMIN_USER_IDS=123456789,987654321
```

---

## 🔍 Optional Production Settings

### **Exchange Rate & Fees**

```bash
# FastForex API for USD/NGN rates
FASTFOREX_API_KEY=your_fastforex_api_key

# Fee configuration
ESCROW_FEE_PERCENT=2.5
MIN_ESCROW_AMOUNT_USD=10.0
MIN_ESCROW_FEE_AMOUNT=1.0
```

### **Feature Toggles**

```bash
# Enable/disable features
AUTO_COMPLETE_CRYPTO_TO_NGN=true
AUTO_COMPLETE_NGN_TO_CRYPTO=true
SMS_INVITATIONS_ENABLED=true
PAYMENT_FAILOVER_ENABLED=true
```

### **Fallback & Resilience**

```bash
# Redis fallback mode (FAIL_CLOSED recommended for production)
REDIS_FALLBACK_MODE=FAIL_CLOSED

# Payment provider selection
PRIMARY_PAYMENT_PROVIDER=dynopay
BACKUP_PAYMENT_PROVIDER=blockbee
```

---

## ✅ Pre-Deployment Verification Checklist

Before deploying to production, verify:

### **Environment Variables**
- [ ] All REQUIRED environment variables are set
- [ ] Webhook URLs point to `lockbay.replit.app` (not `lockbay.io`)
- [ ] Webhook secrets are copied from provider dashboards
- [ ] Admin email secret is generated (32+ character random string)
- [ ] Telegram bot token is from production bot (not test bot)

### **Database**
- [ ] PostgreSQL database is created and accessible
- [ ] `DATABASE_URL` environment variable is set
- [ ] Database connection is working (check startup logs)

### **External Services**
- [ ] DynoPay account is in production mode
- [ ] BlockBee account is active
- [ ] Fincra is in production mode (`FINCRA_TEST_MODE=false`)
- [ ] Brevo sender email is verified
- [ ] Telegram webhook is registered

### **Security**
- [ ] All webhook secrets are configured
- [ ] Admin email secret is set
- [ ] Redis password is set (if using external Redis)
- [ ] Production mode is enabled (`PRODUCTION_MODE=true` or auto-detected)

---

## 🚀 Post-Deployment Verification Steps

After deploying, verify everything works:

### **1. Check Startup Logs**

Look for these success indicators:
```
✅ Production environment detected
✅ Database connection successful
✅ ALL WEBHOOKS CONFIGURED:
   📱 Telegram: https://lockbay.replit.app/webhook
   💳 DynoPay: https://lockbay.replit.app
   💰 BlockBee: https://lockbay.replit.app/blockbee/callback
   🏦 Fincra: https://lockbay.replit.app/webhook/api/fincra/webhook
✅ DYNOPAY_WEBHOOK_SECRET: ✅ Configured
✅ BLOCKBEE_WEBHOOK_SECRET: ✅ Configured
✅ FINCRA_WEBHOOK_ENCRYPTION_KEY: ✅ Configured
```

**Watch for warnings:**
```
⚠️ PRODUCTION_SECURITY_RISK: DYNOPAY_WEBHOOK_SECRET not configured!
❌ CRITICAL: ADMIN_ACTION_BASE_URL must be set in production!
⚠️ Redis connection failed - using fallback mode
```

### **2. Test Bot Functionality**

- [ ] `/start` command works
- [ ] User registration/onboarding completes
- [ ] Wallet balance displays correctly
- [ ] Create escrow flow works
- [ ] Crypto payment address generates successfully

### **3. Test Webhook Delivery**

Create a test escrow and verify:
- [ ] Crypto payment webhook arrives when paid
- [ ] Payment confirmation processes correctly
- [ ] User receives payment confirmation message

**Check webhook logs:**
```
✅ DynoPay webhook received and validated
✅ Payment confirmed: $50.00 BTC
✅ Escrow ESCROW-123 funded successfully
```

### **4. Test Public Profile URLs**

- [ ] Generate public profile link: `/profile`
- [ ] Verify URL uses `lockbay.replit.app` domain
- [ ] Click link and verify profile page loads
- [ ] Check social sharing (Twitter/Facebook card preview)

### **5. Test Email Action Buttons**

Trigger an admin alert email and verify:
- [ ] Email contains action buttons
- [ ] Button URLs use `lockbay.replit.app` (not `lockbay.io`)
- [ ] Clicking button performs action correctly

### **6. Test Maintenance Mode**

```
# Enable maintenance mode
/admin_maintenance on

# Verify:
- Regular users see maintenance message
- Admins can still access bot
- Webhook processing continues

# Disable maintenance mode
/admin_maintenance off
```

---

## 🐛 Common Production Issues & Solutions

### **Issue 1: Crypto payments not confirming**

**Symptoms:**
- User pays crypto
- Payment never confirms in bot
- Escrow stays in "pending" status

**Solution:**
```bash
# Check webhook URL is correct
echo $WEBHOOK_URL
# Should output: https://lockbay.replit.app/webhook

# Check webhook secret is set
echo $DYNOPAY_WEBHOOK_SECRET
# Should output: your_secret (not empty)

# Check startup logs for webhook configuration
# Look for: ✅ ALL WEBHOOKS CONFIGURED
```

**Fix:**
Set correct environment variables:
```bash
WEBHOOK_URL=https://lockbay.replit.app/webhook
DYNOPAY_WEBHOOK_SECRET=your_secret_from_dynopay_dashboard
```

---

### **Issue 2: Public profile links broken (404)**

**Symptoms:**
- Profile link shows as `https://lockbay.io/u/username`
- Clicking link gives 404 error

**Solution:**
```bash
# Set correct admin action base URL
ADMIN_ACTION_BASE_URL=https://lockbay.replit.app
```

**Verify:**
Generate new profile link and check it uses `lockbay.replit.app` domain.

---

### **Issue 3: Maintenance mode won't activate**

**Symptoms:**
- `/admin_maintenance on` command runs
- Users can still access bot normally

**Root cause:**
Database `system_config` table is empty (production doesn't run migrations automatically).

**Solution:**
This was fixed in the codebase using UPSERT pattern. Update to latest code:
```python
# config.py now uses UPSERT instead of UPDATE
INSERT INTO system_config (...) 
ON CONFLICT (key) DO UPDATE SET value = :value
```

**Manual fix:**
```sql
-- If needed, manually insert row:
INSERT INTO system_config (key, value, description) 
VALUES ('maintenance_mode', 'true', 'Global maintenance mode');
```

---

### **Issue 4: Redis connection failures**

**Symptoms:**
```
⚠️ Redis connection failed: Connection refused
⚠️ Using fallback mode: FAIL_CLOSED
```

**Solution:**
Set correct Redis URL:
```bash
REDIS_URL=redis://your-redis-host:6379/0
REDIS_PASSWORD=your_redis_password
```

**Alternative:**
Use database-backed fallback:
```bash
REDIS_FALLBACK_MODE=DB_BACKED
```

---

### **Issue 5: Webhook signature validation failures**

**Symptoms:**
```
❌ DynoPay webhook rejected: Invalid signature
❌ Webhook validation failed
```

**Solution:**
1. Get correct secret from provider dashboard
2. Set environment variable:
```bash
DYNOPAY_WEBHOOK_SECRET=correct_secret_from_dashboard
```
3. Restart deployment
4. Test with new payment

---

## 📊 Production Monitoring

### **Key Metrics to Monitor**

1. **Webhook Success Rate**
   - Should be >99%
   - Check logs for rejected webhooks

2. **Payment Confirmation Time**
   - Should be <30 seconds after crypto payment
   - Delays indicate webhook delivery issues

3. **Database Connection Health**
   - Check for connection pool exhaustion
   - Monitor query performance

4. **Redis Availability**
   - Monitor connection failures
   - Check fallback mode activations

5. **Email Delivery Rate**
   - Monitor Brevo API success rate
   - Check for bounces/rejections

### **Log Monitoring Commands**

```bash
# Check webhook configuration on startup
grep "ALL WEBHOOKS CONFIGURED" logs

# Monitor webhook processing
grep "webhook received" logs

# Check for errors
grep "ERROR\|CRITICAL" logs

# Monitor payment confirmations
grep "Payment confirmed" logs
```

---

## 🔄 Deployment Workflow

### **Initial Production Deployment**

1. **Set all required environment variables** (see sections 1-10 above)
2. **Deploy to Replit** (click "Deploy" button)
3. **Check startup logs** for configuration warnings
4. **Run post-deployment verification** (section above)
5. **Test with small transaction** before announcing launch

### **Updating Production**

1. **Test changes in development** first
2. **Deploy to production**
3. **Monitor logs** for first 10 minutes
4. **Verify critical paths** (payment, webhooks, notifications)
5. **Rollback if issues detected** (use Replit rollback feature)

---

## 🆘 Emergency Contacts & Resources

### **If Production is Down**

1. **Check Replit deployment status**
2. **Review recent logs** for errors
3. **Verify database connectivity**
4. **Check external service status** (DynoPay, Fincra, etc.)
5. **Enable maintenance mode** if needed
6. **Contact Replit support** for infrastructure issues

### **Support Resources**

- **Replit Support:** https://replit.com/support
- **DynoPay Support:** [DynoPay dashboard]
- **Fincra Support:** [Fincra dashboard]
- **Brevo Support:** https://help.brevo.com

---

## ✨ Production Best Practices

1. **Always set environment variables via Replit Secrets** (never hardcode)
2. **Use production secrets** (not test/development secrets)
3. **Monitor logs regularly** for warnings and errors
4. **Test webhook delivery** after any URL changes
5. **Keep admin email secret secure** (rotate if compromised)
6. **Enable all security features** in production
7. **Use database-backed Redis fallback** for reliability
8. **Document any custom configuration** in this file

---

## 📝 Notes

- **Default fallback URLs** are now set to `lockbay.replit.app` (updated from `lockbay.io`)
- **Environment variables always take priority** over fallback values
- **UPSERT pattern used** for all system_config modifications (production-safe)
- **Webhook validation is enforced** in production for security
- **Redis fallback defaults to FAIL_CLOSED** in production (financial safety)

---

**Last Updated:** October 18, 2025  
**Deployment Target:** Replit Reserved VM  
**Production Domain:** `lockbay.replit.app`

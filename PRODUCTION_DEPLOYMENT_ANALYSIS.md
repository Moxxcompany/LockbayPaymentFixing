# Production Deployment Analysis
**What Happens When Environment Changes to Production on Replit Reserved VM**

## 📋 Overview

This document analyzes the complete behavior when secrets are configured for production environment and the bot is deployed to Replit's Reserved VM infrastructure.

---

## 🔍 Production Environment Detection

### Detection Priority (config.py:17-39)

The system uses a **3-tier priority system** to detect production mode:

```
Priority 1: ENVIRONMENT variable (manual override - absolute priority)
↓
Priority 2: REPLIT_ENVIRONMENT (set by Replit in deployments)
↓
Priority 3: Deployment heuristics (auto-detect)
```

### Auto-Detection Triggers

Production mode activates when **ANY** of these conditions are met:

1. **`REPLIT_DEPLOYMENT=1`** - Replit sets this during deployment
2. **`REPLIT_DOMAINS` exists** + **`REPLIT_DEV_DOMAIN` absent** - Deployed app has production domain
3. **`REPLIT_DEPLOYMENT_TYPE` exists** - Indicates deployment type
4. **`RAILWAY_PUBLIC_DOMAIN` exists** - Railway deployment fallback

### Manual Override

```bash
# Force production mode
ENVIRONMENT=production

# Force development mode
ENVIRONMENT=development
```

---

## 🔄 What Changes in Production Mode

### 1. **Telegram Bot Token** (config.py:49-59)

**Development:**
```python
BOT_TOKEN = DEVELOPMENT_BOT_TOKEN or TELEGRAM_BOT_TOKEN or BOT_TOKEN
```

**Production:**
```python
BOT_TOKEN = TELEGRAM_BOT_TOKEN or PRODUCTION_BOT_TOKEN or BOT_TOKEN
```

**Risk:** If `TELEGRAM_BOT_TOKEN` is not set in production, the bot **will fail to start**.

---

### 2. **Database Configuration** (config.py:250-263)

**Both Environments (Unified Architecture):**
```python
DATABASE_URL = os.getenv("DATABASE_URL")  # Same database for both
```

**✅ Current Setup:**
- Development: `DATABASE_URL` → Unified Neon PostgreSQL
- Production: `DATABASE_URL` → Same unified database
- Backup: `RAILWAY_BACKUP_DB_URL` → Railway PostgreSQL (disaster recovery)

**⚠️ Critical Risk:**
- Both dev and production share the **same database**
- Development mistakes can corrupt production data
- No isolation between testing and live user data

---

### 3. **Redis Fallback Security** (config.py:305-352)

**Development:**
```python
REDIS_FALLBACK_MODE = "DB_BACKED"  # Safe fallback to database
ALLOW_IN_MEMORY_FALLBACK = True    # Allows in-memory state
REDIS_REQUIRED_FOR_FINANCIAL_OPS = False  # Can proceed without Redis
```

**Production:**
```python
REDIS_FALLBACK_MODE = "FAIL_CLOSED"  # Fails if Redis unavailable
ALLOW_IN_MEMORY_FALLBACK = False     # NO in-memory fallback (prevents split-brain)
REDIS_REQUIRED_FOR_FINANCIAL_OPS = True  # REQUIRES Redis for financial ops
```

**Security Safeguards:**
```python
if IS_PRODUCTION:
    if ALLOW_IN_MEMORY_FALLBACK:
        logger.critical("🚨 CRITICAL: Auto-disabling in-memory fallback")
        Config.ALLOW_IN_MEMORY_FALLBACK = False  # Force disable
    
    if REDIS_FALLBACK_MODE == "IN_MEMORY":
        logger.critical("🚨 CRITICAL: Switching to FAIL_CLOSED")
        Config.REDIS_FALLBACK_MODE = "FAIL_CLOSED"  # Force safe mode
```

**Why This Matters:**
- Prevents **split-brain scenarios** in multi-instance deployments
- Protects against **double-spend attacks**
- Ensures financial operations are **atomic and consistent**

---

### 4. **HMAC Security Secrets** (config.py:393-431)

#### Admin Email Action Secret

**Production Requirement:**
```python
ADMIN_EMAIL_SECRET must be:
- At least 32 characters long
- Set in environment variables
- Used to sign admin action tokens
```

**If Missing in Production:**
```python
logger.critical("🚨 ADMIN_EMAIL_SECRET not set in production!")
logger.critical("🚨 Admin email action links DISABLED - tokens would be forgeable")
ADMIN_EMAIL_ACTIONS_ENABLED = False  # Feature disabled for security
```

#### Cashout HMAC Secret

**Production Requirement:**
```python
CASHOUT_HMAC_SECRET must be:
- At least 32 characters long
- Set in environment variables
- Used to sign crypto cashout confirmation tokens
```

**If Missing in Production:**
```python
logger.critical("🚨 CASHOUT_HMAC_SECRET not set in production!")
logger.critical("🚨 Crypto cashout confirmations DISABLED")
CASHOUT_HMAC_ENABLED = False  # Feature disabled for security
```

**Development Fallback:**
```python
# Development provides fallback secret
CASHOUT_HMAC_SECRET = "dev_fallback_cashout_secret_32chars_min"
```

---

### 5. **Webhook URLs** (config.py:1561-1616)

**Development:**
```python
# Uses REPLIT_DEV_DOMAIN or current REPLIT_DOMAINS
BASE_WEBHOOK_URL = f"https://{dev_domain}/webhook"
```

**Production:**
```python
# Uses production URL
BASE_WEBHOOK_URL = "https://lockbay.replit.app/webhook"
```

**All Webhook Endpoints:**
```python
TELEGRAM_WEBHOOK_URL = "https://lockbay.replit.app/webhook"
FINCRA_WEBHOOK_URL = "https://lockbay.replit.app/webhook/api/fincra/webhook"
TWILIO_WEBHOOK_URL = "https://lockbay.replit.app/webhook/twilio"
BLOCKBEE_CALLBACK_URL = "https://lockbay.replit.app/blockbee/callback"
```

**Critical:** All external services (Telegram, Fincra, BlockBee) must be reconfigured to point to production webhooks.

---

## 🔑 Critical Secrets Required for Production

### Mandatory Secrets (Bot Won't Function Without These)

1. **`TELEGRAM_BOT_TOKEN`** or **`PRODUCTION_BOT_TOKEN`**
   - Your production Telegram bot token
   - Without this: Bot fails to start

2. **`DATABASE_URL`**
   - Unified Neon PostgreSQL connection string
   - Without this: All database operations fail

3. **`RAILWAY_BACKUP_DB_URL`**
   - Disaster recovery backup database
   - Without this: Backups fail (data loss risk)

### Security Secrets (Features Disabled If Missing)

4. **`ADMIN_EMAIL_SECRET`** (32+ chars)
   - Signs admin email action tokens
   - Missing: Admin email actions disabled

5. **`CASHOUT_HMAC_SECRET`** (32+ chars)
   - Signs crypto cashout confirmation tokens
   - Missing: Cashout confirmations disabled

### Payment Processor Secrets

6. **`DYNOPAY_API_KEY`**
   - Primary cryptocurrency payment processor
   - Missing: Crypto payments fail

7. **`BLOCKBEE_API_KEY`**
   - Backup payment processor
   - Missing: Backup payment processing unavailable

8. **`BLOCKBEE_WEBHOOK_SECRET`**
   - Validates BlockBee webhooks
   - Missing: Webhook validation fails (security risk)

### Banking & Communication Secrets

9. **`FINCRA_API_KEY`**
   - Nigerian bank payouts and verification
   - Missing: NGN cashouts fail

10. **`BREVO_API_KEY`**
    - Email notifications (OTP, alerts)
    - Missing: All email notifications fail

11. **`TWILIO_ACCOUNT_SID`**, **`TWILIO_AUTH_TOKEN`**
    - SMS notifications
    - Missing: SMS fallback notifications fail

### Exchange & Rates

12. **`KRAKEN_API_KEY`**, **`KRAKEN_API_SECRET`**
    - Automated cryptocurrency withdrawals
    - Missing: Auto-cashout to crypto fails

13. **`FASTFOREX_API_KEY`**
    - Real-time exchange rates
    - Missing: Currency conversion fails

### Redis (Required for Financial Operations)

14. **`REDIS_URL`**
    - State management and coordination
    - Missing: Financial operations **fail** in production (FAIL_CLOSED mode)

---

## 🎯 Deployment Flow to Replit Reserved VM

### Step 1: Set Secrets to Production Environment

When you set secrets in Replit's Secrets tool:

```
Development Environment:
- Secrets available in Workspace
- Visible to all collaborators
- Used during development

Production Environment:
- Secrets available in Deployed App
- Passed to Reserved VM on deployment
- Not visible in Workspace during runtime
```

### Step 2: Deploy to Reserved VM

**What Replit Does:**
1. Sets `REPLIT_DEPLOYMENT=1`
2. Sets `REPLIT_ENVIRONMENT=production`
3. Provides `REPLIT_DOMAINS` with production domain
4. Passes **production secrets** as environment variables
5. Starts app using deployment configuration

**What Your App Does:**
1. Detects production mode (`IS_PRODUCTION = True`)
2. Loads production configuration
3. Validates critical secrets
4. Applies security safeguards
5. Connects to production database
6. Registers production webhooks

### Step 3: Security Validation

**Auto-Applied Safety Guards:**

```python
# 1. Redis fallback protection
if IS_PRODUCTION and ALLOW_IN_MEMORY_FALLBACK:
    Config.ALLOW_IN_MEMORY_FALLBACK = False  # Force disable
    
# 2. Fail-closed mode enforcement
if IS_PRODUCTION and REDIS_FALLBACK_MODE == "IN_MEMORY":
    Config.REDIS_FALLBACK_MODE = "FAIL_CLOSED"  # Force safe mode

# 3. HMAC secret validation
if IS_PRODUCTION and not _admin_secret_secure:
    ADMIN_EMAIL_ACTIONS_ENABLED = False  # Disable insecure feature
    
if IS_PRODUCTION and not _cashout_secret_secure:
    CASHOUT_HMAC_ENABLED = False  # Disable insecure feature
```

---

## ⚠️ What Could Go Wrong

### Critical Failures (App Won't Start)

1. **Missing `TELEGRAM_BOT_TOKEN`**
   ```
   ❌ Production environment detected but no TELEGRAM_BOT_TOKEN found!
   Result: Bot fails to initialize
   ```

2. **Missing `DATABASE_URL`**
   ```
   ❌ DATABASE_URL not configured!
   Result: All database operations fail
   ```

3. **Redis Unavailable + FAIL_CLOSED Mode**
   ```
   🚨 Redis unavailable and REDIS_FALLBACK_MODE=FAIL_CLOSED
   Result: All financial operations fail (by design - prevents data corruption)
   ```

### Security Degradations (Features Disabled)

4. **Missing `ADMIN_EMAIL_SECRET`**
   ```
   🚨 ADMIN_EMAIL_SECRET not set or too short in production!
   🚨 Admin email action links DISABLED for security
   Result: Manual admin intervention required for all actions
   ```

5. **Missing `CASHOUT_HMAC_SECRET`**
   ```
   🚨 CASHOUT_HMAC_SECRET not set or too short in production!
   🚨 Crypto cashout confirmations DISABLED for security
   Result: Cashout confirmations won't work
   ```

6. **Missing `BLOCKBEE_WEBHOOK_SECRET`**
   ```
   ⚠️ BLOCKBEE_WEBHOOK_SECRET not set
   Result: Cannot validate webhook authenticity (security risk)
   ```

### Payment Failures

7. **Missing Payment Processor Keys**
   ```
   ❌ DYNOPAY_API_KEY not configured
   Result: Crypto payments fail
   
   ❌ FINCRA_API_KEY not configured
   Result: NGN bank payouts fail
   
   ❌ KRAKEN_API_KEY not configured
   Result: Auto-cashout to crypto addresses fails
   ```

### Communication Failures

8. **Missing Communication Secrets**
   ```
   ❌ BREVO_API_KEY not configured
   Result: Email notifications (OTP, alerts) fail
   
   ❌ TWILIO credentials not configured
   Result: SMS fallback notifications fail
   ```

### Data Loss Risks

9. **Missing `RAILWAY_BACKUP_DB_URL`**
   ```
   ❌ Automated backups fail
   Result: No disaster recovery if database fails
   ```

10. **Webhook Misconfiguration**
    ```
    ⚠️ Production webhooks not updated on external services
    Result: Payments confirmed but not processed by bot
    ```

---

## ✅ Pre-Deployment Checklist

### Before Deploying to Production:

#### 1. Verify Critical Secrets

```bash
# Check all critical secrets are set
printenv | grep -E "TELEGRAM_BOT_TOKEN|DATABASE_URL|RAILWAY_BACKUP|ADMIN_EMAIL_SECRET|CASHOUT_HMAC_SECRET"
```

**Required Minimum:**
- ✅ `TELEGRAM_BOT_TOKEN` (production bot)
- ✅ `DATABASE_URL` (Neon PostgreSQL)
- ✅ `RAILWAY_BACKUP_DB_URL` (backup database)
- ✅ `ADMIN_EMAIL_SECRET` (32+ chars)
- ✅ `CASHOUT_HMAC_SECRET` (32+ chars)
- ✅ `REDIS_URL` (required for financial ops)

#### 2. Verify Payment Processors

- ✅ `DYNOPAY_API_KEY` configured
- ✅ `BLOCKBEE_API_KEY` configured
- ✅ `BLOCKBEE_WEBHOOK_SECRET` configured
- ✅ `FINCRA_API_KEY` configured
- ✅ `KRAKEN_API_KEY` + `KRAKEN_API_SECRET` configured

#### 3. Verify Communication Services

- ✅ `BREVO_API_KEY` configured (emails)
- ✅ `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` configured (SMS)

#### 4. Update External Webhooks

**Telegram:**
```
Old: https://{dev-domain}/webhook
New: https://lockbay.replit.app/webhook
```

**Fincra:**
```
New: https://lockbay.replit.app/webhook/api/fincra/webhook
```

**BlockBee:**
```
New: https://lockbay.replit.app/blockbee/callback
```

**Twilio:**
```
New: https://lockbay.replit.app/webhook/twilio
```

#### 5. Database Safety

⚠️ **Current Risk:** Both dev and production use same database

**Recommendations:**
1. Create manual backup before deployment
2. Test deployment on staging environment first
3. Monitor first 24 hours closely
4. Consider splitting dev/prod databases again

#### 6. Test Deployment Configuration

Create `.replit` configuration if not present:

```toml
[deployment]
run = ["python", "production_start.py"]
deploymentTarget = "cloudrun"

[[ports]]
localPort = 5000
externalPort = 80
```

---

## 📊 Production Monitoring

### Log Startup Messages

**Successful Production Start:**
```
🔧 Bot Environment Configuration:
   Environment: PRODUCTION
   Is Production: True
   Bot Username: @lockbaybot
   Production detected via: REPLIT_DEPLOYMENT=1
   Token Source: TELEGRAM_BOT_TOKEN
   🚀 Database: Neon PostgreSQL (Unified)

🔧 Redis Fallback Security Configuration:
   REDIS_FALLBACK_MODE: FAIL_CLOSED
   ALLOW_IN_MEMORY_FALLBACK: False
   REDIS_REQUIRED_FOR_FINANCIAL_OPS: True
   🔒 SECURITY POSTURE: Financial operations will fail if Redis is unavailable (safest)

✅ ALL WEBHOOKS CONFIGURED:
   📱 Telegram: https://lockbay.replit.app/webhook
   💳 DynoPay: https://lockbay.replit.app/webhook/dynopay
   💰 BlockBee: https://lockbay.replit.app/blockbee/callback
   🏦 Fincra: https://lockbay.replit.app/webhook/api/fincra/webhook
   📞 Twilio: https://lockbay.replit.app/webhook/twilio

✅ BACKUP_STORAGE: Unified DB → Railway Backup scheduled twice daily (6 AM & 6 PM UTC)
```

**Critical Errors to Watch:**
```
❌ Production environment detected but no TELEGRAM_BOT_TOKEN found!
🚨 CRITICAL SECURITY: ADMIN_EMAIL_SECRET not set or too short in production!
🚨 CRITICAL SECURITY: CASHOUT_HMAC_SECRET not set or too short in production!
🚨 CRITICAL SECURITY VIOLATION: ALLOW_IN_MEMORY_FALLBACK=true in production!
❌ DATABASE_URL not configured!
```

---

## 🔄 Rollback Strategy

### If Production Deployment Fails:

1. **Immediate Actions:**
   ```bash
   # Stop deployment
   # Revert to previous working version
   # Check logs for specific error
   ```

2. **Common Fixes:**
   - Missing secret → Add to Replit Secrets (production environment)
   - Webhook error → Update webhook URLs on external services
   - Database error → Verify DATABASE_URL connection string
   - Redis error → Check REDIS_URL and Railway Redis status

3. **Emergency Rollback:**
   - Replit provides automatic rollback to previous deployment
   - Use "Deployments" tab → Select previous working version → Deploy

---

## 📝 Summary

### What Happens in Production:

✅ **Security Hardening:**
- FAIL_CLOSED mode for Redis (no risky fallbacks)
- HMAC token validation enforced
- In-memory fallback disabled

✅ **Production Services:**
- Production bot token used
- Production webhook URLs registered
- Unified database accessed (same as dev)

⚠️ **Risks:**
- Shared dev/prod database (corruption risk)
- Missing secrets disable critical features
- Redis failure blocks financial operations (by design)

✅ **Backup:**
- Twice-daily automated backup to Railway (6 AM & 6 PM UTC)
- Disaster recovery available

### Key Takeaway:

**Production mode activates strict security controls** that may disable features if secrets are missing. This is **intentional** - better to fail safely than allow insecure operations with real user money.

Always test deployment in staging environment before deploying to production Reserved VM.

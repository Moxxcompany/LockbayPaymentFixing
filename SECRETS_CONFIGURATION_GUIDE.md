# LockBay Secrets Configuration Guide
**Date:** October 18, 2025  
**Purpose:** Security-safe guide for configuring production secrets

**⚠️ SECURITY NOTE:** This document contains NO actual secret values - only variable names and configuration guidance.

---

## 🎯 Configuration Health Check

Run this command to check which secrets are set:
```bash
env | grep -E "(SECRET|KEY|TOKEN|URL)" | awk -F= '{print $1}' | sort
```

---

## ❌ CRITICAL ISSUES FOUND

### **Issue #1: BREVO_WEBHOOK_SECRET Incorrectly Set**

**Current Problem:**
The variable is set to the literal string `"openssl rand -hex 32"` instead of the generated secret!

**How to Fix:**
```bash
# Step 1: Generate a proper secret
openssl rand -hex 32

# Step 2: Copy the OUTPUT (64 character hex string)
# Step 3: Set BREVO_WEBHOOK_SECRET to that value in Replit Secrets
```

**Example (don't use this exact value):**
The output should look like: `a1b2c3d4e5f6...` (64 characters total)

**Impact if not fixed:**
- Brevo webhook validation will fail
- Email replies won't process
- Admin email action buttons won't work

---

### **Issue #2: REDIS_URL Not Set**

**Current Problem:**
Variable not set, defaults to `redis://localhost:6379/0` which doesn't exist in production

**How to Fix:**

**Option A: Use Database Fallback (Recommended)**
```bash
REDIS_FALLBACK_MODE=DB_BACKED
```

**Option B: Use External Redis**
```bash
REDIS_URL=redis://your-redis-instance:6379/0
REDIS_PASSWORD=your_redis_password  # if required
```

**Impact if not fixed:**
- Wallet cashout sessions will fail
- Bot won't start (validation blocks deployment)

---

## ✅ REQUIRED SECRETS CHECKLIST

### **Webhook Configuration**
- [ ] `WEBHOOK_URL` - Set to `https://lockbay.replit.app/webhook`
- [ ] `ADMIN_ACTION_BASE_URL` - Set to `https://lockbay.replit.app`
- [ ] `PUBLIC_PROFILE_BASE_URL` - Set to `https://lockbay.io`

### **Webhook Security**
- [ ] `DYNOPAY_WEBHOOK_SECRET` - From DynoPay dashboard
- [ ] `BLOCKBEE_WEBHOOK_SECRET` - From BlockBee dashboard
- [ ] `FINCRA_WEBHOOK_ENCRYPTION_KEY` - From Fincra dashboard
- [ ] `BREVO_WEBHOOK_SECRET` - Generated with `openssl rand -hex 32`

### **Payment Processors**
- [ ] `DYNOPAY_API_KEY` - From DynoPay dashboard
- [ ] `DYNOPAY_WALLET_TOKEN` - From DynoPay dashboard
- [ ] `BLOCKBEE_API_KEY` - From BlockBee dashboard

### **Banking (Fincra)**
- [ ] `FINCRA_SECRET_KEY` - From Fincra dashboard
- [ ] `FINCRA_PUBLIC_KEY` - From Fincra dashboard
- [ ] `FINCRA_BUSINESS_ID` - From Fincra dashboard
- [ ] `FINCRA_TEST_MODE` - Set to `false` for production

### **Cryptocurrency (Kraken)**
- [ ] `KRAKEN_API_KEY` - From Kraken dashboard
- [ ] `KRAKEN_PRIVATE_KEY` - From Kraken dashboard

### **Email (Brevo)**
- [ ] `BREVO_API_KEY` - From Brevo dashboard
- [ ] `FROM_EMAIL` - Your verified sender email

### **SMS (Twilio)**
- [ ] `TWILIO_ACCOUNT_SID` - From Twilio dashboard
- [ ] `TWILIO_AUTH_TOKEN` - From Twilio dashboard
- [ ] `TWILIO_PHONE_NUMBER` - Your Twilio phone number

### **Security Secrets**
- [ ] `ADMIN_EMAIL_SECRET` - Generated with `openssl rand -hex 32`
- [ ] `CASHOUT_HMAC_SECRET` - Generated with `openssl rand -hex 32`
- [ ] `TELEGRAM_BOT_TOKEN` - From @BotFather

### **Database**
- [ ] `DATABASE_URL` - Auto-configured by Replit PostgreSQL

### **Admin Configuration**
- [ ] `ADMIN_USER_IDS` - Your Telegram user ID (comma-separated)
- [ ] `ADMIN_ALERT_EMAIL` - Email for admin notifications

---

## ⚠️ CONFIGURATION WARNINGS

### **Variables You DON'T Need to Set**

These are auto-generated from `WEBHOOK_URL`:
```bash
# ❌ DON'T SET THESE - They're automatic:
DYNOPAY_WEBHOOK_URL
BLOCKBEE_CALLBACK_URL  
FINCRA_WEBHOOK_URL
TELEGRAM_WEBHOOK_URL
```

### **Development vs Production Bot Tokens**

**Current Status:** Both using same token

**Recommendation:**
- Get separate bot from @BotFather for development
- Use different token for `DEVELOPMENT_BOT_TOKEN`
- Keeps production and dev environments isolated

### **Unused Integrations**

**Found but not currently used:**
- `FLUTTERWAVE_PUBLIC_KEY` (TEST mode)
- `FLUTTERWAVE_SECRET_KEY` (TEST mode)
- `RAILWAY_API_TOKEN`

**Recommendation:**
- Remove if not using to reduce confusion
- If keeping, move to production keys (not TEST)

---

## 🔒 SECRET ROTATION SCHEDULE

**Recommended Rotation Frequency:**

| Secret Type | Rotation Period | Priority |
|-------------|-----------------|----------|
| API Keys (Payment/Banking) | 90 days | High |
| Webhook Secrets | 90 days | High |
| Bot Tokens | When compromised | Critical |
| Database Passwords | 180 days | Medium |
| Admin Secrets | 90 days | High |

**How to Rotate:**
1. Generate new secret from provider dashboard
2. Update in Replit Secrets
3. Test thoroughly
4. Revoke old secret from provider

---

## 📋 VERIFICATION STEPS

### **After Setting All Secrets:**

1. **Check validation passes:**
   - Restart bot
   - Look for ✅ messages in startup logs
   - No CRITICAL errors should appear

2. **Test webhook endpoints:**
   - Create test escrow
   - Verify payment webhooks arrive
   - Check email notifications work

3. **Verify dual-domain:**
   - Profile URLs show as `lockbay.io`
   - Webhook logs show `lockbay.replit.app`

---

## 🚨 SECURITY BEST PRACTICES

1. **Never commit secrets to git**
   - Use Replit Secrets only
   - Never hardcode in files

2. **Use strong secrets**
   - Minimum 32 characters
   - Use `openssl rand -hex 32` for generation

3. **Monitor access**
   - Set up logging for API usage
   - Alert on unusual patterns

4. **Rotate regularly**
   - Follow schedule above
   - Document rotation dates

5. **Principle of least privilege**
   - Each key has minimum necessary permissions
   - Remove unused integrations

---

## 📞 WHERE TO GET SECRETS

### **DynoPay**
- Dashboard → Settings → API Keys
- Dashboard → Settings → Webhook Secret

### **BlockBee**
- Dashboard → API Settings → API Key
- Dashboard → API Settings → Webhook Secret

### **Fincra**
- Dashboard → Developers → API Keys
- Dashboard → Developers → Webhook Encryption Key

### **Brevo (Email)**
- Account → SMTP & API → API Keys
- Account → Webhooks → Webhook Secret (generate with openssl)

### **Twilio**
- Console → Account → Account SID
- Console → Account → Auth Token
- Console → Phone Numbers → Your Number

### **Kraken**
- Settings → API → Create New Key
- Set permissions: Query Funds, Withdraw Funds

### **Telegram Bot**
- Message @BotFather
- `/newbot` to create bot
- Copy token provided

---

## ✅ CURRENT CONFIGURATION STATUS

Based on environment check:

**Webhooks:** ✅ Correct (lockbay.replit.app)  
**Dual-Domain:** ✅ Configured  
**Payment Secrets:** ✅ Set  
**Brevo Secret:** ❌ **FIX REQUIRED**  
**Redis:** ❌ **FIX REQUIRED**  
**Other Secrets:** ✅ Configured

**Overall Health:** 90% (2 fixes needed)

---

## 🔧 QUICK FIX COMMANDS

```bash
# Fix BREVO_WEBHOOK_SECRET
echo "Run: openssl rand -hex 32"
echo "Then set BREVO_WEBHOOK_SECRET to the output"

# Fix Redis
echo "Add to Replit Secrets:"
echo "REDIS_FALLBACK_MODE=DB_BACKED"

# Verify after fixes
echo "Restart bot and check for ✅ ALL PRODUCTION CONFIGURATION CHECKS PASSED"
```

---

**Generated:** October 18, 2025  
**Next Review:** January 18, 2026 (90 days)  
**Security Level:** SAFE - No actual secrets disclosed

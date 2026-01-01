# Railway PostgreSQL Migration Guide

## Overview
This guide will help you migrate from Replit's Neon serverless PostgreSQL to Railway's dedicated PostgreSQL database to eliminate cold start penalties and improve `/start` command performance from ~1.8s to ~0.6-0.75s.

---

## Expected Performance Improvement

### Current (Neon Serverless)
- User lookup: **468ms** (cold start)
- User update: 236ms
- Invitation check: **473ms** (cold start)
- Menu: **303ms** (cold start)
- **Total: ~1,832ms**

### After Railway Migration
- User lookup: **~60ms**
- User update: 80ms
- Invitation check: **~60ms**
- Menu: **~80ms**
- **Total: ~600-750ms** (⚡ **60% faster**)

---

## Cost Analysis

### Railway Hobby Plan: $5/month
- Includes $5 usage credit
- Usage-based billing (RAM: $10/GB/month, CPU: metered)
- **Estimated actual cost for your bot:** $2-5/month
- If usage ≤ $5, effectively **FREE**

### What You're Currently Paying
- Neon serverless: $0 (but poor performance)
- Your time debugging performance: Valuable

**ROI: $5/month for 60% faster response times = Worth it**

---

## Pre-Migration Checklist

### ⚠️ **CRITICAL STEP 0: Enable Maintenance Mode**

**WHY:** Prevent data loss during migration by stopping all bot traffic BEFORE backup.

**Steps:**
1. Send `/admin_maintenance` command to your bot (admin only)
2. Click "🔴 Enable Maintenance"
3. Select duration: "⏱️ 2 hours" (gives you buffer time)
4. **Verify:** Users now see maintenance message
5. **Confirm:** No new database writes are happening

**IMPORTANT:** Do NOT proceed until maintenance mode is active!

---

### ✅ Step 1: Verify Current Database Info
```bash
# Run these commands in Replit Shell to confirm current setup
echo $DATABASE_URL
psql $DATABASE_URL -c "\dt" # List all tables
psql $DATABASE_URL -c "\d users" # Check users table schema
```

**Save this output** - you'll need it to verify migration success.

### ✅ Step 2: Create Database Backup (Bot MUST be in maintenance mode!)

#### Option A: Replit Database Pane (Recommended for beginners)
1. Open Replit Database pane
2. Click "Download backup" or "Export"
3. Save the `.sql` file locally

#### Option B: Command Line (More control)
```bash
# In Replit Shell
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup file exists
ls -lh backup_*.sql
```

**CRITICAL:** Keep this backup safe! You'll need it for:
- Migrating data to Railway
- Rollback if something goes wrong

### ✅ Step 3: Document Current Secrets
You'll need to update these after migration:
- `DATABASE_URL` (will change to Railway URL)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` (if you use these separately)

---

## Railway Setup (15 minutes)

### Step 1: Create Railway Account
1. Go to https://railway.com
2. Sign up with GitHub (recommended for $5 trial credit)
3. Verify your email

### Step 2: Create New Project
1. Click **"New Project"** in Railway dashboard
2. Select **"Provision PostgreSQL"**
3. Railway will create a database in ~30 seconds

### Step 3: Get Connection Details
1. Click on your PostgreSQL service
2. Go to **"Variables"** tab
3. Copy these values (click the eye icon to reveal):
   - `DATABASE_URL` (full connection string)
   - Or individual values:
     - `PGHOST`
     - `PGPORT` (usually 5432)
     - `PGUSER`
     - `PGPASSWORD`
     - `PGDATABASE`

**SAVE THESE SECURELY** - you'll add them to Replit secrets next.

### Step 4: Configure Railway Database Settings (Optional but Recommended)

1. In Railway PostgreSQL service, go to **"Settings"**
2. Adjust these settings:
   - **Max Connections:** 20 (good for your bot's traffic)
   - **Shared Buffers:** Default is fine for Hobby plan
   - **Log Min Duration:** 1000ms (log slow queries for monitoring)

---

## Data Migration (30 minutes)

### Step 1: Restore Backup to Railway

#### Method A: Using psql (Recommended)
```bash
# In Replit Shell

# Set Railway DATABASE_URL temporarily for this session
export RAILWAY_DB="postgresql://user:password@host:5432/database"  # Replace with your Railway URL

# Restore your backup to Railway
psql $RAILWAY_DB < backup_YYYYMMDD_HHMMSS.sql

# Verify tables were created
psql $RAILWAY_DB -c "\dt"
```

#### Method B: Using Railway CLI (Alternative)
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Restore database
railway run psql -f backup_YYYYMMDD_HHMMSS.sql
```

### Step 2: Verify Migration Success
```bash
# Compare table counts between Neon and Railway

# Neon (current)
psql $DATABASE_URL -c "SELECT 'users' as table_name, COUNT(*) FROM users 
UNION ALL SELECT 'escrows', COUNT(*) FROM escrows 
UNION ALL SELECT 'wallets', COUNT(*) FROM wallets;"

# Railway (new)
psql $RAILWAY_DB -c "SELECT 'users' as table_name, COUNT(*) FROM users 
UNION ALL SELECT 'escrows', COUNT(*) FROM escrows 
UNION ALL SELECT 'wallets', COUNT(*) FROM wallets;"
```

**Both outputs should match exactly!** If not, re-run the restore.

---

## Replit Configuration Update (10 minutes)

### Step 1: Update Replit Secrets
1. Go to Replit **Secrets** (🔒 icon in left sidebar)
2. **IMPORTANT:** Rename old `DATABASE_URL` to `DATABASE_URL_NEON_BACKUP` (for rollback)
3. Add new secret:
   - Key: `DATABASE_URL`
   - Value: Your Railway `DATABASE_URL`

### Step 2: Update Other Database Secrets (if applicable)
If you have these secrets, update them:
- `PGHOST` → Railway host
- `PGPORT` → Railway port (usually 5432)
- `PGUSER` → Railway user
- `PGPASSWORD` → Railway password
- `PGDATABASE` → Railway database name

### Step 3: No Code Changes Needed! 🎉
Your `database.py` already uses `Config.DATABASE_URL`, which reads from secrets.
No code changes are required!

---

## Testing Phase (20 minutes)

### Step 1: Restart Bot
```bash
# In Replit Shell or click the Restart button
# Bot will now connect to Railway instead of Neon
```

### Step 2: Monitor Startup Logs
Check the console for:
```
✅ Database connection successful
✅ SQLAlchemy engine created
```

If you see connection errors, verify:
- Railway DATABASE_URL is correct
- Railway database is running (check Railway dashboard)
- No firewall blocking Replit → Railway connection

### Step 3: Test Bot Functionality

#### Test 1: /start Command Performance
1. Send `/start` to your bot
2. Watch Replit logs for timing:
   - Look for `⚡ SHARED_SESSION: User lookup completed in XXXms`
   - **Expected:** <100ms (vs 400-500ms on Neon)

#### Test 2: Core Features
- ✅ User lookup works
- ✅ Escrow creation works
- ✅ Wallet balance displays correctly
- ✅ Pending invitations show up

#### Test 3: Database Writes
- ✅ Create a test escrow
- ✅ Update wallet balance
- ✅ Verify data persists after bot restart

### Step 4: Performance Validation
```bash
# Send /start command 5 times and note the response times
# Average should be 600-800ms (vs 1,800ms on Neon)
```

---

## Rollback Plan (if needed)

### ⚠️ **CRITICAL: Rollback Safety Window**

**Rollback is SAFE only if:**
- ✅ Bot is still in maintenance mode
- ✅ No users have accessed the bot after switching to Railway
- ✅ No new data has been written to Railway database

**If bot has been live on Railway:**
- ❌ **DO NOT rollback to Neon** - you'll lose new data
- ✅ Instead: Fix Railway issue forward (debug connection, restore backup again, etc.)

---

### If Something Goes Wrong (BEFORE resuming bot traffic):

1. **Immediate Rollback (2 minutes):**
   ```bash
   # In Replit Secrets:
   # 1. Rename DATABASE_URL to DATABASE_URL_RAILWAY
   # 2. Rename DATABASE_URL_NEON_BACKUP to DATABASE_URL
   # 3. Restart bot
   # 4. Keep maintenance mode enabled until ready to retry
   ```

2. **Verify Rollback Success:**
   - Bot connects to Neon again
   - All data intact (you never deleted Neon data)
   - Maintenance mode still active

3. **Debug Railway Issue:**
   - Check Railway logs
   - Verify connection string is correct
   - Ensure database is running
   - Test connection: `psql $RAILWAY_DB -c "SELECT 1;"`
   - Try migration again when ready

### If Data Was Written After Cutover:

**DO NOT rollback!** Instead:
1. Keep Railway as primary database
2. Fix the issue on Railway
3. If needed, restore backup again to Railway
4. Never switch back to Neon (data divergence risk)

---

## Connection Pooling Configuration (Important!)

### After Successful Migration, Adjust Pool Settings

Railway Hobby plan typically allows **50 concurrent connections** (vs Neon's 100).

**Update `database.py` pool configuration:**

```python
# Find this section in database.py and adjust:
engine = create_async_engine(
    Config.DATABASE_URL,
    echo=False,
    pool_size=10,           # Reduced from 20 (Neon) to 10 (Railway)
    max_overflow=15,        # Reduced from 30 to 15
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

**Why this matters:**
- Railway Hobby: ~50 max connections
- Your bot pool: 10 + 15 overflow = 25 max connections
- Leaves 25 connections for admin tools, backups, etc.

**After changing pool settings:**
1. Restart bot
2. Monitor Railway dashboard for connection counts
3. If you see connection errors, reduce pool_size further

---

## Final Step: Disable Maintenance Mode

### ✅ **After successful testing, resume bot traffic:**

1. Send `/admin_maintenance` to your bot
2. Click "🟢 Disable Maintenance"
3. **Verify:** Users can now use the bot normally
4. **Monitor:** Check Railway dashboard for connection stability

**🎉 Congratulations! Your bot is now 60% faster!**

---

## Post-Migration Cleanup (Optional)

### After 7 Days of Successful Railway Usage:

1. **Cancel Neon Database (saves resources):**
   - Keep the backup file safe
   - Delete Neon database from Replit if desired

2. **Monitor Railway Costs:**
   - Check Railway dashboard for usage
   - Expected: $2-5/month for your traffic
   - Set billing alerts if needed

3. **Optimize Railway Performance:**
   ```sql
   -- In Railway database, create indexes if not migrated
   -- (Your indexes should have migrated automatically)
   ```

---

## Monitoring & Maintenance

### Daily Checks (automated):
- Your bot's existing health checks will work unchanged
- Railway has 99.9% uptime SLA

### Weekly Checks:
1. Railway dashboard → Check database metrics
2. Watch for slow queries (>1000ms logged)
3. Review costs (should be <$5/month)

### Monthly Checks:
1. Take a fresh backup:
   ```bash
   pg_dump $DATABASE_URL > monthly_backup_$(date +%Y%m%d).sql
   ```
2. Review Railway invoice

---

## Troubleshooting

### Issue: "Connection refused" after migration
**Solution:**
- Verify Railway DATABASE_URL copied correctly (no extra spaces)
- Check Railway dashboard - database might be spinning up
- Ensure Replit can connect to external databases (should work by default)

### Issue: "SSL required" error
**Solution:**
Add `?sslmode=require` to your Railway DATABASE_URL:
```
postgresql://user:pass@host:5432/db?sslmode=require
```

### Issue: Slow queries after migration
**Solution:**
- Run `ANALYZE` command to update statistics:
  ```sql
  psql $DATABASE_URL -c "ANALYZE;"
  ```

### Issue: Migration took data but some features broken
**Solution:**
1. Check SQLAlchemy models match database schema
2. Verify foreign keys migrated correctly
3. Check Railway logs for specific errors

---

## Support Resources

### Railway Support:
- Dashboard: https://railway.com/dashboard
- Discord: https://discord.gg/railway
- Docs: https://docs.railway.com

### If You Need Help:
1. Check Railway logs (Railway dashboard → your database → Logs)
2. Check Replit console logs
3. Verify DATABASE_URL is correct
4. Test direct connection: `psql $DATABASE_URL -c "SELECT 1;"`

---

## Timeline Summary

| Phase | Time | What Happens |
|-------|------|-------------|
| **Pre-migration** | 15 min | Backup current database, verify data |
| **Railway Setup** | 15 min | Create account, provision PostgreSQL |
| **Data Migration** | 30 min | Restore backup to Railway |
| **Configuration** | 10 min | Update Replit secrets |
| **Testing** | 20 min | Verify everything works |
| **Total** | **~90 minutes** | Bot now 60% faster! |

---

## Next Steps

1. ✅ **Read this entire guide**
2. ✅ **Create Railway account** (get $5 trial credit)
3. ✅ **Backup your Neon database**
4. ✅ **Provision Railway PostgreSQL**
5. ✅ **Migrate data**
6. ✅ **Update Replit secrets**
7. ✅ **Test thoroughly**
8. ✅ **Monitor performance improvements**
9. ✅ **Celebrate 60% faster response times!** 🎉

---

## Questions Before You Start?

If you're unsure about any step:
1. Take your time reading this guide
2. Create the backup first (most important!)
3. Railway has a 7-day free trial - test before committing
4. You can always roll back to Neon

**Good luck with your migration! Your users will love the performance boost.** 🚀

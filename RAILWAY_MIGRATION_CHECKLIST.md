# Railway Migration Checklist

Use this checklist to track your progress during the migration.

## Pre-Migration ✅

- [ ] Read `RAILWAY_MIGRATION_GUIDE.md` completely
- [ ] **CRITICAL:** Enable maintenance mode via `/admin_maintenance`
  - [ ] Click "🔴 Enable Maintenance"
  - [ ] Select "⏱️ 2 hours" duration
  - [ ] Verify users see maintenance message
  - [ ] **CONFIRM: Bot is in read-only mode - NO NEW WRITES**
- [ ] Verify current database is working
  ```bash
  psql $DATABASE_URL -c "\dt"
  ```
- [ ] Create backup of Neon database (ONLY after maintenance mode enabled)
  ```bash
  pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
  ```
- [ ] Verify backup file exists and has data
  ```bash
  ls -lh backup_*.sql
  head -50 backup_*.sql  # Should show SQL commands
  ```
- [ ] Document current table counts
  ```bash
  psql $DATABASE_URL -c "SELECT 'users' as table, COUNT(*) FROM users 
  UNION ALL SELECT 'escrows', COUNT(*) FROM escrows 
  UNION ALL SELECT 'wallets', COUNT(*) FROM wallets;"
  ```

## Railway Setup ✅

- [ ] Create Railway account at https://railway.com
- [ ] Verify email and get $5 trial credit
- [ ] Create new project
- [ ] Provision PostgreSQL database
- [ ] Copy `DATABASE_URL` from Railway dashboard
- [ ] Save Railway connection details securely

## Data Migration ✅

- [ ] Set temporary RAILWAY_DB variable
  ```bash
  export RAILWAY_DB="your_railway_url_here"
  ```
- [ ] Restore backup to Railway
  ```bash
  psql $RAILWAY_DB < backup_YYYYMMDD_HHMMSS.sql
  ```
- [ ] Verify tables exist on Railway
  ```bash
  psql $RAILWAY_DB -c "\dt"
  ```
- [ ] Compare table counts (Neon vs Railway)
  ```bash
  psql $DATABASE_URL -c "SELECT 'users', COUNT(*) FROM users;"
  psql $RAILWAY_DB -c "SELECT 'users', COUNT(*) FROM users;"
  ```
- [ ] All table counts match exactly ✅

## Replit Configuration ✅

- [ ] Open Replit Secrets panel
- [ ] Rename `DATABASE_URL` → `DATABASE_URL_NEON_BACKUP`
- [ ] Add new secret: `DATABASE_URL` = Railway URL
- [ ] Verify no typos in Railway URL
- [ ] Save secrets

## Testing ✅

- [ ] Restart bot (click Restart button or run workflow)
- [ ] Check startup logs for successful connection
- [ ] Test `/start` command
- [ ] Check response time in logs (should be <100ms for lookups)
- [ ] Test escrow creation
- [ ] Test wallet balance display
- [ ] Test pending invitations
- [ ] Send `/start` 5 times and note average response time

## Performance Validation ✅

**Expected Performance:**
- Old (Neon): User lookup ~468ms, Total ~1,832ms
- New (Railway): User lookup ~60ms, Total ~600-750ms

**Actual Performance After Migration:**
- [ ] User lookup: ______ms (target: <100ms)
- [ ] Total /start time: ______ms (target: <800ms)
- [ ] **Performance improved? YES / NO**

## Connection Pooling Configuration ✅

- [ ] Update `database.py` pool settings for Railway:
  - [ ] Change `pool_size` from 20 to 10
  - [ ] Change `max_overflow` from 30 to 15
- [ ] Restart bot after pool changes
- [ ] Monitor Railway dashboard for connection counts

## Disable Maintenance Mode ✅

- [ ] **AFTER all testing passes:**
  - [ ] Send `/admin_maintenance` to bot
  - [ ] Click "🟢 Disable Maintenance"
  - [ ] Verify users can access bot normally
  - [ ] **Monitor:** Watch Railway connection stability

## Post-Migration (if successful) ✅

- [ ] Monitor bot for 24 hours
- [ ] Check Railway dashboard for usage metrics
- [ ] Verify costs are under $5/month
- [ ] Update documentation (mark migration date in replit.md)
- [ ] Keep Neon backup for 7 days
- [ ] Delete `DATABASE_URL_NEON_BACKUP` secret after 7 days (optional)

## Rollback (if needed) ⏮️

If anything goes wrong:
- [ ] Rename `DATABASE_URL` → `DATABASE_URL_RAILWAY`
- [ ] Rename `DATABASE_URL_NEON_BACKUP` → `DATABASE_URL`
- [ ] Restart bot
- [ ] Verify bot works with Neon again
- [ ] Debug Railway issue before retrying

---

## Quick Command Reference

### Backup Neon
```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore to Railway
```bash
export RAILWAY_DB="postgresql://user:pass@host:5432/db"
psql $RAILWAY_DB < backup_YYYYMMDD_HHMMSS.sql
```

### Verify Table Counts
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
psql $RAILWAY_DB -c "SELECT COUNT(*) FROM users;"
```

### Test Connection
```bash
psql $RAILWAY_DB -c "SELECT 1;"
```

---

## Emergency Contacts

- **Railway Support:** https://discord.gg/railway
- **Railway Docs:** https://docs.railway.com
- **Railway Status:** https://status.railway.com

---

**Estimated Total Time:** 90 minutes
**Expected Performance Gain:** 60% faster (1.8s → 0.6-0.75s)
**Cost:** $5/month (potentially free with usage credits)

Good luck! 🚀

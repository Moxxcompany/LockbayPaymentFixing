# Railway → Neon Disaster Recovery System

## Overview
Automated backup synchronization from Railway (production database) to Neon (disaster recovery backup).

## System Architecture

### Database Roles
- **Railway PostgreSQL**: PRIMARY production database
  - $5/month Hobby plan (50 max connections)
  - Persistent compute (no cold starts)
  - Used for all production traffic
  
- **Neon PostgreSQL**: DISASTER RECOVERY backup
  - Synced twice daily from Railway
  - Used only for disaster recovery if Railway fails
  - Maintains recent copy of production data

## Sync Schedule
- **Morning Sync**: 6:00 AM UTC
- **Evening Sync**: 6:00 PM UTC
- **Duration**: ~30-60 seconds (typical)
- **Max Duration**: 5 minutes (with timeout)

## Safety Features

### 1. Mandatory Safety Backup
- Creates backup of Neon BEFORE overwriting
- Aborts sync if safety backup fails
- Validates backup size (>10KB minimum)

### 2. Automatic Rollback
The system automatically rolls back if ANY of these occur:
- psql restore command fails
- Post-restore verification fails
- Any exception during restore process

**Rollback Process:**
1. Detects failure
2. Logs detailed error information
3. Restores Neon from safety backup
4. Preserves existing Neon data
5. **Result**: Neon is NEVER left empty

### 3. Integrity Checks
- Verifies backup file size before proceeding
- Connection verification before sync
- Data verification after sync

## Monitoring

### Success Indicators
```
✅ Railway → Neon sync completed in X.Xs
✅ Railway accessible: railway (X users)
✅ Neon accessible: neondb
✅ Safety backup created: neon_safety_backup_YYYYMMDD_HHMMSS.sql (X.XX MB)
✅ Neon database restored successfully
✅ Neon verification: X users, X escrows, X wallets
```

### Failure Indicators (with Rollback)
```
❌ psql restore failed: [error details]
🔄 ROLLING BACK: Restoring from safety backup...
✅ Rollback successful - Neon database preserved
```

### Critical Failure (requires attention)
```
❌ Failed to create safety backup - ABORTING restore for safety
❌ Rollback FAILED - Neon database may be empty!
```

## Log Locations

### Application Logs
- Check workflow logs: "Telegram Bot" workflow
- Search for: "RAILWAY → NEON SYNC"
- Scheduled job logs appear at 6 AM and 6 PM UTC

### Backup Files
- Location: `backups/railway_neon_sync/`
- Retention: Last 7 days
- Automatic cleanup of old files

## Manual Testing

### Test Connections Only
```bash
python test_railway_neon_sync.py
# Answer "no" when asked about full sync
```

### Run Full Manual Sync
```bash
python test_railway_neon_sync.py
# Answer "yes" when asked about full sync
```

### Run Via Python Module
```bash
python -m services.railway_neon_sync
```

## Expected Data Volume
- **Current Production Data** (as of October 18, 2025):
  - 13 users
  - 1 escrow
  - 13 wallets
  - 7 transactions
- **Backup Size**: ~0.5-2 MB (typical)

## Disaster Recovery Procedure

### If Railway Fails:
1. **Verify failure**: Check Railway dashboard
2. **Switch to Neon**: Update RAILWAY_DATABASE_URL to point to Neon
3. **Restart app**: Workflow will automatically use Neon
4. **Data loss**: Maximum 12 hours (between syncs)

### If Neon Sync Fails:
1. **Check logs**: Look for rollback messages
2. **If rollback succeeded**: No action needed, Neon preserved
3. **If rollback failed**: Manually restore from Railway using test script
4. **Alert**: Consider setting up monitoring alerts

## Performance Impact
- **Sync frequency**: 2x daily (minimal)
- **Resource usage**: ~5 minutes of compute every 12 hours
- **Production impact**: None (sync runs on separate connections)
- **Connection pool**: Syncs use temporary connections, don't affect production pool

## Connection Pool Configuration
- **Railway Limit**: 50 max connections
- **Production Usage**: 44 max connections (sync: 7+15, async: 7+15)
- **Sync Usage**: Temporary connections (closed after sync)
- **Safety Margin**: 6 connections buffer

## Recommendations

### Immediate (Optional)
1. **Monitoring**: Set up alerts for sync failures
2. **Testing**: Run manual sync to verify end-to-end flow
3. **Documentation**: Share this doc with team

### Future Enhancements (Optional)
1. **Alerting**: Email/SMS notifications on rollback events
2. **Metrics Dashboard**: Track sync success rates
3. **Failure Mode Testing**: Simulate failures to verify rollback
4. **Backup Verification**: Periodic integrity checks

## Files Modified
- `services/railway_neon_sync.py`: Main sync service
- `jobs/consolidated_scheduler.py`: Scheduled job integration
- `services/backup_service.py`: Config.DATABASE_URL fix
- `test_railway_neon_sync.py`: Manual testing script
- `replit.md`: Documentation updates

## Configuration
- **RAILWAY_DATABASE_URL**: Primary production database (required)
- **DATABASE_URL**: Neon backup database (required)
- Both secrets must be set for disaster recovery to work

## Support
If you encounter issues:
1. Check logs for detailed error messages
2. Run test script to verify connections
3. Check Railway and Neon dashboards
4. Review this documentation for troubleshooting steps

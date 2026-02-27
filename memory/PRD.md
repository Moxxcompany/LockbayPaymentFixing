# LockBay Telegram Escrow Bot - PRD

## Original Problem Statement
1. Analyze and set up the existing LockBay Telegram escrow bot codebase with provided environment variables
2. Update Telegram webhook URL to use current pod URL
3. Fix low balance alerts for Fincra/Kraken coming too often - should only come twice daily
4. Analyze code end-to-end for unnecessary data burning, API calls, duplicates - fix to save data on Railway

## Architecture
- **Backend**: Python FastAPI webhook server + python-telegram-bot
- **Database**: PostgreSQL (Railway + Neon)
- **Bot Platform**: Telegram Bot API (webhook mode)
- **Payment Providers**: DynoPay, BlockBee, Fincra, Kraken
- **Email**: Brevo (SendinBlue)
- **SMS**: Twilio
- **Scheduler**: APScheduler with 5 core consolidated jobs

## User Personas
- **Admin**: Monitors balances, receives alerts, manages escrow operations
- **Telegram Users**: Create escrow trades, make payments, receive cashouts

## Core Requirements
- Telegram bot running in webhook mode
- PostgreSQL database connectivity
- Multiple payment provider integrations
- Admin notification system with sane alert frequency
- Efficient resource usage for Railway deployment (data/API savings)

## What's Been Implemented

### Session 1 (2026-02-27): Environment Setup
- Created `/app/.env` with all 80+ environment variables
- Updated `WEBHOOK_URL` to current pod: `https://onboarding-flow-51.preview.emergentagent.com/api/webhook`
- Installed all missing Python dependencies
- Full bot server running with webhook registered with Telegram

### Session 2 (2026-02-27): Data Optimization & Alert Fix
**Balance Alerts (twice daily max):**
- All 4 alert cooldowns changed to 12h (WARNING, CRITICAL, EMERGENCY, OPERATIONAL)
- Added explicit env vars: `BALANCE_ALERT_COOLDOWN_*_HOURS=12`

**Scheduler Optimizations (massive API call reduction):**
- Reconciliation: 5min → 30min (saves ~250 external API calls/day)
- Workflow Runner: 90s → 5min (mostly idle, reduces log spam)
- Crypto Rate Refresh: 5min → 15min (saves ~3,500 API calls/day)
- Promo Messages: 30min → 2h (saves ~40 DB queries/day)

**Cache Optimizations:**
- Fincra balance cache: 45s → 300s (5 min)
- Kraken balance cache: 45s → 300s (5 min)
- `monitor_all_balances()` now uses cached data (not force_fresh)

**DB Query Optimizations:**
- Platform stats: `SELECT amount` (all rows) → `SELECT SUM(amount)` (single aggregate)
- Financial dashboard: Same fix for daily volume
- User weekly summary: Same fix for per-user volume

**Duplicate Elimination:**
- Removed `monitor_all_balances()` from balance report (was duplicate of reconciliation)
- Now uses DB-stored alert state for reports

**Logging Reduction:**
- Idle cycle logs changed from INFO → DEBUG (reduces log volume significantly)
- Crypto rate currencies: 18 → 6 core currencies (DOGE, BCH, BSC, Kraken symbols removed)

**Estimated Daily Savings:**
- ~4,000 fewer external API calls/day
- ~70% less log volume from idle cycles
- ~80% fewer DB queries for reporting
- Balance alerts: max 2/day instead of 24+/day

## Prioritized Backlog
- P0: ✅ Balance alert frequency fixed
- P0: ✅ Data/API optimization complete
- P1: Fincra API key authentication issue (live vs test mode)
- P1: Verify Telegram bot responds to /start commands
- P2: Test escrow creation flow end-to-end
- P2: Verify payment webhook processing
- P3: Test admin notification emails via Brevo

## Next Tasks
- Monitor Railway data usage after optimizations
- Verify bot functionality with real Telegram interactions
- Consider disabling Fincra balance checks until API key is fixed

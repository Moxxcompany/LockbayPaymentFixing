# Lockbay Telegram Escrow Bot - PRD

## Overview
Lockbay is a Telegram-based escrow bot for secure trading, supporting crypto payments (BlockBee, Kraken), fiat payments (Fincra, DynoPay, Flutterwave), and features like wallet management, cashouts, disputes, ratings, and admin controls.

## Architecture
- **Runtime**: Python FastAPI + python-telegram-bot (webhook mode)
- **Database**: PostgreSQL (Railway primary, Neon backup)
- **Entry Point**: `/app/backend/server.py` → loads `/app/webhook_server.py`
- **Bot Handlers**: `/app/handlers/`
- **Services**: `/app/services/`
- **Utils**: `/app/utils/`
- **Jobs/Scheduler**: `/app/jobs/`

## Environment Setup (Emergent Platform)
- **Pod URL**: `https://94234b1f-5c1f-473c-ae1f-23f5b03522cc.preview.emergentagent.com`
- **Webhook URL**: `https://94234b1f-5c1f-473c-ae1f-23f5b03522cc.preview.emergentagent.com/api/webhook`
- **DynoPay Webhook URL**: `https://94234b1f-5c1f-473c-ae1f-23f5b03522cc.preview.emergentagent.com/api/webhook/dynopay`
- **All env vars**: `/app/.env`

## What's Been Implemented - Feb 27, 2026

### Session 1: Initial Setup
1. Restored codebase from git (branch: Groupmessage)
2. Created `/app/.env` with all required environment variables
3. Updated WEBHOOK_URL and DYNOPAY_WEBHOOK_URL to current pod URL
4. **Bug Fix**: Event loop blocking by `DestinationCleanupMonitor` — fixed with `asyncio.to_thread()`

### Session 2: Stale Balance Bug Fix (Critical)
**Problem**: After crypto deposit, updated balance doesn't show on main menu or wallet balance menu.

**Root Cause**: Multiple layers of balance caching with NO invalidation on wallet credit operations:
1. `wallet_prefetch` in `context.user_data` — cached indefinitely with NO TTL
2. `WALLET_DISPLAY_CACHE` in `wallet_performance.py` — 10s TTL but not invalidated on credit
3. `PerformanceCache`, `ProductionCache`, `KeyboardCache` — not invalidated on credit
4. `credit_user_wallet_atomic()` in `services/crypto.py` — only invalidated caches on DEBIT, not CREDIT
5. DynoPay webhook handler — no cache invalidation after deposit credit

**Fixes Applied**:
- `utils/wallet_prefetch.py`: Added 30-second TTL to `wallet_prefetch` cache (was infinite)
- `handlers/dynopay_webhook.py`: Added `balance_cache_invalidation_service.invalidate_user_balance_caches()` after wallet deposit credit
- `handlers/dynopay_exchange_webhook.py`: Added cache invalidation after exchange credit
- `services/crypto.py`: Added cache invalidation to `credit_user_wallet_atomic()` — covers ALL credit paths (escrow release, referral rewards, etc.)
- `handlers/start.py`: Clear `wallet_prefetch` cache when returning to main menu
- `handlers/escrow.py`: Added `wallet_prefetch` invalidation in `invalidate_all_escrow_caches()` + cache invalidation on escrow refund
- `handlers/wallet_direct.py`: Added cache invalidation after cashout debit
- `handlers/admin.py`: Added cache invalidation after admin cashout completion

## Key Integrations
- Telegram Bot API (webhook mode) - Bot: @IVRinboundbot
- BlockBee, Kraken, Fincra, DynoPay, Flutterwave, Brevo, Twilio

## Known Issues
- Fincra API authentication failing — needs key check
- Redis/Replit KV Store unavailable — email queue in NO-OP mode

## Backlog
- P0: User validation of balance display fix
- P1: Fix Fincra API key
- P1: Verify payment webhook processing end-to-end
- P2: Test admin commands and notifications

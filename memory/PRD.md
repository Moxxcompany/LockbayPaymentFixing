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
- **Frontend**: React (minimal, mostly for health/status display)

## Environment Setup (Emergent Platform)
- **Pod URL**: `https://94234b1f-5c1f-473c-ae1f-23f5b03522cc.preview.emergentagent.com`
- **Backend port**: 8001, Frontend port: 3000
- **Webhook URL**: `https://94234b1f-5c1f-473c-ae1f-23f5b03522cc.preview.emergentagent.com/api/webhook`
- **DynoPay Webhook URL**: `https://94234b1f-5c1f-473c-ae1f-23f5b03522cc.preview.emergentagent.com/api/webhook/dynopay`
- **All env vars**: stored in `/app/.env` (root level, loaded with override by server.py)

## What's Been Implemented - Feb 27, 2026
1. Restored codebase from git (branch: Groupmessage)
2. Created `/app/.env` with all required environment variables
3. Updated WEBHOOK_URL and DYNOPAY_WEBHOOK_URL to current pod URL
4. Installed all Python dependencies
5. Backend started, database connected (68 tables), Telegram webhook registered
6. **Bug Fix**: Fixed event loop blocking caused by `DestinationCleanupMonitor.run_cleanup()` — was loading all 282 users synchronously, blocking the entire async event loop and making the bot unresponsive. Fixed by offloading to `asyncio.to_thread()`.

## Key Integrations
- Telegram Bot API (webhook mode) - Bot: @IVRinboundbot
- BlockBee (crypto payments)
- Kraken (crypto exchange/withdrawal)
- Fincra (fiat payments) - **AUTH FAILING** - needs key check
- DynoPay (payment processing)
- Flutterwave (payment gateway)
- Brevo (email service)
- Twilio (SMS)
- FastForex/Tatum (exchange rates)

## Known Issues
- Fincra API authentication failing (`Invalid authentication credentials`) — needs key rotation or test/live mode check
- Redis/Replit KV Store unavailable — email queue in NO-OP fallback mode (expected on Emergent platform)

## Backlog / Next Tasks
- P0: Validate full escrow creation flow end-to-end
- P1: Fix Fincra API key (auth failing)
- P1: Verify payment webhook processing (BlockBee, DynoPay, Fincra)
- P2: Test admin commands and notifications
- P2: Verify email notification delivery (Brevo)

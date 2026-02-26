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
- **Pod URL (API routing)**: `https://a33fe266-4618-471d-8a7f-4a2c5f0573fb.preview.emergentagent.com`
- **User-facing URL**: `https://onboarding-flow-51.preview.emergentagent.com`
- **Note**: API routes (`/api/*`) only work via the UUID-based URL
- **Backend port**: 8001, Frontend port: 3000
- **Webhook URL**: `https://a33fe266-4618-471d-8a7f-4a2c5f0573fb.preview.emergentagent.com/api/webhook`
- **All env vars**: stored in `/app/.env` (root level, loaded with override by server.py)

## What's Been Implemented - Feb 26, 2026
1. Created `/app/.env` with all required environment variables (Telegram, payment providers, database, etc.)
2. Updated `WEBHOOK_URL` to use current pod URL with `/api/webhook` path
3. Updated `DYNOPAY_WEBHOOK_URL` to use current pod URL
4. Installed all Python dependencies from requirements.txt
5. Backend started, database connected (68 tables), Telegram webhook registered successfully
6. Verified end-to-end: health endpoint, webhook POST, Telegram API confirmation

## Key Integrations
- Telegram Bot API (webhook mode)
- BlockBee (crypto payments)
- Kraken (crypto exchange/withdrawal)
- Fincra (fiat payments)
- DynoPay (payment processing)
- Flutterwave (payment gateway)
- Brevo (email service)
- Twilio (SMS)
- FastForex/Tatum (exchange rates)

## Backlog / Next Tasks
- P0: Validate bot responds to /start command in Telegram
- P1: Test full escrow creation flow end-to-end
- P1: Verify payment webhook processing (BlockBee, DynoPay, Fincra)
- P2: Test admin commands and notifications
- P2: Verify email notification delivery (Brevo)

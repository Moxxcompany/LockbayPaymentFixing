# LockBay - PRD & Setup Record

## Project Overview
LockBay is a Telegram-based secure escrow trading platform for peer-to-peer cryptocurrency transactions. It uses a Telegram bot as the primary interface with a FastAPI webhook server backend and PostgreSQL database.

## Architecture
- **Backend**: FastAPI (Python) running on port 8001 via uvicorn (supervisor-managed)
- **Frontend**: React status page on port 3000 (supervisor-managed)
- **Database**: PostgreSQL 15 (local, `lockbay` database with 57 tables)
- **Bot Framework**: python-telegram-bot v22.6 (webhook mode)
- **Queue System**: SQLite-based webhook queue (Redis optional)

## Tech Stack
- Python 3.11, FastAPI, SQLAlchemy (sync + async), asyncpg, psycopg2
- React 18, react-scripts
- PostgreSQL 15
- External integrations: BlockBee (crypto), DynoPay (payments), Fincra (NGN), Kraken (withdrawals), Brevo (email), Twilio (SMS)

## What's Been Implemented (Setup - Feb 14, 2026)
- Cloned repo from https://github.com/Moxxcompany/LockbayPaymentFixing
- Installed PostgreSQL 15, created `lockbay` database and user
- Installed all Python dependencies from requirements.txt
- Installed frontend dependencies via yarn
- Created root `.env` with DATABASE_URL and ENVIRONMENT=development
- Fixed frontend REACT_APP_BACKEND_URL to match platform preview URL
- All 57 database tables created successfully
- Backend running and healthy (health endpoint: `/api/health`)
- Frontend status page loading correctly
- Webhook server initialized with processors for DynoPay, Fincra, BlockBee

## Current Status
- Server: RUNNING
- Database: CONNECTED (57 tables)
- Telegram Bot: NOT ACTIVE (needs BOT_TOKEN)
- Payment processors: NOT CONFIGURED (needs API keys)
- Email (Brevo): NOT CONFIGURED (needs BREVO_API_KEY)

## Required Configuration (P0)
To fully activate the bot, add these to `/app/.env`:
1. `TELEGRAM_BOT_TOKEN` or `BOT_TOKEN` - Telegram bot token from BotFather
2. `DATABASE_URL` - Already configured (local PostgreSQL)
3. `WEBHOOK_URL` - Telegram webhook URL

## Optional Configuration (P1)
- `BREVO_API_KEY` - Email notifications
- `BLOCKBEE_API_KEY` - Crypto payment processing
- `DYNOPAY_API_KEY` + `DYNOPAY_WEBHOOK_SECRET` - DynoPay payments
- `FINCRA_SECRET_KEY` + `FINCRA_PUBLIC_KEY` - NGN payments
- `KRAKEN_API_KEY` + `KRAKEN_SECRET_KEY` - Crypto withdrawals
- `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` - SMS

## Backlog
- P0: Configure Telegram BOT_TOKEN to activate bot
- P1: Configure payment processor API keys
- P1: Set up webhook URL for production
- P2: Configure email notifications (Brevo)
- P2: Set up Redis for production state management

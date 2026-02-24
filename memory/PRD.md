# Lockbay Telegram Escrow Bot - PRD

## Original Problem Statement
User requested: "set up" - analyze code and setup the environment, update .env with all required environment variables and use current pod URL for webhooks.

## Architecture
- **App Type**: Telegram Escrow Bot (Python, FastAPI webhook server)
- **Tech Stack**: Python 3.11, FastAPI, python-telegram-bot, SQLAlchemy, PostgreSQL (Railway + Neon)
- **Payment Integrations**: DynoPay, Fincra, BlockBee, Kraken, Flutterwave
- **Email**: Brevo (Sendinblue)
- **SMS**: Twilio
- **Entry Point**: `/app/backend/server.py` -> imports `/app/webhook_server.py` and initializes the Telegram bot
- **Database**: PostgreSQL (Railway: `yamabiko.proxy.rlwy.net:44505/railway`)

## What's Been Implemented (Feb 24, 2026)
1. **Environment Setup Complete**:
   - All 80+ environment variables configured in `/app/backend/.env`
   - Webhook URLs updated to current pod URL: `https://ea5cd6ed-ea21-4b31-9411-9ec52b5c0b12.preview.emergentagent.com/api/webhook`
   - DynoPay webhook URL: `.../api/webhook/dynopay`
   - Python dependencies installed from `backend/requirements.txt`
   - Frontend dependencies installed (yarn)
2. **Services Running**:
   - Backend (FastAPI + Telegram Bot): Running
   - Frontend (React): Running
   - Telegram webhook registered and confirmed
   - All handlers registered (escrow, wallet, admin, support, rating, etc.)
   - Background schedulers running (reconciliation, cleanup, auto-release)

## Known Issues
- Fincra authentication fails: `'Invalid authentication credentials'` - may need key rotation
- Redis/Replit Key-Value Store not available - falling back to DB-backed mode
- Email queue in NO-OP/degraded mode (no Redis/Replit KV store)

## Prioritized Backlog
### P0 (Critical)
- Verify Telegram bot responds to /start commands via the bot
- Monitor webhook delivery from Telegram

### P1 (Important)  
- Investigate Fincra API key validity
- Set up proper Redis for email queue and caching

### P2 (Nice to have)
- Enable deep monitoring (ENABLE_DEEP_MONITORING=true)
- Performance tuning for background jobs blocking event loop on startup

## Next Tasks
- Test bot interaction via Telegram (@lockbaybot)
- Verify payment webhook flows end-to-end
- Check if Fincra credentials need updating

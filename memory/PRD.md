# LockBay Telegram Escrow Bot - PRD

## Original Problem Statement
Analyze and setup the existing LockBay Telegram Escrow Bot codebase on Emergent platform.

## Architecture
- **Backend**: Python/FastAPI (port 8001) - webhook server for Telegram bot with graceful fallback to minimal status server
- **Frontend**: React (port 3000) - status/monitoring dashboard
- **Database**: PostgreSQL via SQLAlchemy (requires external DATABASE_URL)
- **Cache**: Redis (optional, with SQLite/in-memory fallback)
- **Bot Framework**: python-telegram-bot v22.6 (webhook mode)
- **Scheduler**: APScheduler (AsyncIOScheduler) - 5 core jobs + promotional messages

## User Personas
- **Bot Admin**: Configures DATABASE_URL, BOT_TOKEN, manages trades via Telegram
- **Traders**: Use Telegram bot for P2P escrow trading (crypto, NGN, USD)
- **Sellers**: List trades, receive payments, manage reputation

## Core Requirements (Static)
- Telegram bot webhook server on FastAPI
- Escrow trade lifecycle (create, fund, deliver, release, dispute)
- Multi-currency support (USD, NGN, crypto)
- Payment integrations (DynoPay, BlockBee, Fincra, Kraken)
- Admin dashboard via Telegram commands
- User rating and reputation system
- Referral system
- Promotional messaging system (timezone-aware)

## What's Been Implemented

### Session - Codebase Setup (Feb 14, 2026)
- [x] Repository analyzed - massive codebase with 200+ Python files, 100+ handlers
- [x] Backend dependencies installed (pip install from requirements.txt)
- [x] Frontend dependencies installed (yarn install)
- [x] Fixed stale preview URL in frontend/.env
- [x] Both services running: backend (port 8001) + frontend (port 3000)
- [x] Backend running in minimal status mode (DATABASE_URL and BOT_TOKEN not configured)
- [x] Frontend status page loads correctly showing setup checklist
- [x] All tests passing: 100% backend, 100% frontend, 100% integration

## Current Status
- **Backend**: Running in setup/minimal mode (needs DATABASE_URL + BOT_TOKEN for full bot)
- **Frontend**: Running, showing status dashboard with setup checklist
- **Health endpoint**: /api/health returns proper JSON with status and config info

## Prioritized Backlog

### P0 - Required for Full Bot Activation
- [ ] Configure DATABASE_URL (PostgreSQL) in /app/.env
- [ ] Configure TELEGRAM_BOT_TOKEN in /app/.env
- [ ] Database tables creation (57+ tables)
- [ ] Telegram webhook registration

### P1 - Enhancements
- [ ] Configure payment processors (DynoPay, BlockBee, Fincra)
- [ ] Configure Kraken for crypto withdrawals
- [ ] Set up Redis for production state management
- [ ] Configure Brevo for email notifications

### P2 - Nice to Have
- [ ] A/B test promotional messages
- [ ] Enhanced admin dashboard
- [ ] Performance optimization

## Next Tasks
1. User provides DATABASE_URL (PostgreSQL connection string)
2. User provides TELEGRAM_BOT_TOKEN (from @BotFather)
3. Full bot activation and webhook registration
4. Configure payment integrations as needed

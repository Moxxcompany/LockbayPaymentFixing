# LockBay Telegram Escrow Bot - PRD

## Original Problem Statement
Setup the existing LockBay Telegram Escrow Bot repository code on the Emergent platform.

## Architecture
- **Backend**: Python/FastAPI (port 8001) - webhook server for Telegram bot
- **Frontend**: React (port 3000) - status/monitoring page
- **Database**: PostgreSQL via SQLAlchemy (requires external DATABASE_URL)
- **Cache**: Redis (optional, with SQLite fallback)
- **Bot Framework**: python-telegram-bot v22.6 (webhook mode)
- **Deployment**: Supervisor-managed processes on Emergent platform

## Tech Stack
- Python 3.11 + FastAPI + SQLAlchemy + asyncpg
- React 18 + react-scripts
- PostgreSQL (Neon) + Redis (optional)
- Telegram Bot API (webhook mode)

## Core Requirements (Static)
1. Telegram Escrow Bot for secure cryptocurrency trading
2. Multi-currency wallet management (8 DynoPay cryptocurrencies)
3. NGN bank transfers via Fincra
4. Automated Kraken cashouts
5. Admin dispute resolution and controls
6. Public profile pages, referral system, rating system

## What's Been Implemented (Jan 2026)
- [x] Repository code analyzed and set up on Emergent platform
- [x] Python dependencies installed (164 packages from backend/requirements.txt)
- [x] Frontend dependencies installed (React + react-scripts)
- [x] Backend server modified with graceful fallback for missing DATABASE_URL/BOT_TOKEN
- [x] Minimal status API serving /health, /status, / endpoints in setup mode
- [x] Frontend updated to dynamically reflect actual backend config status
- [x] Frontend .env corrected with proper REACT_APP_BACKEND_URL
- [x] Root .env created with basic environment config
- [x] All services running (backend, frontend, mongodb)
- [x] End-to-end testing passed (100% backend, 95% frontend)

## Prioritized Backlog

### P0 - Required for Full Bot Activation
- [ ] Configure DATABASE_URL (PostgreSQL connection string) in /app/.env
- [ ] Configure TELEGRAM_BOT_TOKEN in /app/.env
- [ ] Database tables creation (57 tables via SQLAlchemy)
- [ ] Telegram webhook registration

### P1 - External Service Integration
- [ ] DynoPay/BlockBee crypto payment webhooks
- [ ] Fincra NGN payment integration
- [ ] Kraken withdrawal service
- [ ] SendGrid/Brevo email service
- [ ] Twilio SMS service

### P2 - Optional Enhancements
- [ ] Redis cache setup for performance
- [ ] Deep monitoring (ENABLE_DEEP_MONITORING)
- [ ] Prometheus/Grafana monitoring stack
- [ ] Production deployment (Railway/Replit)

## User Personas
1. **Traders**: Buy/sell crypto via Telegram with escrow protection
2. **Admins**: Manage disputes, monitor transactions, configure system
3. **Bot Operators**: Deploy, configure, and maintain the bot

## Next Tasks
1. User provides DATABASE_URL and TELEGRAM_BOT_TOKEN
2. Full bot initialization and webhook registration
3. Verify all 57 database tables created
4. Test Telegram bot commands (/start, /menu, /wallet, etc.)

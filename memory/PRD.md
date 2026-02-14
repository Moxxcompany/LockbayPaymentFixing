# LockBay Telegram Escrow Bot - PRD

## Original Problem Statement
Setup the existing LockBay Telegram Escrow Bot repository code on the Emergent platform. Ensure group auto-detection, event broadcasting with bot username, and persuasive marketing messages.

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
6. Group auto-detection and event broadcasting

## What's Been Implemented

### Session 1 - Repo Setup (Jan 2026)
- [x] Repository code analyzed and set up on Emergent platform
- [x] Python dependencies installed (164 packages)
- [x] Frontend dependencies installed (React + react-scripts)
- [x] Backend server with graceful fallback for missing DATABASE_URL/BOT_TOKEN
- [x] Frontend updated with dynamic status checklist
- [x] All services running (backend, frontend, mongodb)

### Session 2 - Group Event System Fixes (Jan 2026)
- [x] Fixed: Group handler NOT registered in backend/server.py — added `register_group_handlers` to `_register_all_critical_handlers()`
- [x] Fixed: Bot @username missing from ALL event messages — added `_bot_tag()` and `_bot_link()` to all 6 broadcast methods
- [x] Fixed: Welcome message now includes @username, deeplink, value proposition
- [x] Rewrote all 6 event messages to be marketing-persuasive with CTAs
- [x] Verified `my_chat_member` in allowed_updates for webhook
- [x] Verified BotGroup model has required fields
- [x] Testing passed 100% (backend + integration)

## Group Event Broadcasting System
- **Auto-detection**: Bot registers groups via ChatMemberHandler.MY_CHAT_MEMBER
- **6 Events**: trade_created, trade_funded, seller_accepted, escrow_completed, rating_submitted, new_user_onboarded
- **Marketing**: All messages include @bot_username, deeplink, CTAs, social proof
- **Cleanup**: Auto-deactivates groups when bot is removed (Forbidden error)

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

### P2 - Optional Enhancements
- [ ] Redis cache for performance
- [ ] A/B test different message formats in groups
- [ ] Group-specific event filtering (admin config per group)
- [ ] Weekly group summary digest

## Next Tasks
1. User provides DATABASE_URL and TELEGRAM_BOT_TOKEN
2. Full bot initialization and webhook registration
3. Live test group auto-detection by adding bot to a test group
4. Verify all 6 event broadcasts fire correctly in groups

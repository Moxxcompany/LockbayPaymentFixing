# Lockbay - Telegram P2P Escrow Bot PRD

## Original Problem Statement
1. Analyze repo and setup/install dependencies
2. Fix: User sent $10 to bot wallet but only $8.71 was credited. Ensure same issue doesn't exist in escrow crypto payments.

## Architecture
- **Backend**: Python FastAPI (port 8001) + python-telegram-bot v22.6
- **Database**: PostgreSQL 15 (SQLAlchemy ORM, 57 tables)
- **Cache**: Redis (optional)
- **Payments**: DynoPay, BlockBee, Kraken, Fincra
- **Email**: Brevo (SendinBlue)

## What's Been Implemented

### Session 1 (Feb 2026) - Setup
- [x] Installed Python dependencies, set up PostgreSQL 15 with lockbay DB
- [x] Backend running on port 8001, health check passing

### Session 2 (Feb 2026) - Bug Fix: Rate Discrepancy
- **Root Cause**: DynoPay wallet deposit handler ignored `base_amount` (authoritative USD) field, re-converting crypto via FastForex causing ~13% loss
- [x] Fixed dynopay_webhook.py `handle_wallet_deposit_webhook` to use `base_amount`
- [x] Fixed simplified_payment_processor.py with `_extract_provider_usd_amount()` for BlockBee
- [x] Verified escrow paths (3 locations) already use `base_amount` correctly
- [x] All tests passing (100% backend, 5/5 unit tests)

## Prioritized Backlog
### P0 - Critical
- Configure BOT_TOKEN for Telegram bot
- Set up payment provider API keys (DynoPay, BlockBee, FastForex)

### P1 - Important
- Rate discrepancy monitoring/alerting
- Configure webhook URLs for production

### P2 - Nice to Have
- Web admin dashboard
- Automated financial reconciliation

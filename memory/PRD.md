# Lockbay Telegram Escrow Bot - PRD

## Original Problem Statement
1. Set up: Analyze code and setup the environment, update .env with all required environment variables and use current pod URL for webhooks.
2. Bug Fix: ETH escrow creation failing on Railway production - investigate deployment logs and fix.

## Architecture
- **App Type**: Telegram Escrow Bot (Python, FastAPI webhook server)
- **Tech Stack**: Python 3.11, FastAPI, python-telegram-bot, SQLAlchemy, PostgreSQL (Railway + Neon)
- **Payment Integrations**: DynoPay, Fincra, BlockBee, Kraken, Flutterwave
- **Email**: Brevo (Sendinblue)
- **SMS**: Twilio
- **Entry Point**: `/app/backend/server.py` -> imports `/app/webhook_server.py` and initializes the Telegram bot
- **Database**: PostgreSQL (Railway: `yamabiko.proxy.rlwy.net:44505/railway`)

## What's Been Implemented

### Feb 24, 2026 - Initial Setup
1. **Environment Setup Complete**:
   - All 80+ environment variables configured in `/app/backend/.env`
   - Webhook URLs updated to current pod URL
   - Python dependencies installed
   - Frontend dependencies installed (yarn)
   - Services running (backend + frontend)

### Feb 24, 2026 - Critical Bug Fix (ETH Escrow Payment)
2. **Root Cause Analysis**:
   - Investigated Railway deployment logs for ID `08d36808-c6b0-490b-a6c2-3e25562c0b98`
   - Found: `column escrows.refund_processed does not exist` - continuous failure every 10-15 min
   - The SQLAlchemy model includes `refund_processed` and `expiry_notified` columns but they were never migrated to the production database
   - This caused ALL escrow-related operations to fail: creation, auto-release, expiry, financial reports
   
3. **Fix Applied - Database Migration**:
   - Added `refund_processed BOOLEAN DEFAULT FALSE NOT NULL` to `escrows` table
   - Added `expiry_notified BOOLEAN DEFAULT FALSE NOT NULL` to `escrows` table
   - All 50 existing escrows updated with correct defaults
   - Also updated local SQLAlchemy model in `/app/models.py` for consistency
   - Verified: No more `UndefinedColumnError` in Railway logs post-migration

## Known Issues
- Fincra authentication fails: `'Invalid authentication credentials'` - keys may need rotation
- Brevo API: 401 Unauthorized - API key may need updating
- Railway service deployment ended - needs new deployment to pick up the DB fix
- Admin email notifications failing

## Prioritized Backlog
### P0 (Critical)
- Trigger new Railway deployment so service picks up the DB migration
- Verify escrow creation flow works end-to-end with ETH

### P1 (Important)
- Investigate/rotate Fincra API credentials
- Fix Brevo email API authentication (401 errors)

### P2 (Nice to have)
- Add database migration tooling (Alembic) to prevent future schema drift
- Set up monitoring for column schema validation on deploy

## Next Tasks
- New Railway deployment needed
- Test ETH escrow payment end-to-end
- Fix email services (Brevo 401)

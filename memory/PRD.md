# LockBay Telegram Escrow Bot - PRD

## Original Problem Statement
Set up the existing LockBay Telegram Escrow Bot repo and install needed dependencies. Fix Railway deployment issues.

## Architecture
- **Backend**: Python FastAPI (port 8001) - serves webhook server + landing page
- **Bot Framework**: python-telegram-bot v22.x
- **Database**: PostgreSQL (Railway/Neon) with SQLAlchemy ORM (57 tables)
- **Cache**: Redis (DB_BACKED fallback mode)
- **Payment Integrations**: BlockBee, DynoPay, Fincra, Kraken
- **Email**: Brevo (SendinBlue)
- **SMS**: Twilio

## What's Been Implemented (2026-02-08)
- Installed all Python dependencies locally
- Installed & configured local PostgreSQL 15 with 57 tables
- Fixed Railway deployment issues:
  1. Removed `replit>=4.1.2` from pyproject.toml (Replit-specific, fails on Railway)
  2. Created `nixpacks.toml` to explicitly use `requirements.txt` for deps
  3. Created `runtime.txt` for Python version
  4. Removed stale `.railway.json` (pointed to wrong project/service)
  5. Fixed `KRAKEN_PRIVATE_KEY` / `KRAKEN_SECRET_KEY` env var mismatch
  6. Made bot initialization resilient (server continues if token fails)
  7. Fixed duplicate index bug in PlatformRevenue model

## Railway Env Var Fix Needed
- Add `KRAKEN_SECRET_KEY` with the value of `KRAKEN_PRIVATE_KEY` in Railway dashboard

## Prioritized Backlog
### P0
- Redeploy on Railway with fixes
- Verify Telegram webhook connectivity

### P1
- Configure Redis (or keep DB_BACKED fallback)
- Test payment flows end-to-end

### P2
- Production monitoring & alerting setup

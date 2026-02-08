# LockBay Telegram Escrow Bot - PRD

## Original Problem Statement
Set up the existing LockBay Telegram Escrow Bot repo and install needed dependencies.

## Architecture
- **Backend**: Python FastAPI (port 8001) - serves webhook server + landing page
- **Bot Framework**: python-telegram-bot v22.x
- **Database**: PostgreSQL (local, port 5432) with SQLAlchemy ORM (57 tables)
- **Cache**: Redis (configured, not running locally)
- **Payment Integrations**: BlockBee, DynoPay, Fincra, Kraken
- **Email**: Brevo (SendinBlue)
- **SMS**: Twilio

## What's Been Implemented (2026-02-08)
- Installed all Python dependencies (35+ packages)
- Installed & configured local PostgreSQL 15
- Created database `lockbay` with 57 tables via SQLAlchemy models
- Created `.env` files (root, backend, frontend)
- Fixed duplicate index issue in PlatformRevenue model
- Made bot initialization resilient (server continues if Telegram token is invalid)
- Backend FastAPI server running and serving landing page

## Core Requirements
- Valid Telegram BOT_TOKEN required for full bot functionality
- DATABASE_URL for PostgreSQL (currently local dev)
- Various API keys for integrations (Kraken, Fincra, BlockBee, Brevo, etc.)

## Prioritized Backlog
### P0 - Critical
- Provide real Telegram BOT_TOKEN to enable bot functionality
- Configure production DATABASE_URL (Neon PostgreSQL)

### P1 - Important
- Configure Redis for state management
- Set up Brevo API key for email notifications
- Configure payment provider keys (BlockBee, DynoPay, Fincra, Kraken)

### P2 - Nice to Have
- Configure Twilio for SMS
- Set up webhook URL for Telegram
- Production deployment configuration

# Lockbay Telegram Escrow Bot - PRD

## Original Problem Statement
Analyze and setup the Lockbay Telegram Escrow Bot codebase. Update .env with provided environment variables and ensure the current pod URL is used for the Telegram webhook.

## Architecture
- **Backend**: FastAPI webhook server (`/app/backend/server.py`) bootstraps the Telegram bot (`/app/main.py`)
- **Database**: PostgreSQL (Railway + Neon) via SQLAlchemy
- **Bot Framework**: python-telegram-bot v22.x
- **Payment Processors**: DynoPay, BlockBee, Fincra
- **Email**: Brevo (SendinBlue)
- **Crypto**: Kraken API, Tatum API
- **Job Scheduler**: APScheduler (consolidated into 11 jobs)

## Core Requirements
- Telegram bot for P2P escrow trading
- Crypto cashouts via Kraken
- NGN bank transfers via Fincra
- Wallet management with multi-currency support
- Admin dashboard and controls
- Webhook-based payment processing

## What's Been Implemented (Feb 28, 2026)
- [x] Created `/app/.env` with all 80+ environment variables
- [x] Updated `WEBHOOK_URL` to use current pod URL: `https://onboarding-flow-51.preview.emergentagent.com/api/webhook`
- [x] Updated `DYNOPAY_WEBHOOK_URL` to: `https://onboarding-flow-51.preview.emergentagent.com/api/webhook/dynopay`
- [x] Telegram webhook registered successfully with Telegram servers
- [x] Database connected (Railway PostgreSQL)
- [x] All background jobs/scheduler running
- [x] Bot fully initialized and ready

## Key Configuration
- Pod URL: `https://onboarding-flow-51.preview.emergentagent.com`
- Telegram webhook: `/api/webhook` (strips to `/webhook` internally)
- Environment: production
- Bot username: @lockbaybot

## Backlog
- P0: Test Telegram bot functionality end-to-end
- P1: Verify payment webhook processing
- P2: Monitor scheduler jobs

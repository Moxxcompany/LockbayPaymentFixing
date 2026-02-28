# Lockbay Telegram Escrow Bot - PRD

## Original Problem Statement
Analyze and setup the Lockbay Telegram Escrow Bot codebase. Update .env with all required environment variables and ensure we use current pod URL for Telegram webhook. Investigate why recent escrow ES022826BX7V shows as expired despite manual DB update to payment_confirmed. Fix the refund error when user tries to cancel from the bot.

## Architecture
- **Backend**: Python FastAPI (webhook_server.py) running on port 8001
- **Database**: PostgreSQL (Railway + Neon)
- **Bot Framework**: python-telegram-bot
- **Payment Providers**: DynoPay, Fincra, Flutterwave, BlockBee
- **Crypto**: Kraken, Tatum
- **Email**: Brevo
- **SMS**: Twilio

## What's Been Implemented

### Session 1 (Feb 28, 2026) - Setup & Webhook Config
- Created root `/app/.env` with all 80+ environment variables
- Updated `WEBHOOK_URL` to pod URL: `https://onboarding-flow-51.preview.emergentagent.com/api/webhook`
- Updated `DYNOPAY_WEBHOOK_URL` to pod URL
- Installed all Python dependencies
- Verified Telegram webhook registered successfully via Telegram API

### Session 2 (Feb 28, 2026) - Escrow Expiry Bug Fix
**Root Cause Analysis:**
1. Escrow ES022826BX7V was created, buyer sent USDT to DynoPay address
2. DynoPay webhook callback went to OLD Railway URL (not current deployment) → payment never processed by system
3. Admin manually updated DB: `status=payment_confirmed`, `payment_confirmed_at` set
4. But `expires_at` was only 1h after payment (payment window) while `delivery_deadline` was 24h
5. Core Cleanup & Expiry job ran, found `status=payment_confirmed` + `expires_at < now` → set status to `expired`
6. Refund failed because no Transaction records existed (payment never went through normal flow)

**Fixes Applied:**
1. **`escrow_expiry_service.py`** - Split Phase 1 query: `PAYMENT_PENDING/PARTIAL_PAYMENT` check `expires_at`, `PAYMENT_CONFIRMED` checks `delivery_deadline`
2. **`refund_service.py`** - Added fallback: if `payment_confirmed_at` is set but no Transaction records exist, use `total_amount` as funding basis
3. **Database restoration** - Restored ES022826BX7V to `payment_confirmed`, created missing Transaction + EscrowHolding records, credited buyer wallet frozen_balance
4. **Verified** - Next cleanup cycle correctly found 0 escrows to expire and 2 (not 3) existing expired escrows

## Core Requirements
- Telegram Bot running in webhook mode
- PostgreSQL database connected (Railway)
- All payment webhook endpoints operational
- Background job scheduler running
- Escrow lifecycle management (create → pay → deliver → release/cancel)

## Backlog
- P0: Verify end-to-end Telegram message flow (cancel escrow from bot)
- P1: Update DynoPay callback URLs for future escrows to use current pod URL
- P1: Test payment webhooks (DynoPay, Fincra, BlockBee) end-to-end
- P2: Monitor error rates and webhook performance
- P2: Add admin dashboard health panel for escrow status monitoring

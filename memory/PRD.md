# Lockbay Telegram Escrow Bot - PRD

## Overview
Lockbay is a Telegram-based escrow bot for secure trading, supporting crypto payments (BlockBee, Kraken), fiat payments (Fincra, DynoPay, Flutterwave), and features like wallet management, cashouts, disputes, ratings, and admin controls.

## Architecture
- **Runtime**: Python FastAPI + python-telegram-bot (webhook mode)
- **Database**: PostgreSQL (Railway primary, Neon backup)
- **Entry Point**: `/app/backend/server.py` → loads `/app/webhook_server.py`
- **Bot Handlers**: `/app/handlers/`
- **Services**: `/app/services/`
- **Utils**: `/app/utils/`
- **Jobs/Scheduler**: `/app/jobs/`
- **Frontend**: React (minimal, mostly for health/status display)

## Environment Setup (Emergent Platform)
- **Pod URL (API routing)**: `https://a33fe266-4618-471d-8a7f-4a2c5f0573fb.preview.emergentagent.com`
- **User-facing URL**: `https://onboarding-flow-51.preview.emergentagent.com`
- **Note**: API routes (`/api/*`) only work via the UUID-based URL
- **Backend port**: 8001, Frontend port: 3000
- **Webhook URL**: `https://a33fe266-4618-471d-8a7f-4a2c5f0573fb.preview.emergentagent.com/api/webhook`
- **All env vars**: stored in `/app/.env` (root level, loaded with override by server.py)

## What's Been Implemented - Feb 26, 2026
1. Created `/app/.env` with all required environment variables (Telegram, payment providers, database, etc.)
2. Updated `WEBHOOK_URL` to use current pod URL with `/api/webhook` path (UUID-based URL for proper API routing)
3. Updated `DYNOPAY_WEBHOOK_URL` to use current pod URL
4. Installed all Python dependencies from requirements.txt
5. Backend started, database connected (68 tables), Telegram webhook registered successfully
6. Verified end-to-end: health endpoint, webhook POST, Telegram API confirmation

### Bug Fix - Feb 26, 2026: Wallet Deposit Crediting Only Invoice Amount (Not Actual Received)
- **Root Cause**: `dynopay_webhook.py` line 1846-1849 used DynoPay's `base_amount` (the invoice/requested amount, e.g. $10) as the wallet credit, ignoring the actual crypto received. When users overpay or DynoPay adds fees to the crypto amount, the user gets short-changed.
- **Example**: User sent 0.00685 ETH (~$13.88), DynoPay received 0.006253 ETH (~$12.67 after network fee), but wallet only credited $10.00 (the invoice base_amount).
- **Fix**: Changed wallet deposit handler to calculate USD from `actual_crypto_received × exchange_rate` instead of using `base_amount`. Uses DynoPay's webhook exchange_rate first, falls back to cached rate, with base_amount as last resort only if no crypto amount is available.
- **Result**: Same deposit would now credit ~$12.67 (actual received value) instead of $10.00
- **Root Cause**: `server.py` startup path never called `CriticalOperationsManager.setup_critical_infrastructure()` from `background_operations.py`, which is the only place that registers 53 `DIRECT_WALLET_HANDLERS` (view_rates, quick_cashout_all, quick_crypto, show_qr, bank handlers, etc.)
- **Impact**: Users could /start and see wallet menu, but clicking any wallet button (add funds, rates, cashout, etc.) resulted in silent no-op — the interceptor logged the callback but no handler matched
- **Fix**: Added DIRECT_WALLET_HANDLERS registration block in `server.py`'s `_register_all_critical_handlers()` function, handling both dict-based and direct handler formats
- **Verified**: All 53 handlers now registered, bot fully initialized

## Key Integrations
- Telegram Bot API (webhook mode)
- BlockBee (crypto payments)
- Kraken (crypto exchange/withdrawal)
- Fincra (fiat payments)
- DynoPay (payment processing)
- Flutterwave (payment gateway)
- Brevo (email service)
- Twilio (SMS)
- FastForex/Tatum (exchange rates)

## Backlog / Next Tasks
- P0: Validate bot responds to /start command in Telegram
- P1: Test full escrow creation flow end-to-end
- P1: Verify payment webhook processing (BlockBee, DynoPay, Fincra)
- P2: Test admin commands and notifications
- P2: Verify email notification delivery (Brevo)

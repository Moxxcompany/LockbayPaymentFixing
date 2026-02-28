# Lockbay Telegram Escrow Bot - PRD

## Original Problem Statement
1. Analyze and setup the Lockbay Telegram Escrow Bot codebase
2. Update .env with provided environment variables, configure Telegram webhook to pod URL
3. Investigate Railway deployment logs for missing admin email notifications on escrow ES022826BX7V
4. Fix identified bugs

## Architecture
- **Backend**: FastAPI webhook server (`/app/backend/server.py`) bootstraps Telegram bot (`/app/main.py`)
- **Database**: PostgreSQL (Railway + Neon) via SQLAlchemy
- **Bot Framework**: python-telegram-bot v22.x
- **Payment Processors**: DynoPay, BlockBee, Fincra
- **Email**: Brevo (SendinBlue)
- **Crypto**: Kraken API, Tatum API
- **Job Scheduler**: APScheduler (consolidated into 11 jobs)

## What's Been Implemented (Feb 28, 2026)

### Phase 1: Setup
- [x] Created `/app/.env` with all 80+ environment variables
- [x] Updated `WEBHOOK_URL` to pod URL: `https://onboarding-flow-51.preview.emergentagent.com/api/webhook`
- [x] Updated `DYNOPAY_WEBHOOK_URL` to pod URL
- [x] Telegram webhook registered successfully
- [x] All services running

### Phase 2: Bug Fixes from Railway Log Analysis

**Bug 1 FIXED: Missing reference_id in DynoPay webhooks**
- File: `/app/handlers/dynopay_webhook.py`
- Root cause: DynoPay doesn't echo back `meta_data.refId` or `customer_reference` in webhook payloads
- Fix: Added `_resolve_reference_id_fallback()` with multi-strategy resolution:
  1. Check `description` field
  2. Lookup by `payment_id` in `payment_addresses.provider_data`
  3. Lookup by `link_id` in `payment_addresses.provider_data`
  4. Last resort: address lookup via `payment_addresses` table
- Also fixed: `meta_data = webhook_data.get('meta_data') or {}` (was using default `{}` which doesn't handle `null` values)

**Bug 2 FIXED: NoneType crash on overpayment field**
- File: `/app/handlers/dynopay_webhook.py`, line 161
- Root cause: DynoPay sends `"overpayment": null`, `.get('overpayment', {})` returns `None` (key exists with null value)
- Fix: `dynopay_overpayment = webhook_data.get('overpayment') or {}`

**Enhancement: DynoPay payment_id/link_id storage**
- File: `/app/services/dynopay_service.py`
- Now stores `dynopay_payment_id` and `dynopay_link_id` in `provider_data` for future webhook resolution

### Known Issues (Not Code Bugs)
- **Fincra auth failure**: API key returns 401 - likely expired/mismatched credentials
- **Balance Guard blocking**: fincra_NGN, kraken_USD operations blocked due to Fincra auth failure
- **Escrow ES022826BX7V**: Still stuck at `payment_pending` - needs manual intervention or webhook replay on Railway

## Backlog
- P0: Deploy fixes to Railway production and replay the stuck DynoPay webhook for ES022826BX7V
- P0: Verify/rotate Fincra API key
- P1: Add webhook payload logging for DynoPay (store raw payload for debugging)
- P2: Add monitoring dashboard for webhook processing health

# Lockbay Telegram Escrow Bot - PRD

## Overview
Lockbay is a Telegram-based escrow bot for secure trading, supporting crypto payments (BlockBee, Kraken), fiat payments (Fincra, DynoPay, Flutterwave), and wallet management, cashouts, disputes, ratings, and admin controls.

## Architecture
- **Runtime**: Python FastAPI + python-telegram-bot (webhook mode)
- **Database**: PostgreSQL (Railway primary, Neon backup)
- **Entry Point**: `/app/backend/server.py` → loads `/app/webhook_server.py`
- **Pod URL**: `https://94234b1f-5c1f-473c-ae1f-23f5b03522cc.preview.emergentagent.com`

## What's Been Implemented - Feb 27, 2026

### Session 1: Initial Setup
- Restored codebase, created `.env`, set webhook URLs to current pod
- Fixed event loop blocking by `DestinationCleanupMonitor` (`asyncio.to_thread()`)

### Session 2: Stale Balance Bug Fix
- Root cause: 5+ caching layers with zero invalidation on wallet credits
- Fixed across 8 files: added TTL to wallet_prefetch, cache invalidation on all credit/debit paths

### Session 3: Deposit Anomaly Fixes (P1 + P2)

**P1 — Stop zombie webhook retries (permanent failure detection)**
- **Root cause**: `webhook_intake_service.py` was converting ALL handler errors to `{"status": "retry"}`, including permanent failures like "missing required fields". DynoPay sends 3 webhooks per deposit (2 status updates with incomplete payloads + 1 complete), and the 2 incomplete ones were retrying 3× each every 60-120s indefinitely.
- **Fix**: `services/webhook_intake_service.py` — Added permanent failure detection: if error message contains "missing" or "invalid", return `{"status": "error"}` (no retry) instead of `{"status": "retry"}`. Applied to both wallet and payment webhook processors.

**P2 — Round USD balance to 2 decimal places**
- **Root cause**: Crypto → USD conversion produced 18+ decimal precision (`$225.58784484274408498286`). Balance stored without rounding.
- **Fix**: 
  - `handlers/dynopay_webhook.py` — Round `usd_amount` via `.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)` before crediting. Also round `new_balance` on credit assignment.
  - `handlers/dynopay_exchange_webhook.py` — Same rounding on exchange wallet credit.
  - `services/crypto.py` — Already had proper rounding via `quantize(precision)`.

## Known Issues
- **P0 (deferred by user)**: Over-crediting ~30% on deposits (`actual_crypto × rate` > `base_amount`)
- Fincra API auth failing — needs key check
- Redis/KV Store unavailable — email queue NO-OP mode

## Backlog
- P0: Fix deposit over-crediting (use `base_amount` instead of `crypto × rate`)
- P1: Fix Fincra API key
- P1: E2E payment webhook verification
- P2: Admin commands and notification testing

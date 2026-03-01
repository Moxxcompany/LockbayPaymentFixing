# LockBay Telegram Escrow Bot - PRD

## Original Problem Statement
1. Setup LockBay Telegram bot environment with all env variables and configure webhook URL to current pod
2. Analyze database for recent disputed escrow by @technine1738 and fix fee calculation bugs

## Architecture
- **Backend**: FastAPI (Python) running on port 8001 via uvicorn/supervisor
- **Database**: PostgreSQL (Railway + Neon)
- **Bot Framework**: python-telegram-bot (webhook mode)
- **Payment Providers**: DynoPay, BlockBee, Fincra, Kraken
- **Email**: Brevo (SendinBlue)
- **SMS**: Twilio

## What's Been Implemented

### Session 1 (2026-03-01): Environment Setup
- All 80+ env variables configured in `/app/backend/.env`
- Webhook URL set to pod URL with `/api/` prefix
- `/api/` strip middleware added to `server.py` for Emergent ingress routing
- Dependencies installed, bot fully initialized

### Session 2 (2026-03-01): Fee Calculation Bug Fixes
**Database Analysis:**
- Escrow ES030126Y77S (disputed): $100, fee=$5, fee_split=buyer_pays
- Escrow ES022826BX7V (cancelled): $100, fee=$5, fee_split=buyer_pays
- Both escrows had $5 fee instead of $10 minimum

**Bug 1: Minimum fee threshold comparison (< vs <=)**
- Files: `utils/fee_calculator.py` (2 methods), `handlers/escrow.py` (2 display functions)
- `MIN_ESCROW_FEE_THRESHOLD=100` used strict `<`, so $100 escrows didn't get $10 min fee
- Fixed: Changed `escrow_decimal < threshold` to `escrow_decimal <= threshold`

**Bug 2: Split fee cancellation - buyer should pay full fee**
- Files: `utils/fee_calculator.py` (breakdown method + refundable_amount), `handlers/escrow.py` (2 cancel handlers)
- When buyer chose "split" and cancelled, they only lost their half of the fee
- Fixed: On cancellation with split, refund = escrow_amount - seller_fee_amount
- Buyer now effectively pays the full platform fee ($10 not $5)

## Core Requirements
- Telegram escrow bot for secure P2P trading
- Minimum $10 platform fee for escrows at or below $100
- On cancellation: canceller pays the full platform fee regardless of fee split option

## Backlog
- P0: Monitor fee calculation correctness on new escrows
- P1: Redis integration (currently using DB_BACKED fallback)
- P2: Retroactive correction for the two affected escrows (ES030126Y77S, ES022826BX7V)

# LockBay Telegram Escrow Bot - PRD

## Original Problem Statement
1. Setup environment and webhook for Telegram bot on Emergent pod
2. Fix fee calculation bugs (minimum fee threshold, split fee cancellation)
3. Update ES030126Y77S to $10 fee, enforce full fee on ALL cancel/dispute scenarios with warnings

## Architecture
- **Backend**: FastAPI (Python) on port 8001 via uvicorn/supervisor
- **Database**: PostgreSQL (Railway + Neon)
- **Bot Framework**: python-telegram-bot (webhook mode)
- **Payment Providers**: DynoPay, BlockBee, Fincra, Kraken

## What's Been Implemented

### Session 1 (2026-03-01): Environment Setup
- All 80+ env variables configured in `/app/backend/.env`
- Webhook URL configured for pod, `/api/` strip middleware added

### Session 2 (2026-03-01): Fee Threshold Fix
- Changed `<` to `<=` in `fee_calculator.py` so $10 min fee applies at exactly $100
- Fixed split-fee cancellation to deduct seller's portion from refund

### Session 3 (2026-03-01): Full Fee Enforcement + Warnings
**Database Update:**
- ES030126Y77S: fee_amount $5→$10, buyer_fee_amount $5→$10, total_amount $105→$110

**Fee Policy: Buyer always pays full fee on cancel/dispute (all 3 scenarios):**
- `buyer_pays`: buyer already paid fee on top → refund = escrow_amount (net loss = fee)
- `seller_pays` (NEW): full fee deducted from escrow refund → refund = escrow - total_fee
- `split` (FIXED): seller's portion deducted from escrow → refund = escrow - seller_fee

**Files changed:**
- `utils/fee_calculator.py`: refundable_amount + cancellation breakdown for seller_pays & split
- `handlers/escrow.py`: handle_cancel_escrow, handle_buyer_cancel_trade (warning), handle_buyer_cancel_confirmed (refund)
- `handlers/messages_hub.py`: handle_dispute_trade (fee warning)

**Buyer Warnings Added:**
- Dispute flow: "The full platform fee of $X will be deducted regardless of the original fee arrangement"
- Cancel confirmation: "This applies regardless of the original fee arrangement (buyer pays, seller pays, or split)"
- Fee split selection: "On cancellation or dispute, the full fee applies regardless of split option"

## Core Business Rules
1. Minimum $10 platform fee for escrows at or below $100
2. On cancellation/dispute, buyer ALWAYS pays full platform fee (all split options)
3. Seller decline (never accepted): buyer gets full refund including buyer_fee

## Backlog
- P0: Monitor new escrows for correct $10 fee + warning display
- P1: Redis integration (currently DB_BACKED fallback)
- P2: Admin dashboard for fee audit trail

# Lockbay - Telegram Escrow Bot PRD

## Original Problem Statement
1. Analyze code and set it up and install dependencies
2. Replace CoinGecko and FastForex rate providers with Tatum API

## Architecture
- **Type**: Telegram Bot (python-telegram-bot v22.6) + FastAPI webhook server
- **Database**: PostgreSQL (SQLAlchemy ORM, 57 tables)
- **Cache**: Redis (optional, fallback to in-memory)
- **Language**: Python 3.11

## What's Been Implemented

### Setup (Feb 8, 2026)
- Analyzed full codebase (~500+ files)
- Installed all Python dependencies
- Set up local PostgreSQL 15 database
- Backend running on port 8001

### Tatum API Migration (Feb 8, 2026)
- **Replaced CoinGecko + FastForex** with **Tatum API** as primary rate provider
- Tatum API key: configured in `.env` as `TATUM_API_KEY`
- Endpoint: `GET https://api.tatum.io/v4/data/rate/symbol?symbol=BTC&basePair=USD`

#### Files Modified:
- `/app/.env` — Added `TATUM_API_KEY`
- `/app/config.py` — Added `TATUM_API_KEY` config
- `/app/services/fastforex_service.py` — Full rewrite: Tatum primary, FastForex legacy fallback
- `/app/services/financial_gateway.py` — Added Tatum methods, replaced CoinGecko
- `/app/utils/exchange_rate_fallback.py` — Added Tatum as primary source
- `/app/utils/exchange_prefetch.py` — Added Tatum as primary source
- `/app/services/api_resilience_service.py` — Added Tatum health monitoring

#### Rate Priority Chain:
1. Cache (in-memory) → 2. Tatum API (primary) → 3. FastForex (legacy fallback)

#### Verified Working:
- Crypto rates: BTC, ETH, LTC, DOGE, TRX, XRP
- Kraken symbol mapping: XXBT→BTC, XETH→ETH, etc.
- Fiat rates: USD→NGN
- Markup calculations
- Batch rate fetching
- Conversions (crypto↔USD, USD↔NGN)

## Required External Credentials (Not Yet Configured)
- `BOT_TOKEN` — Telegram bot token (from @BotFather)
- `BREVO_API_KEY` — Email notifications
- `KRAKEN_API_KEY` / `KRAKEN_SECRET_KEY` — Crypto withdrawals
- `FINCRA_SECRET_KEY` / `FINCRA_PUBLIC_KEY` — NGN payments

## Backlog
- P0: Configure real Telegram BOT_TOKEN
- P1: Configure payment provider API keys
- P2: Remove deprecated FastForex/CoinGecko code entirely (currently kept as fallback)

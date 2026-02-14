# LockBay Telegram Escrow Bot - PRD

## Original Problem Statement
Setup the existing LockBay Telegram Escrow Bot repository code. Ensure group auto-detection and event broadcasting with bot username. Implement daily promotional messages to bot followers across timezones.

## Architecture
- **Backend**: Python/FastAPI (port 8001) - webhook server for Telegram bot
- **Frontend**: React (port 3000) - status/monitoring page
- **Database**: PostgreSQL via SQLAlchemy (requires external DATABASE_URL)
- **Cache**: Redis (optional, with SQLite fallback)
- **Bot Framework**: python-telegram-bot v22.6 (webhook mode)
- **Scheduler**: APScheduler (AsyncIOScheduler) - 5 core jobs + promotional messages

## What's Been Implemented

### Session 1 - Repo Setup (Jan 2026)
- [x] Repository analyzed, dependencies installed, services running
- [x] Backend with graceful fallback for missing DATABASE_URL/BOT_TOKEN

### Session 2 - Group Event System Fixes (Jan 2026)
- [x] Group handler registered in backend/server.py
- [x] All 6 event messages include @bot_username and deeplink
- [x] Messages rewritten to be marketing-persuasive

### Session 3 - Promotional Messaging System (Jan 2026)
- [x] **20 rotating messages**: 10 morning + 10 evening, all with @bot_username + deeplink + CTA
- [x] **Timezone-aware delivery**: Morning batch ~10 AM local, evening batch ~6 PM local
- [x] **Scheduler job**: Runs every 30 minutes, matches users by timezone offset
- [x] **User timezone mapping**: 50+ timezone strings mapped to UTC offsets, WAT (UTC+1) as default
- [x] **Opt-out/opt-in**: /promo_off and /promo_on commands, PromoOptOut table
- [x] **Duplicate prevention**: PromoMessageLog with unique constraint (user_id, sent_date, session_type)
- [x] **Message variety**: pick_message() avoids repeating the last sent message
- [x] **Error handling**: Forbidden (user blocked) -> mark inactive, RetryAfter -> sleep, Telegram rate limiting
- [x] **Opt-out footer**: Every message includes "Reply /promo_off to stop these messages"
- [x] **Models**: PromoMessageLog + PromoOptOut tables added to models.py
- [x] Testing: 100% pass rate on all 18 verification points

## Promotional Message Topics
Morning (motivation/opportunity): safe deals, scam prevention, reputation building, multi-currency, P2P trading, speed, seller protection, community growth
Evening (urgency/social proof): active trades, deal closing, cashout features, referrals, dispute resolution, trader profiles, 24/7 availability, buyer protection, exchange

## Prioritized Backlog

### P0 - Required for Full Bot Activation
- [ ] Configure DATABASE_URL + TELEGRAM_BOT_TOKEN in /app/.env
- [ ] Database tables creation (57+ tables)
- [ ] Telegram webhook registration
- [ ] Live test: promo messages to real users

### P1 - Enhancements
- [ ] A/B test different promo message formats
- [ ] Track click-through rate on promo deeplinks
- [ ] Personalize messages based on user activity (new vs returning)
- [ ] Weekly group digest summary

### P2 - External Services
- [ ] DynoPay/BlockBee crypto payment webhooks
- [ ] Fincra NGN payment integration
- [ ] SendGrid/Brevo email service

## Next Tasks
1. User provides DATABASE_URL and TELEGRAM_BOT_TOKEN
2. Live test promotional messages with real user base
3. Monitor opt-out rates and adjust message frequency/content

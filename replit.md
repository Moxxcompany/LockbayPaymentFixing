# Lockbay Telegram Escrow Bot

## Overview
Lockbay is a Telegram-based escrow bot designed for secure cryptocurrency and NGN cashout transactions. It aims to be a leading platform for secure digital asset transactions, offering automated fee calculation, dispute resolution, and streamlined payment processing with production-grade financial accuracy and robust state machine validation. The project's ambition is to become a top secure digital asset transaction platform.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Application
-   **Telegram Bot Framework**: `python-telegram-bot` with a webhook-only architecture.
-   **Database**: SQLAlchemy ORM (2.0 async patterns) with unified Neon PostgreSQL database (DATABASE_URL) for both development and production. Railway PostgreSQL serves as disaster recovery backup.
-   **Asynchronous Processing**: Asyncio for handlers and non-blocking database operations.
-   **Type Safety**: Comprehensive type checking with mypy.
-   **Financial Precision**: All monetary calculations use Python's Decimal type via MonetaryDecimal with `ROUND_HALF_UP` rounding and `Numeric(38, 18)` database columns.
-   **State Validation**: Entity-specific validators and a centralized `StateTransitionService` for valid state transitions.

### Financial Transaction System
-   **Escrow Engine**: State machine-driven with automated fee calculation, dispute resolution, and refund policies. Seller email auto-population for username-based onboarded sellers ensures complete escrow records.
-   **Multi-Currency Wallet**: Tracks individual balances using Decimal types with a dual-balance architecture (`available_balance` + `trading_credit`).
-   **Exchange System**: Real-time currency conversion with configurable markups and a 5-tier rate caching system.
-   **Payment Processing**: Dual processors with automatic failover, dynamic tolerance, and idempotency.
-   **Auto-Cashout System**: Automated crypto/NGN routing with Fincra integration, PostgreSQL advisory locks, batch processing, and exponential retry.

### Security and Reliability
-   **Webhook Security**: Signature, timestamp, and secret validation.
-   **Concurrency Protection**: Extended payment lock timeouts and unconditional wallet locking with PostgreSQL row-level locking.
-   **Duplicate Transaction Prevention**: Row-locked duplicate detection.
-   **Circuit Breaker Pattern**: For database connections and API fetches.
-   **Unified Rate Lock/Expiry System**: Consistent expiry validation for orders.
-   **Multi-Channel Notification Resilience**: Guaranteed delivery via Telegram → Email → SMS fallback.
-   **Simplified Admin Notifications**: Direct email sending + admin Telegram loop pattern (matching proven dispute/support notification patterns). Immediate delivery with robust per-admin error handling - no database queue complexity.
-   **Redis-Backed State Management**: For wallet cashout flow session storage.
-   **Feature Toggles**: Master switches control feature visibility via environment variables.
-   **Maintenance Mode System**: Database-backed runtime toggle.
-   **Database Timezone Safeguards**: Comprehensive defense-in-depth system to prevent timezone-aware datetime errors through SQLAlchemy event listeners and helper utilities.

### Performance Optimization
-   **Production Email Optimization**: Asynchronous background queuing.
-   **Instant Button Response**: Callback acknowledgment happens BEFORE any processing (Telegram-style architecture) to achieve <200ms response times. Rate limiting, interaction monitoring, and analytics run as non-blocking background tasks via `asyncio.create_task()`.
-   **Instant /start Response**: Command sends immediate welcome message (50-100ms) BEFORE any database queries, then displays final menu after background processing completes. Matches Telegram's official bot response times.
-   **Per-Update Caching System**: Reduces redundant database queries.
-   **Webhook Response Caching**: In-memory caching for webhook requests.
-   **Webhook Performance**: `orjson` integration for 3-5x faster JSON parsing/serialization.

### User Interface
-   **Conversation Handlers**: Multi-step flows for onboarding, escrow creation, and wallet management with persistent state.
-   **Optional Email Onboarding**: Two-tier verification system - users can skip email for instant access (no OTP) or verify email for enhanced security (OTP protection). Upgrade path available in Settings.
-   **Onboarding System**: Enhanced state tracking with database-backed session recovery.
-   **Escrow Context Rehydration**: Ensures `context.user_data` persistence.
-   **Transaction UX**: Clear descriptions, transparent fee handling, overpayment credits, and redesigned trade status displays.
-   **Dispute System**: Enhanced chat UI with visual separators, contextual trade information, and role-based icons.
-   **Referral System**: Rewards for inviting friends, personalized landing pages, dual-channel notifications.
-   **Viral Growth Engine**: Buyer-driven seller onboarding via referral invites in payment confirmations for non-onboarded sellers.
-   **Public Profile System**: Shareable reputation profiles via `/u/{profile_slug}` URLs.
-   **Command Routing**: Bot commands directly start flows instead of showing menus for instant access to features.
-   **Customer Landing Page** (Nov 2025): Conversion-optimized landing page at `/start` with official Lockbay brand (teal #3BB5C8 + dark navy #2C3E50, $ padlock logo), dual buyer/seller personas, special offers (first trade free + $5 welcome bonus via @onarrival1), social proof with conservative statistics (5,000+ traders, $1M+ volume, 4.9/5 rating, 99%+ dispute resolution), mobile-first responsive design, and professional social media marketing package with 7 official logo variations and 100+ ready-to-post content pieces.

### Background Operations
-   **Scheduler System**: APScheduler for automated tasks.
-   **Automated Database Backup**: Twice-daily automated backup from unified database (DATABASE_URL) to Railway backup (6 AM & 6 PM UTC).
-   **Webhook Processing**: Production-grade async webhook processing system with optimized dual-queue architecture:
    - **Optimized SQLite Queue** (Primary): Ultra-fast 0.85ms average enqueue with connection pooling, optimized PRAGMAs, and WAL mode.
    - **Redis Queue** (Fallback): Reliable ~94ms enqueue (cross-cloud Replit→Railway) when SQLite unavailable.
    - **Smart Fallback**: Automatic transparent failover ensures zero message loss.
-   **Background Email Queue**: Redis-backed queue for asynchronous OTP email delivery.
-   **Admin Monitoring System**: Comprehensive 17-event notification system covering escrow lifecycle, user onboarding, wallet activities, and cashout operations:
    - **Escrow Lifecycle (9 events)**: Created, Cancelled, Payment Confirmed, Seller Accepted, Item Delivered, Funds Released, Rating Submitted, Dispute Resolved, Expired
    - **User Onboarding (2 events)**: Onboarding Started, Onboarding Completed
    - **Wallet Activities (4 events)**: Trade Creation Initiated, Add Funds Clicked, Wallet Address Generated, Wallet Funded
    - **Cashout Operations (2 events)**: Cashout Started, Cashout Completed
    - Uses simple direct-send pattern: synchronous email delivery + individual admin Telegram notifications matching the proven dispute/support ticket patterns.
    - **Escrow Cancellation Fix (Nov 2025)**: All 4 cancellation flows now properly populate `cancelled_by` and `reason` fields, with comprehensive seller detection prioritizing User object → seller_contact_display → seller_contact_value → legacy fields, eliminating "Unknown Seller" and "Unknown" placeholders in admin emails.
    - **Wallet Funding Notification Fix (Nov 2025)**: Replaced fire-and-forget `asyncio.create_task()` with proper `await` in DynoPay webhook handler to ensure errors surface in logs. Enhanced `notify_wallet_funded()` to isolate email delivery from Telegram failures, guaranteeing admin emails even when bot is unavailable. Added `_format_currency()` None-value handling for graceful display of unavailable exchange rates.
-   **Comprehensive Email Notification System**: Production-ready email infrastructure with professional UX across all admin and user notifications:
    - **Centralized Formatting Helpers**: Unified currency formatting (NGN: ₦50,000.00, USD: $1,234.56, Crypto: 0.12345678 BTC with 8 decimals), timezone-aware timestamp formatting with relative time ("2 hours ago"), and consistent user identifier display.
    - **Admin Notifications (16 methods)**: Escrow lifecycle (5), exchange operations (3), user onboarding (2), wallet activities (4), cashout operations (2) - all with professional mobile-responsive design.
    - **User Notifications (4 high-priority services)**: Post-completion emails (buyer/seller completion, disputes, refunds), trade cancellations, seller invitations, rating reminders - all with actionable guidance and status badges.
    - **Professional Email Design**: Mobile-responsive layouts (max-width: 600px; width: 100%), summary boxes with key details, color-coded status badges (green/yellow/red/blue), "Recommended Action" sections, improved subject lines with urgency indicators (⭐ 💰 ❌ ✅).
    - **Cross-Channel Consistency**: Email and Telegram notifications use identical formatting for currency amounts and timestamps, ensuring users receive consistent information regardless of delivery channel.

## External Dependencies

### Payment Processors
-   **DynoPay**: Primary cryptocurrency payment processor.
-   **BlockBee**: Backup payment processor.

### Banking Services
-   **Fincra API**: Nigerian bank account verification and payout processing.
-   **FastForex API**: Real-time USD to NGN exchange rate fetching.

### Cryptocurrency Exchange
-   **Kraken API**: Automated cryptocurrency withdrawals.

### Communication Services
-   **Brevo Email**: Transactional email notifications and inbound webhook support.
-   **Twilio SMS**: SMS verification and notifications.

### Infrastructure Services
-   **Replit Reserved VM**: Production hosting platform.
-   **Neon PostgreSQL**: Unified database for both development and production (DATABASE_URL).
-   **Railway PostgreSQL**: Disaster recovery backup storage (RAILWAY_BACKUP_DB_URL).
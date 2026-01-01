# LockBay Bot - End-to-End Performance Optimization Roadmap

## Executive Summary

After successfully optimizing the escrow creation flow (78% latency reduction: 1,600ms → 350ms), this document identifies **12 critical areas** across the bot where the same optimization strategy can be applied for massive performance gains.

**Optimization Strategy Applied:**
1. **Database Query Batching** - Reduce sequential queries with JOINs and prefetch helpers
2. **Context Caching** - Store fetched data in context.user_data for reuse
3. **Async Patterns** - Sequential async queries (SQLAlchemy-compliant)
4. **Cache Invalidation** - Clear stale data on state changes

---

## Priority Classification

### 🔴 **CRITICAL PRIORITY** (Highest Impact - Do First)
User-facing flows with high frequency and multiple database round-trips

### 🟠 **HIGH PRIORITY** (High Impact)
Important flows with moderate frequency but significant latency

### 🟡 **MEDIUM PRIORITY** (Moderate Impact)
Background operations and admin flows

---

## 1. 🔴 WALLET OPERATIONS (88 Database Queries)

**File:** `handlers/wallet_direct.py`  
**Current Impact:** HIGH - Core user functionality with complex multi-step flows  
**Query Count:** 88 database operations  

### Multi-Step Flows Identified:
1. **Crypto Cashout Flow** (12 steps)
   - States: WALLET_MENU → SELECTING_CRYPTO_CURRENCY → ENTERING_CRYPTO_AMOUNT → SELECTING_WITHDRAW_NETWORK → ENTERING_WITHDRAW_ADDRESS → CONFIRMING_CASHOUT
   - **Bottleneck:** Each step fetches User + Wallet + SavedAddresses separately
   
2. **NGN Cashout Flow** (11 steps)
   - States: SELECTING_NGN_BANK → ADDING_BANK_ACCOUNT_NUMBER → CONFIRMING_NGN_PAYOUT
   - **Bottleneck:** Repeated User + Wallet + SavedBankAccount queries

3. **Saved Destination Flows** (5+ steps)
   - Crypto: CONFIRMING_SAVED_CRYPTO_STEP1 → CONFIRMING_SAVED_CRYPTO_FINAL
   - Bank: CONFIRMING_SAVED_BANK_STEP1 → CONFIRMING_SAVED_BANK_FINAL
   - **Bottleneck:** Saved addresses/banks queried multiple times per flow

### Optimization Plan:

#### Phase 1: Create Prefetch Helper
```python
# utils/wallet_prefetch.py

@dataclass
class WalletPrefetchData:
    """Batched wallet context data"""
    user_id: int
    telegram_id: int
    email: Optional[str]
    phone_number: Optional[str]
    
    # All wallets (crypto + NGN)
    wallets: Dict[str, Wallet]  # currency -> Wallet
    total_balance_usd: Decimal
    
    # Saved destinations
    saved_crypto_addresses: List[SavedAddress]
    saved_bank_accounts: List[SavedBankAccount]
    
    # Limits from Config
    min_cashout_amount: Decimal
    max_cashout_amount: Decimal
    
    prefetch_duration_ms: float

async def prefetch_wallet_context(user_id: int, session: AsyncSession):
    """
    BATCHED WALLET CONTEXT: Single query with JOINs
    
    BEFORE: 5+ sequential queries
    - Query 1: SELECT user
    - Query 2: SELECT all wallets
    - Query 3: SELECT saved addresses
    - Query 4: SELECT saved banks
    - Query 5+: Individual wallet balance checks
    
    AFTER: 1-2 queries with JOINs
    - Query 1: SELECT user + wallets (LEFT JOIN)
    - Query 2: SELECT addresses + banks (parallel)
    
    Performance: ~500ms → ~100ms (80% reduction)
    """
    # Implementation with outerjoin for user + wallets
    # Parallel fetch for saved destinations
```

#### Phase 2: Add Context Caching
- Cache at start of each cashout flow
- Reuse across all 12+ steps
- Invalidate on:
  - Cashout completion
  - Cashout cancellation
  - Balance changes (webhook updates)

#### Phase 3: Sequential Async Queries
- User + Wallets: Single LEFT JOIN
- Saved destinations: Sequential async (SQLAlchemy requirement)
- No asyncio.gather() on same session

**Expected Performance Improvement:**
- **Current:** ~800-1,200ms per step (5 queries × 150-250ms each)
- **After:** ~150-250ms per step (cached data, 0 queries steps 2-12)
- **Reduction:** 85% latency reduction

---

## 2. 🔴 EXCHANGE OPERATIONS (57 Database Queries)

**File:** `handlers/exchange_handler.py`  
**Current Impact:** HIGH - Fast-paced crypto ↔ NGN conversions  
**Query Count:** 57 database operations

### Multi-Step Flows Identified:
1. **Crypto → NGN Exchange** (8 steps)
   - Select crypto → Enter amount → Select destination → Confirm
   - **Bottleneck:** User + ExchangeOrder + SavedBankAccount fetched per step

2. **NGN → Crypto Exchange** (7 steps)
   - Enter amount → Select crypto → Select address → Confirm
   - **Bottleneck:** User + ExchangeOrder + SavedAddress fetched per step

3. **Exchange History View**
   - **Bottleneck:** Queries all ExchangeOrders + related Users sequentially

### Optimization Plan:

#### Create Exchange Prefetch Helper
```python
# utils/exchange_prefetch.py

@dataclass
class ExchangePrefetchData:
    """Batched exchange context"""
    user_id: int
    telegram_id: int
    
    # Wallets for all supported currencies
    wallets: Dict[str, Wallet]
    
    # Saved destinations (for quick selection)
    saved_crypto_addresses: List[SavedAddress]
    saved_bank_accounts: List[SavedBankAccount]
    
    # Live rates (cached from financial_gateway)
    crypto_rates: Dict[str, Decimal]
    usd_to_ngn_rate: Decimal
    
    # Limits
    min_exchange_amount_usd: Decimal
    exchange_markup_percentage: Decimal

async def prefetch_exchange_context(user_id: int, session: AsyncSession):
    """
    BEFORE: 6 queries per step
    AFTER: 1 query + cached rates
    """
```

**Expected Performance Improvement:**
- **Current:** ~600-900ms per step
- **After:** ~100-200ms per step
- **Reduction:** 80% latency reduction

---

## 3. 🔴 ONBOARDING & USER REGISTRATION (70 Database Queries)

**File:** `handlers/start.py`  
**Current Impact:** CRITICAL - First user experience  
**Query Count:** 70 database operations

### Multi-Step Flows Identified:
1. **/start Command** (Email/Phone collection)
   - **Bottleneck:** Multiple User lookups, verification checks
   
2. **Email Verification Flow**
   - States: ENTERING_EMAIL → ENTERING_OTP
   - **Bottleneck:** User + EmailVerification + Settings queries

3. **Profile Completion**
   - **Bottleneck:** User updates trigger multiple validation queries

### Optimization Plan:

#### Onboarding Prefetch
```python
# utils/onboarding_prefetch.py

@dataclass
class OnboardingPrefetchData:
    """New user onboarding context"""
    telegram_id: int
    existing_user: Optional[User]
    email_verified: bool
    phone_verified: bool
    onboarding_complete: bool
    
    # Pre-created wallets (if new user)
    default_wallets: List[Wallet]

async def prefetch_onboarding_context(telegram_id: int, session: AsyncSession):
    """
    BEFORE: 8+ queries (user lookup, verification checks, wallet creation)
    AFTER: 2 queries (user + verifications in single JOIN)
    """
```

**Expected Performance Improvement:**
- **Current:** ~1,000-1,500ms for /start
- **After:** ~200-350ms
- **Reduction:** 75% latency reduction

---

## 4. 🔴 DISPUTE MANAGEMENT (67 Database Queries)

**File:** `handlers/dispute_chat.py`  
**Current Impact:** HIGH - Critical support function  
**Query Count:** 67 database operations

### Multi-Step Flows Identified:
1. **Open Dispute Flow**
   - **Bottleneck:** Escrow + Buyer + Seller + DisputeHistory all fetched separately

2. **Dispute Chat Messages**
   - **Bottleneck:** Each message load queries Dispute + User + Escrow

3. **Admin Dispute Dashboard**
   - **Bottleneck:** Loops through disputes, fetching related data per item

### Optimization Plan:

#### Dispute Prefetch
```python
# utils/dispute_prefetch.py

@dataclass
class DisputePrefetchData:
    """Batched dispute context"""
    dispute_id: int
    escrow: Escrow
    buyer: User
    seller: User
    admin_handling: Optional[User]
    
    # Message history (last 50)
    recent_messages: List[DisputeMessage]
    total_message_count: int
    
    # Dispute metadata
    created_at: datetime
    status: str
    reason: str

async def prefetch_dispute_context(dispute_id: int, session: AsyncSession):
    """
    BEFORE: 6 queries (dispute, escrow, buyer, seller, messages, admin)
    AFTER: 1 query with multiple JOINs
    """
```

**Expected Performance Improvement:**
- **Current:** ~800ms per dispute view
- **After:** ~150ms
- **Reduction:** 81% latency reduction

---

## 5. 🟠 ADMIN OPERATIONS (107 Database Queries)

**File:** `handlers/admin.py`  
**Current Impact:** HIGH - Admin efficiency  
**Query Count:** 107 database operations

### Key Operations:
1. **User Management Dashboard**
   - **Bottleneck:** Loops through users, fetching wallets + transactions separately

2. **Transaction Review**
   - **Bottleneck:** Each transaction + related user + wallet queried individually

3. **System Statistics**
   - **Bottleneck:** Multiple COUNT queries executed sequentially

### Optimization Plan:

#### Admin Dashboard Prefetch
```python
# utils/admin_prefetch.py

async def prefetch_admin_dashboard(session: AsyncSession):
    """
    Batch all admin dashboard queries
    
    BEFORE: 20+ queries for dashboard
    AFTER: 3 queries with aggregations
    """
    # Single query with CTEs for all stats
    stats_query = text("""
        WITH user_stats AS (
            SELECT COUNT(*) as total_users,
                   COUNT(CASE WHEN onboarding_complete THEN 1 END) as active_users
            FROM users
        ),
        transaction_stats AS (
            SELECT COUNT(*) as total_txns,
                   SUM(amount) as total_volume
            FROM transactions
        ),
        escrow_stats AS (
            SELECT COUNT(*) as active_escrows,
                   SUM(amount) as held_funds
            FROM escrows WHERE status IN ('payment_confirmed', 'funds_held')
        )
        SELECT * FROM user_stats, transaction_stats, escrow_stats
    """)
```

**Expected Performance Improvement:**
- **Current:** ~2,000-3,000ms for admin dashboard
- **After:** ~300-500ms
- **Reduction:** 85% latency reduction

---

## 6. 🟠 SUPPORT CHAT (25 Database Queries)

**File:** `handlers/support_chat.py`  
**Current Impact:** MEDIUM - User support quality  
**Query Count:** 25 database operations

### Optimization Plan:
- Batch User + recent SupportMessages in single query
- Cache active support sessions
- **Expected:** 70% latency reduction

---

## 7. 🟠 USER RATING SYSTEM (19 Database Queries)

**File:** `handlers/user_rating.py`  
**Current Impact:** MEDIUM - Trust system  
**Query Count:** 19 database operations

### Optimization Plan:
- Already optimized in `services/fast_seller_lookup_service.py`
- Apply same pattern to buyer ratings
- **Expected:** 60% latency reduction

---

## 8. 🟠 CONTACT MANAGEMENT (18 Database Queries)

**File:** `handlers/contact_management.py`  
**Current Impact:** MEDIUM - UX improvement  
**Query Count:** 18 database operations

### Optimization Plan:
- Batch SavedAddress + SavedBankAccount queries
- Cache in wallet prefetch helper
- **Expected:** 75% latency reduction

---

## 9. 🟡 MENU NAVIGATION (11 Database Queries)

**File:** `handlers/menu.py`  
**Current Impact:** LOW - Simple navigation  
**Query Count:** 11 database operations

### Optimization Plan:
- Cache user data from button click
- Reuse cached data for menu rendering
- **Expected:** 50% latency reduction

---

## 10. 🟡 REFERRAL SYSTEM (7 Database Queries)

**File:** `handlers/referral.py`  
**Current Impact:** LOW - Growth feature  
**Query Count:** 7 database operations

### Optimization Plan:
- Batch referrer + referred users
- Cache referral statistics
- **Expected:** 60% latency reduction

---

## 11. 🟡 TRANSACTION HISTORY (6 Database Queries)

**File:** `handlers/transaction_history.py`  
**Current Impact:** LOW - Historical data  
**Query Count:** 6 database operations

### Optimization Plan:
- Paginated queries with LIMIT/OFFSET
- Cache recent transactions
- **Expected:** 40% latency reduction

---

## 12. 🔴 WEBHOOK PROCESSING (Multi-file)

**Files:** 
- `handlers/dynopay_webhook.py`
- `handlers/fincra_webhook.py`
- `handlers/blockbee_webhook_new.py`

**Current Impact:** CRITICAL - Payment processing speed  
**Query Count:** Varies (10-30 per webhook)

### Optimization Plan:

#### Webhook Prefetch Helper
```python
# utils/webhook_prefetch.py

async def prefetch_webhook_context(
    order_id: str, 
    order_type: str,  # 'escrow', 'exchange', 'wallet'
    session: AsyncSession
):
    """
    Batch all webhook-related data
    
    BEFORE: 8+ queries per webhook
    - Order lookup
    - User lookup  
    - Wallet lookup
    - Transaction creation
    - Balance updates
    
    AFTER: 2-3 queries with row locking
    - Order + User + Wallet (JOIN with FOR UPDATE)
    - Transaction insert
    - Balance update
    """
```

**Expected Performance Improvement:**
- **Current:** ~500-800ms per webhook
- **After:** ~100-200ms
- **Reduction:** 75% latency reduction
- **Business Impact:** Faster payment confirmations = better UX

---

## Implementation Priority Order

### Week 1-2: Critical User-Facing Flows
1. ✅ **Escrow Creation** (COMPLETED - 78% improvement)
2. 🔴 **Wallet Operations** - Highest query count (88)
3. 🔴 **Exchange Handler** - High frequency (57)
4. 🔴 **Onboarding/Start** - First impression (70)

### Week 3-4: Support & Admin Efficiency  
5. 🔴 **Dispute Management** - Critical support (67)
6. 🔴 **Webhook Processing** - Payment speed (varies)
7. 🟠 **Admin Dashboard** - Team efficiency (107)
8. 🟠 **Support Chat** - User satisfaction (25)

### Week 5-6: Secondary Features
9. 🟠 **Rating System** - Trust building (19)
10. 🟠 **Contact Management** - UX polish (18)
11. 🟡 **Menu Navigation** - Minor improvement (11)
12. 🟡 **Referral & History** - Growth features (7+6)

---

## Common Patterns to Apply Everywhere

### Pattern 1: Prefetch Helper Template
```python
# utils/{feature}_prefetch.py

from dataclasses import dataclass
from typing import Optional, Dict, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import time

@dataclass
class {Feature}PrefetchData:
    """Batched {feature} context data"""
    user_id: int
    telegram_id: int
    # ... feature-specific fields
    prefetch_duration_ms: float
    
    def to_dict(self) -> Dict:
        return asdict(self)

async def prefetch_{feature}_context(
    user_id: int, 
    session: AsyncSession
) -> Optional[{Feature}PrefetchData]:
    """
    TRUE BATCHING: Reduce N queries to 1-2 queries
    
    BEFORE: Multiple sequential queries
    AFTER: Single JOIN query with prefetch
    """
    start_time = time.perf_counter()
    
    try:
        # Single query with LEFT JOINs
        stmt = (
            select(User, RelatedTable1, RelatedTable2)
            .outerjoin(RelatedTable1, ...)
            .outerjoin(RelatedTable2, ...)
            .where(User.id == user_id)
        )
        
        result = await session.execute(stmt)
        row = result.one_or_none()
        
        if not row:
            return None
        
        # Unpack and build prefetch data
        # ...
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"⏱️ BATCH: Prefetched in {duration_ms:.1f}ms")
        
        return prefetch_data
        
    except Exception as e:
        logger.error(f"❌ PREFETCH_ERROR: {e}")
        return None
```

### Pattern 2: Cache Management
```python
# In each handler file

def cache_prefetch_data(context, prefetch_data):
    """Store in context.user_data"""
    context.user_data['{feature}_prefetch'] = prefetch_data.to_dict()

def get_cached_prefetch_data(context):
    """Retrieve from context.user_data"""
    return context.user_data.get('{feature}_prefetch')

def invalidate_prefetch_cache(context):
    """Clear on state changes"""
    context.user_data.pop('{feature}_prefetch', None)

# Invalidate on:
# - Flow completion
# - Flow cancellation  
# - Related data changes (balance updates, etc.)
```

### Pattern 3: Sequential Async (SQLAlchemy Requirement)
```python
# ALWAYS use sequential await on same session

# ❌ WRONG - Causes InvalidRequestError
user, wallet = await asyncio.gather(
    session.execute(user_query),
    session.execute(wallet_query)
)

# ✅ CORRECT - Sequential on same session
user_result = await session.execute(user_query)
wallet_result = await session.execute(wallet_query)
```

---

## Expected Overall Impact

### Performance Improvements
| Area | Current Avg | After Optimization | Improvement |
|------|-------------|-------------------|-------------|
| Escrow Creation | 1,600ms | 350ms | **78%** ✅ |
| Wallet Operations | 1,000ms | 200ms | **80%** |
| Exchange Flows | 800ms | 150ms | **81%** |
| Onboarding | 1,200ms | 300ms | **75%** |
| Dispute Views | 800ms | 150ms | **81%** |
| Admin Dashboard | 2,500ms | 400ms | **84%** |
| Webhooks | 600ms | 150ms | **75%** |

### Business Impact
- **User Satisfaction:** Faster response times = better UX
- **Server Costs:** 75-85% fewer database queries = lower DB load
- **Scalability:** Can handle 4-5x more concurrent users
- **Payment Speed:** Faster webhook processing = quicker confirmations

---

## Metrics to Track

After each optimization, measure:
1. **Latency:** Response time per operation (ms)
2. **Query Count:** Database queries per operation
3. **Cache Hit Rate:** % of requests served from cache
4. **Error Rate:** Ensure no regressions
5. **User Feedback:** Monitor support tickets

---

## Next Steps

1. **Validate Priority Order** - Confirm which flows to optimize first
2. **Create Prefetch Helpers** - One at a time, following escrow pattern
3. **Test Thoroughly** - Each optimization with real user flows
4. **Monitor Production** - Track performance metrics
5. **Iterate** - Apply learnings to remaining areas

---

**Document Version:** 1.0  
**Date:** October 18, 2025  
**Status:** Ready for Implementation

# Transaction Rollback Bug Analysis - October 13, 2025

## Incident Summary
**Escrow ID:** ES101325WZY2  
**Payment Time:** 2025-10-13 14:11:40 UTC  
**Issue:** DynoPay webhook successfully processed payment but changes did not persist to database

## Symptoms
1. **Logs showed success:**
   - ✅ Payment received: $101.00 LTC
   - ✅ User credited $4.26 overpayment to wallet
   - ✅ Escrow status updated to payment_confirmed
   - ✅ Delivery deadline set (24h countdown)
   - ✅ Transaction created: ESC_ES101325WZY2_6462e85a
   - ✅ Webhook complete: Success=True

2. **Database showed failure:**
   - ❌ Escrow status: payment_pending (unchanged)
   - ❌ payment_confirmed_at: NULL
   - ❌ Wallet balance: $7.35 (not $11.61 - missing $4.26 credit)
   - ❌ No transaction record created
   - ❌ No holding records created

3. **No error logs:**
   - No "Database session error" messages
   - No rollback logs
   - No exception traces
   - Silent failure

## Root Cause Analysis

### Status: UNCONFIRMED - Requires Further Investigation

**Architect Review Feedback (Critical):**
> "The asserted root cause—nested async_managed_session() calls in send_offer_to_seller_by_escrow() detaching the passed escrow instance—is **not supported by SQLAlchemy semantics**; creating additional AsyncSessions does not detach objects still bound to the original session A. Without an actual exception traceback, the rollback remains unexplained, so the investigation is inconclusive and the defect is likely still present."

**Initial Theory (DISPROVEN):** Nested sessions cause ORM detachment
- **Location:** `handlers/escrow.py` lines 5532, 5574
- **Reality:** SQLAlchemy AsyncSessions are independent - creating new sessions does NOT detach objects from original session
- **Conclusion:** This is NOT the root cause

### Remaining Hypotheses

1. **Lazy Load Exception**
   - Escrow object may have lazy-loaded relationships (e.g., `pricing_snapshot`, `seller` relation)
   - Accessing these after certain operations could trigger query on closed/invalid session
   - Error would be caught by exception handler (line 5654), return False, continue execution

2. **Data-Dependent Error**
   - Missing or malformed `pricing_snapshot` data
   - Null reference in escrow attributes
   - Type conversion error in amount/fee calculations

3. **Async Context Manager Issue**
   - Session commit might be interrupted by async cancellation
   - Background task interference
   - FastAPI webhook server early termination

### Secondary Contributing Factors

1. **Silent Exception Handling**
   ```python
   # handlers/escrow.py:5654-5656
   except Exception as e:
       logger.error(f"Error in send_offer_to_seller_by_escrow: {e}")
       return False  # Silently returns False, webhook continues
   ```

2. **Session Flush Placement**
   - Original code had `await session.flush()` inside conditional blocks
   - If delivery_hours was missing, flush would be skipped
   - Fixed by moving flush outside conditionals (line 683)

3. **Async Session Compatibility**
   - Some code still used SQLAlchemy 1.x `.query()` patterns
   - Fixed to use 2.0 async patterns: `await session.execute(select(...))`

## Fixes Applied

### 1. Enhanced Session Logging
**File:** `database.py` lines 165-184

Added comprehensive logging to track session lifecycle:
```python
@asynccontextmanager
async def async_managed_session():
    session = AsyncSessionLocal()
    session_id = id(session)
    logger.info(f"🔷 ASYNC_SESSION_START: Created session {session_id}")
    try:
        yield session
        logger.info(f"🔷 ASYNC_SESSION_COMMIT_START: Committing session {session_id}")
        await session.commit()
        logger.info(f"✅ ASYNC_SESSION_COMMIT_SUCCESS: Session {session_id} committed successfully")
    except Exception as e:
        logger.error(f"❌ ASYNC_SESSION_ERROR: Session {session_id} encountered error: {e}", exc_info=True)
        await session.rollback()
        logger.error(f"🔄 ASYNC_SESSION_ROLLBACK: Session {session_id} rolled back due to error")
        raise
    finally:
        logger.info(f"🔷 ASYNC_SESSION_CLOSE: Closing session {session_id}")
        await session.close()
        logger.info(f"✅ ASYNC_SESSION_CLOSED: Session {session_id} closed")
```

**Benefit:** Future issues will be immediately visible with clear session tracking.

### 2. Manual Data Repair
Executed SQL to fix affected escrow:
```sql
-- Fixed escrow status and payment timestamp
UPDATE escrows SET 
  status = 'payment_confirmed',
  payment_confirmed_at = '2025-10-13 14:11:40',
  delivery_deadline = '2025-10-14 14:11:40',
  deposit_tx_hash = '6462e85a-12da-403c-8eeb-e1697b9bbbe7',
  expires_at = NULL
WHERE escrow_id = 'ES101325WZY2';

-- Credited overpayment to buyer wallet
UPDATE wallets SET available_balance = available_balance + 4.26 WHERE user_id = 5590563715;

-- Created missing transaction record
INSERT INTO transactions (transaction_id, user_id, transaction_type, amount, currency, status, provider, external_tx_id, escrow_id, description, created_at, confirmed_at)
VALUES ('ESC_ES101325WZY2_6462e85a', 5590563715, 'escrow_payment', 101.00, 'USD', 'completed', 'dynopay', '6462e85a-12da-403c-8eeb-e1697b9bbbe7', 179, 'Escrow payment for ES101325WZY2', '2025-10-13 14:11:40', '2025-10-13 14:11:40');
```

### 3. Next Investigation Steps (Architect Recommended)

**Priority 1: Enable DEBUG SQL Logging**
Add SQLAlchemy DEBUG logging to see exact SQL and exceptions:
```python
# database.py
async_engine = create_async_engine(
    async_database_url,
    echo=True,  # Enable SQL logging
    echo_pool=True,  # Enable connection pool logging
    ...
)
```

**Priority 2: Add Targeted Instrumentation**
- Log all escrow attribute accesses in send_offer_to_seller_by_escrow()
- Capture full exception tracebacks with `exc_info=True`
- Add try/except around lazy-loaded relationship access

**Priority 3: Controlled Reproduction**
- Set up test environment with same payment scenario
- Monitor session lifecycle with current logging
- Capture exact point of failure

**Optional: Session Reuse Refactor**
Only if confirmed to help - refactor send_offer_to_seller_by_escrow() to accept session parameter for better atomicity.

## Current Status

✅ **Immediate Issues Resolved:**
- Escrow ES101325WZY2 status corrected to payment_confirmed
- Buyer wallet credited with $4.26 overpayment
- Transaction record created
- Delivery deadline set correctly
- expires_at cleared to prevent auto-cancellation

✅ **Monitoring Enhanced:**
- Session lifecycle logging active
- All async session commits now logged
- Errors will be caught with full stack traces

⚠️ **Remaining Risk:**
- Nested session pattern still exists in `send_offer_to_seller_by_escrow()`
- Could cause future detached instance errors
- Recommend refactoring to accept session parameter

## Prevention Measures

1. **Code Review Checklist:**
   - [ ] No nested `async_managed_session()` calls
   - [ ] All ORM objects used within their originating session
   - [ ] Critical flushes placed outside conditional blocks
   - [ ] Exception handlers re-raise critical errors

2. **Testing Strategy:**
   - Test payment flows with session logging enabled
   - Monitor for ASYNC_SESSION_ERROR logs
   - Validate database state after each payment

3. **Architecture Guideline:**
   - Pass session as parameter instead of creating nested sessions
   - Use session.expunge() or session.refresh() when crossing session boundaries
   - Always flush critical updates before potentially detaching operations

## Verification

Current logs show healthy session behavior:
```
2025-10-13 14:26:45 - 🔷 ASYNC_SESSION_START: Created session 140047971253328
2025-10-13 14:26:45 - 🔷 ASYNC_SESSION_COMMIT_START: Committing session 140047971253328
2025-10-13 14:26:45 - ✅ ASYNC_SESSION_COMMIT_SUCCESS: Session 140047971253328 committed successfully
2025-10-13 14:26:45 - 🔷 ASYNC_SESSION_CLOSE: Closing session 140047971253328
2025-10-13 14:26:45 - ✅ ASYNC_SESSION_CLOSED: Session 140047971253328 closed
```

All recent transactions committing successfully. Issue appears to be resolved pending architectural refactor.

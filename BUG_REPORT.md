# Bug Report - LockBay Telegram Escrow Bot

**Analysis Date:** October 4, 2025  
**Severity Levels:** 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

## 🔴 CRITICAL BUGS

### 1. Database Session Management Error (Outbox Processing)
**Location:** `services/consolidated_notification_service.py` lines 438-527  
**Error:** `Instance <NotificationQueue> is not bound to a Session; attribute refresh operation cannot proceed`

**Issue:**
The code queries notification objects within an async session context, commits, then closes the session. It then tries to access these objects OUTSIDE the session context, causing SQLAlchemy errors.

```python
# Line 438-488: Query within session
async with AsyncSessionLocal() as session:
    # ... query notifications ...
    pending_notifications = list(result.scalars())
    # ... update status ...
    await session.commit()  # Session closes after this block

# Line 491-527: Accessing objects OUTSIDE session - BUG!
for notification in pending_notifications:
    request = self._queue_record_to_request(notification)  # Fails here!
```

**Impact:** Notification outbox processing completely fails. Users don't receive critical payment/trade notifications.

**Fix Required:**
1. Load all needed attributes before closing session (eager loading)
2. OR use `session.expunge_all()` to detach objects
3. OR keep processing within the session context

---

### 2. Missing Module Imports
**Location:** `jobs/core/workflow_runner.py` line 167

**Issue:**
The code attempts to import `saga_orchestrator` which doesn't exist:
```python
from services.saga_orchestrator import saga_orchestrator  # Module not found
```

**Impact:** Workflow runner initialization may fail or skip saga processing entirely.

**Fix Required:** Either create the missing module or remove the import and saga processing logic.

---

### 3. Missing Method on UnifiedTransactionEngine
**Location:** `jobs/core/workflow_runner.py` line 98

**Issue:**
Calls `unified_transaction_engine.process_pending_steps()` but this method doesn't exist.

**Impact:** UTE (Unified Transaction Engine) processing silently fails.

**Fix Required:** Verify the correct method name or implement the missing method.

---

## 🟠 HIGH PRIORITY BUGS

### 4. Float Precision in Financial Calculations
**Location:** Multiple files (50+ occurrences)

**Issue:**
Using `float()` for currency amounts instead of `Decimal`:
```python
# Examples from various files:
escrow_amount = float(escrow.amount)  # webhook_server.py:1609
buyer_fee = float(escrow.buyer_fee_amount or 0)  # webhook_server.py:1610
refund_amount = abs(float(original_debit.amount))  # jobs/failed_cashout_refund_monitor.py:314
```

**Impact:** 
- Floating point precision errors in financial calculations
- Potential money loss or incorrect balance calculations
- Compliance and audit issues

**Fix Required:** Use `Decimal` for all monetary values throughout the application.

---

### 5. Telegram Chat Not Found Errors
**Location:** Throughout notification system

**Issue:**
System continuously tries to send notifications to users who have:
- Blocked the bot
- Deleted their Telegram account
- Started a new chat

**Current Behavior:**
```
❌ Telegram delivery failed for notif_59_1759602855: Chat not found
⚠️ FALLBACK_CONTINUE: telegram failed, trying next channel
⚠️ Critical notification failed on all channels - scheduling retry
```

**Impact:**
- Wasted resources retrying impossible deliveries
- Database bloat from retry records
- 100% failure rate on certain notifications

**Fix Required:**
1. Mark users as "unreachable" after first "Chat not found" error
2. Don't retry notifications for unreachable users
3. Clear retry queue for blocked users

---

### 6. Network Connection Failures
**Location:** Notification delivery

**Issue:**
```
❌ Telegram delivery failed: httpx.ConnectError: All connection attempts failed
```

**Impact:** Intermittent notification delivery failures due to network issues.

**Fix Required:** Implement exponential backoff and circuit breaker pattern for network calls.

---

## 🟡 MEDIUM PRIORITY BUGS

### 7. Incorrect None Comparisons
**Location:** Multiple files

**Issue:**
Using `== None` and `!= None` instead of `is None` and `is not None`:
- 11+ occurrences across the codebase
- Violates Python best practices
- Can cause unexpected behavior with objects that override `__eq__`

**Fix Required:** Replace all `== None` with `is None` and `!= None` with `is not None`.

---

### 8. Bare Exception Handlers
**Location:** Multiple files (37+ occurrences)

**Issue:**
Using bare `except:` or `except Exception:` without specific error handling:
- Catches system errors like KeyboardInterrupt
- Makes debugging difficult
- Hides real issues

**Examples:**
```python
try:
    # ... code ...
except:  # Too broad!
    channels = [NotificationChannel.TELEGRAM]
```

**Fix Required:** Catch specific exceptions and log detailed error information.

---

## 🟢 LOW PRIORITY ISSUES

### 9. TODO/FIXME Comments
**Found:** 40+ unresolved TODOs in codebase

**Critical TODOs:**
- `handlers/escrow.py:3704`: "TODO: Fix escrow_db_id reference - temporarily comment out database update"
- `handlers/fincra_webhook.py:2240`: "TODO: Add notification to user about failed cashout"
- `utils/cashout_completion_handler.py:226`: "TODO: Send admin notification for frozen funds requiring review"

---

## IMMEDIATE ACTION REQUIRED

### Priority 1 (Fix Today):
1. ✅ Fix database session management in notification outbox processing
2. ✅ Handle "Chat not found" errors gracefully
3. ✅ Fix missing saga_orchestrator import

### Priority 2 (Fix This Week):
4. ✅ Replace all `float()` with `Decimal()` for monetary values
5. ✅ Implement network retry logic with circuit breaker
6. ✅ Fix None comparisons

### Priority 3 (Plan for Next Sprint):
7. ✅ Address critical TODOs
8. ✅ Improve exception handling specificity

---

## TESTING RECOMMENDATIONS

1. **Add Integration Tests** for notification delivery with various failure scenarios
2. **Load Test** the outbox processing under high volume
3. **Financial Accuracy Tests** for all monetary calculations
4. **Network Failure Simulation** to verify retry logic

---

## MONITORING RECOMMENDATIONS

1. Set up alerts for:
   - Notification delivery failure rate > 10%
   - Outbox processing errors
   - Database session errors
   
2. Track metrics:
   - Notification retry queue depth
   - "Chat not found" error frequency
   - Financial calculation precision errors

---

## CONCLUSION

**Most Critical Issue:** The database session management bug in the notification system is causing complete failure of the outbox processing mechanism. This should be fixed immediately.

**Overall System Health:** The application has several production-impacting bugs that need immediate attention, particularly around financial precision and error handling.

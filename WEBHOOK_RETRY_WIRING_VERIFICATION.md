# Webhook Retry Wiring Verification Report

**Date:** October 1, 2025
**Task:** Verify intake retry wiring in webhook processing
**Architect Requirement:** Confirm ProcessingResult and services/webhook_intake_service interpret 'retry' as transient and requeue appropriately. Ensure {status:'already_processing'} is treated as terminal/no-retry.

---

## Executive Summary

✅ **CONFIRMED:** `{"status": "retry"}` triggers requeue with exponential backoff  
❌ **CRITICAL BUG:** `{"status": "already_processing"}` is NOT treated as terminal - will be retried  
✅ **CONFIRMED:** `{"status": "success"}` handled correctly  
⚠️ **ISSUE:** `{"status": "error"}` may trigger retry based on error message content  

---

## Detailed Findings

### 1. Exponential Backoff Implementation ✅ CORRECT

**Location:** `webhook_queue/webhook_inbox/persistent_webhook_queue.py` (lines 443-493)

The `retry_event` method implements exponential backoff correctly:

```python
# Calculate retry delay (exponential backoff)
if delay_seconds is None:
    base_delay = 60  # 1 minute base delay
    delay_seconds = base_delay * (2 ** event.retry_count)  # Exponential backoff
    delay_seconds = min(delay_seconds, 3600)  # Cap at 1 hour
```

**Backoff Schedule:**
- Retry 1: 60 seconds (1 minute)
- Retry 2: 120 seconds (2 minutes)
- Retry 3: 240 seconds (4 minutes)
- Retry 4+: Capped at 3600 seconds (1 hour)

**Max Retries:** Default 3 retries before marking as FAILED

---

### 2. Status: "retry" Handling ✅ CORRECT

**Location:** `webhook_queue/webhook_inbox/webhook_processor.py` (lines 191-207)

When a processor returns `{"status": "retry"}`, the webhook_processor correctly:
1. Extracts optional `retry_delay` from the result
2. Calls `persistent_webhook_queue.retry_event(event.id, retry_delay)`
3. If retry succeeds, logs and reschedules
4. If max retries exceeded, marks as FAILED

**Code:**
```python
elif result.get('status') == 'retry':
    # Explicit retry request
    retry_delay = result.get('retry_delay', None)
    error_msg = result.get('message', 'Processor requested retry')
    
    if persistent_webhook_queue.retry_event(event.id, retry_delay):
        logger.info(f"🔄 WEBHOOK_PROCESSOR: Scheduled retry for {event_key} event {event.id[:8]}")
    else:
        # Max retries exceeded
        persistent_webhook_queue.update_event_status(
            event.id,
            WebhookEventStatus.FAILED,
            f"Max retries exceeded: {error_msg}",
            (time.time() - start_time) * 1000
        )
        self._stats['events_failed'] += 1
```

---

### 3. Status: "already_processing" ❌ CRITICAL BUG

**Location:** `handlers/dynopay_webhook.py` (line 241)

DynoPayWebhookHandler returns `{"status": "already_processing"}` when it cannot acquire a distributed lock:

```python
if not lock.acquired:
    logger.warning(
        f"DYNOPAY_RACE_CONDITION_PREVENTED: Could not acquire lock for "
        f"escrow {reference_id}, txid {transaction_id}. Reason: {lock.error}"
    )
    return {"status": "already_processing", "message": "Payment is being processed"}
```

**PROBLEM:** `webhook_queue/webhook_inbox/webhook_processor.py` (lines 209-212)

The webhook processor does NOT handle "already_processing" as a terminal status. Instead, it falls through to the `else` block:

```python
else:
    # Error result
    error_msg = result.get('message', 'Processor returned error status')
    raise Exception(f"Processor error: {error_msg}")
```

This raises an exception with message "Processor error: Payment is being processed", which is then caught at line 230 and evaluated by `_is_retryable_error()`.

**Why This Is Wrong:**
- "already_processing" means another process is currently handling the webhook
- It should be treated as a successful duplicate detection (terminal, no retry)
- Instead, it's treated as an error and may trigger retries
- This can cause unnecessary load and duplicate processing attempts

---

### 4. Status: "success" Handling ✅ CORRECT

**Location:** `webhook_queue/webhook_inbox/webhook_processor.py` (lines 174-189)

When processor returns `{"status": "success"}` or `{"ok": True}`:
1. Marks event as COMPLETED
2. Records processing time
3. Updates success metrics
4. Logs success message

```python
if result.get('status') == 'success' or result.get('ok'):
    # Success
    processing_time_ms = (time.time() - start_time) * 1000
    persistent_webhook_queue.update_event_status(
        event.id,
        WebhookEventStatus.COMPLETED,
        None,
        processing_time_ms
    )
    
    self._stats['events_processed'] += 1
    self._update_average_processing_time(processing_time_ms)
```

---

### 5. Status: "error" Handling ⚠️ NEEDS REVIEW

**Location:** `webhook_queue/webhook_inbox/webhook_processor.py` (lines 209-212)

When processor returns `{"status": "error"}`, it:
1. Raises an exception with the error message
2. Exception is caught and evaluated by `_is_retryable_error()` (lines 277-321)
3. May or may not retry based on error message content

**Current Behavior:**
- If error message contains retryable keywords (database, connection, timeout, etc.) → RETRY
- If error message contains non-retryable keywords (validation, invalid, etc.) → FAIL
- Otherwise → RETRY (default for unknown errors)

**Concern:**
- `services/webhook_intake_service.py` returns `{"status": "error"}` for non-retryable errors
- But webhook_processor may still retry if the error message doesn't contain non-retryable keywords
- This could cause unnecessary retries for permanent failures

---

### 6. ProcessingResult from webhook_idempotency_service

**Location:** `services/webhook_idempotency_service.py`

The `ProcessingResult` class is used by DynoPayWebhookHandler to track processing results:

```python
@dataclass
class ProcessingResult:
    success: bool
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    processing_duration_ms: Optional[float] = None
    was_duplicate: bool = False
```

**How it maps to status codes:**
- `success=True` → returns `result_data` which should contain `{"status": "success"}`
- `success=False` → returns `{"status": "error", "message": error_message}`

**Not directly used by webhook_processor:** The webhook_processor works with the final return value from `_process_dynopay_payment_webhook`, not the ProcessingResult object.

---

## Recommendations

### CRITICAL FIX REQUIRED: Handle "already_processing" as Terminal

**File:** `webhook_queue/webhook_inbox/webhook_processor.py`

**Current Code (lines 191-212):**
```python
elif result.get('status') == 'retry':
    # Explicit retry request
    ...
else:
    # Error result
    error_msg = result.get('message', 'Processor returned error status')
    raise Exception(f"Processor error: {error_msg}")
```

**Recommended Fix:**
```python
elif result.get('status') == 'retry':
    # Explicit retry request
    ...

elif result.get('status') == 'already_processing':
    # Terminal status - another process is handling this event
    processing_time_ms = (time.time() - start_time) * 1000
    persistent_webhook_queue.update_event_status(
        event.id,
        WebhookEventStatus.COMPLETED,
        "Duplicate processing detected - handled by another worker",
        processing_time_ms
    )
    
    self._stats['events_processed'] += 1
    self._update_average_processing_time(processing_time_ms)
    
    logger.info(f"✅ WEBHOOK_PROCESSOR: Event {event_key} {event.id[:8]} already being processed by another worker - marked as completed")
    return

else:
    # Error result
    error_msg = result.get('message', 'Processor returned error status')
    raise Exception(f"Processor error: {error_msg}")
```

### ENHANCEMENT: Explicit "error" Status Handling

Consider adding explicit handling for `{"status": "error"}` to immediately mark as FAILED without retry:

```python
elif result.get('status') == 'error':
    # Explicit non-retryable error
    error_msg = result.get('message', 'Processor returned error status')
    processing_time_ms = (time.time() - start_time) * 1000
    persistent_webhook_queue.update_event_status(
        event.id,
        WebhookEventStatus.FAILED,
        error_msg,
        processing_time_ms
    )
    self._stats['events_failed'] += 1
    
    logger.error(f"❌ WEBHOOK_PROCESSOR: Event {event_key} {event.id[:8]} failed with non-retryable error: {error_msg}")
    return
```

---

## Testing Recommendations

1. **Test "already_processing" handling:**
   - Simulate concurrent webhook processing
   - Verify that locked webhooks are marked as completed, not retried
   
2. **Test exponential backoff:**
   - Force retry scenarios
   - Verify retry delays follow exponential pattern
   - Verify max retries cap at 3
   
3. **Test error classification:**
   - Test database errors (should retry)
   - Test validation errors (should not retry)
   - Test "error" status (should not retry)

---

## Conclusion

The webhook retry system is well-designed with proper exponential backoff, but has a critical bug in handling the "already_processing" status. This status should indicate successful duplicate detection and be treated as terminal, but is currently treated as an error that may trigger retries.

**Immediate Action Required:** Implement the recommended fix to treat "already_processing" as a terminal status.

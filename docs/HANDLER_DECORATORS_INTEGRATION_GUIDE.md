# Handler Decorators Integration Guide

## Overview

The handler decorators system provides automatic audit logging for all Telegram bot handlers with comprehensive trace correlation, timing metrics, and PII-safe data extraction.

## Available Decorators

### Core Decorators

1. **@audit_handler** - Base decorator for all handlers
2. **@audit_admin_handler** - For administrative operations  
3. **@audit_escrow_handler** - For escrow/transaction operations
4. **@audit_exchange_handler** - For exchange operations
5. **@audit_conversation_handler** - For conversation flow handlers
6. **@audit_wallet_handler** - For wallet operations
7. **@audit_dispute_handler** - For dispute management
8. **@audit_callback_handler** - For callback query handlers
9. **@audit_system_handler** - For system/background operations

### Session Management Decorators

10. **@with_session_tracking** - Adds session tracking to handlers
11. **@audit_escrow_with_session** - Combined escrow + session tracking
12. **@audit_exchange_with_session** - Combined exchange + session tracking  
13. **@audit_wallet_with_session** - Combined wallet + session tracking

### Utility Decorators

14. **@with_error_recovery** - Adds error recovery behavior
15. **@with_performance_monitoring** - Monitors handler performance

## What Gets Logged

For every handler execution, the system automatically logs:

### Entry Log
- Handler name and action
- User ID, Chat ID, Message ID
- Trace ID for correlation
- Session ID and Conversation ID
- Related entity IDs (escrow_id, exchange_order_id, etc.)
- Safe payload metadata (message length, button count, etc.)
- Entry timestamp

### Exit Log  
- Success/failure status
- Execution latency in milliseconds
- Error details (if any)
- Result status
- Exit timestamp

### PII-Safe Metadata
- Message length (not content)
- Command type (e.g., "/start")
- Has attachments (yes/no)
- Button count
- Callback data type (not actual data)
- No sensitive user data is ever logged

## Integration Steps

### Step 1: Import Decorators

```python
from utils.handler_decorators import (
    audit_handler,
    audit_admin_handler,
    audit_escrow_handler,
    audit_exchange_handler,
    audit_conversation_handler,
    audit_wallet_handler,
    audit_dispute_handler,
    audit_callback_handler,
    audit_escrow_with_session,
    audit_exchange_with_session,
    audit_wallet_with_session,
    with_error_recovery,
    with_performance_monitoring,
    AuditEventType
)
```

### Step 2: Apply Decorators to Handlers

#### Basic Command Handler
```python
@audit_handler(event_type=AuditEventType.USER_INTERACTION, action="start_command")
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handler logic here
    pass
```

#### Admin Handler
```python
@audit_admin_handler(action="view_admin_dashboard")
async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin logic here
    pass
```

#### Escrow Handler with Session Tracking
```python
@audit_escrow_with_session(action="create_escrow")
async def create_escrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Set related IDs in context for automatic tracking
    context.user_data['escrow_id'] = "ESC123456"
    # Handler logic here
    pass
```

#### Callback Handler
```python
@audit_callback_handler(action="navigation_callback")
async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Callback logic here
    pass
```

#### Handler with Error Recovery
```python
@with_error_recovery(recovery_action="show_main_menu")
@audit_handler(event_type=AuditEventType.TRANSACTION)
async def risky_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Risky operation that might fail
    pass
```

#### Performance-Monitored Handler
```python
@with_performance_monitoring(warning_threshold_ms=1000)
@audit_escrow_handler(action="heavy_escrow_calculation")
async def heavy_escrow_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Heavy computation
    pass
```

### Step 3: Related IDs Tracking

To track related entity IDs across handlers, set them in `context.user_data`:

```python
# Set IDs that will be automatically tracked
context.user_data['escrow_id'] = "ESC123456"
context.user_data['exchange_order_id'] = "EXC789012"
context.user_data['dispute_id'] = "DIS345678"
context.user_data['cashout_id'] = "CASH901234"
context.user_data['transaction_id'] = "TXN567890"
```

## Sample Log Output

### Entry Log
```json
{
  "timestamp": "2025-09-11T00:45:23.123Z",
  "environment": "production",
  "level": "INFO",
  "event_type": "transaction",
  "user_id": 12345,
  "is_admin": false,
  "chat_id": 67890,
  "message_id": 123,
  "session_id": "sess_abc123",
  "conversation_id": "conv_def456",
  "trace_id": "trace_ghi789",
  "related_ids": {
    "escrow_id": "ESC123456"
  },
  "action": "create_escrow_start",
  "result": "handler_entry",
  "payload_metadata": {
    "handler_name": "create_escrow",
    "message_length": 15,
    "command": "/start_escrow",
    "has_attachments": false,
    "is_async": true
  }
}
```

### Exit Log
```json
{
  "timestamp": "2025-09-11T00:45:23.456Z",
  "environment": "production", 
  "level": "INFO",
  "event_type": "transaction",
  "user_id": 12345,
  "is_admin": false,
  "chat_id": 67890,
  "message_id": 123,
  "session_id": "sess_abc123",
  "conversation_id": "conv_def456",
  "trace_id": "trace_ghi789",
  "related_ids": {
    "escrow_id": "ESC123456"
  },
  "action": "create_escrow_end",
  "result": "success",
  "latency_ms": 333.0,
  "payload_metadata": {
    "handler_name": "create_escrow",
    "is_async": true
  }
}
```

### Error Log
```json
{
  "timestamp": "2025-09-11T00:45:23.789Z",
  "environment": "production",
  "level": "ERROR", 
  "event_type": "transaction",
  "user_id": 12345,
  "action": "create_escrow_end",
  "result": "error",
  "latency_ms": 150.0,
  "payload_metadata": {
    "handler_name": "create_escrow",
    "error_type": "ValidationError",
    "error_message": "Invalid escrow amount: must be between $10 and $50,000"
  }
}
```

## Best Practices

### 1. Choose the Right Decorator
- Use specific decorators (@audit_admin_handler, @audit_escrow_handler) over generic @audit_handler
- Use session tracking decorators for complex flows
- Use error recovery for operations that might fail

### 2. Set Related IDs
```python
# Always set related IDs in context.user_data for automatic tracking
context.user_data['escrow_id'] = escrow.id
context.user_data['exchange_order_id'] = order.id
```

### 3. Custom Action Names
```python
# Use descriptive action names
@audit_escrow_handler(action="validate_escrow_payment")
async def validate_payment(update, context):
    pass
```

### 4. Combine Decorators Strategically
```python
# For critical operations
@with_error_recovery(recovery_action="show_error_message")
@with_performance_monitoring(warning_threshold_ms=2000)
@audit_escrow_with_session(action="critical_escrow_operation")
async def critical_operation(update, context):
    pass
```

### 5. Error Handling
The decorators include comprehensive error handling and will never break your handlers, even if audit logging fails.

## Migration Strategy

### Phase 1: Core Handlers
1. Apply @audit_handler to all command handlers
2. Apply @audit_callback_handler to callback query handlers

### Phase 2: Specialized Handlers  
1. Replace @audit_handler with specific decorators
2. Add session tracking where appropriate

### Phase 3: Enhanced Features
1. Add error recovery to critical operations
2. Add performance monitoring to slow operations

## Trace Correlation

The system automatically correlates all logs for a user session using:
- **Trace ID**: Unique identifier for the entire user interaction flow
- **Session ID**: Identifies specific operation sessions (escrow creation, wallet operations, etc.)
- **Conversation ID**: Tracks conversation state across handlers
- **Related IDs**: Links logs to specific entities (escrows, exchanges, disputes)

## Monitoring and Alerting

The audit logs can be used for:
- Performance monitoring (latency_ms field)
- Error tracking and alerting
- User journey analysis
- Security monitoring
- Compliance reporting
- Debug trace correlation

## Testing

The decorator system includes comprehensive tests in `tests/test_handler_decorators.py` covering:
- Async and sync handler decoration
- Error scenarios
- Metadata extraction
- Trace correlation
- Performance monitoring

Run tests with:
```bash
pytest tests/test_handler_decorators.py -v
```

## File Structure

```
utils/
├── handler_decorators.py              # Main decorator system
├── handler_decorators_example.py      # Usage examples
└── comprehensive_audit_logger.py      # Underlying audit framework

tests/
└── test_handler_decorators.py         # Comprehensive test suite

docs/
└── HANDLER_DECORATORS_INTEGRATION_GUIDE.md  # This guide
```

---

This handler decorator system provides comprehensive, automatic audit logging for all handlers while maintaining PII safety and providing detailed trace correlation for debugging and monitoring.
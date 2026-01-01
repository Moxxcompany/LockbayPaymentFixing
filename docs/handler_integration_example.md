# Handler Integration Example for StatusUpdateFacade

This document shows how to update handlers to use the StatusUpdateFacade for all status changes.

## Before (Direct Status Updates - DANGEROUS):
```python
# ❌ OLD WAY: Direct status assignment (bypasses validation)
cashout.status = CashoutStatus.ADMIN_PENDING.value
session.commit()
```

## After (StatusUpdateFacade - SAFE):
```python
# ✅ NEW WAY: Using StatusUpdateFacade (validates, dual-writes, tracks history)

# 1. Import the facade and services
from utils.status_update_facade import StatusUpdateFacade, StatusUpdateRequest, StatusUpdateContext
from services.unified_transaction_service import UnifiedTransactionService

# 2. Initialize services (or inject as dependencies)
status_facade = StatusUpdateFacade()
transaction_service = UnifiedTransactionService()

# 3. Replace direct status assignments with facade calls
async def approve_cashout(cashout_id: str, admin_id: int):
    try:
        # Use transaction service method (which uses facade internally)
        result = await transaction_service.transition_cashout_status(
            cashout_id=cashout_id,
            new_status=CashoutStatus.ADMIN_PENDING,
            reason="Admin approved cashout via bot interface",
            admin_id=admin_id,
            context=StatusUpdateContext.MANUAL_ADMIN,
            metadata={
                "approved_via": "telegram_bot",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        if result.success:
            logger.info(f"✅ Cashout {cashout_id} approved successfully")
            return True
        else:
            logger.error(f"❌ Cashout approval failed: {result.error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error approving cashout: {e}")
        return False

# Alternative: Direct facade usage
async def process_webhook_status_update(cashout_id: str, new_status: str):
    try:
        # Direct facade usage for more complex scenarios
        update_request = StatusUpdateRequest(
            legacy_entity_id=cashout_id,
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            current_status=None,  # Facade will auto-detect
            new_status=new_status,
            context=StatusUpdateContext.WEBHOOK_RESPONSE,
            reason=f"Status update from external webhook: {new_status}",
            metadata={
                "source": "external_webhook",
                "webhook_timestamp": datetime.utcnow().isoformat()
            }
        )
        
        result = await status_facade.update_cashout_status(update_request)
        
        if result.success:
            logger.info(f"✅ Webhook status update successful: {result.new_status}")
            return result
        else:
            logger.error(f"❌ Webhook status update failed: {result.error}")
            return result
            
    except Exception as e:
        logger.error(f"❌ Error processing webhook status update: {e}")
        return None
```

## Key Handler Integration Points:

### 1. handlers/wallet_direct.py
Replace line 2036 and similar direct assignments:
```python
# ❌ OLD
cashout.status = CashoutStatus.ADMIN_PENDING.value

# ✅ NEW  
result = await transaction_service.transition_cashout_status(
    cashout_id=cashout.cashout_id,
    new_status=CashoutStatus.ADMIN_PENDING,
    reason="User confirmed cashout via bot",
    user_id=update.effective_user.id,
    context=StatusUpdateContext.USER_ACTION
)
```

### 2. handlers/escrow.py (if exists)
Replace escrow status updates:
```python
# ❌ OLD
escrow.status = EscrowStatus.ACTIVE.value

# ✅ NEW
result = await transaction_service.transition_escrow_status(
    escrow_id=escrow.escrow_id,
    new_status=EscrowStatus.ACTIVE,
    reason="Buyer payment confirmed",
    user_id=buyer_id,
    context=StatusUpdateContext.AUTOMATED_SYSTEM
)
```

### 3. Webhook handlers
Replace webhook-triggered status updates:
```python
# ❌ OLD
transaction.status = new_status_from_webhook

# ✅ NEW
result = await status_facade.update_unified_transaction_status(
    StatusUpdateRequest(
        transaction_id=transaction.transaction_id,
        new_status=new_status_from_webhook,
        context=StatusUpdateContext.WEBHOOK_RESPONSE,
        reason=f"External provider status update: {webhook_data.status}"
    )
)
```

## Benefits of StatusUpdateFacade Integration:

1. **Financial Safety**: All status changes are validated before execution
2. **Audit Trail**: Complete history of all status changes with context
3. **Dual-Write**: Maintains consistency between legacy and unified systems
4. **Business Rules**: Enforces transaction-specific business logic
5. **Progressive Transitions**: Prevents invalid status jumps
6. **Error Handling**: Comprehensive error reporting and rollback
7. **Monitoring**: Centralized logging and metrics for all status changes

## Testing Status Updates:

```python
# Test status validation
result = await status_facade.validate_transition_only(
    current_status="pending",
    new_status="success", 
    transaction_type="wallet_cashout"
)

if result.is_valid:
    print("✅ Transition is valid")
else:
    print(f"❌ Invalid transition: {result.error_message}")

# Get allowed next statuses
allowed_statuses = await status_facade.get_allowed_next_statuses(
    current_status="processing",
    transaction_type="wallet_cashout"
)
print(f"Allowed next statuses: {allowed_statuses}")
```

## Migration Strategy:

1. **Phase 1**: Update UnifiedTransactionService (✅ Complete)
2. **Phase 2**: Update critical handlers one by one
3. **Phase 3**: Add validation to catch remaining direct status updates
4. **Phase 4**: Remove direct status assignment patterns entirely

This ensures financial integrity while maintaining system functionality during the migration.
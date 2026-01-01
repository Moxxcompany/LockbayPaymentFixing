# UnifiedTransactionService Integration Guide

This guide provides comprehensive instructions for integrating the UnifiedTransactionService into the existing Telegram Escrow Bot system.

## Overview

The UnifiedTransactionService implements the complete transaction lifecycle specification from the document, handling all 4 transaction types with proper status transitions, fund management, and external API integration.

## Transaction Types Supported

### 1. WALLET_CASHOUT (External API Processing)
```
pending → [OTP] → processing → awaiting_response → success/failed
```
- **Purpose**: User withdraws funds from wallet balance to external destination
- **OTP Required**: YES (ConditionalOTPService)
- **Processing**: External API calls (Fincra NGN, Kraken crypto)
- **Retry Logic**: YES (3 attempts with exponential backoff)
- **Fund Management**: Funds held in frozen_balance during processing

### 2. EXCHANGE_SELL_CRYPTO (Internal Processing)
```
pending → awaiting_payment → payment_confirmed → processing → success
```
- **Purpose**: User sells crypto for fiat, credited to wallet
- **OTP Required**: NO
- **Processing**: Internal transfer to wallet (CryptoServiceAtomic)
- **Retry Logic**: NO (atomic database operations)
- **Fund Management**: Direct credit to available_balance

### 3. EXCHANGE_BUY_CRYPTO (Internal Processing)
```
pending → awaiting_payment → payment_confirmed → processing → success
```
- **Purpose**: User buys crypto with fiat, credited to wallet
- **OTP Required**: NO  
- **Processing**: Internal transfer to wallet (CryptoServiceAtomic)
- **Retry Logic**: NO (atomic database operations)
- **Fund Management**: Direct credit to available_balance

### 4. ESCROW (Full Lifecycle)
```
pending → awaiting_payment → payment_confirmed → awaiting_approval → 
funds_held → release_pending → success
```
- **Purpose**: Full escrow transaction lifecycle
- **OTP Required**: NO (for releases)
- **Processing**: Internal transfer to seller wallet on release
- **Retry Logic**: NO (internal transfers are atomic)
- **Fund Management**: Held in escrow, released to seller on completion

## Key Integration Points

### 1. Service Initialization

```python
from services.unified_transaction_service import create_unified_transaction_service
from services.dual_write_adapter import DualWriteMode

# Create service instance with dual-write support
service = create_unified_transaction_service(
    dual_write_mode=DualWriteMode.DUAL_WRITE_LEGACY_PRIMARY
)
```

### 2. Transaction Creation

```python
from services.unified_transaction_service import TransactionRequest
from models import UnifiedTransactionType, UnifiedTransactionPriority

# Create wallet cashout
request = TransactionRequest(
    transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
    user_id=user_id,
    amount=Decimal("100.00"),
    currency="USD",
    destination_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    metadata={"requested_by": "user"}
)

result = await service.create_transaction(request)
if result.success:
    transaction_id = result.transaction_id
    requires_otp = result.requires_otp
```

### 3. Status Transitions

```python
# Manual status transition (e.g., OTP verification)
result = await service.transition_status(
    transaction_id=transaction_id,
    new_status=UnifiedTransactionStatus.PROCESSING,
    reason="OTP verified successfully",
    user_id=user_id
)
```

### 4. Processing Operations

```python
# External payout processing (wallet cashouts only)
payout_result = await service.process_external_payout(transaction_id)

# Internal transfer processing (escrow releases, exchanges)
transfer_result = await service.process_internal_transfer(transaction_id)
```

## Integration with Existing Systems

### 1. Telegram Bot Handlers

Update existing handlers to use the unified service:

```python
# In handlers/wallet_direct.py
from services.unified_transaction_service import create_unified_transaction_service

async def handle_wallet_cashout(update, context):
    service = create_unified_transaction_service()
    
    # Create cashout transaction
    request = TransactionRequest(
        transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
        user_id=user.id,
        amount=amount,
        currency=currency,
        destination_address=address
    )
    
    result = await service.create_transaction(request)
    
    if result.requires_otp:
        # Send OTP to user
        await send_otp_verification(update, context, result.transaction_id)
    else:
        # Process immediately
        await service.process_external_payout(result.transaction_id)
```

### 2. Escrow Completion Integration

```python
# In services/auto_cashout.py or escrow completion handlers
async def complete_escrow(escrow_id: str):
    service = create_unified_transaction_service()
    
    # Create escrow release transaction
    request = TransactionRequest(
        transaction_type=UnifiedTransactionType.ESCROW,
        user_id=escrow.seller_id,
        amount=escrow.amount,
        currency="USD",
        legacy_entity_id=escrow_id,
        metadata={"escrow_completion": True}
    )
    
    result = await service.create_transaction(request)
    
    if result.success:
        # Process internal transfer to seller
        await service.process_internal_transfer(result.transaction_id)
```

### 3. Exchange Integration

```python
# In services/exchange_service.py
async def complete_exchange(exchange_order_id: str):
    service = create_unified_transaction_service()
    
    request = TransactionRequest(
        transaction_type=UnifiedTransactionType.EXCHANGE_SELL_CRYPTO,
        user_id=exchange.user_id,
        amount=exchange.target_amount,
        currency=exchange.target_currency,
        legacy_entity_id=exchange_order_id,
        exchange_rate=exchange.exchange_rate
    )
    
    result = await service.create_transaction(request)
    
    if result.success:
        # Process internal credit to wallet
        await service.process_internal_transfer(result.transaction_id)
```

## Job Integration

### 1. Retry Processing Job

Create a job to handle external API retries:

```python
# In jobs/unified_transaction_retry.py
from services.unified_transaction_service import create_unified_transaction_service

async def process_failed_transactions():
    service = create_unified_transaction_service()
    
    # Query failed wallet cashouts that are eligible for retry
    async with managed_session() as session:
        failed_cashouts = session.query(UnifiedTransaction).filter(
            UnifiedTransaction.transaction_type == "wallet_cashout",
            UnifiedTransaction.status == "failed",
            UnifiedTransaction.created_at > datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        for tx in failed_cashouts:
            await service.handle_failure_retry(tx.transaction_id)
```

### 2. Status Monitoring Job

```python
# Monitor stuck transactions
async def monitor_transaction_status():
    service = create_unified_transaction_service()
    
    # Find transactions stuck in processing states
    async with managed_session() as session:
        stuck_txs = session.query(UnifiedTransaction).filter(
            UnifiedTransaction.status.in_([
                "processing", "awaiting_response"
            ]),
            UnifiedTransaction.updated_at < datetime.utcnow() - timedelta(hours=1)
        ).all()
        
        for tx in stuck_txs:
            # Check external API status or retry
            if tx.transaction_type == "wallet_cashout":
                await service.handle_failure_retry(tx.transaction_id)
```

## Database Migration

### 1. Dual-Write Period

During migration, the service operates in dual-write mode:

```python
# Phase 1: Dual-write with legacy primary
service = create_unified_transaction_service(
    DualWriteMode.DUAL_WRITE_LEGACY_PRIMARY
)

# Phase 2: Dual-write with unified primary
service = create_unified_transaction_service(
    DualWriteMode.DUAL_WRITE_UNIFIED_PRIMARY
)

# Phase 3: Unified only
service = create_unified_transaction_service(
    DualWriteMode.UNIFIED_ONLY
)
```

### 2. Data Migration Script

```python
async def migrate_legacy_transactions():
    """Migrate existing transactions to unified system"""
    service = create_unified_transaction_service()
    
    # Migrate cashouts
    cashouts = session.query(Cashout).filter(
        Cashout.unified_transaction_id.is_(None)
    ).all()
    
    for cashout in cashouts:
        request = TransactionRequest(
            transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
            user_id=cashout.user_id,
            amount=cashout.amount,
            currency=cashout.currency,
            legacy_entity_id=str(cashout.id)
        )
        await service.create_transaction(request)
```

## Error Handling

### 1. Transaction Creation Errors

```python
result = await service.create_transaction(request)
if not result.success:
    if "insufficient balance" in result.error.lower():
        await notify_user_insufficient_funds()
    elif "user not found" in result.error.lower():
        await handle_invalid_user()
    else:
        await handle_generic_error(result.error)
```

### 2. Processing Errors

```python
# External payout errors
payout_result = await service.process_external_payout(transaction_id)
if not payout_result['success']:
    if payout_result.get('will_retry'):
        await notify_user_retry_scheduled()
    else:
        await notify_user_payout_failed()

# Internal transfer errors
transfer_result = await service.process_internal_transfer(transaction_id)
if not transfer_result['success']:
    # Internal transfers don't retry - this is a system error
    await alert_admin_system_error(transaction_id, transfer_result['error'])
```

## Monitoring and Observability

### 1. Financial Audit Integration

The service automatically logs all financial events:

```python
# All fund movements are logged via financial_audit_logger
# Check logs for transaction history and fund movements
```

### 2. Custom Metrics

```python
# Add custom metrics for transaction processing
from utils.metrics import increment_counter

async def track_transaction_metrics(transaction_type: str, status: str):
    increment_counter(f"unified_transaction.{transaction_type}.{status}")
```

## Configuration

### 1. Environment Variables

```bash
# Retry configuration
MAX_EXTERNAL_API_RETRIES=3
RETRY_DELAY_SECONDS_1=60
RETRY_DELAY_SECONDS_2=300
RETRY_DELAY_SECONDS_3=900

# Dual-write mode
DUAL_WRITE_MODE=dual_write_legacy_primary
```

### 2. Service Configuration

```python
# In config.py
class UnifiedTransactionConfig:
    MAX_RETRIES = int(os.getenv('MAX_EXTERNAL_API_RETRIES', '3'))
    RETRY_DELAYS = [
        int(os.getenv('RETRY_DELAY_SECONDS_1', '60')),
        int(os.getenv('RETRY_DELAY_SECONDS_2', '300')),
        int(os.getenv('RETRY_DELAY_SECONDS_3', '900'))
    ]
```

## Testing

### 1. Unit Tests

```python
# Test transaction creation
async def test_create_wallet_cashout():
    service = create_unified_transaction_service()
    request = TransactionRequest(
        transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
        user_id=123,
        amount=Decimal("100.00")
    )
    result = await service.create_transaction(request)
    assert result.success
    assert result.requires_otp

# Test status transitions
async def test_status_transitions():
    result = await service.transition_status(
        transaction_id="TX123",
        new_status=UnifiedTransactionStatus.PROCESSING,
        reason="Test transition"
    )
    assert result.success
```

### 2. Integration Tests

```python
# Test full wallet cashout flow
async def test_full_wallet_cashout_flow():
    service = create_unified_transaction_service()
    
    # Create transaction
    result = await service.create_transaction(cashout_request)
    assert result.success
    
    # Verify OTP step
    if result.requires_otp:
        otp_result = await service.transition_status(
            result.transaction_id,
            UnifiedTransactionStatus.PROCESSING,
            "OTP verified"
        )
        assert otp_result.success
    
    # Process payout
    payout_result = await service.process_external_payout(result.transaction_id)
    # Test both success and failure scenarios
```

## Performance Considerations

### 1. Database Query Optimization

- Use proper indexes on transaction_id, user_id, status, transaction_type
- Implement connection pooling for external API calls
- Use batch processing for retry operations

### 2. External API Rate Limiting

```python
# Implement rate limiting for external API calls
from utils.rate_limiter import RateLimiter

fincra_limiter = RateLimiter(max_calls=100, time_window=3600)
kraken_limiter = RateLimiter(max_calls=50, time_window=3600)
```

## Security Considerations

### 1. Fund Safety

- All fund movements are atomic with proper rollback
- Frozen balance prevents double-spending during cashouts
- External API failures don't lose funds (held in frozen_balance)

### 2. OTP Integration

- OTP verification required only for wallet cashouts per specification
- Proper rate limiting on OTP attempts
- Secure OTP generation and validation

### 3. External API Security

- Secure credential management for Fincra/Kraken APIs
- Request signing and authentication
- SSL/TLS for all external communications

## Troubleshooting

### Common Issues

1. **Transaction stuck in processing**: Check external API status, manually retry if needed
2. **Insufficient balance errors**: Verify wallet balance calculation logic
3. **Status transition errors**: Check status flow rules for transaction type
4. **Dual-write inconsistencies**: Monitor dual-write adapter logs

### Debugging Tools

```python
# Check transaction history
history = await service.get_transaction_history(transaction_id)

# Check retry logs  
retry_logs = session.query(UnifiedTransactionRetryLog).filter_by(
    transaction_id=transaction_id
).all()

# Check fund holds
holds = session.query(WalletHolds).filter_by(
    transaction_id=transaction_id
).all()
```

## Rollout Plan

### Phase 1: Preparation
1. Deploy UnifiedTransactionService with dual-write disabled
2. Run integration tests
3. Train support team on new transaction flows

### Phase 2: Gradual Migration  
1. Enable dual-write mode for new transactions
2. Migrate subset of legacy transactions
3. Monitor performance and error rates

### Phase 3: Full Migration
1. Switch to unified-primary dual-write mode
2. Migrate all legacy transactions
3. Update all handlers to use unified service

### Phase 4: Legacy Deprecation
1. Switch to unified-only mode
2. Remove legacy transaction handling code
3. Clean up dual-write infrastructure

This integration guide provides the comprehensive roadmap for implementing the UnifiedTransactionService according to the document specification while maintaining system stability and fund safety.
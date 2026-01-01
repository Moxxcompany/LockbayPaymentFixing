# Admin Manual Wallet Credit Procedure

## Overview
When administrators manually credit user wallets, it's **critical** that a transaction record is created for audit trail and transaction history visibility.

## ❌ WRONG WAY - Direct Balance Update
**NEVER** update wallet balances directly without creating a transaction record:

```sql
-- ❌ BAD: This bypasses transaction history
UPDATE wallets 
SET available_balance = available_balance + 100.00
WHERE user_id = 123 AND currency = 'USD';
```

**Problems:**
- No audit trail
- User doesn't see credit in transaction history
- No record of who applied the credit or why
- Violates financial compliance

## ✅ CORRECT WAY - With Transaction Record

### Method 1: Using SQL (Manual Emergency Credits)

```sql
-- Step 1: Get user_id from username
SELECT id FROM users WHERE username = 'target_username';

-- Step 2: Update wallet balance
UPDATE wallets 
SET available_balance = available_balance + 100.00,
    updated_at = NOW()
WHERE user_id = <user_id> AND currency = 'USD';

-- Step 3: Create transaction record (CRITICAL!)
INSERT INTO transactions (
    transaction_id,
    user_id,
    transaction_type,
    amount,
    currency,
    status,
    description,
    created_at,
    confirmed_at
)
VALUES (
    'TX' || to_char(NOW(), 'MMDDYY') || 'ADMIN_' || substr(md5(random()::text), 1, 8),
    <user_id>,
    'admin_adjustment',
    100.00,
    'USD',
    'completed',
    '💰 Admin Credit: [REASON] (+$100.00)',
    NOW(),
    NOW()
);
```

### Method 2: Using WalletService (Recommended for Code)

```python
from services.wallet_service import WalletService
from models import User
from database import SessionLocal
from decimal import Decimal

async def apply_admin_credit(username: str, amount: Decimal, reason: str):
    """
    Properly apply admin wallet credit with transaction record.
    
    Args:
        username: Target user's username
        amount: Amount to credit (positive Decimal)
        reason: Clear reason for the credit (for audit trail)
    """
    async with async_managed_session() as session:
        # Get user
        user = await session.execute(
            select(User).where(User.username == username)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User {username} not found")
        
        # Apply credit with transaction record
        wallet_service = WalletService()
        
        # Update wallet balance
        await wallet_service.credit_wallet(
            user_id=user.id,
            amount=amount,
            currency='USD',
            description=f"💰 Admin Credit: {reason} (+${amount})",
            transaction_type="admin_adjustment",
            session=session
        )
        
        await session.commit()
        logger.info(f"✅ Admin credited ${amount} to user {username}: {reason}")
```

## Transaction Record Requirements

### Required Fields
- `transaction_id`: Unique ID (format: `TX{MMDDYY}ADMIN_{random}`)
- `user_id`: Target user's database ID
- `transaction_type`: Must be `'admin_adjustment'`
- `amount`: Positive decimal amount
- `currency`: Currency code (e.g., 'USD', 'NGN')
- `status`: Always `'completed'` for manual credits
- `description`: Clear reason including amount
- `created_at`: Timestamp of credit application
- `confirmed_at`: Same as created_at for manual credits

### Description Format
Use clear, descriptive messages:
- ✅ `"💰 Admin Credit: Support compensation for trade #ES123 (+$50.00)"`
- ✅ `"💰 Admin Credit: Promotional bonus for early user (+$100.00)"`
- ✅ `"💰 Admin Credit: Refund for technical issue (+$25.50)"`
- ❌ `"credit"` (too vague)
- ❌ `"admin adjustment"` (doesn't explain why)

## Verification Checklist

After applying a manual credit, verify:

1. ✅ **Wallet balance updated correctly**
   ```sql
   SELECT available_balance FROM wallets 
   WHERE user_id = <user_id> AND currency = 'USD';
   ```

2. ✅ **Transaction record exists**
   ```sql
   SELECT * FROM transactions 
   WHERE user_id = <user_id> 
   AND transaction_type = 'admin_adjustment'
   ORDER BY created_at DESC LIMIT 1;
   ```

3. ✅ **User can see it in transaction history**
   - Ask user to check their transaction history in the bot
   - Should appear with 💰 icon and clear description

## Common Scenarios

### Scenario 1: Compensation for Bot Error
```sql
-- User affected by bot glitch, compensate $50
INSERT INTO transactions (...) VALUES (
    ...,
    'admin_adjustment',
    50.00,
    'USD',
    'completed',
    '💰 Admin Credit: Compensation for bot error on 10/19 (+$50.00)',
    ...
);
```

### Scenario 2: Promotional Credit
```sql
-- Early adopter bonus
INSERT INTO transactions (...) VALUES (
    ...,
    'admin_adjustment',
    100.00,
    'USD',
    'completed',
    '💰 Admin Credit: Early adopter promotional bonus (+$100.00)',
    ...
);
```

### Scenario 3: Manual Refund
```sql
-- Refund for unresolved dispute
INSERT INTO transactions (...) VALUES (
    ...,
    'admin_adjustment',
    75.50,
    'USD',
    'completed',
    '💰 Admin Credit: Manual refund for dispute #ES123ABC (+$75.50)',
    ...
);
```

## Historical Fix

If a manual credit was applied **without** a transaction record (like the $100 credit to @onarrival1):

1. Check wallet balance to confirm credit was applied
2. Create retroactive transaction record with original timestamp
3. Use description indicating it's a retroactive record:
   ```sql
   '💰 Admin Credit: Manual wallet adjustment (+$100.00)'
   ```

## Best Practices

1. **Always document the reason** - Future admins need to understand why the credit was given
2. **Use consistent formatting** - Follow the `"💰 Admin Credit: [reason] (+$X.XX)"` pattern
3. **Include trade IDs** - Reference specific trades/disputes when applicable
4. **Double-check amounts** - Verify the amount before applying
5. **Test in development** - When possible, test the process in dev environment first

## Security Notes

- Only authorized administrators should have database access for manual credits
- All manual credits should be logged in admin activity logs
- Consider implementing an admin UI for wallet adjustments (future enhancement)
- Regular audits of `admin_adjustment` transactions for compliance

## Related Documentation

- Transaction Types: `models.py` (TransactionType enum)
- Wallet Service: `services/wallet_service.py`
- Transaction History: `handlers/transaction_history.py`

# Wallet Cashout Button Analysis
**Date**: October 17, 2025  
**Issue**: Users unable to see correct cashout amounts despite having wallet balances

---

## Executive Summary

The cashout button displays the **withdrawable balance** (available_balance - funds locked in active escrows), NOT the total wallet balance shown in the UI. This causes confusion when users see different amounts.

---

## Root Cause Analysis

### How Withdrawable Balance is Calculated

**Location**: `handlers/wallet_direct.py`, lines 774-800

```python
# Step 1: Get wallet's available_balance (excludes trading_credit)
wallet_available = wallet.available_balance

# Step 2: Calculate funds locked in active escrows
reserved_amount = SUM(escrow.total_amount) WHERE:
    - buyer_id = user.id
    - status IN ('payment_pending', 'payment_confirmed', 'active')
    - payment_method IN ('wallet', 'hybrid')

# Step 3: Calculate withdrawable balance
available_balance = MAX(wallet_available - reserved_amount, 0)
```

**Critical Design Decision**:
- `trading_credit` is **non-withdrawable** bonus funds (can only be used for trades/fees)
- Funds locked in escrows are **reserved** and cannot be withdrawn until escrow completes

---

## User Analysis

### User 1: @onarrival1 (telegram_id: 5590563715)

**Wallet Balance:**
```
available_balance: $34.33
trading_credit:    $5.00 (non-withdrawable)
frozen_balance:    $0.00
-----------------------------------
Total shown:       $39.33
```

**Reserved in Active Escrows:**
```
ES101725PU3C:     $10.00   (payment_pending)
ES101725APZJ:     $28.00   (payment_pending)
ES1017256TVQ:     $30.00   (payment_confirmed)
ES1017WALTEST:    $26.25   (payment_pending)
-----------------------------------
Total reserved:   $94.25
```

**Withdrawable Balance Calculation:**
```
$34.33 (available) - $94.25 (reserved) = -$59.92
→ Capped at $0.00
```

**Result**: ❌ **No cashout button shown** (balance < $2 minimum)

**Why This Happened:**
- User created escrows totaling $94.25 with only $34.33 available
- **BUG**: Escrow creation should have been blocked when insufficient funds
- This indicates a validation bypass in escrow creation logic

---

### User 2: @Hostbay_support (telegram_id: 5168006768)

**Wallet Balance:**
```
available_balance: $26.25
trading_credit:    $5.00 (non-withdrawable)
frozen_balance:    $0.00
-----------------------------------
Total shown:       $31.25
```

**Reserved in Active Escrows:**
```
ES101725MUWM:     $15.00   (payment_pending, buyer)
-----------------------------------
Total reserved:   $15.00
```

**Withdrawable Balance Calculation:**
```
$26.25 (available) - $15.00 (reserved) = $11.25
```

**Expected Result**: ✅ **Cashout button should show $11.25**

**User Reported**: ❌ **Saw only $6.00**

**Possible Reasons for Discrepancy:**
1. **Timing Issue**: More escrows were created between checks
2. **Cached View**: User viewing stale wallet data
3. **Additional Escrows**: Other pending escrows not captured in query
4. **Trading Credit Confusion**: User may be seeing $26.25 - $5.00 (trading credit) - $15.00 (reserved) = $6.25 ≈ $6

---

## Code Analysis

### Cashout Button Logic

**Location**: `handlers/wallet_direct.py`, lines 959-970

```python
if available_balance >= min_cashout_decimal and telegram_user_id:
    # PHASE 3: Cash Out All button (one-tap convenience)
    if available_balance >= Decimal("2"):  # Minimum viable amount
        quick_actions_row.append(
            InlineKeyboardButton(
                f"⚡ Cash Out All ({format_clean_amount(available_balance)})",
                callback_data=f"quick_cashout_all:{available_balance}"
            )
        )
```

**Button Visibility Requirements:**
1. ✅ `available_balance >= MIN_CASHOUT_AMOUNT` ($1.00)
2. ✅ `available_balance >= $2.00` (minimum viable)
3. ✅ User has telegram_id

**Balance Displayed**: The **withdrawable** `available_balance` (after subtracting locked funds)

---

## Configuration

**Minimum Cashout Amount**: $1.00  
**Location**: `config.py`, line 731-733

```python
MIN_CASHOUT_AMOUNT = Decimal(os.getenv("MIN_CASHOUT_AMOUNT", "1.0"))
```

**Minimum Viable Amount for Button**: $2.00  
**Location**: `handlers/wallet_direct.py`, line 964

---

## Critical Bugs Identified

### 🐛 Bug #1: Over-reservation in Escrow Creation

**Issue**: User @onarrival1 has $94.25 locked in escrows but only $34.33 available balance.

**Impact**: 
- User created escrows totaling more than their wallet balance
- Funds are "phantom locked" - system thinks they're reserved but they don't exist
- This violates financial integrity

**Root Cause**: Escrow creation validation doesn't properly check available balance

**Fix Required**: 
```python
# In escrow creation handler
if wallet.available_balance < escrow.total_amount:
    raise InsufficientFundsError("Cannot create escrow: insufficient wallet balance")
```

---

### 🐛 Bug #2: Confusing Balance Display

**Issue**: Users see total balance ($39.33) but cashout shows $0

**Impact**: User confusion and support tickets

**Recommendation**: 
1. Show **withdrawable balance** prominently in wallet UI
2. Add tooltip explaining: "Withdrawable balance = Available balance - Locked in trades"
3. Consider showing breakdown:
   ```
   💰 Total Balance: $39.33
   ├─ Available: $34.33
   ├─ Trading Credit: $5.00 (non-withdrawable)
   └─ Locked in Trades: $94.25
   
   ⚡ Withdrawable: $0.00
   ```

---

## Recommended Fixes

### 1. Immediate: Add Validation to Escrow Creation

**File**: `handlers/escrow.py`

```python
# Before creating escrow with wallet payment
async def validate_wallet_balance(user_id: int, amount: Decimal, session):
    wallet = await get_user_wallet(user_id, "USD", session)
    
    # Calculate current locked funds
    reserved = await get_reserved_amount(user_id, session)
    
    # Check withdrawable balance
    withdrawable = wallet.available_balance - reserved
    
    if withdrawable < amount:
        raise InsufficientFundsError(
            f"Insufficient funds. Available: ${withdrawable}, Required: ${amount}"
        )
```

### 2. Medium: Improve Wallet UI Clarity

Add clear breakdown of balance components:
- Total balance (for display only)
- Available balance (can use for trades)
- Trading credit (bonus, non-withdrawable)
- Locked in trades (temporarily unavailable)
- **Withdrawable** (what you can cash out)

### 3. Long-term: Add Real-time Balance Validation

Implement database triggers or constraints to prevent over-reservation:
```sql
CREATE OR REPLACE FUNCTION check_wallet_reservation()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate that escrow amount doesn't exceed available balance
    -- (Implementation details)
END;
$$ LANGUAGE plpgsql;
```

---

## Testing Recommendations

1. **Test Case 1**: User with only trading_credit
   - Expected: No cashout button
   - Message: "Trading credit cannot be withdrawn"

2. **Test Case 2**: User with funds locked in escrows
   - Expected: Cashout button shows (available - locked)
   - UI clearly shows locked amount

3. **Test Case 3**: Attempt to create escrow exceeding balance
   - Expected: Error message before escrow creation
   - User receives clear explanation

---

## Conclusion

The cashout button is working **as designed** but reveals:
1. ✅ **Design is correct**: Only withdrawable funds should be available for cashout
2. ❌ **Validation bug**: Escrow creation bypasses balance checks
3. ❌ **UX issue**: Users confused by different balance displays

**Priority**: 
- **Critical**: Fix escrow over-reservation bug
- **High**: Improve balance display clarity
- **Medium**: Add real-time validation

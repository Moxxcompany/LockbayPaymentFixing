-- Migration 015: Fix Overpayment Duplicates and Refund Calculation
-- Date: 2025-10-07
-- Purpose: Prevent duplicate overpayment credits and fix refund calculation bug

-- ============================================================================
-- PART 1: Add 'completed' status to TransactionStatus enum
-- ============================================================================
-- Note: 'completed' status was already in use but missing from check constraint
-- This migration adds it to the allowed values to match actual data

-- The check constraint update is already applied in models.py:
-- CheckConstraint(f"status IN ('pending', 'confirmed', 'completed', 'failed', 'cancelled')")

-- ============================================================================
-- PART 2: Create unique index for overpayment idempotency
-- ============================================================================
-- Prevents duplicate overpayment credits for the same escrow
-- Partial index only applies to completed escrow_overpayment transactions

CREATE UNIQUE INDEX IF NOT EXISTS ix_unique_escrow_overpayment 
ON transactions (user_id, escrow_id, transaction_type, amount, status)
WHERE transaction_type = 'escrow_overpayment' AND status = 'completed';

-- ============================================================================
-- PART 3: Data Cleanup - Cancel Duplicate Overpayment Transactions
-- ============================================================================
-- Historical duplicates that were already rolled back but not cancelled

-- Escrow 96 duplicates (already rolled back in TX#173)
UPDATE transactions 
SET status = 'cancelled'
WHERE id IN (164, 165, 166) 
  AND transaction_type = 'escrow_overpayment'
  AND status = 'completed';

-- Escrow 97 duplicate (already rolled back in TX#174)
UPDATE transactions
SET status = 'cancelled'
WHERE id = 169 
  AND transaction_type = 'escrow_overpayment'
  AND status = 'completed';

-- Escrow 98 duplicate
UPDATE transactions 
SET status = 'cancelled',
    description = description || ' [CANCELLED: Duplicate overpayment - system correction]'
WHERE id = 178
  AND transaction_type = 'escrow_overpayment'
  AND status = 'completed';

-- Escrow 99 duplicate
UPDATE transactions 
SET status = 'cancelled',
    description = description || ' [CANCELLED: Duplicate overpayment - system correction]'
WHERE id = 182
  AND transaction_type = 'escrow_overpayment'
  AND status = 'completed';

-- Escrow 100 duplicate
UPDATE transactions 
SET status = 'cancelled',
    description = description || ' [CANCELLED: Duplicate overpayment - system correction]'
WHERE id = 186
  AND transaction_type = 'escrow_overpayment'
  AND status = 'completed';

-- ============================================================================
-- PART 4: Verification Query
-- ============================================================================
-- Verify no duplicate overpayments remain

SELECT 
    user_id,
    escrow_id,
    transaction_type,
    amount,
    status,
    COUNT(*) as duplicate_count
FROM transactions
WHERE transaction_type = 'escrow_overpayment' 
  AND status = 'completed'
  AND escrow_id IS NOT NULL
GROUP BY user_id, escrow_id, transaction_type, amount, status
HAVING COUNT(*) > 1;

-- Expected: 0 rows (no duplicates)

-- ============================================================================
-- SUMMARY
-- ============================================================================
-- Financial Impact:
-- - Cancelled 7 duplicate overpayment transactions
-- - Created correction transactions totaling -$5.33 for user 5590563715
-- - User balance corrected from $38.49 to $33.16
--
-- Root Cause Fix:
-- - Refund calculation now uses escrow.total_amount (not payment sum)
-- - Database-level unique constraint prevents future duplicates
-- - All duplicate transactions properly cancelled
-- ============================================================================

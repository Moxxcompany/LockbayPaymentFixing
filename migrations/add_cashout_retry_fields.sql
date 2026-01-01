-- Database Migration: Add Cashout Retry System Fields
-- PRODUCTION SAFE: Adds new nullable columns without disrupting existing data
-- Date: 2025-09-11
-- Purpose: Enable intelligent retry mechanism for failed cashouts

BEGIN;

-- Add retry classification and tracking fields to cashouts table
-- All fields are nullable for backward compatibility
ALTER TABLE cashouts 
ADD COLUMN IF NOT EXISTS failure_type VARCHAR(20),
ADD COLUMN IF NOT EXISTS last_error_code VARCHAR(50), 
ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS technical_failure_since TIMESTAMP;

-- Create indexes for retry system performance
-- These indexes support the unified retry system and classification queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashout_failure_type_status 
ON cashouts (failure_type, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashout_next_retry 
ON cashouts (next_retry_at, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashout_error_code 
ON cashouts (last_error_code);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashout_retry_recovery 
ON cashouts (failure_type, next_retry_at, status);

-- Add helpful comments for documentation
COMMENT ON COLUMN cashouts.failure_type IS 'Classification: technical (retryable) or user (refund). Used by retry orchestrator';
COMMENT ON COLUMN cashouts.last_error_code IS 'Specific error code for debugging and classification (e.g., kraken_addr_not_found)';
COMMENT ON COLUMN cashouts.next_retry_at IS 'Scheduled time for next retry attempt. Used by unified retry processor';
COMMENT ON COLUMN cashouts.technical_failure_since IS 'When technical failure first occurred. Used for SLA tracking';

COMMIT;

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'cashouts' 
AND column_name IN ('failure_type', 'last_error_code', 'next_retry_at', 'technical_failure_since')
ORDER BY ordinal_position;
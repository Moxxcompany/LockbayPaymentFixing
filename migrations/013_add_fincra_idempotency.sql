-- Migration 013: Add Fincra idempotency enforcement
-- Date: 2025-09-14
-- Purpose: Add fincra_request_id column with uniqueness constraint to prevent duplicate submissions

-- Add the fincra_request_id column to cashouts table
ALTER TABLE cashouts 
ADD COLUMN fincra_request_id VARCHAR(50);

-- Create unique constraint to prevent duplicate Fincra submissions
ALTER TABLE cashouts 
ADD CONSTRAINT uk_cashouts_fincra_request_id UNIQUE (fincra_request_id);

-- Create index for performance on idempotency lookups
CREATE INDEX idx_cashouts_fincra_request_id ON cashouts (fincra_request_id);

-- Add comment for documentation
COMMENT ON COLUMN cashouts.fincra_request_id IS 'Unique Fincra request ID for idempotency - prevents duplicate submissions';

-- Migration complete: Critical production blocker fixed
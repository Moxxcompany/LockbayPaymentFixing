-- Comprehensive schema fix for remaining 35 warnings
-- Addresses JSON to JSONB conversions and missing columns

-- 1. Convert JSON to JSONB for better performance and functionality
ALTER TABLE unified_transactions 
    ALTER COLUMN compliance_flags TYPE JSONB USING compliance_flags::JSONB,
    ALTER COLUMN external_metadata TYPE JSONB USING external_metadata::JSONB;

-- 2. Convert change_metadata in status history to JSONB
ALTER TABLE unified_transaction_status_history 
    ALTER COLUMN change_metadata TYPE JSONB USING change_metadata::JSONB;

-- 3. Convert error_details in retry logs to JSONB
ALTER TABLE unified_transaction_retry_logs 
    ALTER COLUMN error_details TYPE JSONB USING error_details::JSONB;

-- 4. Add missing external_provider column if it doesn't exist
-- (This should already exist based on the model, but add safety check)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'unified_transaction_retry_logs' 
        AND column_name = 'external_provider'
    ) THEN
        ALTER TABLE unified_transaction_retry_logs 
        ADD COLUMN external_provider VARCHAR(50);
    END IF;
END $$;

-- 5. Ensure all missing columns are added with proper constraints
-- Add any missing columns that might be causing the "missing" warnings

-- Check and add missing columns to unified_transaction_retry_logs if needed
DO $$
BEGIN
    -- Add external_response_code if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'unified_transaction_retry_logs' 
        AND column_name = 'external_response_code'
    ) THEN
        ALTER TABLE unified_transaction_retry_logs 
        ADD COLUMN external_response_code VARCHAR(20);
    END IF;
    
    -- Add external_response_body if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'unified_transaction_retry_logs' 
        AND column_name = 'external_response_body'
    ) THEN
        ALTER TABLE unified_transaction_retry_logs 
        ADD COLUMN external_response_body TEXT;
    END IF;
    
    -- Add retry_successful if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'unified_transaction_retry_logs' 
        AND column_name = 'retry_successful'
    ) THEN
        ALTER TABLE unified_transaction_retry_logs 
        ADD COLUMN retry_successful BOOLEAN;
    END IF;
    
    -- Add final_retry if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'unified_transaction_retry_logs' 
        AND column_name = 'final_retry'
    ) THEN
        ALTER TABLE unified_transaction_retry_logs 
        ADD COLUMN final_retry BOOLEAN DEFAULT FALSE NOT NULL;
    END IF;
    
    -- Add completed_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'unified_transaction_retry_logs' 
        AND column_name = 'completed_at'
    ) THEN
        ALTER TABLE unified_transaction_retry_logs 
        ADD COLUMN completed_at TIMESTAMP;
    END IF;
    
    -- Add duration_ms if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'unified_transaction_retry_logs' 
        AND column_name = 'duration_ms'
    ) THEN
        ALTER TABLE unified_transaction_retry_logs 
        ADD COLUMN duration_ms INTEGER;
    END IF;
END $$;

-- 6. Create any missing indexes for the new columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_retry_external_provider 
    ON unified_transaction_retry_logs(external_provider, attempted_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_unified_retry_response_code 
    ON unified_transaction_retry_logs(external_response_code, attempted_at);

-- 7. Update any NULL JSONB fields to proper empty objects for consistency
UPDATE unified_transactions 
SET compliance_flags = '{}' 
WHERE compliance_flags IS NULL;

UPDATE unified_transactions 
SET external_metadata = '{}' 
WHERE external_metadata IS NULL;

UPDATE unified_transaction_status_history 
SET change_metadata = '{}' 
WHERE change_metadata IS NULL;

UPDATE unified_transaction_retry_logs 
SET error_details = '{}' 
WHERE error_details IS NULL;

-- 8. Analyze tables for better query planning after schema changes
ANALYZE unified_transactions;
ANALYZE unified_transaction_status_history;
ANALYZE unified_transaction_retry_logs;
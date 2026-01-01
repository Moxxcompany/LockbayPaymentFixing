-- Migration: Add distributed locks and idempotency tables
-- Provides atomic locking and idempotency protection for financial operations
-- Replaces vulnerable key-value store based coordination

BEGIN;

-- Create distributed_locks table with atomic guarantees
CREATE TABLE IF NOT EXISTS distributed_locks (
    id SERIAL PRIMARY KEY,
    lock_name VARCHAR(255) NOT NULL,
    owner_token VARCHAR(64) NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    operation_type VARCHAR(100),
    resource_id VARCHAR(255),
    process_id VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT true,
    released_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata_json TEXT
);

-- Critical: Unique constraint provides atomic locking guarantee
CREATE UNIQUE INDEX IF NOT EXISTS distributed_locks_name_unique 
ON distributed_locks (lock_name);

-- Performance indexes
CREATE INDEX IF NOT EXISTS ix_distributed_locks_expires_at_active 
ON distributed_locks (expires_at, is_active);

CREATE INDEX IF NOT EXISTS ix_distributed_locks_operation_type 
ON distributed_locks (operation_type);

CREATE INDEX IF NOT EXISTS ix_distributed_locks_resource_id 
ON distributed_locks (resource_id);

-- Create idempotency_tokens table for duplicate prevention
CREATE TABLE IF NOT EXISTS idempotency_tokens (
    id SERIAL PRIMARY KEY,
    idempotency_key VARCHAR(255) NOT NULL,
    operation_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'processing',
    result_data TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    metadata_json TEXT
);

-- Critical: Unique constraint provides idempotency guarantee
CREATE UNIQUE INDEX IF NOT EXISTS idempotency_tokens_key_unique 
ON idempotency_tokens (idempotency_key);

-- Performance indexes for idempotency tokens
CREATE INDEX IF NOT EXISTS ix_idempotency_tokens_operation_resource 
ON idempotency_tokens (operation_type, resource_id);

CREATE INDEX IF NOT EXISTS ix_idempotency_tokens_status 
ON idempotency_tokens (status);

CREATE INDEX IF NOT EXISTS ix_idempotency_tokens_expires_at 
ON idempotency_tokens (expires_at);

-- Add update trigger for distributed_locks
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_distributed_locks_modtime 
    BEFORE UPDATE ON distributed_locks 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- Add comments for documentation
COMMENT ON TABLE distributed_locks IS 'Atomic distributed locking using database unique constraints';
COMMENT ON COLUMN distributed_locks.lock_name IS 'Unique lock identifier - enforced by constraint';
COMMENT ON COLUMN distributed_locks.owner_token IS 'UUID token proving lock ownership';
COMMENT ON COLUMN distributed_locks.expires_at IS 'Lock expiration time - indexed for cleanup';

COMMENT ON TABLE idempotency_tokens IS 'Idempotency protection for critical operations';
COMMENT ON COLUMN idempotency_tokens.idempotency_key IS 'Unique operation key - enforced by constraint';
COMMENT ON COLUMN idempotency_tokens.status IS 'Operation status: processing, completed, failed';

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration completed: Added distributed_locks and idempotency_tokens tables';
    RAISE NOTICE 'Atomic locking now available for financial operations';
END $$;

COMMIT;
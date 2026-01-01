-- Migration: Add missing Cashout and User model fields
-- Created: 2025-10-06
-- Description: Add destination, bank_account_id, cashout_metadata, external_tx_id, 
--              fincra_request_id, processing_mode to Cashout table
--              Add cashout_preference to User table

-- Add missing columns to cashouts table
ALTER TABLE cashouts 
    ADD COLUMN IF NOT EXISTS destination VARCHAR(50),
    ADD COLUMN IF NOT EXISTS bank_account_id INTEGER,
    ADD COLUMN IF NOT EXISTS cashout_metadata JSONB,
    ADD COLUMN IF NOT EXISTS external_tx_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS fincra_request_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS processing_mode VARCHAR(50);

-- Add missing column to users table
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS cashout_preference VARCHAR(20);

-- Add helpful indexes for new columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashouts_destination ON cashouts(destination) WHERE destination IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashouts_bank_account_id ON cashouts(bank_account_id) WHERE bank_account_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashouts_external_tx_id ON cashouts(external_tx_id) WHERE external_tx_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cashouts_fincra_request_id ON cashouts(fincra_request_id) WHERE fincra_request_id IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_cashout_preference ON users(cashout_preference) WHERE cashout_preference IS NOT NULL;

-- Add comments to document the new fields
COMMENT ON COLUMN cashouts.destination IS 'Cashout destination type (CRYPTO, NGN_BANK)';
COMMENT ON COLUMN cashouts.bank_account_id IS 'Foreign key to bank_accounts table for NGN cashouts';
COMMENT ON COLUMN cashouts.cashout_metadata IS 'Additional metadata for cashout processing';
COMMENT ON COLUMN cashouts.external_tx_id IS 'External transaction ID from payment provider';
COMMENT ON COLUMN cashouts.fincra_request_id IS 'Fincra API request ID for NGN cashouts';
COMMENT ON COLUMN cashouts.processing_mode IS 'Processing mode (AUTO, MANUAL)';
COMMENT ON COLUMN users.cashout_preference IS 'User preferred cashout method (CRYPTO, NGN_BANK)';

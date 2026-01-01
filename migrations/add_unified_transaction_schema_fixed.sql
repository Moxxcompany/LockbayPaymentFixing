-- Database Migration: Add Unified Transaction Schema (Fixed)
-- PRODUCTION SAFE: Creates new tables without disrupting existing data
-- Date: 2025-09-12
-- Purpose: Enable unified transaction system supporting cashouts, escrows, exchanges, and deposits

-- ===================================================================
-- 1. MAIN UNIFIED TRANSACTIONS TABLE
-- ===================================================================

CREATE TABLE IF NOT EXISTS unified_transactions (
    -- Primary identification
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(20) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    
    -- Transaction classification
    transaction_type VARCHAR(25) NOT NULL CHECK (
        transaction_type IN ('wallet_cashout', 'exchange_sell_crypto', 'exchange_buy_crypto', 'escrow')
    ),
    status VARCHAR(20) NOT NULL CHECK (
        status IN ('pending', 'awaiting_payment', 'payment_confirmed', 'funds_held', 'awaiting_approval', 
                  'otp_pending', 'admin_pending', 'processing', 'awaiting_response', 'release_pending', 
                  'success', 'failed', 'cancelled', 'disputed', 'expired', 'partial_payment')
    ),
    priority VARCHAR(10) DEFAULT 'normal' NOT NULL CHECK (
        priority IN ('low', 'normal', 'high', 'urgent')
    ),
    
    -- Financial details
    amount DECIMAL(20, 8) NOT NULL CHECK (amount >= 0),
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    fee_amount DECIMAL(20, 8) DEFAULT 0 NOT NULL CHECK (fee_amount >= 0),
    total_amount DECIMAL(20, 8) NOT NULL CHECK (total_amount >= amount),
    
    -- Fund movement tracking
    fund_movement_type VARCHAR(15) NOT NULL CHECK (
        fund_movement_type IN ('hold', 'release', 'debit', 'credit', 'transfer', 'consume')
    ),
    held_amount DECIMAL(20, 8) DEFAULT 0 NOT NULL CHECK (held_amount >= 0),
    available_amount_before DECIMAL(20, 8),
    available_amount_after DECIMAL(20, 8),
    
    -- Authorization and security
    requires_otp BOOLEAN DEFAULT FALSE NOT NULL,
    otp_verified BOOLEAN DEFAULT FALSE NOT NULL,
    otp_attempts INTEGER DEFAULT 0 NOT NULL CHECK (otp_attempts >= 0),
    requires_admin_approval BOOLEAN DEFAULT FALSE NOT NULL,
    admin_approved BOOLEAN DEFAULT FALSE NOT NULL,
    admin_approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    admin_approved_at TIMESTAMP,
    
    -- Risk and compliance
    risk_score REAL DEFAULT 0.0 NOT NULL CHECK (risk_score >= 0 AND risk_score <= 1),
    compliance_checked BOOLEAN DEFAULT FALSE NOT NULL,
    compliance_flags JSONB,
    
    -- External integration
    external_reference_id VARCHAR(100),
    external_provider VARCHAR(50),
    external_metadata JSONB,
    
    -- Blockchain integration
    blockchain_tx_hash VARCHAR(200),
    blockchain_address VARCHAR(200),
    blockchain_confirmations INTEGER DEFAULT 0 NOT NULL CHECK (blockchain_confirmations >= 0),
    blockchain_network VARCHAR(50),
    
    -- Unified retry system
    retry_count INTEGER DEFAULT 0 NOT NULL CHECK (retry_count >= 0),
    max_retries INTEGER DEFAULT 3 NOT NULL CHECK (max_retries >= 0),
    next_retry_at TIMESTAMP,
    last_retry_at TIMESTAMP,
    failure_type VARCHAR(20) CHECK (failure_type IN ('technical', 'user')),
    last_error_code VARCHAR(50),
    error_message TEXT,
    technical_failure_since TIMESTAMP,
    
    -- Related entity references (only one should be set at a time)
    escrow_id VARCHAR(20),
    cashout_id VARCHAR(20),
    exchange_order_id INTEGER,
    parent_transaction_id VARCHAR(20),
    
    -- Lifecycle timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    payment_confirmed_at TIMESTAMP,
    funds_held_at TIMESTAMP,
    processing_started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_at TIMESTAMP,
    expired_at TIMESTAMP,
    
    -- Timeout and expiry management
    payment_timeout_at TIMESTAMP,
    processing_timeout_at TIMESTAMP,
    auto_expire_at TIMESTAMP,
    
    -- Audit and description
    description TEXT NOT NULL,
    internal_notes TEXT,
    user_notes TEXT,
    
    -- Business logic constraints
    CONSTRAINT chk_unified_tx_otp_only_cashout 
        CHECK ((NOT requires_otp) OR (requires_otp AND transaction_type = 'wallet_cashout')),
    CONSTRAINT chk_unified_tx_otp_verified_logic 
        CHECK ((NOT otp_verified) OR (otp_verified AND requires_otp)),
    CONSTRAINT chk_unified_tx_admin_approved_logic 
        CHECK ((NOT admin_approved) OR (admin_approved AND requires_admin_approval)),
    CONSTRAINT chk_unified_tx_single_entity_ref 
        CHECK ((escrow_id IS NULL OR (cashout_id IS NULL AND exchange_order_id IS NULL)) AND 
               (cashout_id IS NULL OR (escrow_id IS NULL AND exchange_order_id IS NULL)) AND 
               (exchange_order_id IS NULL OR (escrow_id IS NULL AND cashout_id IS NULL)))
);

-- ===================================================================
-- 2. UNIFIED TRANSACTION STATUS HISTORY TABLE
-- ===================================================================

CREATE TABLE IF NOT EXISTS unified_transaction_status_history (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(20) NOT NULL REFERENCES unified_transactions(transaction_id) ON DELETE CASCADE,
    
    -- Status change details
    from_status VARCHAR(20),
    to_status VARCHAR(20) NOT NULL,
    change_reason VARCHAR(100) NOT NULL,
    
    -- Context and metadata
    triggered_by VARCHAR(50) NOT NULL CHECK (
        triggered_by IN ('user', 'admin', 'system', 'external_api', 'scheduler', 'webhook')
    ),
    triggered_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    external_reference VARCHAR(100),
    
    -- Additional context
    change_metadata JSONB,
    error_details TEXT,
    
    -- Timing
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processing_duration_ms INTEGER CHECK (processing_duration_ms >= 0)
);

-- ===================================================================
-- 3. UNIFIED TRANSACTION RETRY LOGS TABLE
-- ===================================================================

CREATE TABLE IF NOT EXISTS unified_transaction_retry_logs (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(20) NOT NULL REFERENCES unified_transactions(transaction_id) ON DELETE CASCADE,
    
    -- Retry attempt details
    retry_attempt INTEGER NOT NULL CHECK (retry_attempt > 0),
    retry_type VARCHAR(20) NOT NULL CHECK (
        retry_type IN ('manual', 'automatic', 'scheduled', 'escalation')
    ),
    
    -- Error and failure tracking
    error_code VARCHAR(50) NOT NULL,
    error_message TEXT,
    failure_type VARCHAR(20) NOT NULL CHECK (failure_type IN ('technical', 'user')),
    
    -- Retry strategy
    retry_strategy VARCHAR(30) NOT NULL CHECK (
        retry_strategy IN ('exponential_backoff', 'fixed_interval', 'immediate', 'custom')
    ),
    backoff_multiplier REAL DEFAULT 2.0 CHECK (backoff_multiplier >= 1.0),
    base_delay_seconds INTEGER DEFAULT 300 CHECK (base_delay_seconds >= 0),
    max_delay_seconds INTEGER DEFAULT 3600 CHECK (max_delay_seconds >= base_delay_seconds),
    
    -- Execution timing
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    execution_duration_ms INTEGER CHECK (execution_duration_ms >= 0),
    next_scheduled_retry TIMESTAMP,
    
    -- Results
    retry_result VARCHAR(20) NOT NULL CHECK (
        retry_result IN ('success', 'failed', 'rescheduled', 'abandoned', 'escalated')
    ),
    result_details JSONB,
    
    -- Context
    triggered_by VARCHAR(50) NOT NULL CHECK (
        triggered_by IN ('user', 'admin', 'system', 'scheduler', 'webhook', 'manual_intervention')
    ),
    triggered_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    system_state JSONB
);

-- ===================================================================
-- 4. UNIFIED TRANSACTION METADATA TABLE
-- ===================================================================

CREATE TABLE IF NOT EXISTS unified_transaction_metadata (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(20) NOT NULL REFERENCES unified_transactions(transaction_id) ON DELETE CASCADE,
    
    -- Metadata classification
    metadata_key VARCHAR(100) NOT NULL,
    metadata_category VARCHAR(50) NOT NULL CHECK (
        metadata_category IN ('system', 'user', 'external', 'compliance', 'audit', 'integration', 'risk')
    ),
    
    -- Value and typing
    metadata_value JSONB NOT NULL,
    data_type VARCHAR(20) NOT NULL CHECK (
        data_type IN ('string', 'number', 'boolean', 'object', 'array')
    ),
    
    -- Security and access
    is_sensitive BOOLEAN DEFAULT FALSE NOT NULL,
    access_level VARCHAR(20) DEFAULT 'standard' NOT NULL CHECK (
        access_level IN ('public', 'standard', 'restricted', 'admin_only', 'system_only')
    ),
    encryption_method VARCHAR(50),
    
    -- Lifecycle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    
    -- Source tracking
    created_by_system VARCHAR(50) NOT NULL,
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    source_reference VARCHAR(100),
    
    -- Uniqueness constraint
    UNIQUE(transaction_id, metadata_key)
);

-- ===================================================================
-- 5. BASIC INDEXES (Non-concurrent for migration safety)
-- ===================================================================

-- Primary lookup indexes
CREATE INDEX IF NOT EXISTS idx_unified_tx_transaction_id 
    ON unified_transactions(transaction_id);
CREATE INDEX IF NOT EXISTS idx_unified_tx_user_id 
    ON unified_transactions(user_id);

-- Core business logic indexes
CREATE INDEX IF NOT EXISTS idx_unified_tx_user_type_status 
    ON unified_transactions(user_id, transaction_type, status);
CREATE INDEX IF NOT EXISTS idx_unified_tx_status_created 
    ON unified_transactions(status, created_at);
CREATE INDEX IF NOT EXISTS idx_unified_tx_type_status 
    ON unified_transactions(transaction_type, status);

-- External reference indexes
CREATE INDEX IF NOT EXISTS idx_unified_tx_external_ref 
    ON unified_transactions(external_reference_id) WHERE external_reference_id IS NOT NULL;

-- Retry system indexes
CREATE INDEX IF NOT EXISTS idx_unified_tx_retry_schedule 
    ON unified_transactions(next_retry_at, status) WHERE next_retry_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_unified_tx_error_code 
    ON unified_transactions(last_error_code) WHERE last_error_code IS NOT NULL;

-- Related entity indexes
CREATE INDEX IF NOT EXISTS idx_unified_tx_escrow 
    ON unified_transactions(escrow_id) WHERE escrow_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_unified_tx_cashout 
    ON unified_transactions(cashout_id) WHERE cashout_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_unified_tx_exchange 
    ON unified_transactions(exchange_order_id) WHERE exchange_order_id IS NOT NULL;

-- Status History indexes
CREATE INDEX IF NOT EXISTS idx_unified_tx_history_transaction 
    ON unified_transaction_status_history(transaction_id, changed_at);
CREATE INDEX IF NOT EXISTS idx_unified_tx_history_status 
    ON unified_transaction_status_history(to_status, changed_at);

-- Retry Logs indexes
CREATE INDEX IF NOT EXISTS idx_unified_tx_retry_transaction 
    ON unified_transaction_retry_logs(transaction_id, attempted_at);
CREATE INDEX IF NOT EXISTS idx_unified_tx_retry_error_code 
    ON unified_transaction_retry_logs(error_code, attempted_at);

-- Metadata indexes
CREATE INDEX IF NOT EXISTS idx_unified_tx_metadata_transaction 
    ON unified_transaction_metadata(transaction_id, metadata_category);
CREATE INDEX IF NOT EXISTS idx_unified_tx_metadata_key 
    ON unified_transaction_metadata(metadata_key, metadata_category);

-- ===================================================================
-- 6. FUNCTIONS AND TRIGGERS
-- ===================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_unified_tx_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at on unified_transactions
DROP TRIGGER IF EXISTS trigger_unified_tx_updated_at ON unified_transactions;
CREATE TRIGGER trigger_unified_tx_updated_at
    BEFORE UPDATE ON unified_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_unified_tx_updated_at();

-- Update timestamp trigger for metadata
DROP TRIGGER IF EXISTS trigger_unified_tx_metadata_updated_at ON unified_transaction_metadata;
CREATE TRIGGER trigger_unified_tx_metadata_updated_at
    BEFORE UPDATE ON unified_transaction_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_unified_tx_updated_at();

-- ===================================================================
-- 7. HELPFUL COMMENTS FOR DOCUMENTATION
-- ===================================================================

COMMENT ON TABLE unified_transactions IS 'Unified transaction model supporting all transaction types with standardized lifecycle';
COMMENT ON COLUMN unified_transactions.transaction_id IS 'Unique transaction identifier with format UTX + 17 chars';
COMMENT ON COLUMN unified_transactions.fund_movement_type IS 'Type of fund movement: hold, release, debit, credit, transfer, consume';
COMMENT ON COLUMN unified_transactions.requires_otp IS 'OTP required only for wallet_cashout transactions';
COMMENT ON COLUMN unified_transactions.failure_type IS 'Classification: technical (retryable) or user (refund)';
COMMENT ON COLUMN unified_transactions.risk_score IS 'Risk assessment score from 0.0 to 1.0';

COMMENT ON TABLE unified_transaction_status_history IS 'Audit trail for all status changes in unified transactions';
COMMENT ON COLUMN unified_transaction_status_history.processing_duration_ms IS 'Time spent in previous status (milliseconds)';

COMMENT ON TABLE unified_transaction_retry_logs IS 'Detailed logging for retry attempts in unified transactions';
COMMENT ON COLUMN unified_transaction_retry_logs.retry_strategy IS 'Strategy used for retry timing';

COMMENT ON TABLE unified_transaction_metadata IS 'Flexible metadata storage for unified transactions';
COMMENT ON COLUMN unified_transaction_metadata.is_sensitive IS 'Whether the metadata contains sensitive information';
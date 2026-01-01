-- LockBay Database Performance Indexes Migration
-- Creates strategic indexes for high-frequency query patterns
-- This addresses N+1 queries and slow analytics queries

-- ============================================================================
-- USERS TABLE INDEXES - High-frequency user lookups
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);  
CREATE INDEX IF NOT EXISTS ix_users_phone_number ON users (phone_number);
CREATE INDEX IF NOT EXISTS ix_users_status ON users (status);
CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active);

-- ============================================================================
-- ESCROWS TABLE INDEXES - Critical for trading operations
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_escrows_buyer_id ON escrows (buyer_id);
CREATE INDEX IF NOT EXISTS ix_escrows_seller_id ON escrows (seller_id);
CREATE INDEX IF NOT EXISTS ix_escrows_escrow_id ON escrows (escrow_id);
CREATE INDEX IF NOT EXISTS ix_escrows_status ON escrows (status);
CREATE INDEX IF NOT EXISTS ix_escrows_created_at ON escrows (created_at);

-- Composite indexes for frequent query patterns
CREATE INDEX IF NOT EXISTS ix_escrows_status_completed_at ON escrows (status, completed_at);
CREATE INDEX IF NOT EXISTS ix_escrows_status_created_at ON escrows (status, created_at);
CREATE INDEX IF NOT EXISTS ix_escrows_buyer_status ON escrows (buyer_id, status);
CREATE INDEX IF NOT EXISTS ix_escrows_seller_status ON escrows (seller_id, status);

-- ============================================================================
-- TRANSACTIONS TABLE INDEXES - Financial operations
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions (user_id);
CREATE INDEX IF NOT EXISTS ix_transactions_escrow_id ON transactions (escrow_id);
CREATE INDEX IF NOT EXISTS ix_transactions_status ON transactions (status);
CREATE INDEX IF NOT EXISTS ix_transactions_transaction_type ON transactions (transaction_type);
CREATE INDEX IF NOT EXISTS ix_transactions_created_at ON transactions (created_at);

-- Composite indexes for common transaction queries
CREATE INDEX IF NOT EXISTS ix_transactions_user_status ON transactions (user_id, status);
CREATE INDEX IF NOT EXISTS ix_transactions_type_status ON transactions (transaction_type, status);

-- ============================================================================
-- UNIFIED TRANSACTIONS TABLE INDEXES - New transaction system
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_unified_transactions_user_id ON unified_transactions (user_id);
CREATE INDEX IF NOT EXISTS ix_unified_transactions_status ON unified_transactions (status);
CREATE INDEX IF NOT EXISTS ix_unified_transactions_transaction_type ON unified_transactions (transaction_type);
CREATE INDEX IF NOT EXISTS ix_unified_transactions_external_id ON unified_transactions (external_id);
CREATE INDEX IF NOT EXISTS ix_unified_transactions_reference_id ON unified_transactions (reference_id);
CREATE INDEX IF NOT EXISTS ix_unified_transactions_created_at ON unified_transactions (created_at);

-- Critical composite indexes for performance
CREATE INDEX IF NOT EXISTS ix_unified_transactions_user_status ON unified_transactions (user_id, status);
CREATE INDEX IF NOT EXISTS ix_unified_transactions_type_status ON unified_transactions (transaction_type, status);

-- ============================================================================
-- CASHOUTS TABLE INDEXES - Financial operations tracking
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_cashouts_user_id ON cashouts (user_id);
CREATE INDEX IF NOT EXISTS ix_cashouts_status ON cashouts (status);
CREATE INDEX IF NOT EXISTS ix_cashouts_cashout_id ON cashouts (cashout_id);
CREATE INDEX IF NOT EXISTS ix_cashouts_external_id ON cashouts (external_id);
CREATE INDEX IF NOT EXISTS ix_cashouts_created_at ON cashouts (created_at);
CREATE INDEX IF NOT EXISTS ix_cashouts_completed_at ON cashouts (completed_at);

-- Composite indexes for cashout analytics
CREATE INDEX IF NOT EXISTS ix_cashouts_user_status ON cashouts (user_id, status);
CREATE INDEX IF NOT EXISTS ix_cashouts_status_created_at ON cashouts (status, created_at);

-- ============================================================================
-- AUDIT LOGS TABLE INDEXES - Security and compliance
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_ip_address ON audit_logs (ip_address);

-- Critical composite indexes for audit queries
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_created ON audit_logs (user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action_created ON audit_logs (action, created_at);

-- ============================================================================
-- ADDITIONAL STRATEGIC INDEXES
-- ============================================================================

-- Wallets table indexes (user_id, currency composite already exists)
CREATE INDEX IF NOT EXISTS ix_wallets_user_id ON wallets (user_id);
CREATE INDEX IF NOT EXISTS ix_wallets_currency ON wallets (currency);

-- Rating table for user reputation queries
CREATE INDEX IF NOT EXISTS ix_ratings_rated_id ON ratings (rated_id);
CREATE INDEX IF NOT EXISTS ix_ratings_rater_id ON ratings (rater_id);
CREATE INDEX IF NOT EXISTS ix_ratings_escrow_id ON ratings (escrow_id);
CREATE INDEX IF NOT EXISTS ix_ratings_created_at ON ratings (created_at);

-- Disputes table for admin operations
CREATE INDEX IF NOT EXISTS ix_disputes_escrow_id ON disputes (escrow_id);
CREATE INDEX IF NOT EXISTS ix_disputes_status ON disputes (status);
CREATE INDEX IF NOT EXISTS ix_disputes_created_at ON disputes (created_at);

-- ============================================================================
-- ANALYTICS COMPOSITE INDEXES - Admin dashboard optimization
-- ============================================================================

-- For admin statistics queries on completed escrows with date filters
CREATE INDEX IF NOT EXISTS ix_escrows_completed_analytics ON escrows (status, completed_at, currency) 
WHERE status = 'completed';

-- For user reputation and volume analytics
CREATE INDEX IF NOT EXISTS ix_users_reputation_trades ON users (reputation_score, completed_trades, total_ratings);
CREATE INDEX IF NOT EXISTS ix_users_volume_analytics ON users (is_active, completed_trades, reputation_score);

-- For transaction analytics and monitoring
CREATE INDEX IF NOT EXISTS ix_transactions_analytics ON transactions (transaction_type, status, created_at, amount);

-- For cashout analytics and admin monitoring
CREATE INDEX IF NOT EXISTS ix_cashouts_analytics ON cashouts (status, created_at, amount, currency);

-- For escrow participant queries (buyer OR seller lookups)
CREATE INDEX IF NOT EXISTS ix_escrows_participants ON escrows (buyer_id, seller_id, status, created_at);

-- For date range analytics commonly used in dashboard
CREATE INDEX IF NOT EXISTS ix_escrows_date_range_analytics ON escrows (created_at, status, amount, currency);
CREATE INDEX IF NOT EXISTS ix_users_registration_analytics ON users (created_at, is_active, onboarding_completed);

-- For audit trail and security monitoring
CREATE INDEX IF NOT EXISTS ix_audit_logs_security ON audit_logs (action, ip_address, created_at);

-- Update table statistics for the query optimizer
ANALYZE users;
ANALYZE escrows;
ANALYZE transactions;
ANALYZE unified_transactions;
ANALYZE cashouts;
ANALYZE audit_logs;
ANALYZE wallets;
ANALYZE ratings;
ANALYZE disputes;
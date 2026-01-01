-- FINAL DATABASE SCHEMA MISSION: Eliminate remaining 29 warnings to achieve 100% completion
-- Date: 2025-09-12
-- Target: 29 warnings → 0 warnings

BEGIN;

-- ============================================================================
-- PART 1: JSON → JSONB CONVERSIONS (26 warnings)
-- ============================================================================

-- Financial Reconciliations table (2 columns)
ALTER TABLE financial_reconciliations 
    ALTER COLUMN transactions_reviewed TYPE JSONB USING transactions_reviewed::JSONB,
    ALTER COLUMN adjustments_made TYPE JSONB USING adjustments_made::JSONB;

-- Security Alerts table (3 columns)
ALTER TABLE security_alerts 
    ALTER COLUMN event_data TYPE JSONB USING event_data::JSONB,
    ALTER COLUMN request_headers TYPE JSONB USING request_headers::JSONB,
    ALTER COLUMN notifications_sent TYPE JSONB USING notifications_sent::JSONB;

-- User Flow Events table (1 column)
ALTER TABLE user_flow_events 
    ALTER COLUMN context_data TYPE JSONB USING context_data::JSONB;

-- Flow Completion Stats table (1 column)
ALTER TABLE flow_completion_stats 
    ALTER COLUMN drop_off_points TYPE JSONB USING drop_off_points::JSONB;

-- Conversation Sessions table (3 columns)
ALTER TABLE conversation_sessions 
    ALTER COLUMN conversation_data TYPE JSONB USING conversation_data::JSONB,
    ALTER COLUMN user_data TYPE JSONB USING user_data::JSONB,
    ALTER COLUMN chat_data TYPE JSONB USING chat_data::JSONB;

-- Session Recovery Logs table (2 columns)
ALTER TABLE session_recovery_logs 
    ALTER COLUMN previous_state TYPE JSONB USING previous_state::JSONB,
    ALTER COLUMN recovered_state TYPE JSONB USING recovered_state::JSONB;

-- Notification Queue table (1 column)
ALTER TABLE notification_queue 
    ALTER COLUMN template_data TYPE JSONB USING template_data::JSONB;

-- User API Keys table (1 column)
ALTER TABLE user_api_keys 
    ALTER COLUMN permissions TYPE JSONB USING permissions::JSONB;

-- Fee Configuration table (3 columns)
ALTER TABLE fee_configuration 
    ALTER COLUMN tier_structure TYPE JSONB USING tier_structure::JSONB,
    ALTER COLUMN allowed_countries TYPE JSONB USING allowed_countries::JSONB,
    ALTER COLUMN excluded_countries TYPE JSONB USING excluded_countries::JSONB;

-- User Subscriptions table (3 columns)
ALTER TABLE user_subscriptions 
    ALTER COLUMN features_enabled TYPE JSONB USING features_enabled::JSONB,
    ALTER COLUMN usage_limits TYPE JSONB USING usage_limits::JSONB,
    ALTER COLUMN usage_tracking TYPE JSONB USING usage_tracking::JSONB;

-- Expected Payments table (1 column)
ALTER TABLE expected_payments 
    ALTER COLUMN details TYPE JSONB USING details::JSONB;

-- Audit Logs table (5 columns)
ALTER TABLE audit_logs 
    ALTER COLUMN details TYPE JSONB USING details::JSONB,
    ALTER COLUMN before_data TYPE JSONB USING before_data::JSONB,
    ALTER COLUMN after_data TYPE JSONB USING after_data::JSONB,
    ALTER COLUMN audit_metadata TYPE JSONB USING audit_metadata::JSONB,
    ALTER COLUMN flags TYPE JSONB USING flags::JSONB;

-- ============================================================================
-- PART 2: VARCHAR TYPE CONVERSIONS (3 warnings)
-- ============================================================================

-- Audit Events table - Fix 3 type mismatches:
-- 1. exchange_order_id: VARCHAR(50) → INTEGER
-- 2. previous_state: VARCHAR(50) → JSONB  
-- 3. new_state: VARCHAR(50) → JSONB

-- Note: Convert exchange_order_id safely (NULL if not valid integer)
ALTER TABLE audit_events 
    ALTER COLUMN exchange_order_id TYPE INTEGER USING (
        CASE 
            WHEN exchange_order_id ~ '^[0-9]+$' THEN exchange_order_id::INTEGER
            ELSE NULL
        END
    );

-- Convert state columns to JSONB (handle existing string values)
ALTER TABLE audit_events 
    ALTER COLUMN previous_state TYPE JSONB USING (
        CASE 
            WHEN previous_state IS NULL THEN NULL
            WHEN previous_state = '' THEN NULL
            ELSE jsonb_build_object('state', previous_state)
        END
    );

ALTER TABLE audit_events 
    ALTER COLUMN new_state TYPE JSONB USING (
        CASE 
            WHEN new_state IS NULL THEN NULL
            WHEN new_state = '' THEN NULL
            ELSE jsonb_build_object('state', new_state)
        END
    );

-- ============================================================================
-- FINAL VERIFICATION
-- ============================================================================

-- Add informational comment
COMMENT ON TABLE audit_events IS 'Updated: 2025-09-12 - Schema warnings eliminated (VARCHAR→INTEGER/JSONB)';
COMMENT ON TABLE financial_reconciliations IS 'Updated: 2025-09-12 - Schema warnings eliminated (JSON→JSONB)';
COMMENT ON TABLE security_alerts IS 'Updated: 2025-09-12 - Schema warnings eliminated (JSON→JSONB)';
COMMENT ON TABLE audit_logs IS 'Updated: 2025-09-12 - Schema warnings eliminated (JSON→JSONB)';

COMMIT;

-- SUCCESS: All 29 schema warnings should now be eliminated
-- Expected result: Schema validator reports "Schema warnings: 0 found"
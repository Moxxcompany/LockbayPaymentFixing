-- Migration: Add Duration Validation Constraints
-- Purpose: Prevent negative duration values from being stored in the database
-- Created: 2025-09-13

-- Add check constraints to ensure all duration fields are non-negative

-- 1. Completion time records
ALTER TABLE completion_time_records 
ADD CONSTRAINT check_completion_time_non_negative 
CHECK (completion_time_ms >= 0);

-- 2. Completion time trends
ALTER TABLE completion_time_trends 
ADD CONSTRAINT check_avg_completion_time_non_negative 
CHECK (avg_completion_time_ms >= 0),
ADD CONSTRAINT check_baseline_avg_non_negative 
CHECK (baseline_avg_ms >= 0),
ADD CONSTRAINT check_min_completion_time_non_negative 
CHECK (min_completion_time_ms >= 0),
ADD CONSTRAINT check_max_completion_time_non_negative 
CHECK (max_completion_time_ms >= 0),
ADD CONSTRAINT check_median_completion_time_non_negative 
CHECK (median_completion_time_ms >= 0),
ADD CONSTRAINT check_p95_completion_time_non_negative 
CHECK (p95_completion_time_ms >= 0),
ADD CONSTRAINT check_p99_completion_time_non_negative 
CHECK (p99_completion_time_ms >= 0);

-- 3. Job executions
ALTER TABLE job_executions 
ADD CONSTRAINT check_job_duration_non_negative 
CHECK (duration_ms >= 0);

-- 4. User flow events
ALTER TABLE user_flow_events 
ADD CONSTRAINT check_step_duration_non_negative 
CHECK (step_duration_ms >= 0),
ADD CONSTRAINT check_total_flow_duration_non_negative 
CHECK (total_flow_duration_ms >= 0);

-- 5. Unified transaction retry logs
ALTER TABLE unified_transaction_retry_logs 
ADD CONSTRAINT check_retry_duration_non_negative 
CHECK (duration_ms >= 0);

-- 6. Unified transaction status history
ALTER TABLE unified_transaction_status_history 
ADD CONSTRAINT check_processing_duration_non_negative 
CHECK (processing_duration_ms >= 0);

-- 7. Session recovery logs
ALTER TABLE session_recovery_logs 
ADD CONSTRAINT check_recovery_time_non_negative 
CHECK (recovery_time_ms >= 0);

-- 8. Flow completion stats
ALTER TABLE flow_completion_stats 
ADD CONSTRAINT check_avg_flow_completion_non_negative 
CHECK (avg_completion_time_ms >= 0),
ADD CONSTRAINT check_median_flow_completion_non_negative 
CHECK (median_completion_time_ms >= 0);

-- Create a function to validate and fix existing negative durations
CREATE OR REPLACE FUNCTION fix_negative_durations() 
RETURNS TABLE(
    table_name TEXT,
    column_name TEXT,
    records_fixed INTEGER,
    min_value_before NUMERIC,
    min_value_after NUMERIC
) AS $$
DECLARE
    fix_count INTEGER;
    min_before NUMERIC;
    min_after NUMERIC;
BEGIN
    -- Fix completion_time_records
    SELECT MIN(completion_time_ms) INTO min_before FROM completion_time_records;
    UPDATE completion_time_records SET completion_time_ms = 0 WHERE completion_time_ms < 0;
    GET DIAGNOSTICS fix_count = ROW_COUNT;
    SELECT MIN(completion_time_ms) INTO min_after FROM completion_time_records;
    
    IF fix_count > 0 THEN
        RETURN QUERY SELECT 'completion_time_records'::TEXT, 'completion_time_ms'::TEXT, 
                          fix_count, min_before, min_after;
    END IF;
    
    -- Fix job_executions
    SELECT MIN(duration_ms) INTO min_before FROM job_executions;
    UPDATE job_executions SET duration_ms = 0 WHERE duration_ms < 0;
    GET DIAGNOSTICS fix_count = ROW_COUNT;
    SELECT MIN(duration_ms) INTO min_after FROM job_executions;
    
    IF fix_count > 0 THEN
        RETURN QUERY SELECT 'job_executions'::TEXT, 'duration_ms'::TEXT, 
                          fix_count, min_before, min_after;
    END IF;
    
    -- Fix user_flow_events
    SELECT MIN(step_duration_ms) INTO min_before FROM user_flow_events;
    UPDATE user_flow_events SET step_duration_ms = 0 WHERE step_duration_ms < 0;
    GET DIAGNOSTICS fix_count = ROW_COUNT;
    SELECT MIN(step_duration_ms) INTO min_after FROM user_flow_events;
    
    IF fix_count > 0 THEN
        RETURN QUERY SELECT 'user_flow_events'::TEXT, 'step_duration_ms'::TEXT, 
                          fix_count, min_before, min_after;
    END IF;
    
    SELECT MIN(total_flow_duration_ms) INTO min_before FROM user_flow_events;
    UPDATE user_flow_events SET total_flow_duration_ms = 0 WHERE total_flow_duration_ms < 0;
    GET DIAGNOSTICS fix_count = ROW_COUNT;
    SELECT MIN(total_flow_duration_ms) INTO min_after FROM user_flow_events;
    
    IF fix_count > 0 THEN
        RETURN QUERY SELECT 'user_flow_events'::TEXT, 'total_flow_duration_ms'::TEXT, 
                          fix_count, min_before, min_after;
    END IF;
    
    -- Fix unified_transaction_retry_logs
    SELECT MIN(duration_ms) INTO min_before FROM unified_transaction_retry_logs;
    UPDATE unified_transaction_retry_logs SET duration_ms = 0 WHERE duration_ms < 0;
    GET DIAGNOSTICS fix_count = ROW_COUNT;
    SELECT MIN(duration_ms) INTO min_after FROM unified_transaction_retry_logs;
    
    IF fix_count > 0 THEN
        RETURN QUERY SELECT 'unified_transaction_retry_logs'::TEXT, 'duration_ms'::TEXT, 
                          fix_count, min_before, min_after;
    END IF;
    
    -- Fix unified_transaction_status_history
    SELECT MIN(processing_duration_ms) INTO min_before FROM unified_transaction_status_history;
    UPDATE unified_transaction_status_history SET processing_duration_ms = 0 WHERE processing_duration_ms < 0;
    GET DIAGNOSTICS fix_count = ROW_COUNT;
    SELECT MIN(processing_duration_ms) INTO min_after FROM unified_transaction_status_history;
    
    IF fix_count > 0 THEN
        RETURN QUERY SELECT 'unified_transaction_status_history'::TEXT, 'processing_duration_ms'::TEXT, 
                          fix_count, min_before, min_after;
    END IF;
    
    -- Fix session_recovery_logs
    SELECT MIN(recovery_time_ms) INTO min_before FROM session_recovery_logs;
    UPDATE session_recovery_logs SET recovery_time_ms = 0 WHERE recovery_time_ms < 0;
    GET DIAGNOSTICS fix_count = ROW_COUNT;
    SELECT MIN(recovery_time_ms) INTO min_after FROM session_recovery_logs;
    
    IF fix_count > 0 THEN
        RETURN QUERY SELECT 'session_recovery_logs'::TEXT, 'recovery_time_ms'::TEXT, 
                          fix_count, min_before, min_after;
    END IF;
    
    -- Fix flow_completion_stats
    SELECT MIN(avg_completion_time_ms) INTO min_before FROM flow_completion_stats;
    UPDATE flow_completion_stats SET avg_completion_time_ms = 0 WHERE avg_completion_time_ms < 0;
    GET DIAGNOSTICS fix_count = ROW_COUNT;
    
    IF fix_count > 0 THEN
        RETURN QUERY SELECT 'flow_completion_stats'::TEXT, 'avg_completion_time_ms'::TEXT, 
                          fix_count, min_before, 0;
    END IF;
    
    UPDATE flow_completion_stats SET median_completion_time_ms = 0 WHERE median_completion_time_ms < 0;
    GET DIAGNOSTICS fix_count = ROW_COUNT;
    
    IF fix_count > 0 THEN
        RETURN QUERY SELECT 'flow_completion_stats'::TEXT, 'median_completion_time_ms'::TEXT, 
                          fix_count, min_before, 0;
    END IF;
    
END;
$$ LANGUAGE plpgsql;

-- Execute the function to fix any existing negative durations
SELECT * FROM fix_negative_durations();

-- Drop the function after use
DROP FUNCTION fix_negative_durations();

-- Add comments to document the constraints
COMMENT ON CONSTRAINT check_completion_time_non_negative ON completion_time_records 
IS 'Ensures completion times are non-negative to prevent timing calculation errors';

COMMENT ON CONSTRAINT check_job_duration_non_negative ON job_executions 
IS 'Ensures job execution durations are non-negative to prevent timing calculation errors';

-- Create an index for performance monitoring queries
CREATE INDEX IF NOT EXISTS idx_completion_time_records_timing_analysis 
ON completion_time_records (operation_type, operation_name, timestamp DESC, completion_time_ms);

-- Log successful migration
INSERT INTO schema_migrations (migration_name, applied_at) 
VALUES ('add_duration_validation_constraints', CURRENT_TIMESTAMP)
ON CONFLICT (migration_name) DO NOTHING;
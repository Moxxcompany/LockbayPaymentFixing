-- Migration: Fix user_id integer out of range issue
-- Problem: Telegram user IDs exceed 32-bit integer range
-- Solution: Change users.id and all user_id foreign keys to bigint

-- This migration must be run during maintenance window due to schema changes
BEGIN;

-- Step 1: Create temporary sequence for user IDs if needed
-- (PostgreSQL will automatically handle sequence conversion)

-- Step 2: Drop all foreign key constraints temporarily
-- This allows us to modify the primary key and then recreate foreign keys

DO $$
DECLARE
    r RECORD;
BEGIN
    -- Drop all foreign key constraints referencing users.id
    FOR r IN (
        SELECT tc.table_name, tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND rc.unique_constraint_name IN (
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'users' AND constraint_type = 'PRIMARY KEY'
        )
    )
    LOOP
        EXECUTE format('ALTER TABLE %I DROP CONSTRAINT %I', r.table_name, r.constraint_name);
        RAISE NOTICE 'Dropped FK constraint %s on table %s', r.constraint_name, r.table_name;
    END LOOP;
END $$;

-- Step 3: Change users.id from integer to bigint
ALTER TABLE users ALTER COLUMN id TYPE bigint;
RAISE NOTICE 'Changed users.id to bigint';

-- Step 4: Change all user_id columns from integer to bigint
-- (Found 42 tables with user_id integer columns)

ALTER TABLE audit_events ALTER COLUMN user_id TYPE bigint;
ALTER TABLE audit_logs ALTER COLUMN user_id TYPE bigint;
ALTER TABLE balance_protection_logs ALTER COLUMN user_id TYPE bigint;
ALTER TABLE cashouts ALTER COLUMN user_id TYPE bigint;
ALTER TABLE completion_time_records ALTER COLUMN user_id TYPE bigint;
ALTER TABLE conversation_sessions ALTER COLUMN user_id TYPE bigint;
ALTER TABLE direct_exchanges ALTER COLUMN user_id TYPE bigint;
ALTER TABLE distributed_locks ALTER COLUMN user_id TYPE bigint;
ALTER TABLE distributed_rate_locks ALTER COLUMN user_id TYPE bigint;
ALTER TABLE email_verifications ALTER COLUMN user_id TYPE bigint;
ALTER TABLE exchange_transactions ALTER COLUMN user_id TYPE bigint;
ALTER TABLE expected_payments ALTER COLUMN user_id TYPE bigint;
ALTER TABLE idempotency_keys ALTER COLUMN user_id TYPE bigint;
ALTER TABLE mobile_verifications ALTER COLUMN user_id TYPE bigint;
ALTER TABLE notification_activities ALTER COLUMN user_id TYPE bigint;
ALTER TABLE notification_preferences ALTER COLUMN user_id TYPE bigint;
ALTER TABLE notification_queue ALTER COLUMN user_id TYPE bigint;
ALTER TABLE onboarding_sessions ALTER COLUMN user_id TYPE bigint;
ALTER TABLE otp_verifications ALTER COLUMN user_id TYPE bigint;
ALTER TABLE outbox_events ALTER COLUMN user_id TYPE bigint;
ALTER TABLE payment_attempts ALTER COLUMN user_id TYPE bigint;
ALTER TABLE referral_fraud_alerts ALTER COLUMN user_id TYPE bigint;
ALTER TABLE refunds ALTER COLUMN user_id TYPE bigint;
ALTER TABLE saved_addresses ALTER COLUMN user_id TYPE bigint;
ALTER TABLE saved_bank_accounts ALTER COLUMN user_id TYPE bigint;
ALTER TABLE security_alerts ALTER COLUMN user_id TYPE bigint;
ALTER TABLE security_audits ALTER COLUMN user_id TYPE bigint;
ALTER TABLE session_recovery_logs ALTER COLUMN user_id TYPE bigint;
ALTER TABLE session_registry ALTER COLUMN user_id TYPE bigint;
ALTER TABLE support_tickets ALTER COLUMN user_id TYPE bigint;
ALTER TABLE transactions ALTER COLUMN user_id TYPE bigint;
ALTER TABLE unified_transactions ALTER COLUMN user_id TYPE bigint;
ALTER TABLE user_achievements ALTER COLUMN user_id TYPE bigint;
ALTER TABLE user_api_keys ALTER COLUMN user_id TYPE bigint;
ALTER TABLE user_contacts ALTER COLUMN user_id TYPE bigint;
ALTER TABLE user_earnings ALTER COLUMN user_id TYPE bigint;
ALTER TABLE user_sms_usage ALTER COLUMN user_id TYPE bigint;
ALTER TABLE user_streak_tracking ALTER COLUMN user_id TYPE bigint;
ALTER TABLE user_subscriptions ALTER COLUMN user_id TYPE bigint;
ALTER TABLE wallet_holds ALTER COLUMN user_id TYPE bigint;
ALTER TABLE wallets ALTER COLUMN user_id TYPE bigint;

RAISE NOTICE 'Changed all user_id columns to bigint';

-- Step 5: Change other user ID related columns that might store large values
-- Check for other columns that might store Telegram user IDs

-- Update referred_by column in users table (stores user IDs)
ALTER TABLE users ALTER COLUMN referred_by TYPE bigint;

-- Update any other columns that might store Telegram user IDs directly
-- Check for telegram_user_id, telegram_id columns that might be stored as integers

DO $$
DECLARE
    r RECORD;
BEGIN
    -- Find columns that might store telegram user IDs as integers
    FOR r IN (
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE data_type = 'integer' 
        AND (column_name LIKE '%telegram%' OR column_name LIKE '%user_telegram%')
        AND table_schema = 'public'
    )
    LOOP
        -- Skip the telegram_id in users table as it's already a varchar
        IF NOT (r.table_name = 'users' AND r.column_name = 'telegram_id') THEN
            EXECUTE format('ALTER TABLE %I ALTER COLUMN %I TYPE bigint', r.table_name, r.column_name);
            RAISE NOTICE 'Changed %s.%s to bigint', r.table_name, r.column_name;
        END IF;
    END LOOP;
END $$;

-- Step 6: Recreate all foreign key constraints with bigint references
DO $$
DECLARE
    constraint_sql TEXT;
BEGIN
    -- Recreate foreign key constraints for all tables
    -- audit_events
    ALTER TABLE audit_events ADD CONSTRAINT fk_audit_events_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- cashouts
    ALTER TABLE cashouts ADD CONSTRAINT fk_cashouts_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- direct_exchanges  
    ALTER TABLE direct_exchanges ADD CONSTRAINT fk_direct_exchanges_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- email_verifications
    ALTER TABLE email_verifications ADD CONSTRAINT fk_email_verifications_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- exchange_transactions
    ALTER TABLE exchange_transactions ADD CONSTRAINT fk_exchange_transactions_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- expected_payments
    ALTER TABLE expected_payments ADD CONSTRAINT fk_expected_payments_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- mobile_verifications
    ALTER TABLE mobile_verifications ADD CONSTRAINT fk_mobile_verifications_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- notification_activities
    ALTER TABLE notification_activities ADD CONSTRAINT fk_notification_activities_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- notification_preferences
    ALTER TABLE notification_preferences ADD CONSTRAINT fk_notification_preferences_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- notification_queue
    ALTER TABLE notification_queue ADD CONSTRAINT fk_notification_queue_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- otp_verifications
    ALTER TABLE otp_verifications ADD CONSTRAINT fk_otp_verifications_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- outbox_events
    ALTER TABLE outbox_events ADD CONSTRAINT fk_outbox_events_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- refunds
    ALTER TABLE refunds ADD CONSTRAINT fk_refunds_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- saved_addresses
    ALTER TABLE saved_addresses ADD CONSTRAINT fk_saved_addresses_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- saved_bank_accounts
    ALTER TABLE saved_bank_accounts ADD CONSTRAINT fk_saved_bank_accounts_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- support_tickets
    ALTER TABLE support_tickets ADD CONSTRAINT fk_support_tickets_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- transactions
    ALTER TABLE transactions ADD CONSTRAINT fk_transactions_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- unified_transactions
    ALTER TABLE unified_transactions ADD CONSTRAINT fk_unified_transactions_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- user_achievements
    ALTER TABLE user_achievements ADD CONSTRAINT fk_user_achievements_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- user_api_keys
    ALTER TABLE user_api_keys ADD CONSTRAINT fk_user_api_keys_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- user_contacts
    ALTER TABLE user_contacts ADD CONSTRAINT fk_user_contacts_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- user_earnings
    ALTER TABLE user_earnings ADD CONSTRAINT fk_user_earnings_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- user_sms_usage
    ALTER TABLE user_sms_usage ADD CONSTRAINT fk_user_sms_usage_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- user_streak_tracking
    ALTER TABLE user_streak_tracking ADD CONSTRAINT fk_user_streak_tracking_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- user_subscriptions
    ALTER TABLE user_subscriptions ADD CONSTRAINT fk_user_subscriptions_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- wallet_holds
    ALTER TABLE wallet_holds ADD CONSTRAINT fk_wallet_holds_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- wallets
    ALTER TABLE wallets ADD CONSTRAINT fk_wallets_user_id 
        FOREIGN KEY (user_id) REFERENCES users(id);
    
    -- users self-referential FK for referred_by
    ALTER TABLE users ADD CONSTRAINT fk_users_referred_by 
        FOREIGN KEY (referred_by) REFERENCES users(id);

    RAISE NOTICE 'Recreated all foreign key constraints with bigint references';
END $$;

-- Step 7: Update session-related tables if they exist
-- Check for user_sessions table from session_models.py
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_sessions') THEN
        ALTER TABLE user_sessions ALTER COLUMN user_id TYPE bigint;
        RAISE NOTICE 'Updated user_sessions.user_id to bigint';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversation_contexts') THEN
        ALTER TABLE conversation_contexts ALTER COLUMN user_id TYPE bigint;
        RAISE NOTICE 'Updated conversation_contexts.user_id to bigint';
    END IF;
END $$;

-- Step 8: Verify the migration
DO $$
DECLARE
    integer_user_id_count INTEGER;
    bigint_user_id_count INTEGER;
BEGIN
    -- Count remaining integer user_id columns
    SELECT COUNT(*) INTO integer_user_id_count
    FROM information_schema.columns 
    WHERE column_name = 'user_id' 
    AND data_type = 'integer'
    AND table_schema = 'public';
    
    -- Count bigint user_id columns
    SELECT COUNT(*) INTO bigint_user_id_count
    FROM information_schema.columns 
    WHERE column_name = 'user_id' 
    AND data_type = 'bigint'
    AND table_schema = 'public';
    
    RAISE NOTICE 'Migration verification:';
    RAISE NOTICE '  Remaining integer user_id columns: %', integer_user_id_count;
    RAISE NOTICE '  Total bigint user_id columns: %', bigint_user_id_count;
    
    IF integer_user_id_count > 0 THEN
        RAISE EXCEPTION 'Migration incomplete: % integer user_id columns remain', integer_user_id_count;
    END IF;
END $$;

COMMIT;

-- Final success message
SELECT 'Migration completed successfully: All user_id columns converted from integer to bigint' AS result;
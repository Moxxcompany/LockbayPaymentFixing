-- Migration: Upgrade auxiliary tables from Numeric(20, 8) to Numeric(38, 18)
-- Date: 2025-10-18
-- Purpose: Ensure all monetary columns have consistent bank-grade precision

-- SAFE: Expanding precision from (20, 8) to (38, 18) is non-destructive
-- Existing data will be preserved without loss

BEGIN;

-- 1. PendingCashout table
ALTER TABLE pending_cashouts 
    ALTER COLUMN amount TYPE numeric(38, 18),
    ALTER COLUMN fee_amount TYPE numeric(38, 18),
    ALTER COLUMN net_amount TYPE numeric(38, 18);

-- 2. ExchangeOrder table
ALTER TABLE exchange_orders
    ALTER COLUMN source_amount TYPE numeric(38, 18),
    ALTER COLUMN target_amount TYPE numeric(38, 18),
    ALTER COLUMN exchange_rate TYPE numeric(38, 18),
    ALTER COLUMN fee_amount TYPE numeric(38, 18),
    ALTER COLUMN final_amount TYPE numeric(38, 18),
    ALTER COLUMN usd_equivalent TYPE numeric(38, 18);

-- 3. PlatformRevenue table
ALTER TABLE platform_revenue
    ALTER COLUMN fee_amount TYPE numeric(38, 18);

-- 4. InternalWallet table
ALTER TABLE internal_wallets
    ALTER COLUMN available_balance TYPE numeric(38, 18),
    ALTER COLUMN locked_balance TYPE numeric(38, 18),
    ALTER COLUMN reserved_balance TYPE numeric(38, 18),
    ALTER COLUMN total_balance TYPE numeric(38, 18),
    ALTER COLUMN minimum_balance TYPE numeric(38, 18),
    ALTER COLUMN withdrawal_limit TYPE numeric(38, 18),
    ALTER COLUMN daily_limit TYPE numeric(38, 18);

-- 5. WalletBalanceSnapshot table
ALTER TABLE wallet_balance_snapshots
    ALTER COLUMN available_balance TYPE numeric(38, 18),
    ALTER COLUMN frozen_balance TYPE numeric(38, 18),
    ALTER COLUMN locked_balance TYPE numeric(38, 18),
    ALTER COLUMN reserved_balance TYPE numeric(38, 18),
    ALTER COLUMN total_balance TYPE numeric(38, 18);

-- 6. CryptoDeposit table
ALTER TABLE crypto_deposits
    ALTER COLUMN amount TYPE numeric(38, 18),
    ALTER COLUMN amount_fiat TYPE numeric(38, 18);

-- 7. BalanceProtectionLog table
ALTER TABLE balance_protection_logs
    ALTER COLUMN amount TYPE numeric(38, 18);

COMMIT;

-- Verification queries (run these to confirm changes)
-- SELECT 
--     table_name,
--     column_name,
--     data_type,
--     numeric_precision,
--     numeric_scale
-- FROM information_schema.columns
-- WHERE table_name IN ('pending_cashouts', 'exchange_orders', 'platform_revenue', 
--                      'internal_wallets', 'wallet_balance_snapshots', 
--                      'crypto_deposits', 'balance_protection_logs')
--   AND numeric_precision IS NOT NULL
-- ORDER BY table_name, column_name;

-- Migration: create_balance_alert_state
-- Created: 2025-09-17T06:24:00.000Z
-- Description: Create Balance Alert State Table For BalanceGuard Cooldown Tracking

-- Create balance_alert_state table for BalanceGuard system
-- This table provides granular cooldown tracking by provider+currency+alert_level
-- Unlike the generic AlertCooldown table, this supports multiple alert types per service
CREATE TABLE IF NOT EXISTS balance_alert_state (
    id SERIAL PRIMARY KEY,
    alert_key VARCHAR(200) UNIQUE NOT NULL,  -- e.g. "fincra_NGN_WARNING", "kraken_USD_CRITICAL"
    provider VARCHAR(50) NOT NULL,           -- "fincra", "kraken"
    currency VARCHAR(10) NOT NULL,           -- "NGN", "USD", "BTC", etc.
    alert_level VARCHAR(50) NOT NULL,        -- "WARNING", "CRITICAL", "EMERGENCY", "OPERATIONAL_DANGER"
    last_alert_time TIMESTAMP WITH TIME ZONE NOT NULL,
    alert_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_balance_alert_state_alert_key ON balance_alert_state(alert_key);
CREATE INDEX IF NOT EXISTS idx_balance_alert_state_provider ON balance_alert_state(provider);
CREATE INDEX IF NOT EXISTS idx_balance_alert_state_currency ON balance_alert_state(currency);
CREATE INDEX IF NOT EXISTS idx_balance_alert_state_alert_level ON balance_alert_state(alert_level);
CREATE INDEX IF NOT EXISTS idx_balance_alert_state_last_alert ON balance_alert_state(last_alert_time);
CREATE INDEX IF NOT EXISTS idx_balance_alert_state_provider_currency ON balance_alert_state(provider, currency);

-- Add updated_at trigger for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_balance_alert_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_balance_alert_state_updated_at ON balance_alert_state;
CREATE TRIGGER trigger_update_balance_alert_state_updated_at
    BEFORE UPDATE ON balance_alert_state
    FOR EACH ROW
    EXECUTE FUNCTION update_balance_alert_state_updated_at();

-- Add comment for documentation
COMMENT ON TABLE balance_alert_state IS 'BalanceGuard cooldown tracking for preventing duplicate alerts by provider+currency+level';
COMMENT ON COLUMN balance_alert_state.alert_key IS 'Unique composite key: provider_currency_level (e.g. fincra_NGN_WARNING)';
COMMENT ON COLUMN balance_alert_state.alert_count IS 'Total number of alerts sent for this specific key';
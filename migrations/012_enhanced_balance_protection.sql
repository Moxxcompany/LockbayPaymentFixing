-- Enhanced Balance Protection System Migration
-- Creates tables and indexes for comprehensive balance monitoring and protection

-- Enhanced alert cooldowns table for multi-tier balance alerts
CREATE TABLE IF NOT EXISTS enhanced_alert_cooldowns (
    id SERIAL PRIMARY KEY,
    alert_key VARCHAR(100) UNIQUE NOT NULL, -- service_currency_alertlevel (e.g., fincra_NGN_critical)
    service VARCHAR(50) NOT NULL, -- fincra, kraken
    currency VARCHAR(10) NOT NULL, -- NGN, BTC, ETH, etc.
    alert_level VARCHAR(20) NOT NULL, -- warning, critical, emergency, operational_danger
    last_alert_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient alert cooldown lookups
CREATE INDEX IF NOT EXISTS idx_enhanced_alert_cooldowns_alert_key ON enhanced_alert_cooldowns(alert_key);
CREATE INDEX IF NOT EXISTS idx_enhanced_alert_cooldowns_service_currency ON enhanced_alert_cooldowns(service, currency);
CREATE INDEX IF NOT EXISTS idx_enhanced_alert_cooldowns_alert_level ON enhanced_alert_cooldowns(alert_level);
CREATE INDEX IF NOT EXISTS idx_enhanced_alert_cooldowns_last_alert_time ON enhanced_alert_cooldowns(last_alert_time);

-- Balance protection log table for audit trail
CREATE TABLE IF NOT EXISTS balance_protection_logs (
    id SERIAL PRIMARY KEY,
    operation_type VARCHAR(50) NOT NULL, -- cashout, withdrawal, transfer
    currency VARCHAR(10) NOT NULL,
    amount DECIMAL(20, 8) NOT NULL,
    user_id INTEGER,
    operation_allowed BOOLEAN NOT NULL,
    alert_level VARCHAR(20), -- NULL if healthy, otherwise warning/critical/emergency/operational_danger
    balance_check_passed BOOLEAN NOT NULL,
    insufficient_services TEXT[], -- Array of services with insufficient balances
    warning_message TEXT,
    blocking_reason TEXT,
    fincra_balance DECIMAL(15, 2),
    kraken_balances JSONB, -- Store kraken balances as JSON for all currencies
    protection_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for balance protection logs
CREATE INDEX IF NOT EXISTS idx_balance_protection_logs_operation_type ON balance_protection_logs(operation_type);
CREATE INDEX IF NOT EXISTS idx_balance_protection_logs_currency ON balance_protection_logs(currency);
CREATE INDEX IF NOT EXISTS idx_balance_protection_logs_user_id ON balance_protection_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_balance_protection_logs_operation_allowed ON balance_protection_logs(operation_allowed);
CREATE INDEX IF NOT EXISTS idx_balance_protection_logs_alert_level ON balance_protection_logs(alert_level);
CREATE INDEX IF NOT EXISTS idx_balance_protection_logs_timestamp ON balance_protection_logs(protection_timestamp);

-- Balance threshold configuration table for dynamic threshold management
CREATE TABLE IF NOT EXISTS balance_threshold_config (
    id SERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL, -- fincra, kraken
    currency VARCHAR(10) NOT NULL, -- NGN, USD (for kraken equivalents)
    base_threshold DECIMAL(20, 8) NOT NULL,
    warning_threshold DECIMAL(20, 8) NOT NULL, -- 75% of base
    critical_threshold DECIMAL(20, 8) NOT NULL, -- 50% of base
    emergency_threshold DECIMAL(20, 8) NOT NULL, -- 25% of base
    operational_minimum DECIMAL(20, 8) NOT NULL, -- 10% of base - blocks operations
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(service, currency)
);

-- Insert default threshold configurations
INSERT INTO balance_threshold_config (service, currency, base_threshold, warning_threshold, critical_threshold, emergency_threshold, operational_minimum)
VALUES 
    ('fincra', 'NGN', 100000.0, 75000.0, 50000.0, 25000.0, 10000.0),
    ('kraken', 'USD', 1000.0, 750.0, 500.0, 250.0, 100.0)
ON CONFLICT (service, currency) DO NOTHING;

-- Balance monitoring summary table for dashboard and reporting
CREATE TABLE IF NOT EXISTS balance_monitoring_summary (
    id SERIAL PRIMARY KEY,
    check_timestamp TIMESTAMP NOT NULL,
    overall_status VARCHAR(20) NOT NULL, -- healthy, warning, critical, emergency
    services_operational INTEGER DEFAULT 0,
    services_warning INTEGER DEFAULT 0,
    services_critical INTEGER DEFAULT 0,
    services_emergency INTEGER DEFAULT 0,
    services_blocked INTEGER DEFAULT 0,
    alerts_sent INTEGER DEFAULT 0,
    fincra_status JSONB, -- Fincra status details
    kraken_status JSONB, -- Kraken status details
    protection_summary JSONB, -- Overall protection summary
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for balance monitoring summary
CREATE INDEX IF NOT EXISTS idx_balance_monitoring_summary_timestamp ON balance_monitoring_summary(check_timestamp);
CREATE INDEX IF NOT EXISTS idx_balance_monitoring_summary_status ON balance_monitoring_summary(overall_status);

-- Add comments for documentation
COMMENT ON TABLE enhanced_alert_cooldowns IS 'Cooldown tracking for enhanced multi-tier balance alerts';
COMMENT ON TABLE balance_protection_logs IS 'Audit log for balance protection decisions on financial operations';
COMMENT ON TABLE balance_threshold_config IS 'Configuration table for dynamic balance threshold management';
COMMENT ON TABLE balance_monitoring_summary IS 'Summary table for balance monitoring dashboard and reporting';

-- Create function for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_enhanced_alert_cooldowns_updated_at BEFORE UPDATE ON enhanced_alert_cooldowns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_balance_threshold_config_updated_at BEFORE UPDATE ON balance_threshold_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
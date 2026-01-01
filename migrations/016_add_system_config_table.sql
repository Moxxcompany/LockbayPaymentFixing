-- Migration 016: Add System Configuration Table for Maintenance Mode and Other System Settings
-- Created: 2025-10-16
-- Purpose: Create persistent storage for system-wide configuration including maintenance mode

-- Create system_config table for runtime configuration
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(key);

-- Insert default maintenance mode setting
INSERT INTO system_config (key, value, description, updated_by)
VALUES ('maintenance_mode', 'false', 'Global maintenance mode - when true, only admins can access the bot', NULL)
ON CONFLICT (key) DO NOTHING;

-- Insert other useful system config defaults
INSERT INTO system_config (key, value, description, updated_by)
VALUES ('maintenance_message', 'System maintenance in progress. We''ll be back shortly!', 'Message shown to users during maintenance mode', NULL)
ON CONFLICT (key) DO NOTHING;

-- Insert maintenance duration tracking defaults
INSERT INTO system_config (key, value, description, updated_by)
VALUES ('maintenance_duration', NULL, 'Estimated maintenance duration in minutes (NULL for unspecified)', NULL)
ON CONFLICT (key) DO NOTHING;

INSERT INTO system_config (key, value, description, updated_by)
VALUES ('maintenance_start_time', NULL, 'Timestamp when maintenance mode was enabled', NULL)
ON CONFLICT (key) DO NOTHING;

INSERT INTO system_config (key, value, description, updated_by)
VALUES ('maintenance_end_time', NULL, 'Calculated end time for maintenance (start + duration)', NULL)
ON CONFLICT (key) DO NOTHING;

-- Add comments for documentation
COMMENT ON TABLE system_config IS 'System-wide configuration settings that can be modified at runtime';
COMMENT ON COLUMN system_config.key IS 'Unique configuration key identifier';
COMMENT ON COLUMN system_config.value IS 'Configuration value (stored as text, parse as needed)';
COMMENT ON COLUMN system_config.description IS 'Human-readable description of the configuration setting';
COMMENT ON COLUMN system_config.updated_at IS 'Timestamp of last update';
COMMENT ON COLUMN system_config.updated_by IS 'Admin user ID who last updated this setting';

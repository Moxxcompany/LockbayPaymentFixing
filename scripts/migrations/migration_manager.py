"""Database migration management system"""

import logging
from datetime import datetime
from typing import List, Dict, Any
import hashlib
import json
from pathlib import Path

from sqlalchemy import (
    create_engine,
    text,
    MetaData,
)

logger = logging.getLogger(__name__)


class MigrationManager:
    """Comprehensive database migration management"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.migrations_dir = Path("scripts/migrations/sql")
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_migrations_table(self):
        """Ensure migrations tracking table exists"""
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS migrations (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) UNIQUE NOT NULL,
                        checksum VARCHAR(64) NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT TRUE,
                        execution_time_ms INTEGER DEFAULT 0,
                        error_message TEXT
                    )
                """
                    )
                )
                logger.info("Migrations table ensured")
        except Exception as e:
            logger.error(f"Failed to create migrations table: {e}")
            raise

    def _calculate_checksum(self, content: str) -> str:
        """Calculate checksum for migration content"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_applied_migrations(self) -> Dict[str, Dict]:
        """Get list of applied migrations"""
        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                    SELECT filename, checksum, applied_at, success 
                    FROM migrations 
                    ORDER BY applied_at
                """
                    )
                )

                return {
                    row.filename: {
                        "checksum": row.checksum,
                        "applied_at": row.applied_at,
                        "success": row.success,
                    }
                    for row in result
                }
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return {}

    def _get_pending_migrations(self) -> List[Path]:
        """Get list of pending migrations"""
        applied = self._get_applied_migrations()

        migration_files = sorted(
            self.migrations_dir.glob("*.sql"), key=lambda x: x.name
        )

        pending = []
        for migration_file in migration_files:
            if migration_file.name not in applied:
                pending.append(migration_file)
            else:
                # Check if checksum changed
                content = migration_file.read_text()
                current_checksum = self._calculate_checksum(content)
                if applied[migration_file.name]["checksum"] != current_checksum:
                    logger.warning(f"Migration {migration_file.name} checksum changed!")

        return pending

    def create_migration(self, name: str, content: str) -> Path:
        """Create new migration file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.sql"
        migration_file = self.migrations_dir / filename

        # Add migration header
        header = f"""-- Migration: {name}
-- Created: {datetime.now().isoformat()}
-- Description: {name.replace('_', ' ').title()}

"""

        migration_file.write_text(header + content)
        logger.info(f"Created migration: {filename}")
        return migration_file

    def apply_migration(self, migration_file: Path) -> bool:
        """Apply single migration"""
        start_time = datetime.now()

        try:
            content = migration_file.read_text()
            checksum = self._calculate_checksum(content)

            with self.engine.begin() as conn:
                # Execute migration
                conn.execute(text(content))

                # Record success
                execution_time = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                conn.execute(
                    text(
                        """
                    INSERT INTO migrations (filename, checksum, execution_time_ms)
                    VALUES (:filename, :checksum, :execution_time)
                """
                    ),
                    {
                        "filename": migration_file.name,
                        "checksum": checksum,
                        "execution_time": execution_time,
                    },
                )

            logger.info(
                f"✅ Applied migration: {migration_file.name} ({execution_time}ms)"
            )
            return True

        except Exception as e:
            # Record failure
            try:
                with self.engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                        INSERT INTO migrations (filename, checksum, success, error_message)
                        VALUES (:filename, :checksum, FALSE, :error)
                    """
                        ),
                        {
                            "filename": migration_file.name,
                            "checksum": self._calculate_checksum(
                                migration_file.read_text()
                            ),
                            "error": str(e),
                        },
                    )
            except Exception as err:
                logger.warning(f"Could not record migration failure: {err}")
                pass  # Don't fail on recording failure

            logger.error(f"❌ Migration failed: {migration_file.name} - {e}")
            return False

    def run_migrations(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run all pending migrations"""
        self._ensure_migrations_table()

        pending = self._get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return {
                "status": "success",
                "applied": 0,
                "message": "No pending migrations",
            }

        if dry_run:
            logger.info(f"DRY RUN: Would apply {len(pending)} migrations:")
            for migration in pending:
                logger.info(f"  - {migration.name}")
            return {"status": "dry_run", "pending": len(pending)}

        results = {"applied": 0, "failed": 0, "errors": []}

        for migration in pending:
            if self.apply_migration(migration):
                results["applied"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(migration.name)

        if results["failed"] == 0:
            results["status"] = "success"
            logger.info(f"✅ All {results['applied']} migrations applied successfully")
        else:
            results["status"] = "partial"
            logger.error(f"❌ {results['failed']} migrations failed")

        return results

    def rollback_migration(self, filename: str) -> bool:
        """Rollback specific migration (if rollback script exists)"""
        rollback_file = self.migrations_dir / f"rollback_{filename}"

        if not rollback_file.exists():
            logger.error(f"No rollback script found for {filename}")
            return False

        try:
            content = rollback_file.read_text()

            with self.engine.begin() as conn:
                conn.execute(text(content))

                # Remove from migrations table
                conn.execute(
                    text(
                        """
                    DELETE FROM migrations WHERE filename = :filename
                """
                    ),
                    {"filename": filename},
                )

            logger.info(f"✅ Rolled back migration: {filename}")
            return True

        except Exception as e:
            logger.error(f"❌ Rollback failed: {filename} - {e}")
            return False

    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status"""
        applied = self._get_applied_migrations()
        pending = self._get_pending_migrations()

        return {
            "total_applied": len(applied),
            "pending_count": len(pending),
            "last_applied": max(
                [m["applied_at"] for m in applied.values()], default=None
            ),
            "applied_migrations": list(applied.keys()),
            "pending_migrations": [p.name for p in pending],
            "failed_migrations": [
                name for name, info in applied.items() if not info["success"]
            ],
        }

    def validate_database_schema(self) -> Dict[str, Any]:
        """Validate current database schema"""
        try:
            metadata = MetaData()
            metadata.reflect(bind=self.engine)

            tables = list(metadata.tables.keys())
            table_info = {}

            for table_name in tables:
                table = metadata.tables[table_name]
                table_info[table_name] = {
                    "columns": len(table.columns),
                    "primary_keys": [col.name for col in table.primary_key.columns],
                    "foreign_keys": len(table.foreign_keys),
                    "indexes": len(table.indexes),
                }

            return {
                "status": "valid",
                "total_tables": len(tables),
                "tables": table_info,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}


# Predefined migrations for common operations
SAMPLE_MIGRATIONS = {
    "add_user_indexes": """
-- Add performance indexes for user operations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;
""",
    "add_transaction_indexes": """
-- Add performance indexes for transaction operations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
""",
    "add_escrow_indexes": """
-- Add performance indexes for escrow operations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_escrows_seller_id ON escrows(seller_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_escrows_buyer_id ON escrows(buyer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_escrows_status ON escrows(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_escrows_created_at ON escrows(created_at);
""",
    "optimize_wallet_queries": """
-- Optimize wallet query performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wallets_user_currency ON wallets(user_id, currency);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wallets_active ON wallets(is_active) WHERE is_active = true;
""",
    "add_audit_table": """
-- Create audit log table for compliance
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
""",
    "add_rate_limit_table": """
-- Create rate limiting tracking table
CREATE TABLE IF NOT EXISTS rate_limits (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    count INTEGER DEFAULT 1,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    UNIQUE(identifier, rule_name, window_start)
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier ON rate_limits(identifier);
CREATE INDEX IF NOT EXISTS idx_rate_limits_expires_at ON rate_limits(expires_at);
""",
    "cleanup_expired_data": """
-- Clean up expired data for performance
DELETE FROM rate_limits WHERE expires_at < NOW() - INTERVAL '1 day';
DELETE FROM otp_codes WHERE expires_at < NOW() - INTERVAL '1 hour';
DELETE FROM user_sessions WHERE expires_at < NOW() - INTERVAL '1 day';
DELETE FROM notification_queue WHERE created_at < NOW() - INTERVAL '7 days' AND status = 'sent';
""",
}


def create_sample_migrations():
    """Create sample migration files"""
    from config import Config

    if not Config.DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")
    
    manager = MigrationManager(Config.DATABASE_URL)

    for name, content in SAMPLE_MIGRATIONS.items():
        try:
            manager.create_migration(name, content)
            print(f"✅ Created migration: {name}")
        except Exception as e:
            print(f"❌ Failed to create {name}: {e}")


if __name__ == "__main__":
    import sys
    from config import Config

    if len(sys.argv) < 2:
        print(
            "Usage: python migration_manager.py [create|run|status|rollback] [args...]"
        )
        sys.exit(1)

    if not Config.DATABASE_URL:
        print("ERROR: DATABASE_URL not configured")
        sys.exit(1)
    
    manager = MigrationManager(Config.DATABASE_URL)
    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 3:
            print("Usage: python migration_manager.py create <migration_name>")
            sys.exit(1)

        name = sys.argv[2]
        content = input("Enter migration SQL (end with empty line):\n")
        lines = [content]
        while True:
            line = input()
            if not line:
                break
            lines.append(line)

        migration_file = manager.create_migration(name, "\n".join(lines))
        print(f"Created: {migration_file}")

    elif command == "run":
        dry_run = "--dry-run" in sys.argv
        result = manager.run_migrations(dry_run=dry_run)
        print(json.dumps(result, indent=2, default=str))

    elif command == "status":
        status = manager.get_migration_status()
        print(json.dumps(status, indent=2, default=str))

    elif command == "validate":
        validation = manager.validate_database_schema()
        print(json.dumps(validation, indent=2, default=str))

    elif command == "sample":
        create_sample_migrations()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

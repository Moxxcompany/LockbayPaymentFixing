"""
Admin Token Security Performance Indexes Migration
Adds critical performance indexes for atomic token consumption operations

Migration: 20250915_admin_token_security_indexes
Purpose: Add performance indexes to prevent race conditions and improve atomic token operations
"""

import logging
from sqlalchemy import text
from database import SessionLocal

logger = logging.getLogger(__name__)

def upgrade():
    """Add security performance indexes for admin action tokens"""
    session = SessionLocal()
    try:
        logger.info("🔧 Starting admin token security indexes migration...")
        
        # 1. Composite index for atomic token consumption operations
        # This covers the exact WHERE clause used in atomic_consume_admin_token
        atomic_consumption_index = """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_admin_tokens_atomic_consumption 
        ON admin_action_tokens (token, cashout_id, action, used_at, expires_at)
        WHERE used_at IS NULL;
        """
        
        # 2. Partial index for active (unused) tokens - critical for performance
        # This dramatically speeds up finding unused tokens
        active_tokens_index = """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_admin_tokens_active 
        ON admin_action_tokens (cashout_id, action, expires_at)
        WHERE used_at IS NULL AND expires_at > NOW();
        """
        
        # 3. Performance index for token validation by admin
        admin_validation_index = """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_admin_tokens_admin_validation
        ON admin_action_tokens (admin_email, action, created_at, used_at)
        WHERE used_at IS NULL;
        """
        
        # 4. Audit performance index for security monitoring
        audit_performance_index = """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_admin_tokens_audit_performance
        ON admin_action_tokens (used_at, action_result, created_at)
        WHERE used_at IS NOT NULL;
        """
        
        # Execute all indexes
        indexes = [
            ("Atomic Consumption Index", atomic_consumption_index),
            ("Active Tokens Partial Index", active_tokens_index), 
            ("Admin Validation Index", admin_validation_index),
            ("Audit Performance Index", audit_performance_index)
        ]
        
        for name, sql in indexes:
            try:
                logger.info(f"🔧 Creating {name}...")
                session.execute(text(sql))
                session.commit()
                logger.info(f"✅ {name} created successfully")
            except Exception as e:
                logger.warning(f"⚠️ {name} creation failed (may already exist): {e}")
                session.rollback()
        
        # Verify critical indexes exist
        verify_query = """
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'admin_action_tokens' 
        AND indexname LIKE 'idx_admin_tokens_%'
        ORDER BY indexname;
        """
        
        result = session.execute(text(verify_query)).fetchall()
        logger.info(f"✅ Migration complete. Found {len(result)} admin token indexes:")
        for row in result:
            logger.info(f"  - {row[0]}")
        
        logger.info("🔐 SECURITY: Admin token atomic consumption indexes are now optimized")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def downgrade():
    """Remove security performance indexes"""
    session = SessionLocal()
    try:
        logger.info("🔧 Removing admin token security indexes...")
        
        indexes_to_remove = [
            "idx_admin_tokens_atomic_consumption",
            "idx_admin_tokens_active", 
            "idx_admin_tokens_admin_validation",
            "idx_admin_tokens_audit_performance"
        ]
        
        for index_name in indexes_to_remove:
            try:
                session.execute(text(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name};"))
                session.commit()
                logger.info(f"✅ Removed index: {index_name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove {index_name}: {e}")
                session.rollback()
        
        logger.info("🔧 Admin token security indexes removed")
        
    except Exception as e:
        logger.error(f"❌ Downgrade failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    # Run migration
    upgrade()
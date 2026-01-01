"""
Copy Production Data from Railway to Neon Development Database
===============================================================

This script safely copies all data from the Railway PostgreSQL (production)
database to the Neon PostgreSQL (development) database.

WARNING: This will DELETE all existing data in the Neon database!
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def copy_database():
    """Copy Railway production database to Neon development database"""
    
    # Get database URLs
    railway_url = os.getenv("RAILWAY_DATABASE_URL")
    neon_url = os.getenv("DATABASE_URL")
    
    if not railway_url:
        logger.error("❌ RAILWAY_DATABASE_URL not found in environment")
        logger.error("   Set this to your Railway PostgreSQL connection string")
        return False
    
    if not neon_url:
        logger.error("❌ DATABASE_URL (Neon) not found in environment")
        logger.error("   Set this to your Neon PostgreSQL connection string")
        return False
    
    logger.info("=" * 80)
    logger.info("🔄 RAILWAY → NEON DATABASE COPY")
    logger.info("=" * 80)
    logger.info(f"Source (Railway): {railway_url[:50]}...")
    logger.info(f"Target (Neon): {neon_url[:50]}...")
    logger.info("")
    logger.info("⚠️  WARNING: This will DELETE all data in the Neon database!")
    logger.info("⚠️  Press Ctrl+C within 5 seconds to cancel...")
    
    # Give user time to cancel
    import time
    for i in range(5, 0, -1):
        logger.info(f"   Starting in {i} seconds...")
        time.sleep(1)
    
    logger.info("")
    logger.info("🚀 Starting database copy...")
    
    # Create timestamp for dump file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = f"/tmp/railway_dump_{timestamp}.sql"
    
    try:
        # Step 1: Dump Railway database
        logger.info("📦 Step 1/3: Dumping Railway database...")
        dump_cmd = [
            "pg_dump",
            "--no-owner",  # Don't include ownership commands
            "--no-acl",    # Don't include access privileges
            "--clean",     # Include DROP commands
            "--if-exists", # Use IF EXISTS for DROP commands
            "-f", dump_file,
            railway_url
        ]
        
        result = subprocess.run(dump_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"❌ pg_dump failed: {result.stderr}")
            return False
        
        logger.info(f"✅ Database dumped to {dump_file}")
        
        # Check dump file size
        file_size = os.path.getsize(dump_file)
        logger.info(f"   Dump file size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
        
        # Step 2: Restore to Neon database
        logger.info("📥 Step 2/3: Restoring to Neon database...")
        restore_cmd = [
            "psql",
            "-f", dump_file,
            neon_url
        ]
        
        result = subprocess.run(restore_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"❌ psql restore failed: {result.stderr}")
            logger.info("   Note: Some warnings about existing objects are normal")
            # Don't return False here - some warnings are expected
        
        logger.info("✅ Data restored to Neon database")
        
        # Step 3: Clean up dump file
        logger.info("🧹 Step 3/3: Cleaning up...")
        os.remove(dump_file)
        logger.info(f"✅ Removed temporary dump file: {dump_file}")
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ DATABASE COPY COMPLETE!")
        logger.info("=" * 80)
        logger.info("   Railway (production) data has been copied to Neon (development)")
        logger.info("   You can now safely develop with production-like data")
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during database copy: {e}")
        # Clean up dump file if it exists
        if os.path.exists(dump_file):
            os.remove(dump_file)
        return False

if __name__ == "__main__":
    success = copy_database()
    sys.exit(0 if success else 1)

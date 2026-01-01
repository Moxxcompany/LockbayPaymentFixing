#!/usr/bin/env python3
"""
Test script for Railway → Neon backup sync
Verifies connections and runs a test sync
"""

import asyncio
import logging
import sys
from services.railway_neon_sync import RailwayNeonSync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_sync():
    """Test the Railway → Neon sync"""
    print("=" * 80)
    print("🧪 TESTING RAILWAY → NEON SYNC")
    print("=" * 80)
    
    try:
        # Create sync instance
        sync = RailwayNeonSync()
        
        # Test 1: Verify connections
        print("\n📡 Test 1: Verifying database connections...")
        if not await sync.verify_connections():
            print("❌ Connection verification failed!")
            return False
        print("✅ Both databases are accessible")
        
        # Test 2: Get Railway stats
        print("\n📊 Test 2: Getting Railway database stats...")
        railway_stats = await sync.get_railway_stats()
        if not railway_stats:
            print("❌ Failed to get Railway stats")
            return False
        print(f"✅ Railway stats: {railway_stats}")
        
        # Test 3: Ask user if they want to run full sync
        print("\n" + "=" * 80)
        print("⚠️  WARNING: Full sync will overwrite ALL data in Neon database")
        print("=" * 80)
        response = input("Do you want to proceed with full sync? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("❌ Full sync cancelled by user")
            print("✅ Basic connectivity tests passed!")
            return True
        
        # Test 4: Run full sync
        print("\n🔄 Test 4: Running full Railway → Neon sync...")
        result = await sync.sync_railway_to_neon()
        
        if result["success"]:
            print("\n" + "=" * 80)
            print("✅ SYNC TEST SUCCESSFUL!")
            print("=" * 80)
            print(f"Duration: {result['duration_seconds']:.1f}s")
            print(f"Railway: {result['railway_stats']}")
            print(f"Neon: {result['neon_stats']}")
            return True
        else:
            print(f"\n❌ Sync failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sync())
    sys.exit(0 if success else 1)

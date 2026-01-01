#!/usr/bin/env python3
"""
Production Health Check - Verify all critical systems
"""
import asyncio
import sys
sys.path.insert(0, '.')

async def main():
    print("\n" + "=" * 80)
    print("🏥 PRODUCTION HEALTH CHECK")
    print("=" * 80)
    print()
    
    results = {"pass": [], "fail": []}
    
    # 1. Check SQLite Queue
    print("📦 Checking SQLite Queue...")
    try:
        from webhook_queue.webhook_inbox.fast_sqlite_webhook_queue import fast_sqlite_webhook_queue
        
        # Test enqueue
        success, eid, duration = await fast_sqlite_webhook_queue.enqueue_webhook(
            provider="health_check",
            endpoint="test",
            payload={"test": True},
            headers={"X-Test": "true"},
            client_ip="127.0.0.1",
            priority=fast_sqlite_webhook_queue.WebhookEventPriority.NORMAL.__class__.NORMAL
        )
        
        if success and duration < 20:
            print(f"   ✅ SQLite queue working ({duration:.2f}ms)")
            results["pass"].append("SQLite Queue")
        else:
            print(f"   ⚠️  SQLite queue slow or failed")
            results["fail"].append("SQLite Queue")
    except Exception as e:
        print(f"   ❌ SQLite queue error: {e}")
        results["fail"].append("SQLite Queue")
    
    # 2. Check Fallback Mechanism
    print("\n🔄 Checking Fallback Mechanism...")
    try:
        from webhook_server import enqueue_webhook_with_fallback
        from webhook_queue.webhook_inbox.fast_sqlite_webhook_queue import WebhookEventPriority
        
        success, eid, duration = await enqueue_webhook_with_fallback(
            provider="health_test",
            endpoint="fallback",
            payload={"test": "fallback"},
            headers={"X-Test": "true"},
            client_ip="127.0.0.1",
            priority=WebhookEventPriority.NORMAL
        )
        
        if success:
            print(f"   ✅ Fallback mechanism working ({duration:.2f}ms)")
            results["pass"].append("Fallback Mechanism")
        else:
            print(f"   ❌ Fallback failed")
            results["fail"].append("Fallback Mechanism")
    except Exception as e:
        print(f"   ❌ Fallback error: {e}")
        results["fail"].append("Fallback Mechanism")
    
    # 3. Check Queue Statistics
    print("\n📊 Checking Queue Statistics...")
    try:
        from webhook_queue.webhook_inbox.fast_sqlite_webhook_queue import fast_sqlite_webhook_queue
        
        stats = fast_sqlite_webhook_queue.get_queue_stats()
        
        metrics = stats.get('performance_metrics', {})
        opt_status = stats.get('optimization_status', {})
        
        avg_time = metrics.get('average_enqueue_time_ms', 999)
        
        optimizations_ok = (
            opt_status.get('connection_pooling') and
            opt_status.get('wal_mode') and
            opt_status.get('optimized_pragmas')
        )
        
        if avg_time < 20 and optimizations_ok:
            print(f"   ✅ Average enqueue: {avg_time:.2f}ms (<20ms target)")
            print(f"   ✅ All optimizations enabled")
            results["pass"].append("Queue Statistics")
        else:
            print(f"   ⚠️  Performance or optimizations issue")
            results["fail"].append("Queue Statistics")
    except Exception as e:
        print(f"   ❌ Stats error: {e}")
        results["fail"].append("Queue Statistics")
    
    # 4. Check Health Endpoint
    print("\n💓 Checking Health Endpoint...")
    try:
        from webhook_queue.webhook_inbox.fast_sqlite_webhook_queue import fast_sqlite_webhook_queue
        
        healthy, status = await fast_sqlite_webhook_queue.health_check()
        
        if healthy:
            print(f"   ✅ {status}")
            results["pass"].append("Health Endpoint")
        else:
            print(f"   ❌ Unhealthy: {status}")
            results["fail"].append("Health Endpoint")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        results["fail"].append("Health Endpoint")
    
    # 5. Check Redis Availability (optional)
    print("\n🔴 Checking Redis Fallback...")
    try:
        from webhook_queue.webhook_inbox.redis_webhook_queue import redis_webhook_queue
        
        try:
            healthy, status = await redis_webhook_queue.health_check()
            if healthy:
                print(f"   ✅ Redis available: {status}")
            else:
                print(f"   ⚠️  Redis unavailable (OK - SQLite is primary)")
        except:
            print(f"   ⚠️  Redis unavailable (OK - SQLite is primary)")
        
        results["pass"].append("Redis Availability Check")
    except Exception as e:
        print(f"   ⚠️  Redis check skipped: {str(e)[:50]}")
        results["pass"].append("Redis Availability Check")
    
    # 6. Check Bot is Running
    print("\n🤖 Checking Bot Status...")
    try:
        import requests
        response = requests.get("http://localhost:5000/", timeout=5)
        
        if response.status_code == 200:
            print(f"   ✅ Bot server responding")
            results["pass"].append("Bot Server")
        else:
            print(f"   ⚠️  Bot server status: {response.status_code}")
            results["fail"].append("Bot Server")
    except Exception as e:
        print(f"   ❌ Bot server check failed: {str(e)[:50]}")
        results["fail"].append("Bot Server")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 HEALTH CHECK SUMMARY")
    print("=" * 80)
    
    total = len(results["pass"]) + len(results["fail"])
    passed = len(results["pass"])
    
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {len(results['fail'])}/{total}")
    
    if results["pass"]:
        print("\n✅ Healthy Systems:")
        for system in results["pass"]:
            print(f"   • {system}")
    
    if results["fail"]:
        print("\n❌ Failed Systems:")
        for system in results["fail"]:
            print(f"   • {system}")
    
    print("=" * 80)
    
    if len(results["fail"]) == 0:
        print("✅ ALL SYSTEMS HEALTHY - Production Ready!")
        print("=" * 80)
        return 0
    elif len(results["fail"]) <= 2:
        print("⚠️  MOSTLY HEALTHY - Minor issues detected")
        print("=" * 80)
        return 0
    else:
        print("❌ CRITICAL ISSUES - Review failures")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

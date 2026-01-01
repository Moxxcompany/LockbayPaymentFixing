"""Simple test to verify audit logger functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.comprehensive_audit_logger import (
        ComprehensiveAuditLogger,
        AuditEventType,
        AuditLevel,
        RelatedIDs,
        TraceContext
    )
    print("✅ Successfully imported audit logging framework")
    
    # Test basic functionality
    logger = ComprehensiveAuditLogger("test")
    trace_id = TraceContext.generate_trace_id()
    TraceContext.set_trace_id(trace_id)
    
    # Test basic logging
    logger.audit(
        event_type=AuditEventType.SYSTEM,
        action="test_verification",
        result="success",
        payload={"test": True, "message_length": 42}
    )
    
    print("✅ Basic audit logging test passed")
    print(f"✅ Generated trace ID: {trace_id}")
    print("✅ Audit logging framework is ready for use")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
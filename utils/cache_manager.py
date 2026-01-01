"""
Cache Management Utilities
Provides cache clearing and management functions for the monitoring system
"""

import logging
import gc
from typing import Dict, Any

logger = logging.getLogger(__name__)

def clear_all_caches() -> Dict[str, Any]:
    """Clear all available caches"""
    cleared_caches = []
    
    try:
        # Clear Python internal caches
        import sys
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()
            cleared_caches.append("python_type_cache")
        
        # Clear import cache (selective)
        import importlib
        if hasattr(importlib, 'invalidate_caches'):
            importlib.invalidate_caches()
            cleared_caches.append("import_cache")
        
        # Force garbage collection
        collected = gc.collect()
        cleared_caches.append(f"garbage_collection({collected}_objects)")
        
        logger.info(f"🧹 Cleared caches: {', '.join(cleared_caches)}")
        
        return {
            'success': True,
            'caches_cleared': cleared_caches,
            'objects_collected': collected
        }
        
    except Exception as e:
        logger.error(f"Cache clearing error: {e}")
        return {
            'success': False,
            'error': str(e),
            'caches_cleared': cleared_caches
        }
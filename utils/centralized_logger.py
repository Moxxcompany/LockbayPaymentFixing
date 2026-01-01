"""
Centralized Error Logging System
Provides unified error tracking and monitoring
"""

import logging
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

class CentralizedLogger:
    """Production-ready centralized logging system"""
    
    def __init__(self):
        self.logger = logging.getLogger("centralized_errors")
        self.setup_file_handler()
    
    def setup_file_handler(self):
        """Setup file logging for persistent error tracking"""
        try:
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(
                f"{log_dir}/bot_errors.log", 
                mode='a', 
                encoding='utf-8'
            )
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.ERROR)
            
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to setup file logging: {e}")
    
    def log_error(self, 
                  error_type: str, 
                  message: str, 
                  user_id: Optional[int] = None,
                  context: Optional[Dict[str, Any]] = None):
        """Log error with structured data"""
        
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "message": message,
            "user_id": user_id,
            "context": context or {}
        }
        
        self.logger.error(json.dumps(error_data, ensure_ascii=False))
    
    def log_critical_error(self, message: str, details: Optional[Dict] = None):
        """Log critical system errors"""
        self.log_error("CRITICAL", message, context=details)
    
    def log_user_error(self, user_id: int, error_type: str, message: str):
        """Log user-specific errors"""
        self.log_error(error_type, message, user_id=user_id)

# Global instance
centralized_logger = CentralizedLogger()
"""
Comprehensive Audit Logging System
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from database import SessionLocal
from models import User
import json

logger = logging.getLogger(__name__)


class AuditLogger:
    """Service for comprehensive audit logging"""
    
    def __init__(self):
        audit_handler = logging.FileHandler('audit.log')
        audit_formatter = logging.Formatter(
            '%(asctime)s [AUDIT] %(levelname)s - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.addHandler(audit_handler)
        self.audit_logger.setLevel(logging.INFO)
    
    async def log_admin_action(
        self, 
        admin_id: int, 
        action: str, 
        target_type: str,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Log administrative actions for audit trail"""
        try:
            session = SessionLocal()
            try:
                admin = session.query(User).filter(User.id == admin_id).first()
                admin_name = getattr(admin, 'first_name', 'Unknown') if admin else 'Unknown'
                
                audit_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'admin_id': admin_id,
                    'admin_name': admin_name,
                    'action': action,
                    'target_type': target_type,
                    'target_id': target_id,
                    'details': details or {},
                    'ip_address': ip_address
                }
                
                self.audit_logger.info(json.dumps(audit_entry))
                
                logger.info(
                    f"🛡️ ADMIN ACTION: {admin_name} ({admin_id}) performed '{action}' on {target_type} {target_id or ''}"
                )
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
    
    async def log_financial_operation(
        self,
        operation_type: str,
        amount: float,
        currency: str,
        user_id: Optional[int] = None,
        reference: Optional[str] = None,
        status: str = "initiated",
        details: Optional[Dict[str, Any]] = None
    ):
        """Log financial operations for compliance tracking"""
        try:
            audit_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'operation_type': operation_type,
                'amount': amount,
                'currency': currency,
                'user_id': user_id,
                'reference': reference,
                'status': status,
                'details': details or {}
            }
            
            self.audit_logger.info(f"FINANCIAL: {json.dumps(audit_entry)}")
            
            if amount >= 1000 or operation_type in ['manual_payout', 'admin_transfer']:
                logger.warning(
                    f"💰 FINANCIAL OPERATION: {operation_type} - {currency} {amount:,.2f} - "
                    f"User: {user_id} - Ref: {reference} - Status: {status}"
                )
                
        except Exception as e:
            logger.error(f"Error logging financial operation: {e}")


# Global audit logger instance
audit_logger = AuditLogger()
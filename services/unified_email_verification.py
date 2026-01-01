"""
Unified Email Verification Service

Provides a unified interface for email OTP verification across the platform.
Now uses the comprehensive EmailVerificationService for all operations.
"""

import logging
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class UnifiedEmailVerificationService:
    """
    Unified email verification service that wraps EmailVerificationService functionality
    
    Provides backward compatibility while using the new comprehensive service
    """
    
    @classmethod
    async def send_verification_otp(
        cls, 
        email: str, 
        user_id: int, 
        verification_type: str, 
        context_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Send OTP verification email using EmailVerificationService"""
        try:
            from services.email_verification_service import EmailVerificationService
            
            # Map verification_type to purpose (backward compatibility)
            purpose_mapping = {
                'registration': 'registration',
                'cashout': 'cashout', 
                'email_change': 'change_email',
                'password_reset': 'password_reset'
            }
            purpose = purpose_mapping.get(verification_type, 'registration')
            
            # Extract IP and user agent from context if available
            ip_address = context_data.get('ip_address') if context_data else None
            user_agent = context_data.get('user_agent') if context_data else None
            cashout_context = context_data.get('cashout_context') if context_data else None
            
            # Fix: Use proper async session for send_otp_async call
            from database import async_managed_session
            async with async_managed_session() as session:
                result = await EmailVerificationService.send_otp_async(
                    session=session,
                    user_id=user_id,
                    email=email,
                    purpose=purpose,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    cashout_context=cashout_context
                )
            
            if result["success"]:
                logger.info(f"✅ OTP sent successfully to {email} for {verification_type}")
                return True, result["message"]
            else:
                logger.error(f"❌ Failed to send OTP to {email}: {result['message']}")
                return False, result["message"]
                
        except Exception as e:
            logger.error(f"❌ UnifiedEmailVerificationService.send_verification_otp failed: {e}")
            return False, f"Failed to send verification email: {str(e)}"
    
    @classmethod
    async def verify_otp(
        cls, 
        email: str, 
        otp: str, 
        user_id: int, 
        verification_type: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Verify OTP code using EmailVerificationService"""
        try:
            from services.email_verification_service import EmailVerificationService
            
            # Map verification_type to purpose (backward compatibility)
            purpose_mapping = {
                'registration': 'registration',
                'cashout': 'cashout',
                'email_change': 'change_email', 
                'password_reset': 'password_reset'
            }
            purpose = purpose_mapping.get(verification_type, 'registration')
            
            result = EmailVerificationService.verify_otp(
                user_id=user_id,
                otp_code=otp,
                purpose=purpose
            )
            
            if result["success"]:
                logger.info(f"✅ OTP verified successfully for {email} ({verification_type})")
                return True, result["message"], result.get("context_data")
            else:
                logger.warning(f"❌ OTP verification failed for {email}: {result['message']}")
                return False, result["message"], None
                
        except Exception as e:
            logger.error(f"❌ UnifiedEmailVerificationService.verify_otp failed: {e}")
            return False, f"OTP verification failed: {str(e)}", None
    
    @classmethod
    async def can_resend_otp(
        cls,
        user_id: int,
        email: str
    ) -> Tuple[bool, str, int]:
        """
        Check if user can resend OTP
        
        Returns:
            (can_resend, message, cooldown_seconds)
        """
        try:
            from services.email_verification_service import EmailVerificationService
            
            result = EmailVerificationService.can_resend(user_id, email)
            
            if result["can_resend"]:
                return True, "Can resend", 0
            else:
                cooldown = result.get("cooldown_remaining", 0)
                if cooldown > 0:
                    return False, f"Please wait {cooldown} seconds before resending", cooldown
                elif not result.get("within_daily_limit", True):
                    return False, f"Daily limit reached ({result['daily_count']}/{result['daily_limit']})", 0
                else:
                    return False, "Cannot resend at this time", 0
                    
        except Exception as e:
            logger.error(f"❌ UnifiedEmailVerificationService.can_resend_otp failed: {e}")
            return False, f"Error checking resend availability: {str(e)}", 0
    
    @classmethod
    async def get_verification_status(
        cls,
        user_id: int,
        verification_type: str
    ) -> Dict[str, Any]:
        """Get verification status for user and type"""
        try:
            from services.email_verification_service import EmailVerificationService
            
            # Map verification_type to purpose
            purpose_mapping = {
                'registration': 'registration',
                'cashout': 'cashout',
                'email_change': 'change_email',
                'password_reset': 'password_reset'
            }
            purpose = purpose_mapping.get(verification_type, 'registration')
            
            return EmailVerificationService.get_verification_status(user_id, purpose)
            
        except Exception as e:
            logger.error(f"❌ UnifiedEmailVerificationService.get_verification_status failed: {e}")
            return {
                "has_verification": False,
                "status": "error",
                "error": str(e)
            }
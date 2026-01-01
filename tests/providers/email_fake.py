"""
Email Service Fake Provider
Comprehensive test double for email sending services (Brevo, SendGrid, etc.)
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EmailFakeProvider:
    """
    Comprehensive fake provider for email sending services
    
    Features:
    - Email sending simulation with delivery tracking
    - OTP email generation and validation
    - Template-based email simulation
    - Delivery failure scenarios
    - Email content validation
    """
    
    def __init__(self):
        self.api_key = "test_email_api_key"
        self.sender_email = "test@lockbay.io"
        self.sender_name = "LockBay Test"
        
        # State management
        self.sent_emails = []
        self.delivery_failures = []
        self.failure_mode = None  # None, "network_error", "auth_failed", "rate_limit", "invalid_email"
        self.generated_otps = {}  # email -> otp_data
        
        # Email templates simulation
        self.templates = {
            "welcome": {
                "subject": "Welcome to LockBay!",
                "template_id": "welcome_template_123"
            },
            "otp_verification": {
                "subject": "Your LockBay Verification Code",
                "template_id": "otp_template_456"
            },
            "escrow_notification": {
                "subject": "LockBay Escrow Update",
                "template_id": "escrow_template_789"
            }
        }
        
        # Message ID counter for realistic simulation
        self.message_id_counter = 1000
        
    def reset_state(self):
        """Reset fake provider state for test isolation"""
        self.sent_emails.clear()
        self.delivery_failures.clear()
        self.failure_mode = None
        self.generated_otps.clear()
        self.message_id_counter = 1000
        
    def set_failure_mode(self, mode: Optional[str]):
        """Configure failure scenarios"""
        self.failure_mode = mode
        
    def _get_next_message_id(self) -> str:
        """Get next message ID for realistic simulation"""
        self.message_id_counter += 1
        return f"<test_message_{self.message_id_counter}@lockbay.test>"
    
    def _validate_email(self, email: str) -> bool:
        """Basic email validation for testing"""
        return "@" in email and "." in email
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        template_id: Optional[str] = None,
        template_data: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fake email sending
        Simulates email service API (Brevo, SendGrid, etc.)
        """
        # Simulate failure modes
        if self.failure_mode == "network_error":
            raise Exception("Network error: Unable to connect to email service")
        elif self.failure_mode == "auth_failed":
            raise Exception("Authentication failed: Invalid API key")
        elif self.failure_mode == "rate_limit":
            raise Exception("Rate limit exceeded: Too many emails sent")
        elif self.failure_mode == "invalid_email":
            raise Exception(f"Invalid email address: {to_email}")
            
        # Validate email address
        if not self._validate_email(to_email):
            raise Exception(f"Invalid email address format: {to_email}")
            
        # Special handling for test email addresses
        if to_email.endswith("_FAIL@test.com"):
            delivery_failure = {
                "to_email": to_email,
                "error": "Email delivery failed",
                "timestamp": datetime.now(timezone.utc)
            }
            self.delivery_failures.append(delivery_failure)
            raise Exception("Email delivery failed")
        
        message_id = self._get_next_message_id()
        
        # Generate email content based on template or direct content
        final_content = html_content or text_content or ""
        final_subject = subject
        
        if template_id and template_id in [t["template_id"] for t in self.templates.values()]:
            # Find template by ID
            template_name = None
            for name, template in self.templates.items():
                if template["template_id"] == template_id:
                    template_name = name
                    break
                    
            if template_name:
                # Apply template data
                if template_data:
                    final_content = self._apply_template_data(template_name, template_data)
                final_subject = self.templates[template_name]["subject"]
        
        email_data = {
            "message_id": message_id,
            "to_email": to_email,
            "subject": final_subject,
            "html_content": final_content,
            "text_content": text_content,
            "template_id": template_id,
            "template_data": template_data,
            "delivery_time_ms": 250,  # Simulated delivery time
            "status": "sent",
            "timestamp": datetime.now(timezone.utc),
            **kwargs
        }
        
        self.sent_emails.append(email_data)
        
        return {
            "success": True,
            "message_id": message_id,
            "delivery_time_ms": 250
        }
    
    async def send_otp_email(
        self,
        to_email: str,
        otp: str,
        expiry_minutes: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fake OTP email sending
        Specialized method for OTP verification emails
        """
        # Store OTP for verification testing
        self.generated_otps[to_email] = {
            "otp": otp,
            "expiry_minutes": expiry_minutes,
            "generated_at": datetime.now(timezone.utc),
            "verified": False
        }
        
        # Send email with OTP template
        template_data = {
            "otp_code": otp,
            "expiry_minutes": expiry_minutes,
            "user_email": to_email
        }
        
        return await self.send_email(
            to_email=to_email,
            subject=self.templates["otp_verification"]["subject"],
            template_id=self.templates["otp_verification"]["template_id"],
            template_data=template_data,
            **kwargs
        )
    
    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fake welcome email sending
        Specialized method for welcome emails
        """
        template_data = {
            "user_name": user_name,
            "user_email": to_email
        }
        
        return await self.send_email(
            to_email=to_email,
            subject=self.templates["welcome"]["subject"],
            template_id=self.templates["welcome"]["template_id"],
            template_data=template_data,
            **kwargs
        )
    
    def _apply_template_data(self, template_name: str, template_data: Dict) -> str:
        """
        Apply template data to generate email content
        Simulates template rendering
        """
        if template_name == "otp_verification":
            return f"""
            <html>
            <body>
                <h2>Your LockBay Verification Code</h2>
                <p>Hello,</p>
                <p>Your verification code is: <strong>{template_data.get('otp_code', 'XXXXXX')}</strong></p>
                <p>This code will expire in {template_data.get('expiry_minutes', 10)} minutes.</p>
                <p>If you didn't request this, please ignore this email.</p>
                <p>Best regards,<br>The LockBay Team</p>
            </body>
            </html>
            """
        elif template_name == "welcome":
            return f"""
            <html>
            <body>
                <h2>Welcome to LockBay, {template_data.get('user_name', 'User')}!</h2>
                <p>Thank you for joining our secure escrow platform.</p>
                <p>Your account ({template_data.get('user_email', '')}) is now ready to use.</p>
                <p>Best regards,<br>The LockBay Team</p>
            </body>
            </html>
            """
        else:
            return f"<html><body><h2>LockBay Notification</h2><pre>{template_data}</pre></body></html>"
    
    def verify_otp(self, email: str, provided_otp: str) -> Dict[str, Any]:
        """
        Verify OTP for testing
        Simulates OTP verification logic
        """
        if email not in self.generated_otps:
            return {
                "success": False,
                "message": "No OTP found for this email",
                "remaining_attempts": 0
            }
        
        otp_data = self.generated_otps[email]
        
        # Check if already verified
        if otp_data["verified"]:
            return {
                "success": False,
                "message": "OTP already used",
                "remaining_attempts": 0
            }
        
        # Check expiry
        from datetime import timedelta
        expiry_time = otp_data["generated_at"] + timedelta(minutes=otp_data["expiry_minutes"])
        if datetime.now(timezone.utc) > expiry_time:
            return {
                "success": False,
                "message": "OTP has expired",
                "remaining_attempts": 0
            }
        
        # Verify OTP
        if provided_otp == otp_data["otp"]:
            otp_data["verified"] = True
            return {
                "success": True,
                "message": "OTP verified successfully",
                "email": email,
                "remaining_attempts": 4
            }
        else:
            return {
                "success": False,
                "message": "Invalid OTP",
                "remaining_attempts": 3
            }
    
    def get_sent_emails(self, to_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all sent emails, optionally filtered by recipient"""
        if to_email:
            return [email for email in self.sent_emails if email["to_email"] == to_email]
        return self.sent_emails.copy()
    
    def get_last_email(self, to_email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the last sent email, optionally filtered by recipient"""
        emails = self.get_sent_emails(to_email)
        return emails[-1] if emails else None
    
    def get_otp_data(self, email: str) -> Optional[Dict[str, Any]]:
        """Get OTP data for email address"""
        return self.generated_otps.get(email)
    
    def clear_history(self):
        """Clear email history and OTP data"""
        self.sent_emails.clear()
        self.delivery_failures.clear()
        self.generated_otps.clear()


# Global instance for test patching  
email_fake = EmailFakeProvider()
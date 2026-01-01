"""Welcome email service for new user onboarding and retention"""

import asyncio
import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from services.email_templates import (
    get_welcome_email_template,
)
from services.pdf_generator import PDFAgreementGenerator
from config import Config
import base64
from typing import Optional

logger = logging.getLogger(__name__)


class WelcomeEmailService:
    """Service for sending retention-focused welcome emails to new users"""

    def __init__(self):
        """Initialize email service with Brevo API"""
        api_key = Config.BREVO_API_KEY
        if not api_key:
            logger.warning(
                "BREVO_API_KEY not configured - welcome emails will be skipped"
            )
            self.api_client = None
            return

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = api_key
        self.api_client = sib_api_v3_sdk.ApiClient(configuration)
        self.transactional_emails_api = sib_api_v3_sdk.TransactionalEmailsApi(
            self.api_client
        )

    async def send_welcome_email(
        self, user_email: str, user_name: str, user_id: int = None, include_agreement_pdf: bool = True
    ) -> bool:
        """
        Send a retention-focused welcome email to new users with optional PDF agreement

        Args:
            user_email: User's email address
            user_name: User's first name or username
            user_id: User's database ID for membership number (optional)
            include_agreement_pdf: Whether to attach PDF agreement (default: True)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.api_client:
            logger.warning("Email service not configured - skipping welcome email")
            return False

        try:
            # Generate email template with membership number
            membership_number = str(user_id) if user_id else None
            template = get_welcome_email_template(user_name, user_email, membership_number)

            # Prepare attachments
            attachments = []
            if include_agreement_pdf:
                try:
                    # Generate PDF agreement
                    pdf_bytes = PDFAgreementGenerator.generate_user_agreement(
                        user_name, user_email
                    )
                    pdf_filename = PDFAgreementGenerator.get_agreement_filename(
                        user_name
                    )

                    # Convert to base64 for Brevo API
                    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

                    # Add to attachments
                    attachments.append(
                        sib_api_v3_sdk.SendSmtpEmailAttachment(
                            content=pdf_base64, name=pdf_filename
                        )
                    )

                    logger.info(
                        f"Generated PDF agreement for {user_email}: {pdf_filename}"
                    )

                except Exception as pdf_error:
                    logger.warning(
                        f"Failed to generate PDF agreement for {user_email}: {pdf_error}"
                    )
                    # Continue without PDF attachment

            # Create email object
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[sib_api_v3_sdk.SendSmtpEmailTo(email=user_email, name=user_name)],
                sender=sib_api_v3_sdk.SendSmtpEmailSender(
                    email=Config.FROM_EMAIL, name=Config.FROM_NAME
                ),
                subject=template["subject"],
                html_content=template["html_content"],
                text_content=template.get("text_content"),
                attachment=attachments if attachments else None,
                tags=["welcome", "onboarding", "retention", "pdf-agreement"],
            )

            # Send email with non-blocking I/O and retry logic
            api_response = await self._send_email_with_retry(
                send_smtp_email, user_email
            )

            attachment_info = " with PDF agreement" if attachments else ""
            logger.info(
                f"Welcome email{attachment_info} sent successfully to {user_email} - Message ID: {api_response.message_id}"
            )
            return True

        except ApiException as e:
            logger.error(f"Error sending welcome email to {user_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending welcome email to {user_email}: {e}")
            return False

    async def send_custom_email(
        self, to_email: str, subject: str, html_content: str, text_content: str = None
    ) -> bool:
        """
        Send a custom email with provided content

        Args:
            to_email: Recipient's email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text content (optional)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.api_client:
            logger.warning("Email service not configured - skipping custom email")
            return False

        try:
            # Create email object
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[sib_api_v3_sdk.SendSmtpEmailTo(email=to_email)],
                sender=sib_api_v3_sdk.SendSmtpEmailSender(
                    email=Config.FROM_EMAIL, name=Config.FROM_NAME
                ),
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                tags=["custom", "invitation", "escrow"],
            )

            # Send email with non-blocking I/O and retry logic
            api_response = await self._send_email_with_retry(
                send_smtp_email, to_email
            )
            logger.info(
                f"Custom email sent successfully to {to_email} - Message ID: {api_response.message_id}"
            )
            return True

        except ApiException as e:
            logger.error(f"Error sending custom email to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending custom email to {to_email}: {e}")
            return False

    async def send_followup_email(
        self, user_email: str, user_name: str, days_since_signup: int
    ) -> bool:
        """
        Send follow-up email for users who haven't started trading

        Args:
            user_email: User's email address
            user_name: User's first name or username
            days_since_signup: Number of days since user signed up

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.api_client:
            logger.warning("Email service not configured - skipping follow-up email")
            return False

        try:
            # Generate follow-up email template (using welcome template as fallback)
            # TODO: Create dedicated quick start email template
            template = get_welcome_email_template(user_name, user_email, None)

            # Create email object
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[sib_api_v3_sdk.SendSmtpEmailTo(email=user_email, name=user_name)],
                sender=sib_api_v3_sdk.SendSmtpEmailSender(
                    email=Config.FROM_EMAIL, name=Config.FROM_NAME
                ),
                subject=template["subject"],
                html_content=template["html_content"],
                text_content=template.get("text_content"),
                tags=["followup", "retention", f"day_{days_since_signup}"],
            )

            # Send email with non-blocking I/O and retry logic
            api_response = await self._send_email_with_retry(
                send_smtp_email, user_email
            )
            logger.info(
                f"Follow-up email sent successfully to {user_email} - Message ID: {api_response.message_id}"
            )
            return True

        except ApiException as e:
            logger.error(f"Error sending follow-up email to {user_email}: {e}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending follow-up email to {user_email}: {e}"
            )
            return False

    async def _send_email_with_retry(
        self, send_smtp_email: sib_api_v3_sdk.SendSmtpEmail, recipient_email: str, 
        max_retries: int = 3, timeout: float = 30.0
    ) -> Optional[sib_api_v3_sdk.CreateSmtpEmail]:
        """Send email with non-blocking I/O, timeout, and retry logic"""
        for attempt in range(max_retries):
            try:
                # Wrap blocking Brevo API call in asyncio.to_thread to prevent blocking the event loop
                api_response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.transactional_emails_api.send_transac_email,
                        send_smtp_email
                    ),
                    timeout=timeout
                )
                return api_response
                
            except asyncio.TimeoutError:
                logger.warning(
                    f"Email send timeout (attempt {attempt + 1}/{max_retries}) for {recipient_email}"
                )
                if attempt == max_retries - 1:
                    raise
                    
            except ApiException as e:
                logger.warning(
                    f"Email API error (attempt {attempt + 1}/{max_retries}) for {recipient_email}: {e}"
                )
                if attempt == max_retries - 1:
                    raise
                    
            except Exception as e:
                logger.warning(
                    f"Email send error (attempt {attempt + 1}/{max_retries}) for {recipient_email}: {e}"
                )
                if attempt == max_retries - 1:
                    raise
                    
            # Exponential backoff between retries
            if attempt < max_retries - 1:
                backoff_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                await asyncio.sleep(backoff_time)
                
        return None  # This should never be reached due to raises above

    def test_connection(self) -> bool:
        """Test if email service is properly configured"""
        if not self.api_client:
            return False
        try:
            # Try to get account info to test connection
            account_api = sib_api_v3_sdk.AccountApi(self.api_client)
            account_api.get_account()
            return True
        except Exception:
            return False

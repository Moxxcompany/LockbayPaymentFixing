"""NGN Bank Transfer Notification Service for sending completion notifications to customers"""

import logging
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.error import TelegramError

from services.email import EmailService
from services.consolidated_notification_service import (
    ConsolidatedNotificationService,
    NotificationRequest,
    NotificationCategory,
    NotificationPriority,
    NotificationChannel
)
from config import Config

logger = logging.getLogger(__name__)


class NGNNotificationService:
    """Send NGN bank transfer completion notifications via unified notification system"""
    
    def __init__(self):
        self.bot = Bot(token=Config.BOT_TOKEN)
        self.email_service = EmailService()
        self.notification_service = None
    
    async def send_ngn_completion_notification(
        self,
        user_id: int,
        cashout_id: str,
        usd_amount: float,
        ngn_amount: float,
        bank_name: str,
        account_number: str,
        bank_reference: str,
        user_email: Optional[str] = None
    ) -> bool:
        """Send unified NGN bank transfer completion notification via ConsolidatedNotificationService"""
        
        try:
            # Use the unified notification system for better reliability
            success = await self._send_unified_ngn_notification(
                user_id, cashout_id, usd_amount, ngn_amount, bank_name, account_number, bank_reference
            )
            
            if success:
                logger.info(f"✅ NGN transfer notification sent via unified system for {cashout_id}")
            else:
                logger.warning(f"⚠️ NGN unified notification failed for {cashout_id}, trying legacy fallback")
                # Fallback to legacy system if unified fails
                success = await self._send_telegram_notification(
                    user_id, cashout_id, usd_amount, ngn_amount, bank_name, account_number, bank_reference
                )
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error sending NGN transfer notification for {cashout_id}: {str(e)}")
            return False

    async def _send_unified_ngn_notification(
        self,
        user_id: int,
        cashout_id: str,
        usd_amount: float,
        ngn_amount: float,
        bank_name: str,
        account_number: str,
        bank_reference: str
    ) -> bool:
        """Send NGN completion notification via ConsolidatedNotificationService"""
        
        try:
            # Initialize notification service if needed
            if not self.notification_service:
                self.notification_service = ConsolidatedNotificationService()
                await self.notification_service.initialize()
            
            # Format amounts
            usd_str = f"{usd_amount:.2f}"
            ngn_str = f"{ngn_amount:,.2f}"
            
            # Mask account number for security
            account_display = f"****{account_number[-4:]}" if len(account_number) >= 4 else account_number
            
            # Truncate reference for display
            ref_display = f"{bank_reference[:12]}...{bank_reference[-4:]}" if len(bank_reference) > 16 else bank_reference
            
            # Create unified message
            message = (
                f"✅ Bank Transfer Complete!\n\n"
                f"💰 Amount: ₦{ngn_str} (${usd_str})\n"
                f"🏦 To: {bank_name} • {account_display}\n"
                f"🆔 Ref: {cashout_id}\n"
                f"🏦 Bank Ref: {ref_display}\n\n"
                f"⏰ Arrives in 1-5 minutes\n"
                f"Use /wallet to view your balance."
            )
            
            # Create notification request
            notification_request = NotificationRequest(
                user_id=user_id,
                category=NotificationCategory.PAYMENTS,
                priority=NotificationPriority.HIGH,
                title=f"Bank Transfer Complete: ₦{ngn_str}",
                message=message,
                template_data={
                    'cashout_id': cashout_id,
                    'usd_amount': usd_str,
                    'ngn_amount': ngn_str,
                    'bank_name': bank_name,
                    'account_display': account_display,
                    'bank_reference': bank_reference,
                    'transfer_type': 'ngn_bank_transfer'
                },
                channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL],
                require_delivery=True,
                broadcast_mode=False
            )
            
            # Send via unified system
            delivery_results = await self.notification_service.send_notification(notification_request)
            
            # Check if at least one channel succeeded
            successful_channels = [
                channel for channel, result in delivery_results.items()
                if hasattr(result, 'status') and result.status.value in ['sent', 'delivered']
            ]
            
            if successful_channels:
                logger.info(f"✅ NGN_UNIFIED_NOTIFICATION_SUCCESS: {cashout_id} delivered via {successful_channels}")
                return True
            else:
                logger.warning(f"⚠️ NGN_UNIFIED_NOTIFICATION_FAILED: {cashout_id} - no successful channels")
                return False
                
        except Exception as e:
            logger.error(f"❌ NGN_UNIFIED_NOTIFICATION_ERROR: {cashout_id} error: {e}")
            return False
    
    async def _send_telegram_notification(
        self,
        user_id: int,
        cashout_id: str,
        usd_amount: float,
        ngn_amount: float,
        bank_name: str,
        account_number: str,
        bank_reference: str
    ) -> bool:
        """Send Telegram notification with NGN bank transfer completion details"""
        
        try:
            # Format amounts
            usd_str = f"{usd_amount:.2f}"
            ngn_str = f"{ngn_amount:,.2f}"
            
            # Mask account number for security
            account_display = f"****{account_number[-4:]}" if len(account_number) >= 4 else account_number
            
            # Truncate reference for display
            ref_display = f"{bank_reference[:12]}...{bank_reference[-4:]}" if len(bank_reference) > 16 else bank_reference
            
            # Compose message
            message = (
                "✅ <b>Bank Transfer Complete!</b>\n\n"
                f"💰 <b>Amount:</b> ₦{ngn_str} (${usd_str})\n"
                f"🏦 <b>To:</b> {bank_name} • {account_display}\n"
                f"🆔 <b>Ref:</b> <code>{cashout_id}</code>\n"
                f"🏦 <b>Bank Ref:</b> <code>{ref_display}</code>\n\n"
                "⏰ <i>Arrives in 1-5 minutes</i>\n"
                "📧 <i>Tap refs to copy • Check email for details</i>"
            )
            
            # Send message
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error sending NGN transfer notification to {user_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram NGN transfer notification: {str(e)}")
            return False
    
    async def _send_email_notification(
        self,
        user_email: str,
        cashout_id: str,
        usd_amount: float,
        ngn_amount: float,
        bank_name: str,
        account_number: str,
        bank_reference: str
    ) -> bool:
        """Send email notification with complete NGN transfer details"""
        
        try:
            # Format amounts
            usd_str = f"{usd_amount:.2f}"
            ngn_str = f"{ngn_amount:,.2f}"
            
            # Email subject
            subject = f"✅ Sent: ₦{ngn_str} (${usd_str})"
            
            # Email body (HTML)
            email_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
                <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h2 style="color: #28a745; margin: 0;">✅ Bank Transfer Complete</h2>
                        <p style="color: #6c757d; margin: 10px 0 0 0;">Your NGN bank transfer has been successfully processed</p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                        <h3 style="color: #343a40; margin: 0 0 15px 0;">Transfer Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #495057;">Amount (USD):</td>
                                <td style="padding: 8px 0; color: #212529;">${usd_str}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #495057;">Amount (NGN):</td>
                                <td style="padding: 8px 0; color: #212529;">₦{ngn_str}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #495057;">Cashout ID:</td>
                                <td style="padding: 8px 0; color: #212529; font-family: monospace;">{cashout_id}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #495057;">Bank:</td>
                                <td style="padding: 8px 0; color: #212529;">{bank_name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #495057;">Account:</td>
                                <td style="padding: 8px 0; color: #212529;">{account_number}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #495057;">Bank Reference:</td>
                                <td style="padding: 8px 0; color: #212529; font-family: monospace; word-break: break-all;">{bank_reference}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">
                        <h4 style="color: #0056b3; margin: 0 0 10px 0;">📋 What This Means</h4>
                        <p style="color: #495057; margin: 0; line-height: 1.5;">
                            Your NGN bank transfer has been successfully processed and sent to your {bank_name} account. 
                            The funds should appear in your account within 1-5 minutes. Use the bank reference number for any inquiries with your bank.
                        </p>
                    </div>
                    
                    <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; margin-top: 20px;">
                        <h4 style="color: #664d03; margin: 0 0 10px 0;">📱 Next Steps</h4>
                        <ul style="color: #495057; margin: 0; padding-left: 20px; line-height: 1.5;">
                            <li>Check your bank app or SMS notifications</li>
                            <li>Contact your bank if funds don't arrive within 30 minutes</li>
                            <li>Keep this email as proof of transaction</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                        <p style="color: #6c757d; margin: 0; font-size: 14px;">
                            Thank you for using LockBay • Secure Cryptocurrency Trading Platform
                        </p>
                    </div>
                </div>
            </div>
            """
            
            # Send email
            success = self.email_service.send_email(
                to_email=user_email,
                subject=subject,
                html_content=email_body
            )
            
            if success:
                logger.info(f"NGN transfer completion email sent to {user_email} for {cashout_id}")
            else:
                logger.error(f"Failed to send NGN transfer completion email to {user_email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending NGN transfer completion email: {str(e)}")
            return False
    
    async def send_test_notification(
        self,
        user_id: int,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send test NGN notification for testing purposes"""
        
        # Test data
        test_data = {
            'cashout_id': 'NGN_240907_001',
            'usd_amount': 50.0,
            'ngn_amount': 76000.0,
            'bank_name': 'Access Bank',
            'account_number': '0123456789',
            'bank_reference': 'FIN_TXN_ABC123DEF456GHI789'
        }
        
        try:
            success = await self.send_ngn_completion_notification(
                user_id=user_id,
                cashout_id=test_data['cashout_id'],
                usd_amount=test_data['usd_amount'],
                ngn_amount=test_data['ngn_amount'],
                bank_name=test_data['bank_name'],
                account_number=test_data['account_number'],
                bank_reference=test_data['bank_reference'],
                user_email=user_email
            )
            
            return {
                'success': success,
                'message': 'Test NGN notification sent successfully' if success else 'Test notification failed',
                'test_data': test_data
            }
            
        except Exception as e:
            logger.error(f"Error sending test NGN notification: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Test NGN notification failed with error'
            }


# Global instance for use across the application
ngn_notification = NGNNotificationService()
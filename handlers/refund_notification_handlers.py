"""
Missing Refund Notification Handlers
Implements callback handlers for refund notification buttons that were missing
"""

import logging
from datetime import datetime
from typing import Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, Application, CallbackQueryHandler
from telegram.constants import ParseMode

from database import SessionLocal
from models import User, Refund, RefundStatus
from utils.callback_utils import safe_answer_callback_query, safe_edit_message_text
from utils.admin_security import is_admin_secure
from handlers.commands import get_user_from_update
from config import Config
from utils.enhanced_audit_logger import audit_logger

logger = logging.getLogger(__name__)


class RefundNotificationHandlers:
    """Handlers for refund notification callbacks with security validation"""
    
    @staticmethod
    async def _validate_refund_ownership(refund_id: str, user: User) -> Tuple[Optional[Refund], bool]:
        """Validate that the refund_id belongs to the requesting user
        
        Args:
            refund_id: The refund ID to validate
            user: The user requesting access
            
        Returns:
            Tuple of (Refund object or None, is_authorized)
        """
        session = SessionLocal()
        try:
            refund = session.query(Refund).filter(
                Refund.refund_id == refund_id
            ).first()
            
            if not refund:
                logger.warning(f"🔒 SECURITY: User {user.id} attempted access to non-existent refund {refund_id}")
                audit_logger.log_security_event(
                    user_id=user.id,
                    event_type="refund_access_attempt",
                    severity="medium",
                    details={
                        "refund_id": refund_id,
                        "reason": "refund_not_found",
                        "user_telegram_id": user.telegram_id
                    }
                )
                return None, False
                
            # Check ownership
            if refund.user_id != user.id:
                logger.error(f"🚨 SECURITY VIOLATION: User {user.id} attempted unauthorized access to refund {refund_id} (owner: {refund.user_id})")
                audit_logger.log_security_event(
                    user_id=user.id,
                    event_type="unauthorized_refund_access",
                    severity="high", 
                    details={
                        "refund_id": refund_id,
                        "actual_owner_id": refund.user_id,
                        "attempted_by": user.id,
                        "user_telegram_id": user.telegram_id,
                        "reason": "ownership_violation"
                    }
                )
                return refund, False
                
            # Access authorized
            logger.info(f"✅ SECURITY: User {user.id} authorized access to refund {refund_id}")
            return refund, True
            
        except Exception as e:
            logger.error(f"❌ SECURITY: Error validating refund ownership for {refund_id}: {e}")
            audit_logger.log_security_event(
                user_id=user.id if user else None,
                event_type="refund_validation_error",
                severity="high",
                details={
                    "refund_id": refund_id,
                    "error": str(e),
                    "user_telegram_id": user.telegram_id if user else None
                }
            )
            return None, False
        finally:
            session.close()
    
    @staticmethod
    async def handle_confirm_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle confirm_notification_{refund_id} callbacks with authorization validation"""
        try:
            query = update.callback_query
            await safe_answer_callback_query(query, "✅ Acknowledged")
            
            # Extract refund ID from callback data
            callback_data = query.data
            refund_id = callback_data.replace("confirm_notification_", "")
            
            user = await get_user_from_update(update)
            if not user:
                await safe_edit_message_text(
                    query,
                    "❌ User session expired. Please use /start to continue.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
                
            # SECURITY: Validate refund ownership
            refund, is_authorized = await RefundNotificationHandlers._validate_refund_ownership(refund_id, user)
            if not is_authorized:
                await safe_edit_message_text(
                    query,
                    "🔒 **Access Denied**\n\nYou don't have permission to access this refund notification. This incident has been logged.\n\nIf you believe this is an error, please contact support.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                        [InlineKeyboardButton("💬 Contact Support", callback_data="create_ticket_general")]
                    ]),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Update message to show acknowledgment
            acknowledged_text = f"""✅ **Notification Acknowledged**

Thank you for confirming receipt of this refund notification.

**Refund ID:** `{refund_id}`
**Status:** Acknowledged by user
**Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC

If you need further assistance, use the buttons below:"""
            
            keyboard = [
                [InlineKeyboardButton("🔍 Check Refund Status", callback_data=f"refund_status_{refund_id}")],
                [InlineKeyboardButton("💬 Contact Support", callback_data=f"create_ticket_{refund_id}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            await safe_edit_message_text(
                query,
                acknowledged_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"✅ User {user.id} acknowledged refund notification {refund_id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling confirm_notification: {e}")
            await safe_answer_callback_query(
                update.callback_query,
                "❌ Error processing acknowledgment",
                show_alert=True
            )
    
    @staticmethod
    async def handle_callback_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback_request_{refund_id} callbacks with authorization validation"""
        try:
            query = update.callback_query
            await safe_answer_callback_query(query, "📞 Callback request received")
            
            # Extract refund ID from callback data
            callback_data = query.data
            refund_id = callback_data.replace("callback_request_", "")
            
            user = await get_user_from_update(update)
            if not user:
                await safe_edit_message_text(
                    query,
                    "❌ User session expired. Please use /start to continue.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
                
            # SECURITY: Validate refund ownership
            refund, is_authorized = await RefundNotificationHandlers._validate_refund_ownership(refund_id, user)
            if not is_authorized:
                await safe_edit_message_text(
                    query,
                    "🔒 **Access Denied**\n\nYou don't have permission to request a callback for this refund. This incident has been logged.\n\nIf you believe this is an error, please contact support.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                        [InlineKeyboardButton("💬 Contact Support", callback_data="create_ticket_general")]
                    ]),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Show callback request confirmation
            callback_text = f"""📞 **Callback Request Submitted**

Your callback request has been received and forwarded to our support team.

**Refund ID:** `{refund_id}`
**User:** {user.username or user.first_name}
**Contact:** {user.email or 'Not provided'}
**Request Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC

📋 **What happens next:**
• Our support team will review your request
• You'll be contacted within 24 hours
• We'll discuss your refund status and any questions

**Need immediate help?** Use the support ticket option below."""
            
            keyboard = [
                [InlineKeyboardButton("🎫 Create Support Ticket", callback_data=f"create_ticket_{refund_id}")],
                [InlineKeyboardButton("📋 Refund FAQ", callback_data="refund_faq")],
                [InlineKeyboardButton("🔍 Check Status", callback_data=f"refund_status_{refund_id}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            await safe_edit_message_text(
                query,
                callback_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log the callback request for admin follow-up
            logger.info(f"📞 CALLBACK_REQUEST: User {user.id} ({user.username}) requested callback for refund {refund_id}")
            
            # TODO: Send notification to admin team about callback request
            
        except Exception as e:
            logger.error(f"❌ Error handling callback_request: {e}")
            await safe_answer_callback_query(
                update.callback_query,
                "❌ Error processing callback request",
                show_alert=True
            )
    
    @staticmethod
    async def handle_create_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle create_ticket_{refund_id} callbacks with authorization validation"""
        try:
            query = update.callback_query
            await safe_answer_callback_query(query, "🎫 Creating support ticket...")
            
            # Extract refund ID from callback data
            callback_data = query.data
            refund_id = callback_data.replace("create_ticket_", "")
            
            # Handle general ticket creation (no refund_id validation needed)
            if refund_id == "general":
                user = await get_user_from_update(update)
                if not user:
                    await safe_edit_message_text(
                        query,
                        "❌ User session expired. Please use /start to continue.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                # Proceed with general ticket creation (skip ownership validation)
            else:
                user = await get_user_from_update(update)
                if not user:
                    await safe_edit_message_text(
                        query,
                        "❌ User session expired. Please use /start to continue.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                    
                # SECURITY: Validate refund ownership for refund-specific tickets
                refund, is_authorized = await RefundNotificationHandlers._validate_refund_ownership(refund_id, user)
                if not is_authorized:
                    await safe_edit_message_text(
                        query,
                        "🔒 **Access Denied**\n\nYou don't have permission to create a ticket for this refund. This incident has been logged.\n\nYou can still create a general support ticket if needed.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🎫 General Support Ticket", callback_data="create_ticket_general")],
                            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                        ]),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
            
            # Show support ticket creation interface
            ticket_text = f"""🎫 **Support Ticket - Refund Issue**

**Refund ID:** `{refund_id}`
**User:** {user.username or user.first_name}
**Ticket Type:** Refund Support
**Created:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC

📝 **Describe your issue:**
Please reply with a message describing your refund-related question or concern. Our support team will respond as soon as possible.

**Common Issues:**
• Refund not received
• Incorrect refund amount  
• Refund processing delays
• Questions about refund status
• Technical issues with refund

**Response Time:** Usually within 4-8 hours"""
            
            keyboard = [
                [InlineKeyboardButton("❓ View Common Solutions", callback_data="refund_faq")],
                [InlineKeyboardButton("🔍 Check Refund Status", callback_data=f"refund_status_{refund_id}")],
                [InlineKeyboardButton("📞 Request Callback", callback_data=f"callback_request_{refund_id}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            await safe_edit_message_text(
                query,
                ticket_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Set context for ticket creation
            context.user_data['creating_support_ticket'] = {
                'refund_id': refund_id,
                'user_id': user.id,
                'created_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"🎫 SUPPORT_TICKET: User {user.id} creating ticket for refund {refund_id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling create_ticket: {e}")
            await safe_answer_callback_query(
                update.callback_query,
                "❌ Error creating support ticket",
                show_alert=True
            )
    
    @staticmethod
    async def handle_refund_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle refund_faq callbacks"""
        try:
            query = update.callback_query
            await safe_answer_callback_query(query, "📋 Loading FAQ...")
            
            # Show comprehensive refund FAQ
            faq_text = f"""📋 **{Config.PLATFORM_NAME} - Refund FAQ**

**🔄 How long do refunds take?**
• Escrow refunds: Usually instant
• Exchange refunds: 5-15 minutes  
• Bank refunds: 1-3 business days
• Crypto refunds: 15-60 minutes

**💰 Will I receive the full amount?**
• Yes, minus any transaction fees already incurred
• Network fees for crypto are deducted
• Bank transfer fees may apply

**❓ Why was my transaction refunded?**
• Payment timeout (seller didn't confirm)
• Exchange rate lock expired
• Trade cancelled by counterparty
• System error or technical issue

**🔍 How to track refund status?**
• Use the "Check Status" button
• Check your wallet balance
• Look for email notifications

**📞 Need more help?**
• Create a support ticket
• Request a callback
• Email: {getattr(Config, 'SUPPORT_EMAIL', 'support@platform.com')}

**🛡️ Security Notice:**
All refunds are processed automatically by our secure system. We never ask for passwords or private keys."""
            
            keyboard = [
                [InlineKeyboardButton("🎫 Create Support Ticket", callback_data="create_ticket_general")],
                [InlineKeyboardButton("💰 Check My Wallet", callback_data="menu_wallet")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
            
            await safe_edit_message_text(
                query,
                faq_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"📋 User {update.effective_user.id if update.effective_user else 'None'} viewed refund FAQ")
            
        except Exception as e:
            logger.error(f"❌ Error handling refund_faq: {e}")
            await safe_answer_callback_query(
                update.callback_query,
                "❌ Error loading FAQ",
                show_alert=True
            )
    
    @staticmethod
    async def handle_refund_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle refund_status_{refund_id} callbacks with enhanced authorization validation"""
        try:
            query = update.callback_query
            await safe_answer_callback_query(query, "🔍 Checking refund status...")
            
            # Extract refund ID from callback data
            callback_data = query.data
            refund_id = callback_data.replace("refund_status_", "")
            
            user = await get_user_from_update(update)
            if not user:
                await safe_edit_message_text(
                    query,
                    "❌ User session expired. Please use /start to continue.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # SECURITY: Use centralized ownership validation
            refund, is_authorized = await RefundNotificationHandlers._validate_refund_ownership(refund_id, user)
            if not is_authorized:
                await safe_edit_message_text(
                    query,
                    "🔒 **Access Denied**\n\nYou don't have permission to view this refund status. This incident has been logged.\n\nIf you believe this is an error, please contact support.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                        [InlineKeyboardButton("💬 Contact Support", callback_data="create_ticket_general")]
                    ]),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Process authorized request
            try:
                
                if not refund:
                    # This should not happen due to validation above, but handle gracefully
                    status_text = f"""🔍 **Refund Status Lookup**

**Refund ID:** `{refund_id}`
**Status:** Not found in database

This could mean:
• Refund ID is incorrect
• Refund is being processed by external system
• Transaction was not actually refunded

**Next Steps:**
• Verify the refund ID is correct
• Check your wallet balance
• Contact support if you believe this is an error"""
                else:
                    # Show refund details
                    status_emoji = {
                        RefundStatus.PENDING: "⏳",
                        RefundStatus.PROCESSING: "🔄", 
                        RefundStatus.COMPLETED: "✅",
                        RefundStatus.FAILED: "❌",
                        RefundStatus.CANCELLED: "🚫"
                    }.get(refund.status, "❓")
                    
                    status_text = f"""🔍 **Refund Status**

**Refund ID:** `{refund_id}`
**Status:** {status_emoji} {refund.status.value if refund.status else 'Unknown'}
**Amount:** ${refund.amount:.2f} USD
**Type:** {refund.refund_type.value if refund.refund_type else 'Unknown'}
**Created:** {refund.created_at.strftime('%Y-%m-%d %H:%M')} UTC

**Transaction Details:**
• Original TX: `{refund.transaction_id or 'N/A'}`
• Refund TX: `{refund.refund_transaction_id or 'Processing...'}`

**Last Update:** {refund.updated_at.strftime('%Y-%m-%d %H:%M')} UTC"""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Refresh Status", callback_data=f"refund_status_{refund_id}")],
                    [InlineKeyboardButton("💰 Check Wallet", callback_data="menu_wallet")],
                    [InlineKeyboardButton("💬 Contact Support", callback_data=f"create_ticket_{refund_id}")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                
                await safe_edit_message_text(
                    query,
                    status_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                
            except Exception as db_error:
                logger.error(f"❌ Database error in refund_status: {db_error}")
                await safe_edit_message_text(
                    query,
                    "❌ **Database Error**\n\nThere was an error retrieving refund status. Please try again later or contact support.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Try Again", callback_data=f"refund_status_{refund_id}")],
                        [InlineKeyboardButton("💬 Contact Support", callback_data="create_ticket_general")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                    ]),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            logger.info(f"🔍 User {user.id} checked status for refund {refund_id}")
            
        except Exception as e:
            logger.error(f"❌ Error handling refund_status: {e}")
            await safe_answer_callback_query(
                update.callback_query,
                "❌ Error checking refund status",
                show_alert=True
            )
    
    @staticmethod
    def register_handlers(application: Application):
        """Register all refund notification handlers"""
        try:
            # Confirm notification callbacks
            application.add_handler(CallbackQueryHandler(
                RefundNotificationHandlers.handle_confirm_notification,
                pattern=r"^confirm_notification_(.+)$"
            ))
            
            # Callback request callbacks  
            application.add_handler(CallbackQueryHandler(
                RefundNotificationHandlers.handle_callback_request,
                pattern=r"^callback_request_(.+)$"
            ))
            
            # Create ticket callbacks
            application.add_handler(CallbackQueryHandler(
                RefundNotificationHandlers.handle_create_ticket,
                pattern=r"^create_ticket_(.+)$"
            ))
            
            # General ticket creation
            application.add_handler(CallbackQueryHandler(
                RefundNotificationHandlers.handle_create_ticket,
                pattern=r"^create_ticket_general$"
            ))
            
            # Refund FAQ callbacks
            application.add_handler(CallbackQueryHandler(
                RefundNotificationHandlers.handle_refund_faq,
                pattern=r"^refund_faq$"
            ))
            
            # Refund status check callbacks
            application.add_handler(CallbackQueryHandler(
                RefundNotificationHandlers.handle_refund_status,
                pattern=r"^refund_status_(.+)$"
            ))
            
            logger.info("✅ Refund notification handlers registered successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to register refund notification handlers: {e}")


# Global registry function for easy import
def register_refund_notification_handlers(application: Application):
    """Global function to register refund notification handlers"""
    RefundNotificationHandlers.register_handlers(application)
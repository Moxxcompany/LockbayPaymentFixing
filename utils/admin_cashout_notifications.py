#!/usr/bin/env python3
"""
Admin CashOut Notification System
Enhanced notifications for cashout processing with urgency indicators
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from telegram import Bot
from config import Config
from utils.admin_security import AdminSecurity
from models import Cashout, User, Escrow, CashoutType

logger = logging.getLogger(__name__)


async def notify_admin_cashout_created(session, cashout_request: Cashout, escrow: Optional[Escrow] = None):
    """Send admin notification when cashout request is created"""
    try:
        # Check if notifications are enabled
        if not Config.ADMIN_CASHOUT_CREATION_ALERTS:
            logger.debug("Admin cashout creation alerts disabled")
            return
            
        if not Config.BOT_TOKEN:
            logger.warning("Bot token not configured for admin cashout notifications")
            return
            
        # Get user info
        user = session.query(User).filter(User.id == cashout_request.user_id).first()
        if not user:
            logger.error(f"User not found for cashout {cashout_request.id}")
            return
            
        # Format cashout details
        amount = cashout_request.amount
        currency = cashout_request.currency or "CRYPTO"
        
        if currency == "NGN":
            amount_display = f"₦{amount:,.2f}"
        else:
            amount_display = f"${amount:.2f} {currency}"
            
        # Get detailed destination info
        if cashout_request.cashout_type == CashoutType.NGN_BANK.value:
            # Parse bank details from destination (format: bank_code:account_number)
            destination_parts = cashout_request.destination.split(":")
            if len(destination_parts) == 2:
                bank_code, account_number = destination_parts
                # Get bank name from saved accounts
                from models import SavedBankAccount
                bank_account = session.query(SavedBankAccount).filter(
                    SavedBankAccount.user_id == cashout_request.user_id,
                    SavedBankAccount.bank_code == bank_code,
                    SavedBankAccount.account_number == account_number
                ).first()
                
                if bank_account:
                    destination = f"🏦 {bank_account.bank_name}\n📱 {bank_account.account_number} ({bank_account.account_name})"
                else:
                    destination = f"🏦 Bank Code: {bank_code}\n📱 Account: {account_number}"
            else:
                destination = "🏦 Bank Account (Details TBA)"
        else:
            # Parse crypto details from destination (format: address:network)
            destination_parts = cashout_request.destination.split(":")
            if len(destination_parts) == 2:
                address, network = destination_parts
                destination = f"💎 {network}\n📍 {address}"
            else:
                address = cashout_request.destination
                destination = f"💎 Crypto Address\n📍 {address}"
            
        # Format created time
        created_time = cashout_request.created_at.strftime("%H:%M:%S")
        
        # Build escrow context
        escrow_info = ""
        if escrow:
            escrow_info = f"\n🔗 From Escrow: #{escrow.escrow_id}"
            
        message = f"""🚨 NEW CASHOUT REQUEST CREATED

🆔 Cashout: {cashout_request.cashout_id or f'W{cashout_request.id}'}
👤 User: {user.first_name} (@{user.username or 'N/A'})
📧 Email: {user.email or 'Not provided'}
💰 Amount: {amount_display}
📍 Destination:
{destination}{escrow_info}
⏰ Created: {created_time}

⚠️ REQUIRES MANUAL APPROVAL
🔧 Use /admin → Manual Operations → Manual CashOuts"""

        # Send to all configured admins
        bot = Bot(Config.BOT_TOKEN)
        # SECURITY FIX: Get admin IDs directly without triggering security alerts
        import os
        admin_ids_env = os.getenv("ADMIN_IDS", "").strip()
        if admin_ids_env:
            admin_ids = [int(id.strip()) for id in admin_ids_env.split(",") if id.strip()]
        else:
            admin_ids = []
            logger.warning("No admin IDs configured for cashout notifications")
        
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
                logger.info(f"Cashout creation notification sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send cashout creation notification to admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in notify_admin_cashout_created: {e}")


async def notify_admin_cashout_confirmation(session, cashout_request: Cashout, urgency_level: str = "NEW"):
    """Send admin notification when cashout needs processing with urgency indicators"""
    try:
        if not Config.BOT_TOKEN:
            logger.warning("Bot token not configured for admin cashout notifications")
            return
            
        # Get user info
        user = session.query(User).filter(User.id == cashout_request.user_id).first()
        if not user:
            logger.error(f"User not found for cashout {cashout_request.id}")
            return
            
        # Calculate urgency based on age
        created_at = cashout_request.created_at
        age_minutes = (datetime.utcnow() - created_at).total_seconds() / 60
        
        if age_minutes <= 15:
            urgency_icon = "⚡"
            urgency_text = "NEW"
        elif age_minutes <= 30:
            urgency_icon = "🔥" 
            urgency_text = "PRIORITY"
        else:
            urgency_icon = "🚨"
            urgency_text = "URGENT HIGH PRIORITY"
            
        # Format age display
        if age_minutes < 60:
            age_display = f"{int(age_minutes)} minutes old"
        else:
            age_display = f"{int(age_minutes/60)} hours old"
            
        # Format cashout details
        amount = cashout_request.amount
        currency = cashout_request.currency or "CRYPTO"
        
        if currency == "NGN":
            amount_display = f"₦{amount:,.2f}"
            process_type = "NGN Bank Transfer"
        else:
            amount_display = f"${amount:.2f} {currency}"
            process_type = "Crypto Cashout"
            
        # Get destination info
        if cashout_request.currency == "NGN":
            destination = "Bank Account"
        else:
            address = cashout_request.address or "TBA"
            network = cashout_request.network or "TRC20"
            destination = f"{address[:12]}...{address[-8:]}" if len(address) > 20 else address
            
        # Format created time
        created_time = created_at.strftime("%H:%M:%S")
        
        message = f"""🔧 MANUAL CASHOUT PROCESSING REQUIRED

{urgency_icon} {urgency_text} - {age_display}

📋 Cashout: {cashout_request.utid or f'W{cashout_request.id}'}
👤 User ID: {user.telegram_id}
💰 Amount: {amount_display}
📍 Destination: {destination}
⏰ Created: {created_time}

✅ Ready for {process_type.lower()} processing
🔧 Use /admin_manual_ops to approve"""

        # Send to all configured admins
        bot = Bot(Config.BOT_TOKEN)
        # SECURITY FIX: Get admin IDs directly without triggering security alerts
        import os
        admin_ids_env = os.getenv("ADMIN_IDS", "").strip()
        if admin_ids_env:
            admin_ids = [int(id.strip()) for id in admin_ids_env.split(",") if id.strip()]
        else:
            admin_ids = []
            logger.warning("No admin IDs configured for cashout notifications")
        
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
                logger.info(f"Cashout confirmation notification sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send cashout confirmation notification to admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in notify_admin_cashout_confirmation: {e}")


def get_cashout_urgency_level(cashout_request: Cashout) -> Dict[str, str]:
    """Get urgency level and display info for a cashout based on age"""
    age_minutes = (datetime.utcnow() - cashout_request.created_at).total_seconds() / 60
    
    if age_minutes <= 15:
        return {
            "icon": "⚡",
            "level": "NEW",
            "age_display": f"{int(age_minutes)} minutes old"
        }
    elif age_minutes <= 30:
        return {
            "icon": "🔥",
            "level": "PRIORITY", 
            "age_display": f"{int(age_minutes)} minutes old"
        }
    else:
        hours = int(age_minutes / 60)
        return {
            "icon": "🚨",
            "level": "URGENT HIGH PRIORITY",
            "age_display": f"{hours} hours old" if hours > 0 else f"{int(age_minutes)} minutes old"
        }


async def notify_admin_cashout_ready_for_processing(cashout_request: Cashout):
    """Notify admins when cashout is ready for manual processing (like exchange crypto notifications)"""
    try:
        if not Config.BOT_TOKEN:
            logger.warning("Bot token not configured for admin cashout notifications")
            return
            
        from database import SessionLocal
        session = SessionLocal()
        
        try:
            # Get user info
            user = session.query(User).filter(User.id == cashout_request.user_id).first()
            if not user:
                logger.error(f"User not found for cashout {cashout_request.id}")
                return
                
            # Get urgency info
            urgency_info = get_cashout_urgency_level(cashout_request)
            
            # Format cashout details
            amount = cashout_request.amount
            currency = cashout_request.currency or "CRYPTO"
            
            if currency == "NGN":
                amount_display = f"₦{amount:,.2f}"
                process_type = "NGN Bank Transfer"
            else:
                amount_display = f"${amount:.2f} {currency}"
                process_type = "Crypto Cashout"
                
            # Get destination info
            if cashout_request.currency == "NGN":
                destination = "Bank Account"
            else:
                address = cashout_request.address or "TBA"
                network = cashout_request.network or "TRC20"
                destination = f"{address[:12]}...{address[-8:]}" if len(address) > 20 else address
                
            # Format created time
            created_time = cashout_request.created_at.strftime("%H:%M:%S")
            
            message = f"""🔧 MANUAL CASHOUT PROCESSING REQUIRED

{urgency_info['icon']} {urgency_info['level']} - {urgency_info['age_display']}

📋 Cashout: {cashout_request.utid or f'W{cashout_request.id}'}
👤 User ID: {user.telegram_id}
💰 Amount: {amount_display}
📍 Destination: {destination}
⏰ Created: {created_time}

✅ Ready for {process_type.lower()} processing
🔧 Use /admin_manual_ops to approve"""

            # Send to all configured admins
            bot = Bot(Config.BOT_TOKEN)
            # SECURITY FIX: Get admin IDs directly without triggering security alerts
            import os
            admin_ids_env = os.getenv("ADMIN_IDS", "").strip()
            if admin_ids_env:
                admin_ids = [int(id.strip()) for id in admin_ids_env.split(",") if id.strip()]
            else:
                admin_ids = []
                logger.warning("No admin IDs configured for cashout notifications")
                
            for admin_id in admin_ids:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Cashout processing notification sent to admin {admin_id}")
                except Exception as e:
                    logger.error(f"Failed to send cashout processing notification to admin {admin_id}: {e}")
                    
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in notify_admin_cashout_ready_for_processing: {e}")


async def notify_admin_critical_cashout_failure(cashout_request: Cashout, failure_reason: str = "Critical failure"):
    """Send URGENT admin notification for critical cashout failures requiring immediate attention"""
    try:
        if not Config.BOT_TOKEN:
            logger.warning("Bot token not configured for critical admin notifications")
            return
            
        from database import SessionLocal
        session = SessionLocal()
        
        try:
            # Get user info
            user = session.query(User).filter(User.id == cashout_request.user_id).first()
            if not user:
                logger.error(f"User not found for critical cashout failure {cashout_request.id}")
                return
                
            # Format cashout details
            amount = cashout_request.amount
            currency = cashout_request.currency or "CRYPTO"
            
            if currency == "NGN":
                amount_display = f"₦{amount:,.2f}"
                process_type = "NGN Bank Transfer"
            else:
                amount_display = f"${amount:.2f} {currency}"
                process_type = "Crypto Cashout"
                
            # Format created time
            created_time = cashout_request.created_at.strftime("%H:%M:%S")
            current_time = datetime.now().strftime("%H:%M:%S")
            
            message = f"""🚨🚨 CRITICAL CASHOUT FAILURE - IMMEDIATE ACTION REQUIRED 🚨🚨

❌ CUSTOMER FUNDS AT RISK ❌

📋 Cashout ID: {cashout_request.utid or f'W{cashout_request.id}'}
👤 User: {user.first_name} (@{user.username or 'N/A'}) - ID: {user.telegram_id}
💰 Amount: {amount_display}
📍 Type: {process_type}
⏰ Created: {created_time}
🚨 Failed: {current_time}

🔥 FAILURE REASON:
{failure_reason}

⚠️ URGENT ACTION REQUIRED:
1. Check user wallet balance
2. Verify transfer status
3. Process manual refund if needed
4. Contact customer immediately

🔧 Use /admin_manual_ops to investigate"""

            # Send to all configured admins with high priority
            bot = Bot(Config.BOT_TOKEN)
            import os
            admin_ids_env = os.getenv("ADMIN_IDS", "").strip()
            if admin_ids_env:
                admin_ids = [int(id.strip()) for id in admin_ids_env.split(",") if id.strip()]
            else:
                admin_ids = []
                logger.warning("No admin IDs configured for critical failure notifications")
                
            for admin_id in admin_ids:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"CRITICAL cashout failure notification sent to admin {admin_id}")
                except Exception as e:
                    logger.error(f"CRITICAL: Failed to send failure notification to admin {admin_id}: {e}")
                    
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"CRITICAL ERROR in notify_admin_critical_cashout_failure: {e}")
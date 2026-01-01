"""
OTP Verification Handler - Dedicated handler for OTP verification during cashouts
Processes OTP codes for both crypto and NGN cashout verification
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_otp_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OTP verification input for cashouts"""
    try:
        user = update.effective_user
        text = update.message.text.strip()
        
        if not user or not text:
            return
            
        user_id = user.id
        wallet_state = context.user_data.get('wallet_state', '')
        
        logger.info(f"🔐 OTP_VERIFICATION: User {user_id} in state '{wallet_state}' sent OTP: '{text[:3]}***'")
        
        # Validate OTP format (6 digits)
        if not text.isdigit() or len(text) != 6:
            await update.message.reply_text(
                "❌ Invalid OTP format.\n\n"
                "Please enter the 6-digit verification code sent to your email."
            )
            return
        
        # Route to appropriate OTP verification based on wallet state
        if wallet_state == 'verifying_crypto_otp':
            return await handle_crypto_otp_verification(update, context, text)
        elif wallet_state == 'verifying_ngn_otp':
            return await handle_ngn_otp_verification(update, context, text)
        else:
            # Check other state indicators
            current_state = context.user_data.get('current_state', '')
            if current_state in ['VERIFYING_CRYPTO_OTP']:
                return await handle_crypto_otp_verification(update, context, text)
            elif current_state in ['VERIFYING_NGN_OTP']:
                return await handle_ngn_otp_verification(update, context, text)
            else:
                logger.warning(f"⚠️ OTP verification called but no clear verification state for user {user_id}")
                await update.message.reply_text(
                    "❌ Verification session not found.\n\n"
                    "Please start the cashout process again."
                )
                return
                
    except Exception as e:
        logger.error(f"❌ Error in OTP verification handler: {e}")
        await update.message.reply_text(
            "❌ An error occurred during verification. Please try again or contact support."
        )


async def handle_crypto_otp_verification(update: Update, context: ContextTypes.DEFAULT_TYPE, otp_code: str):
    """Handle crypto cashout OTP verification"""
    try:
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"🔐 Verifying crypto cashout OTP for user {user_id}: {otp_code[:3]}***")
        
        from services.cashout_otp_flow import CashoutOTPFlow
        from models import User
        from database import get_session
        
        # Get the database user record to use the correct database user ID
        with get_session() as session:
            db_user = session.query(User).filter(User.telegram_id == str(user_id)).first()
            if not db_user:
                logger.error(f"❌ Database user not found for Telegram ID {user_id}")
                await update.message.reply_text(
                    "❌ User verification failed.\n\n"
                    "Please start the cashout process again."
                )
                return
            
            database_user_id = db_user.id
            logger.info(f"🔗 Using database user ID {database_user_id} for Telegram user {user_id}")
        
        # Get the stored fingerprint from the cashout context
        fingerprint = context.user_data.get('cashout_data', {}).get('fingerprint')
        if not fingerprint:
            logger.error(f"❌ Missing fingerprint for crypto OTP verification - user {user_id}")
            await update.message.reply_text(
                "❌ Verification session expired.\n\n"
                "Please start the cashout process again."
            )
            return
        
        # Verify OTP using the cashout OTP flow service with database user ID
        result = CashoutOTPFlow.verify_otp_code(
            user_id=database_user_id,
            otp_code=otp_code,
            expected_fingerprint=fingerprint,
            channel='crypto'
        )
        
        if result.get('success'):
            logger.info(f"✅ Crypto cashout OTP verification successful for user {user_id}")
            
            # Clear wallet state since OTP is verified
            context.user_data['wallet_state'] = 'otp_verified'
            context.user_data['current_state'] = 'OTP_VERIFIED'
            
            # Process the crypto cashout
            from handlers.wallet_direct import handle_process_crypto_cashout
            await handle_process_crypto_cashout(update, context)
            return
            
        else:
            error_msg = result.get('error', 'Invalid verification code')
            remaining_attempts = result.get('remaining_attempts')
            
            logger.warning(f"❌ Crypto OTP verification failed for user {user_id}: {error_msg}")
            
            if remaining_attempts is not None and remaining_attempts > 0:
                await update.message.reply_text(
                    f"❌ {error_msg}\n\n"
                    f"You have {remaining_attempts} attempts remaining.\n"
                    "Please enter the correct 6-digit verification code."
                )
            else:
                await update.message.reply_text(
                    f"❌ {error_msg}\n\n"
                    "Please request a new verification code or contact support."
                )
            return
            
    except Exception as e:
        logger.error(f"❌ Error verifying crypto OTP for user {user.id}: {e}")
        await update.message.reply_text(
            "❌ An error occurred during verification.\n\n"
            "Please try again or contact support if the problem persists."
        )


async def handle_ngn_otp_verification(update: Update, context: ContextTypes.DEFAULT_TYPE, otp_code: str):
    """Handle NGN cashout OTP verification"""
    try:
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"🔐 Verifying NGN cashout OTP for user {user_id}: {otp_code[:3]}***")
        
        from services.cashout_otp_flow import CashoutOTPFlow
        from models import User
        from database import get_session
        
        # Get the database user record to use the correct database user ID
        with get_session() as session:
            db_user = session.query(User).filter(User.telegram_id == str(user_id)).first()
            if not db_user:
                logger.error(f"❌ Database user not found for Telegram ID {user_id}")
                await update.message.reply_text(
                    "❌ User verification failed.\n\n"
                    "Please start the cashout process again."
                )
                return
            
            database_user_id = db_user.id
        
        # Get the stored fingerprint from the cashout context
        fingerprint = context.user_data.get('cashout_data', {}).get('fingerprint')
        if not fingerprint:
            logger.error(f"❌ Missing fingerprint for NGN OTP verification - user {user_id}")
            await update.message.reply_text(
                "❌ Verification session expired.\n\n"
                "Please start the cashout process again."
            )
            return
        
        # Verify OTP using the cashout OTP flow service
        result = CashoutOTPFlow.verify_otp_code(
            user_id=database_user_id,
            otp_code=otp_code,
            expected_fingerprint=fingerprint,
            channel='ngn'
        )
        
        if result.get('success'):
            logger.info(f"✅ NGN cashout OTP verification successful for user {user_id}")
            
            # Clear wallet state since OTP is verified
            context.user_data['wallet_state'] = 'otp_verified'
            context.user_data['current_state'] = 'OTP_VERIFIED'
            
            # Process the NGN cashout
            from handlers.wallet_direct import handle_process_ngn_cashout
            await handle_process_ngn_cashout(update, context)
            return
            
        else:
            error_msg = result.get('error', 'Invalid verification code')
            remaining_attempts = result.get('remaining_attempts')
            
            logger.warning(f"❌ NGN OTP verification failed for user {user_id}: {error_msg}")
            
            if remaining_attempts is not None and remaining_attempts > 0:
                await update.message.reply_text(
                    f"❌ {error_msg}\n\n"
                    f"You have {remaining_attempts} attempts remaining.\n"
                    "Please enter the correct 6-digit verification code."
                )
            else:
                await update.message.reply_text(
                    f"❌ {error_msg}\n\n"
                    "Please request a new verification code or contact support."
                )
            return
            
    except Exception as e:
        logger.error(f"❌ Error verifying NGN OTP for user {user.id}: {e}")
        await update.message.reply_text(
            "❌ An error occurred during verification.\n\n"
            "Please try again or contact support if the problem persists."
        )
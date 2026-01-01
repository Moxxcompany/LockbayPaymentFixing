"""
Smart amount interface with dynamic minimums
Prevents user errors by showing real-time crypto minimums
"""

import logging
from decimal import Decimal
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.dynamic_minimum_calculator import DynamicMinimumCalculator

logger = logging.getLogger(__name__)

class SmartAmountInterface:
    """Create smart amount selection interfaces with dynamic minimums"""
    
    @classmethod
    async def create_amount_keyboard(cls, crypto_type: str) -> InlineKeyboardMarkup:
        """Create dynamic amount keyboard with real-time minimums"""
        try:
            suggestions = await DynamicMinimumCalculator.get_suggested_amounts(crypto_type)
            
            buttons = []
            
            # Row 1: Minimum and Small amounts
            buttons.append([
                InlineKeyboardButton(
                    f"💎 Min: ${suggestions['minimum']}", 
                    callback_data=f"amount:{suggestions['minimum']}"
                ),
                InlineKeyboardButton(
                    f"💰 ${suggestions['small']}", 
                    callback_data=f"amount:{suggestions['small']}"
                )
            ])
            
            # Row 2: Medium and Large amounts
            buttons.append([
                InlineKeyboardButton(
                    f"💵 ${suggestions['medium']}", 
                    callback_data=f"amount:{suggestions['medium']}"
                ),
                InlineKeyboardButton(
                    f"💸 ${suggestions['large']}", 
                    callback_data=f"amount:{suggestions['large']}"
                )
            ])
            
            # Row 3: Custom amount
            buttons.append([
                InlineKeyboardButton(
                    "✏️ Custom Amount", 
                    callback_data="amount:custom"
                )
            ])
            
            # Row 4: Back button
            buttons.append([
                InlineKeyboardButton("🔙 Back", callback_data="back_to_crypto")
            ])
            
            return InlineKeyboardMarkup(buttons)
            
        except Exception as e:
            logger.error(f"Error creating amount keyboard for {crypto_type}: {e}")
            # Fallback to static amounts
            return cls._create_fallback_keyboard()
    
    @classmethod
    async def create_amount_message(cls, crypto_type: str, user_balance: Decimal) -> str:
        """Create informative amount selection message"""
        try:
            minimum_usd = await DynamicMinimumCalculator.get_crypto_minimum_usd(crypto_type)
            
            message = f"💰 <b>{crypto_type.upper()} Cashout</b>\n\n"
            message += f"💳 Your balance: <b>${user_balance:.2f}</b>\n"
            
            if minimum_usd:
                message += f"📏 Current minimum: <b>${minimum_usd}</b>\n"
                message += f"💱 (Based on real-time {crypto_type} price)\n\n"
            
            message += "Select withdrawal amount:"
            
            return message
            
        except Exception as e:
            logger.error(f"Error creating amount message for {crypto_type}: {e}")
            return f"💰 <b>{crypto_type.upper()} Cashout</b>\n\nSelect withdrawal amount:"
    
    @classmethod 
    async def validate_custom_amount(cls, crypto_type: str, amount_str: str) -> dict:
        """Validate custom amount input with dynamic minimums"""
        try:
            amount = Decimal(amount_str)
            
            # Basic validation
            if amount <= 0:
                return {
                    "valid": False,
                    "error": "Amount must be greater than $0"
                }
            
            # Check against dynamic minimum
            validation = await DynamicMinimumCalculator.validate_amount_against_minimum(
                crypto_type, amount
            )
            
            if not validation["valid"]:
                return {
                    "valid": False,
                    "error": validation["message"],
                    "minimum_required": validation.get("minimum_required"),
                    "shortage": validation.get("shortage")
                }
            
            return {"valid": True, "amount": amount}
            
        except (ValueError, TypeError):
            return {
                "valid": False,
                "error": "Please enter a valid number (e.g., 25.50)"
            }
    
    @classmethod
    def _create_fallback_keyboard(cls) -> InlineKeyboardMarkup:
        """Fallback keyboard if dynamic calculation fails"""
        buttons = [
            [
                InlineKeyboardButton("💎 $25", callback_data="amount:25"),
                InlineKeyboardButton("💰 $50", callback_data="amount:50")
            ],
            [
                InlineKeyboardButton("💵 $100", callback_data="amount:100"), 
                InlineKeyboardButton("💸 $250", callback_data="amount:250")
            ],
            [InlineKeyboardButton("✏️ Custom Amount", callback_data="amount:custom")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_crypto")]
        ]
        return InlineKeyboardMarkup(buttons)
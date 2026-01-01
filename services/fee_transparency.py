"""
Fee Transparency Service
Handles upfront fee disclosure and acceptance before trade creation
"""

import logging
from decimal import Decimal
from typing import Dict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import Config

logger = logging.getLogger(__name__)


class FeeTransparencyService:
    """Service for transparent fee handling and user acceptance"""

    @staticmethod
    def calculate_fee_breakdown(amount: Decimal) -> Dict[str, Decimal]:
        """Calculate comprehensive fee breakdown"""
        platform_fee_rate = Decimal(str(Config.ESCROW_FEE_PERCENTAGE / 100))
        platform_fee = amount * platform_fee_rate
        total_amount = amount + platform_fee

        return {
            "base_amount": amount,
            "platform_fee": platform_fee,
            "platform_fee_rate": platform_fee_rate,
            "total_amount": total_amount,
        }

    @staticmethod
    async def show_fee_acceptance_dialog(
        amount: Decimal,
        seller_display: str,
        description: str,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
    ) -> None:
        """Show comprehensive fee acceptance dialog BEFORE trade creation"""

        fees = FeeTransparencyService.calculate_fee_breakdown(amount)

        fee_text = f"""💰 TRADE SUMMARY & FEES

📋 Trade Details:
• Seller: {seller_display}
• Item: {description[:50]}{'...' if len(description) > 50 else ''}

💵 Financial Breakdown:
• Trade Amount: ${fees['base_amount']:.2f} USD
• Platform Fee ({Config.ESCROW_FEE_PERCENTAGE:.0f}%): ${fees['platform_fee']:.2f} USD
═══════════════════════
• YOUR TOTAL: ${fees['total_amount']:.2f} USD

⚠️ IMPORTANT NOTICE:
• These fees are final and non-refundable once the trade begins
• Payment secures your funds in escrow until delivery
• Seller gets notified only after your payment confirms
• Full refund if seller declines (minus network fees if any)

🔒 ESCROW PROTECTION:
• Your money stays locked until you confirm delivery
• Dispute resolution available if issues arise
• Automatic refund if seller doesn't respond in 48h

Do you accept these fees and terms?"""

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ I Accept - Create Trade",
                        callback_data="accept_fees_create_trade",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❓ How do fees work?", callback_data="explain_fees"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Cancel - Go Back", callback_data="cancel_fee_acceptance"
                    )
                ],
            ]
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=fee_text,
            reply_markup=keyboard,
        )

    @staticmethod
    async def show_fee_explanation(
        context: ContextTypes.DEFAULT_TYPE, chat_id: int
    ) -> None:
        """Show detailed fee explanation"""

        explanation_text = f"""❓ HOW FEES WORK

🏦 Platform Fee ({Config.ESCROW_FEE_PERCENTAGE:.0f}%)
• Covers secure escrow service
• 24/7 dispute resolution
• Payment processing costs
• Platform maintenance & security

💡 Why Fees Are Charged:
• Guarantees seller payment upon delivery
• Provides insurance against fraud
• Maintains secure communication channels
• Funds customer support team

🆚 Compared to Alternatives:
• Bank wire transfers: 3-5% + fixed fees
• PayPal goods/services: 3.49% + $0.49
• Traditional escrow: 1-3% + $100+ setup
• {Config.PLATFORM_NAME}: {Config.ESCROW_FEE_PERCENTAGE:.0f}% only (no hidden fees)

🔒 What You Get:
✅ Military-grade encryption
✅ Funds held until delivery confirmed
✅ Professional dispute resolution
✅ 24/7 customer support
✅ Fraud protection guarantee

💰 Fee Structure:
• No setup fees
• No monthly charges  
• No hidden costs
• Only pay when you trade"""

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Accept Fees & Continue",
                        callback_data="accept_fees_create_trade",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 Back to Summary", callback_data="back_to_fee_summary"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Cancel Trade", callback_data="cancel_fee_acceptance"
                    )
                ],
            ]
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=explanation_text,
            reply_markup=keyboard,
        )

    @staticmethod
    def calculate_escrow_fees(amount: Decimal, buyer_id: int, seller_id: int) -> Dict[str, Decimal]:
        """Calculate escrow fees for given amount and participants
        
        Args:
            amount: Base escrow amount in USD
            buyer_id: Buyer user ID (for future customization)
            seller_id: Seller user ID (for future customization)
            
        Returns:
            Dict containing fee breakdown including platform_fee, total_amount, etc.
        """
        return FeeTransparencyService.calculate_fee_breakdown(amount)

    @staticmethod
    async def show_payment_method_with_fees(
        fees: Dict[str, Decimal],
        wallet_balance: Decimal,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
    ) -> None:
        """Show payment method selection with fee-inclusive amounts"""

        total_amount = fees["total_amount"]

        # Determine wallet payment availability
        if wallet_balance >= total_amount:
            wallet_text = (
                f"💰 Wallet Balance (${wallet_balance:.2f}) - Pay ${total_amount:.2f}"
            )
            wallet_callback = "payment_wallet"
        else:
            needed = total_amount - wallet_balance
            wallet_text = (
                f"💰 Wallet Balance (${wallet_balance:.2f}) - Need ${needed:.2f} more"
            )
            wallet_callback = "insufficient_wallet"

        payment_text = f"""💳 SELECT PAYMENT METHOD

Amount to pay: ${total_amount:.2f} USD
(Includes ${fees['platform_fee']:.2f} platform fee)

Choose your payment method:"""

        keyboard = [
            [InlineKeyboardButton(wallet_text, callback_data=wallet_callback)],
            [
                InlineKeyboardButton("₿ Bitcoin", callback_data="crypto_BTC"),
                InlineKeyboardButton("Ξ Ethereum", callback_data="crypto_ETH"),
                InlineKeyboardButton("₮ USDT", callback_data="crypto_USDT"),
            ],
            [
                InlineKeyboardButton("Ł Litecoin", callback_data="crypto_LTC"),
                InlineKeyboardButton("Ð Dogecoin", callback_data="crypto_DOGE"),
                InlineKeyboardButton("◊ Tron", callback_data="crypto_TRX"),
            ],
        ]
        
        if Config.ENABLE_NGN_FEATURES:
            keyboard.append([
                InlineKeyboardButton(
                    "🇳🇬 Bank Transfer (NGN)", callback_data="payment_ngn"
                )
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("❓ Payment Help", callback_data="payment_help")],
            [InlineKeyboardButton("❌ Cancel Trade", callback_data="cancel_escrow")],
        ])

        await context.bot.send_message(
            chat_id=chat_id,
            text=payment_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

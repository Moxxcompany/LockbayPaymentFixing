"""Fee Policy Messages and Communication Utils"""

from decimal import Decimal
from config import Config

class FeePolicyMessages:
    """Centralized fee policy messaging for consistent communication"""
    
    # Core fee policy constants
    PLATFORM_FEE_PERCENTAGE = Config.ESCROW_FEE_PERCENTAGE
    
    @staticmethod
    def get_fee_policy_short():
        """Short fee policy for inline display"""
        return f"5% platform fee • Refundable on early cancellation"
    
    @staticmethod
    def get_fee_policy_tooltip():
        """Tooltip-style fee explanation"""
        return (
            f"💡 **Platform Fee Policy**\n"
            f"• {FeePolicyMessages.PLATFORM_FEE_PERCENTAGE}% fee keeps your trades secure\n"
            f"• Early cancellations: Full refund including fees\n"
            f"• Completed/disputed trades: Fees support platform"
        )
    
    @staticmethod
    def get_onboarding_fee_info():
        """Fee information for new users during onboarding"""
        return (
            f"**Our Fair Fee Policy** 💵\n\n"
            f"• Simple {FeePolicyMessages.PLATFORM_FEE_PERCENTAGE}% platform fee\n"
            f"• **100% refundable** if you cancel early\n"
            f"• Keeps your trades secure & supported\n"
            f"• No hidden charges"
        )
    
    @staticmethod
    def get_trade_creation_fee_info(amount: Decimal):
        """Fee breakdown during trade creation"""
        fee = amount * Decimal(str(FeePolicyMessages.PLATFORM_FEE_PERCENTAGE / 100))
        total = amount + fee
        
        return (
            f"💰 **Trade Amount**: ${amount:.2f}\n"
            f"➕ **Platform Fee**: ${fee:.2f} ({FeePolicyMessages.PLATFORM_FEE_PERCENTAGE}%)\n"
            f"━━━━━━━━━━━━━\n"
            f"💳 **Total**: ${total:.2f}\n\n"
            f"✅ Fee is 100% refundable if cancelled early"
        )
    
    @staticmethod
    def get_payment_screen_fee_info(amount: Decimal, fee: Decimal):
        """Fee info for payment confirmation screen"""
        return (
            f"📋 **Payment Breakdown**\n"
            f"• Trade: ${amount:.2f}\n"
            f"• Fee: ${fee:.2f} (Refundable)\n"
            f"• Total: ${amount + fee:.2f}"
        )
    
    @staticmethod
    def get_cancellation_refund_info(amount: Decimal, fee: Decimal):
        """Refund information for cancellations"""
        return (
            f"✅ Refunded ${amount + fee:.2f}\n\n"
            f"Funds returned to your wallet."
        )
    
    @staticmethod
    def get_dispute_fee_retention_info():
        """Fee retention info for disputes"""
        return (
            f"⚠️ **Dispute Resolution Notice**\n\n"
            f"Platform fees ({FeePolicyMessages.PLATFORM_FEE_PERCENTAGE}%) are retained during disputes "
            f"to cover resolution costs and maintain service quality.\n\n"
            f"The trade amount will be refunded based on the dispute outcome."
        )
    
    @staticmethod
    def get_help_section_fee_policy():
        """Complete fee policy for help section"""
        return (
            f"💵 **Platform Fee Policy**\n\n"
            f"• {FeePolicyMessages.PLATFORM_FEE_PERCENTAGE}% fee on all trades\n"
            f"• 100% refundable on early cancellations\n"
            f"• Keeps trades secure & supported"
        )
    
    @staticmethod
    def get_inline_fee_hint():
        """Ultra-short inline fee hint"""
        return "5% fee (refundable)"
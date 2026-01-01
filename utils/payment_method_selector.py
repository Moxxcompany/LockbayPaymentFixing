"""
Unified Payment Method Selector Component
Provides consistent payment method switching across escrow, cashout, and exchange flows
"""

import logging
from typing import Dict, Optional, Any, Tuple
from enum import Enum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config

logger = logging.getLogger(__name__)


class PaymentContext(Enum):
    """Payment flow contexts"""

    ESCROW_CREATION = "escrow"
    CASHOUT_CASHOUT = "cashout"
    DIRECT_EXCHANGE = "exchange"


class PaymentMethod(Enum):
    """Supported payment methods"""

    CRYPTOCURRENCY = "crypto"
    NGN_BANK = "ngn"
    WALLET_BALANCE = "wallet"


class UnifiedPaymentMethodSelector:
    """Unified component for consistent payment method selection across all flows"""

    # Standardized payment method icons and labels
    METHOD_CONFIG = {
        PaymentMethod.CRYPTOCURRENCY: {
            "icon": "💎",
            "label": "Cryptocurrency",
            "short_label": "Crypto",
        },
        PaymentMethod.NGN_BANK: {
            "icon": "🇳🇬",
            "label": "Bank Transfer",
            "short_label": "NGN",
        },
        PaymentMethod.WALLET_BALANCE: {
            "icon": "💰",
            "label": "Wallet Balance",
            "short_label": "Wallet",
        },
    }

    # Context-specific method availability
    CONTEXT_METHODS = {
        PaymentContext.ESCROW_CREATION: [
            PaymentMethod.WALLET_BALANCE,
            PaymentMethod.CRYPTOCURRENCY,
            PaymentMethod.NGN_BANK,
        ],
        PaymentContext.CASHOUT_CASHOUT: [
            PaymentMethod.CRYPTOCURRENCY,
            PaymentMethod.NGN_BANK,
        ],
        PaymentContext.DIRECT_EXCHANGE: [
            PaymentMethod.CRYPTOCURRENCY,
            PaymentMethod.NGN_BANK,
        ],
    }

    @classmethod
    def generate_method_selection_text(
        cls,
        context: PaymentContext,
        amount: Optional[float] = None,
        wallet_balance: Optional[float] = None,
        exchange_direction: Optional[str] = None,
    ) -> str:
        """Generate context-appropriate header text for payment method selection"""

        if context == PaymentContext.ESCROW_CREATION:
            if amount:
                text = f"💼 Escrow Payment - ${amount:.2f}\n\n"
            else:
                text = "💼 Escrow Payment\n\n"
            text += "Choose your payment method:"

        elif context == PaymentContext.CASHOUT_CASHOUT:
            if amount:
                text = f"💸 Cash Out - ${amount:.2f}\n\n"
            else:
                text = "💸 Cash Out\n\n"
            text += "Choose cashout method:"

        elif context == PaymentContext.DIRECT_EXCHANGE:
            if exchange_direction == "crypto_to_ngn":
                text = "💱 Sell Crypto → NGN\n\n"
                text += "Select source currency:"
            elif exchange_direction == "ngn_to_crypto":
                text = "💱 Buy Crypto with NGN\n\n"
                text += "Select target currency:"
            else:
                text = "💱 Direct Exchange\n\n"
                text += "Choose exchange direction:"
        else:
            text = "💳 Payment Method\n\n"
            text += "Choose your method:"

        return text

    @classmethod
    def generate_method_selection_keyboard(
        cls,
        context: PaymentContext,
        callback_prefix: str,
        wallet_balance: Optional[float] = None,
        amount_needed: Optional[float] = None,
        back_callback: str = "back",
        selected_method: Optional[PaymentMethod] = None,
        exchange_direction: Optional[str] = None,
    ) -> InlineKeyboardMarkup:
        """Generate context-aware payment method selection keyboard"""

        available_methods = cls.CONTEXT_METHODS[context]
        keyboard = []

        # Special handling for direct exchange context
        if context == PaymentContext.DIRECT_EXCHANGE:
            if exchange_direction is None:
                # Show direction selection first (only if NGN features enabled)
                if Config.ENABLE_NGN_FEATURES:
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "💎→🇳🇬 Sell Crypto for NGN",
                                callback_data=f"{callback_prefix}crypto_to_ngn",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🇳🇬→💎 Buy Crypto with NGN",
                                callback_data=f"{callback_prefix}ngn_to_crypto",
                            )
                        ],
                    ]
            else:
                # Show currency type selection
                if exchange_direction == "crypto_to_ngn":
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "💎 Select Cryptocurrency",
                                callback_data=f"{callback_prefix}crypto",
                            )
                        ]
                    ]
                else:  # ngn_to_crypto
                    if Config.ENABLE_NGN_FEATURES:
                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "🇳🇬 NGN Bank Payment",
                                    callback_data=f"{callback_prefix}ngn",
                                )
                            ]
                        ]
        else:
            # Standard method selection for escrow and cashout
            for method in available_methods:
                config = cls.METHOD_CONFIG[method]
                icon = config["icon"]
                label = config["label"]

                # Check method availability and create appropriate button text
                button_text = f"{icon} {label}"
                is_available = True

                # Wallet balance availability check
                if (
                    method == PaymentMethod.WALLET_BALANCE
                    and wallet_balance is not None
                ):
                    if amount_needed and wallet_balance < amount_needed:
                        is_available = False
                        button_text = f"💰 Wallet ${wallet_balance:.2f} ❌"
                    else:
                        button_text = f"{icon} {label} ${wallet_balance:.2f}"

                # Add selection indicator if this method is currently selected
                if selected_method == method:
                    button_text = f"✅ {button_text}"

                # Create button (disabled if not available)
                callback_data = (
                    f"{callback_prefix}{method.value}"
                    if is_available
                    else "method_unavailable"
                )

                keyboard.append(
                    [InlineKeyboardButton(button_text, callback_data=callback_data)]
                )

        # Add standard back button
        if back_callback != "none":
            keyboard.append(
                [InlineKeyboardButton("⬅️ Back", callback_data=back_callback)]
            )

        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def generate_method_switch_keyboard(
        cls,
        context: PaymentContext,
        current_method: PaymentMethod,
        callback_prefix: str,
        include_current: bool = False,
    ) -> InlineKeyboardMarkup:
        """Generate keyboard for switching between payment methods mid-flow"""

        available_methods = cls.CONTEXT_METHODS[context]
        keyboard = []

        switch_buttons = []
        for method in available_methods:
            if method == current_method and not include_current:
                continue

            config = cls.METHOD_CONFIG[method]
            icon = config["icon"]
            short_label = config["short_label"]

            button_text = f"{icon} Switch to {short_label}"
            callback_data = f"{callback_prefix}{method.value}"

            switch_buttons.append(
                InlineKeyboardButton(button_text, callback_data=callback_data)
            )

        # Arrange in pairs for compact layout
        for i in range(0, len(switch_buttons), 2):
            if i + 1 < len(switch_buttons):
                keyboard.append([switch_buttons[i], switch_buttons[i + 1]])
            else:
                keyboard.append([switch_buttons[i]])

        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def preserve_method_state(
        cls,
        context_data: Dict[str, Any],
        method: PaymentMethod,
        method_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Preserve method-specific data when switching between payment methods"""

        if "method_states" not in context_data:
            context_data["method_states"] = {}

        context_data["method_states"][method.value] = method_data.copy()
        return context_data

    @classmethod
    def restore_method_state(
        cls, context_data: Dict[str, Any], method: PaymentMethod
    ) -> Dict[str, Any]:
        """Restore previously saved method-specific data"""

        method_states = context_data.get("method_states", {})
        return method_states.get(method.value, {})

    @classmethod
    def get_method_validation_rules(
        cls, method: PaymentMethod, context: PaymentContext
    ) -> Dict[str, Any]:
        """Get validation rules for specific payment method in context"""

        base_rules = {
            PaymentMethod.CRYPTOCURRENCY: {
                "min_amount": 10.0,
                "max_amount": 50000.0,
                "required_fields": ["currency", "network"],
                "address_required": True,
            },
            PaymentMethod.NGN_BANK: {
                "min_amount": 1000.0,  # ₦1000 minimum
                "max_amount": 5000000.0,  # ₦5M maximum
                "required_fields": ["bank_account", "account_name"],
                "verification_required": True,
            },
            PaymentMethod.WALLET_BALANCE: {
                "min_amount": 1.0,
                "max_amount": None,  # Limited by available balance
                "required_fields": [],
                "instant_execution": True,
            },
        }

        # Context-specific rule modifications
        rules = base_rules[method].copy()

        if context == PaymentContext.ESCROW_CREATION:
            # Escrow has higher minimums for security
            rules["min_amount"] = max(rules["min_amount"], 50.0)

        elif context == PaymentContext.CASHOUT_CASHOUT:
            # Cashout minimums from config
            from config import Config

            rules["min_amount"] = max(
                rules["min_amount"], getattr(Config, "MIN_CASHOUT_AMOUNT", 25.0)
            )

        return rules

    @classmethod
    def validate_method_transition(
        cls,
        from_method: PaymentMethod,
        to_method: PaymentMethod,
        context: PaymentContext,
        user_data: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Validate if transition between payment methods is allowed and safe"""

        # Check if target method is available in this context
        available_methods = cls.CONTEXT_METHODS[context]
        if to_method not in available_methods:
            return False, "Payment method not available in this context"

        # Check wallet balance if switching to wallet payment
        if to_method == PaymentMethod.WALLET_BALANCE:
            wallet_balance = user_data.get("wallet_balance", 0.0)
            amount_needed = user_data.get("amount", 0.0)

            if amount_needed > wallet_balance:
                return (
                    False,
                    f"Insufficient wallet balance (${wallet_balance:.2f} available, ${amount_needed:.2f} needed)",
                )

        # Check method-specific requirements
        validation_rules = cls.get_method_validation_rules(to_method, context)
        amount = user_data.get("amount", 0.0)

        if amount < validation_rules["min_amount"]:
            return (
                False,
                f"Amount below minimum for {to_method.value} (${validation_rules['min_amount']:.2f})",
            )

        if validation_rules["max_amount"] and amount > validation_rules["max_amount"]:
            return (
                False,
                f"Amount exceeds maximum for {to_method.value} (${validation_rules['max_amount']:.2f})",
            )

        return True, "Transition allowed"

    @classmethod
    def get_method_status_text(
        cls, method: PaymentMethod, context: PaymentContext, user_data: Dict[str, Any]
    ) -> str:
        """Get status text for a payment method (available, selected, blocked, etc.)"""

        config = cls.METHOD_CONFIG[method]
        icon = config["icon"]
        label = config["label"]

        # Check availability
        is_valid, message = cls.validate_method_transition(
            PaymentMethod.CRYPTOCURRENCY,  # dummy from_method
            method,
            context,
            user_data,
        )

        if not is_valid:
            return f"{icon} {label} ❌ - {message}"

        # Add context-specific status info
        if method == PaymentMethod.WALLET_BALANCE:
            balance = user_data.get("wallet_balance", 0.0)
            return f"{icon} {label} (${balance:.2f} available)"

        elif method == PaymentMethod.NGN_BANK:
            if context == PaymentContext.CASHOUT_CASHOUT:
                return f"{icon} {label} (Bank Transfer)"
            else:
                return f"{icon} {label} (Fincra Payment)"

        elif method == PaymentMethod.CRYPTOCURRENCY:
            return f"{icon} {label} (Multiple networks)"

        return f"{icon} {label}"

    @classmethod
    def generate_switch_method_text(
        cls,
        current_method: PaymentMethod,
        context: PaymentContext,
        amount: Optional[float] = None,
    ) -> str:
        """Generate text for method switching interface"""

        config = cls.METHOD_CONFIG[current_method]
        current_label = config["label"]

        if context == PaymentContext.ESCROW_CREATION:
            text = f"💼 Current Payment Method: {current_label}\n\n"
            if amount:
                text += f"Amount: ${amount:.2f}\n\n"
            text += "Switch to a different payment method:"

        elif context == PaymentContext.CASHOUT_CASHOUT:
            text = f"💸 Current Cashout Method: {current_label}\n\n"
            if amount:
                text += f"Amount: ${amount:.2f}\n\n"
            text += "Switch to a different cashout method:"

        elif context == PaymentContext.DIRECT_EXCHANGE:
            text = f"💱 Current Exchange Method: {current_label}\n\n"
            text += "Switch exchange direction:"

        return text

    @classmethod
    def handle_method_switch_request(
        cls,
        context_data: Dict[str, Any],
        from_method: PaymentMethod,
        to_method: PaymentMethod,
        context: PaymentContext,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle payment method switching with validation and state preservation"""

        # Validate transition
        is_valid, validation_message = cls.validate_method_transition(
            from_method, to_method, context, context_data
        )

        if not is_valid:
            return False, validation_message, context_data

        # Preserve current method state
        method_data = {
            "amount": context_data.get("amount"),
            "currency": context_data.get("currency"),
            "network": context_data.get("network"),
            "address": context_data.get("address"),
            "bank_account": context_data.get("bank_account"),
            "partial_progress": context_data.get("partial_progress", {}),
        }

        # Clean None values
        method_data = {k: v for k, v in method_data.items() if v is not None}

        # Store state for current method
        updated_context = cls.preserve_method_state(
            context_data, from_method, method_data
        )

        # Switch to new method and restore any previous state
        updated_context["current_payment_method"] = to_method.value
        restored_data = cls.restore_method_state(updated_context, to_method)

        # Apply restored data to context
        for key, value in restored_data.items():
            if key != "partial_progress":  # Handle partial progress separately
                updated_context[key] = value

        success_message = (
            f"Switched to {cls.METHOD_CONFIG[to_method]['label']} payment method"
        )
        return True, success_message, updated_context

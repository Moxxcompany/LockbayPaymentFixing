"""
Standardized crypto payment UI components for consistent design across all payment interfaces
Ensures uniform address display, QR codes, currency selection, and navigation patterns
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


class CryptoUIComponents:
    """Unified crypto payment UI components for consistent design"""

    # Standardized crypto icons across all interfaces (DynoPay supported only)
    CRYPTO_ICONS = {
        "BTC": "₿",
        "ETH": "Ξ",
        "LTC": "Ł",
        "DOGE": "Ð",
        "BCH": "◊",
        "TRX": "🔴",
        "USDT-ERC20": "₮",
        "USDT-TRC20": "₮",
    }

    # Standardized crypto display names (DynoPay supported only)
    CRYPTO_DISPLAY_NAMES = {
        "BCH": "Bitcoin Cash",
        "TRX": "Tron",
        "USDT-ERC20": "USDT (Ethereum)",
        "USDT-TRC20": "USDT (Tron)",
    }

    # Core supported cryptocurrencies for cashout (Streamlined)
    SUPPORTED_CRYPTOS = [
        "BTC",
        "ETH",
        "LTC",
        "USDT-ERC20",
        "USDT-TRC20",
    ]

    @classmethod
    def get_crypto_selection_keyboard(
        cls,
        callback_prefix: str,
        layout: str = "grid",
        back_callback: str = "back",
        selected_cryptos: Optional[List[str]] = None,
    ) -> InlineKeyboardMarkup:
        """
        Generate standardized crypto selection keyboard

        Args:
            callback_prefix: Prefix for callback data (e.g., "deposit_currency:")
            layout: "grid" (3x3) or "compact" (2-column)
            back_callback: Callback data for back button
            selected_cryptos: List of cryptos to include (default: all supported)
        """
        cryptos = selected_cryptos or cls.SUPPORTED_CRYPTOS
        keyboard = []

        # Create buttons with standardized format
        buttons = []
        for crypto in cryptos:
            icon = cls.CRYPTO_ICONS.get(crypto, "🪙")
            display_name = cls.CRYPTO_DISPLAY_NAMES.get(crypto, crypto)
            button_text = f"{icon} {display_name}"
            callback_data = f"{callback_prefix}{crypto}"
            buttons.append(
                InlineKeyboardButton(button_text, callback_data=callback_data)
            )

        if layout == "grid":
            # 3x3 grid layout for wallet/deposit interfaces
            for i in range(0, len(buttons), 3):
                row = buttons[i : i + 3]
                keyboard.append(row)
        else:
            # 2-column compact layout for exchanges/trades
            for i in range(0, len(buttons), 2):
                if i + 1 < len(buttons):
                    keyboard.append([buttons[i], buttons[i + 1]])
                else:
                    keyboard.append([buttons[i]])

        # Add standardized back button
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=back_callback)])

        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def format_crypto_address(
        cls, address: str, currency: str, use_backticks: bool = True
    ) -> str:
        """
        Standardized crypto address formatting

        Args:
            address: The cryptocurrency address
            currency: Currency type (BTC, ETH, etc.)
            use_backticks: Whether to wrap address in backticks for monospace
        """
        if not address:
            return "❌ No address provided"

        # Standardized address formatting with proper truncation
        if use_backticks:
            if len(address) > 42:
                # Truncate long addresses for display
                formatted = f"`{address[:20]}...{address[-20:]}`"
            else:
                formatted = f"`{address}`"
        else:
            formatted = address

        return formatted

    @classmethod
    def generate_payment_instructions_text(
        cls,
        currency: str,
        address: str,
        amount: Optional[float] = None,
        qr_url: Optional[str] = None,
        network_info: Optional[str] = None,
        expiry_minutes: Optional[int] = None,
    ) -> str:
        """
        Generate standardized payment instruction text

        Args:
            currency: Cryptocurrency (BTC, ETH, etc.)
            address: Payment address
            amount: Amount to send (optional)
            qr_url: QR code URL (optional)
            network_info: Network information (optional)
            expiry_minutes: Payment expiry in minutes (optional)
        """
        icon = cls.CRYPTO_ICONS.get(currency, "🪙")
        display_name = cls.CRYPTO_DISPLAY_NAMES.get(currency, currency)
        formatted_address = cls.format_crypto_address(address, currency)

        text = f"""💳 {icon} {display_name} Payment\n\n"""

        if amount:
            text += f"💰 Amount: {amount:.8f} {currency}\n"

        text += f"📬 Address: {formatted_address}\n"

        if network_info:
            text += f"🌐 Network: {network_info}\n"

        if qr_url:
            text += f"\n📱 QR Code: [Scan to Pay]({qr_url})\n"

        # Standard security warnings
        text += "\n⚠️ Important:\n"
        text += f"• Send only {display_name} to this address\n"
        text += "• Double-check the address before sending\n"
        text += "• Minimum confirmations required\n"

        if expiry_minutes:
            text += f"• Payment expires in {expiry_minutes} minutes\n"

        return text

    @classmethod
    def generate_address_input_text(
        cls,
        currency: str,
        action: str = "Enter",
        saved_addresses: Optional[List[Dict]] = None,
    ) -> str:
        """
        Generate standardized address input instruction text

        Args:
            currency: Cryptocurrency (BTC, ETH, etc.)
            action: Action verb ("Enter", "Provide", etc.)
            saved_addresses: List of saved addresses to display
        """
        icon = cls.CRYPTO_ICONS.get(currency, "🪙")
        display_name = cls.CRYPTO_DISPLAY_NAMES.get(currency, currency)

        text = f"""🔗 {icon} {display_name} Wallet Address\n\n"""
        text += f"📝 {action} your {display_name} wallet address:\n\n"

        if saved_addresses:
            text += "💾 Saved Addresses:\n"
            for i, addr in enumerate(saved_addresses[:3], 1):  # Show max 3
                label = addr.get("label", f"Address {i}")
                address = addr.get("address", "")
                truncated = cls.format_crypto_address(
                    address, currency, use_backticks=False
                )
                text += f"{i}. {label}: {truncated}\n"
            text += "\n"

        text += "⚠️ Security Warning:\n"
        text += "Double-check your address - wrong addresses result in permanent loss."

        return text

    @classmethod
    def create_amount_selection_keyboard(
        cls,
        quick_amounts: List[float],
        currency: str,
        callback_prefix: str = "quick_amount:",
        back_callback: str = "back",
    ) -> InlineKeyboardMarkup:
        """
        Generate standardized amount selection keyboard

        Args:
            quick_amounts: List of quick amount options
            currency: Currency symbol for display
            callback_prefix: Prefix for callback data
            back_callback: Callback data for back button
        """
        keyboard = []

        # Create amount buttons in pairs
        for i in range(0, len(quick_amounts), 2):
            row = []
            for j in range(2):
                if i + j < len(quick_amounts):
                    amount = quick_amounts[i + j]
                    if amount >= 1000:
                        display = f"${amount/1000:.0f}K"
                    else:
                        display = f"${amount:.0f}"

                    button = InlineKeyboardButton(
                        display, callback_data=f"{callback_prefix}{amount}"
                    )
                    row.append(button)
            keyboard.append(row)

        # Add custom amount and back buttons
        keyboard.append(
            [InlineKeyboardButton("✏️ Custom Amount", callback_data="custom_amount")]
        )
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=back_callback)])

        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def generate_qr_payment_text(
        cls,
        currency: str,
        address: str,
        amount: Optional[float] = None,
        qr_data: Optional[str] = None,
    ) -> str:
        """
        Generate standardized QR code payment text with mobile-optimized formatting

        Args:
            currency: Cryptocurrency
            address: Payment address
            amount: Payment amount (optional)
            qr_data: QR code data string (optional)
        """
        icon = cls.CRYPTO_ICONS.get(currency, "🪙")
        display_name = cls.CRYPTO_DISPLAY_NAMES.get(currency, currency)
        formatted_address = cls.format_crypto_address(address, currency)

        text = f"""📱 {icon} {display_name} Payment QR\n\n"""

        if amount:
            text += f"💰 Amount: {amount:.8f} {currency}\n"

        text += f"📬 Address: {formatted_address}\n\n"

        text += "🔲 Scan QR Code:\n"
        text += "• Open your crypto wallet app\n"
        text += "• Use camera to scan QR code\n"
        text += "• Verify address and amount\n"
        text += "• Confirm transaction\n\n"

        text += "⚡ Quick & Secure\n"
        text += "QR scanning prevents address errors"

        return text

    @classmethod
    def get_navigation_keyboard(
        cls,
        primary_action: Optional[Dict[str, str]] = None,
        secondary_actions: Optional[List[Dict[str, str]]] = None,
        back_callback: str = "back",
        cancel_callback: str = "cancel",
    ) -> InlineKeyboardMarkup:
        """
        Generate standardized navigation keyboard

        Args:
            primary_action: Dict with 'text' and 'callback' for main action button
            secondary_actions: List of secondary action buttons
            back_callback: Callback for back button
            cancel_callback: Callback for cancel button
        """
        keyboard = []

        # Add primary action if provided
        if primary_action:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        primary_action["text"], callback_data=primary_action["callback"]
                    )
                ]
            )

        # Add secondary actions if provided
        if secondary_actions:
            for action in secondary_actions:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            action["text"], callback_data=action["callback"]
                        )
                    ]
                )

        # Standard navigation row
        nav_row = []
        if back_callback != "none":
            nav_row.append(InlineKeyboardButton("⬅️ Back", callback_data=back_callback))
        if cancel_callback != "none":
            nav_row.append(
                InlineKeyboardButton("❌ Cancel", callback_data=cancel_callback)
            )

        if nav_row:
            keyboard.append(nav_row)

        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def validate_and_format_amount(
        cls, amount_str: str, currency: str
    ) -> Tuple[bool, Optional[float], str]:
        """
        Validate and format crypto amount input

        Returns:
            (is_valid, formatted_amount, error_message)
        """
        try:
            amount = float(amount_str.strip())

            if amount <= 0:
                return False, None, "Amount must be greater than zero"

            # Currency-specific validations
            if currency in ["BTC", "ETH", "LTC"]:
                if amount < 0.0001:
                    return False, None, f"Minimum {currency} amount is 0.0001"
            elif currency.startswith("USDT"):
                if amount < 1.0:
                    return False, None, "Minimum USDT amount is 1.0"
            elif currency == "DOGE":
                if amount < 1.0:
                    return False, None, "Minimum DOGE amount is 1.0"

            # Maximum amount check
            if amount > 1000000:
                return (
                    False,
                    None,
                    "Amount too large - contact support for large transactions",
                )

            return True, amount, ""

        except (ValueError, TypeError):
            return False, None, "Invalid amount format - enter numbers only"

    @classmethod
    def get_crypto_network_info(cls, currency: str) -> Dict[str, Any]:
        """Get network information for a cryptocurrency"""
        network_info = {
            "BTC": {
                "name": "Bitcoin",
                "confirmations": 1,
                "avg_time": "10-30 minutes",
                "fees": "Network fees apply",
            },
            "ETH": {
                "name": "Ethereum",
                "confirmations": 12,
                "avg_time": "5-15 minutes",
                "fees": "Gas fees apply",
            },
            "USDT-TRC20": {
                "name": "Tron (TRC20)",
                "confirmations": 19,
                "avg_time": "1-3 minutes",
                "fees": "Low fees",
            },
            "USDT-ERC20": {
                "name": "Ethereum (ERC20)",
                "confirmations": 12,
                "avg_time": "5-15 minutes",
                "fees": "Gas fees apply",
            },
            "LTC": {
                "name": "Litecoin",
                "confirmations": 6,
                "avg_time": "5-15 minutes",
                "fees": "Low fees",
            },
            "DOGE": {
                "name": "Dogecoin",
                "confirmations": 6,
                "avg_time": "5-15 minutes",
                "fees": "Very low fees",
            },
            "BCH": {
                "name": "Bitcoin Cash",
                "confirmations": 6,
                "avg_time": "10-30 minutes",
                "fees": "Low fees",
            },
            "BSC": {
                "name": "Binance Smart Chain",
                "confirmations": 15,
                "avg_time": "1-3 minutes",
                "fees": "Very low fees",
            },
            "TRX": {
                "name": "Tron",
                "confirmations": 19,
                "avg_time": "1-3 minutes",
                "fees": "Very low fees",
            },
        }

        return network_info.get(
            currency,
            {
                "name": currency,
                "confirmations": 6,
                "avg_time": "5-15 minutes",
                "fees": "Network fees apply",
            },
        )

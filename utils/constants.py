"""Constants and enums for the Telegram Escrow Bot"""

from typing import Optional
from models import CashoutStatus

# ==================== CASHOUT STATUS CONSTANTS ====================

# Centralized cancellable cashout statuses - prevents drift between services and handlers
CANCELLABLE_CASHOUT_STATUSES = [
    CashoutStatus.PENDING.value,           # Standard pending cashouts  
    CashoutStatus.OTP_PENDING.value,       # LTC records in OTP verification (no holds yet)
    CashoutStatus.USER_CONFIRM_PENDING.value,  # Awaiting user final confirmation (no holds yet)
    CashoutStatus.ADMIN_PENDING.value,     # Waiting for admin approval
    CashoutStatus.PENDING_ADDRESS_CONFIG.value,       # Waiting for admin address setup
    CashoutStatus.PENDING_SERVICE_FUNDING.value       # Waiting for service funding
]

# Statuses with actual fund holds that can be processed by retry systems
CASHOUT_STATUSES_WITH_HOLDS = [
    CashoutStatus.PENDING.value,           # Standard pending cashouts with holds
    CashoutStatus.ADMIN_PENDING.value,     # Admin approval with holds
    CashoutStatus.PENDING_ADDRESS_CONFIG.value,       # Address config with holds
    CashoutStatus.PENDING_SERVICE_FUNDING.value,      # Service funding with holds
    CashoutStatus.EXECUTING.value,         # Currently processing with holds
]

# Statuses without fund holds (should NOT be processed by retry/job systems)
CASHOUT_STATUSES_WITHOUT_HOLDS = [
    CashoutStatus.OTP_PENDING.value,       # No holds - awaiting OTP verification
    CashoutStatus.USER_CONFIRM_PENDING.value,  # No holds - awaiting user confirmation
]

# Statuses that indicate a cashout is stuck and needs orphan cleanup
# IMPORTANT: Only includes statuses WITH actual holds to prevent refunding non-existent funds
ORPHANABLE_CASHOUT_STATUSES = [
    CashoutStatus.PENDING.value,           # Standard stuck cashouts with holds
    CashoutStatus.ADMIN_PENDING.value,     # Long-pending admin approvals with holds
    CashoutStatus.PENDING_ADDRESS_CONFIG.value,       # Stuck address config with holds
    CashoutStatus.PENDING_SERVICE_FUNDING.value,      # Stuck service funding with holds
]


# Bot states for conversation handler
class States:
    # Onboarding states
    COLLECTING_EMAIL = 100
    VERIFYING_EMAIL_OTP = 101
    CONFIRMING_EMAIL = 102
    ACCEPTING_TOS = 103
    ONBOARDING_SHOWCASE = 104

    # Escrow creation states
    ENTERING_SELLER = 200
    ENTERING_AMOUNT = 201
    SELECTING_PAYMENT_METHOD = 202  # Moved to post-acceptance
    SELECTING_CURRENCY = 203  # Moved to post-acceptance
    SELECTING_NETWORK = 204  # Moved to post-acceptance
    ENTERING_DESCRIPTION = 205
    SETTING_TIMEOUT = 206
    CONFIRMING_ESCROW = 207

    # Post-acceptance payment states
    POST_ACCEPTANCE_PAYMENT_SELECTION = 208
    POST_ACCEPTANCE_CURRENCY_SELECTION = 209
    POST_ACCEPTANCE_NETWORK_SELECTION = 210

    # Wallet states (Binance-style cashout flow)
    WALLET_MENU = 299  # Main wallet menu state
    SELECTING_AMOUNT = 300  # NEW: Amount selection first
    SELECTING_METHOD = 301  # NEW: Method selection (NGN/USDT)
    # REMOVED: Legacy cashout type selection - now handled by direct method selection
    ENTERING_CUSTOM_AMOUNT = 321  # NEW: Custom amount input
    SELECTING_WITHDRAW_CURRENCY = 302
    SELECTING_CRYPTO_CURRENCY = 308
    ENTERING_WITHDRAW_AMOUNT = 303
    SELECTING_WITHDRAW_NETWORK = 304
    ENTERING_WITHDRAW_ADDRESS = 305
    CONFIRMING_CASHOUT = 306
    CONFIRMING_SAVED_ADDRESS = 307
    CONFIRMING_SAVE_ADDRESS = 308

    # NGN cashout states
    ENTERING_NGN_BANK_DETAILS = 310
    SELECTING_NGN_BANK = 311
    CONFIRMING_NGN_CASHOUT = 312
    CONFIRMING_NGN_SAVE = 313
    SELECTING_NGN_MATCH = 314
    SELECTING_BANK_FROM_MATCHES = 315  # NEW: Select bank when multiple matches found
    VERIFICATION_OPTIONS = 316  # NEW: For verification failure options
    AWAITING_EMAIL_VERIFICATION = 317
    SELECTING_SAVED_BANK = 318

    # Messaging states
    COMPOSING_MESSAGE = 400
    UPLOADING_FILE = 401

    # Dispute states
    SELECTING_DISPUTE_REASON = 500
    ENTERING_DISPUTE_DESCRIPTION = 501
    UPLOADING_DISPUTE_EVIDENCE = 502

    # Rating states
    GIVING_RATING = 600
    WRITING_REVIEW = 601

    # Add funds states
    SELECTING_DEPOSIT_CURRENCY = 700
    DEPOSIT_WAITING = 701

    # Email verification states for cashout
    ENTERING_EMAIL = 800
    ENTERING_OTP = 801

    # Email invitation verification for new users
    VERIFYING_EMAIL_INVITATION = 900


# Callback data prefixes
class CallbackData:
    # Main menu
    MENU_CREATE = "menu_create"
    MENU_ESCROWS = "menu_escrows"
    MENU_WALLET = "menu_wallet"
    MENU_HELP = "menu_help"
    MENU_PROFILE = "menu_profile"

    # Hamburger menu callbacks
    HAMBURGER_MENU = "hamburger_menu"
    BACK_TO_MAIN = "back_to_main"
    ESCROW_HISTORY = "escrow_history"
    CASHOUT_HISTORY = "cashout_history"
    REPUTATION_DETAILS = "reputation_details"
    DISPUTE_CENTER = "dispute_center"
    USER_STATS = "user_stats"
    USER_SETTINGS = "user_settings"
    NOTIFICATION_SETTINGS = "notification_settings"
    CONTACT_SUPPORT = "contact_support"
    SECURITY_SETTINGS = "security_settings"
    TERMS_PRIVACY = "terms_privacy"

    # Currency selection
    CURRENCY_SELECT = "cur_sel"
    NETWORK_SELECT = "net_sel"

    # Escrow actions
    ESCROW_CONFIRM = "esc_confirm"
    ESCROW_CANCEL = "esc_cancel"
    ESCROW_ACCEPT = "esc_accept"
    ESCROW_DECLINE = "esc_decline"
    ESCROW_RELEASE = "esc_release"
    ESCROW_DISPUTE = "esc_dispute"
    ESCROW_VIEW = "esc_view"
    ESCROW_MESSAGE = "esc_msg"
    ESCROW_FILES = "esc_files"

    # Wallet actions - consistent "wallet_" prefix
    WALLET_MENU = "wallet_menu"
    WALLET_CASH_OUT = "wallet_cash_out"
    WALLET_WITHDRAW = "wallet_withdraw"
    WALLET_ADD_FUNDS = "wallet_add_funds"
    WALLET_HISTORY = "wallet_history"
    WALLET_SETTINGS = "wallet_settings"
    WALLET_EXPORT = "wallet_export"

    # Dispute actions
    DISPUTE_REASON = "dis_reason"
    DISPUTE_EVIDENCE = "dis_evidence"

    # Rating actions
    RATING_GIVE = "rat_give"
    RATING_SKIP = "rat_skip"

    # Admin actions
    ADMIN_RESOLVE = "adm_resolve"
    ADMIN_CASHOUT = "adm_cashout"

    # Navigation
    BACK = "back"
    CANCEL = "cancel"
    REFRESH = "refresh"


# Dispute reasons - compact mobile display
DISPUTE_REASONS = {
    "not_received": "❌ Not received",
    "not_as_described": "⚠️ Not as described",
    "poor_quality": "👎 Poor quality",
    "delayed_delivery": "⏰ Delayed",
    "communication_issues": "💬 Communication",
    "other": "❓ Other",
}

# Delivery timeout options (in hours) - compact mobile-friendly
TIMEOUT_OPTIONS = {24: "24h", 48: "2d", 72: "3d ⭐", 120: "5d", 168: "1w", 336: "2w"}

# Status emojis
STATUS_EMOJIS = {
    "created": "⚪",
    "payment_pending": "🟡",
    "payment_confirmed": "🟠",
    "awaiting_seller": "🟡",
    "pending_seller": "🟡",
    "pending_deposit": "🟠",
    "active": "🟢",
    "completed": "✅",
    "disputed": "🔴",
    "cancelled": "⚫",
    "refunded": "🔵",
    "expired": "⚪",
}

# Currency emojis
CURRENCY_EMOJIS = {
    "BTC": "₿",
    "ETH": "⟠",
    "LTC": "🥈",
    "DOGE": "🐕",
    "BCH": "💚",
    "BSC": "🟡",
    "TRX": "🔴",
    "USDT-ERC20": "💵",
    "USDT-TRC20": "💴",
}

# Network display names
NETWORK_NAMES = {
    "Bitcoin": "Bitcoin Network",
    "Ethereum": "Ethereum Network",
    "Litecoin": "Litecoin Network",
    "Dogecoin": "Dogecoin Network",
    "BitcoinCash": "Bitcoin Cash Network",
    "BinanceSmartChain": "Binance Smart Chain (BSC)",
    "Tron": "Tron Network",
    "ERC20": "Ethereum (ERC-20)",
    "TRC20": "Tron (TRC-20)",
}

# Platform branding
PLATFORM_NAME = "LockBay"

# File type icons
FILE_TYPE_ICONS = {
    "image": "🖼️",
    "video": "🎥",
    "audio": "🎵",
    "document": "📄",
    "archive": "📦",
    "other": "📎",
}

# Rating stars
RATING_STARS = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]

# Message limits
MAX_MESSAGE_LENGTH = 4000
MAX_DESCRIPTION_LENGTH = 500
MAX_REVIEW_LENGTH = 300

# Time format
DATETIME_FORMAT = "%Y-%m-%d %H:%M UTC"
DATE_FORMAT = "%Y-%m-%d"

# Dynamic minimum amounts - Retrieved from BlockBee API or configured fallbacks
# These should be fetched dynamically via get_dynamic_min_amounts() function
MIN_AMOUNTS_FALLBACK = {
    "BTC": 0.0005,
    "ETH": 0.005,
    "LTC": 0.01,
    "DOGE": 10.0,
    "BCH": 0.001,
    "BSC": 0.001,
    "TRX": 10.0,
    "USDT-ERC20": 5.0,
    "USDT-TRC20": 5.0,
}


async def get_dynamic_min_amounts(currency: Optional[str] = None) -> dict:
    """Get dynamic minimum amounts from configured payment provider"""
    try:
        from services.payment_processor_manager import payment_manager

        try:
            # Get currency info from payment manager which includes minimum amounts
            if currency:
                currency_info = await payment_manager.get_currency_info(currency)
                min_amount = currency_info.get(
                    "minimum_transaction", MIN_AMOUNTS_FALLBACK.get(currency, 10.0)
                )
                return {currency: min_amount}
            else:
                # Get all supported currencies and their minimums
                dynamic_minimums = {}
                for curr in MIN_AMOUNTS_FALLBACK.keys():
                    try:
                        currency_info = await payment_manager.get_currency_info(curr)
                        dynamic_minimums[curr] = currency_info.get(
                            "minimum_transaction", MIN_AMOUNTS_FALLBACK[curr]
                        )
                    except Exception as e:
                        import logging
                        logging.debug(f"Could not get minimum amount for {curr}: {e}")
                        dynamic_minimums[curr] = MIN_AMOUNTS_FALLBACK[curr]
                return dynamic_minimums
        except Exception as e:
            import logging

            logging.warning(f"Failed to get dynamic minimums from payment provider: {e}")

        # Return fallback values if API fails
        return (
            MIN_AMOUNTS_FALLBACK.copy()
            if not currency
            else {currency: MIN_AMOUNTS_FALLBACK.get(currency, 10.0)}
        )

    except Exception as e:
        import logging

        logging.error(f"Error in get_dynamic_min_amounts: {e}")
        return (
            MIN_AMOUNTS_FALLBACK.copy()
            if not currency
            else {currency: MIN_AMOUNTS_FALLBACK.get(currency, 10.0)}
        )


# Conversation states for the escrow flow
class EscrowStates:
    SELLER_INPUT = 0
    AMOUNT_INPUT = 1
    DESCRIPTION_INPUT = 2
    DELIVERY_TIME = 3
    FEE_SPLIT_OPTION = 4  # NEW: Fee split selection step
    TRADE_REVIEW = 5      # NEW: Trade review and confirmation step (matches exchange flow)
    PAYMENT_METHOD = 6    # Payment method selection from review page
    PAYMENT_PROCESSING = 7
    CRYPTO_SELECTION = 8  # NEW: Independent crypto selection state for smooth switching
    SELECTING_CRYPTO = 9  # NEW: Additional crypto selection state for compatibility

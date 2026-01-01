"""Inline keyboard utilities for the Telegram Escrow Bot"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.constants import (
    CallbackData,
    CURRENCY_EMOJIS,
    STATUS_EMOJIS,
    TIMEOUT_OPTIONS,
    DISPUTE_REASONS,
)
from config import Config


def main_menu_keyboard(
    balance: float = 0.0, total_trades: int = 0, active_escrows: int = 0, pending_invitations: int = 0, referral_count: int = 0, user_telegram_id: str = "", active_disputes: int = 0
):
    """Dynamic main menu with context-aware buttons and user access control"""
    keyboard_rows = []
    
    # Check if user has exchange access
    has_exchange_access = True
    if user_telegram_id:
        from utils.user_access_control import check_feature_access
        has_exchange_access = check_feature_access(user_telegram_id, "exchange")

    # IMPROVED: Consistent trade creation language for all users
    if total_trades == 0:  # New user
        keyboard_rows.append(
            [InlineKeyboardButton("🤝 Create New Trade", callback_data="menu_create")]
        )
    # HIDDEN: Active Trades button - removed per user request
    # elif active_escrows > 0:  # Active trader
    #     keyboard_rows.append(
    #         [InlineKeyboardButton("⚡ Active Trades", callback_data="menu_escrows")]
    #     )
    else:  # Experienced user (total_trades > 0)
        # Show Quick Exchange for experienced users regardless of balance
        if has_exchange_access and Config.ENABLE_EXCHANGE_FEATURES:
            keyboard_rows.append(
                [InlineKeyboardButton("🔄 Quick Exchange", callback_data="start_exchange")]
            )
        else:
            # Show alternative action for users without exchange access
            keyboard_rows.append(
                [InlineKeyboardButton("🤝 Create New Trade", callback_data="menu_create")]
            )

    # Core actions row - avoid duplicates
    core_row = []

    # Only add Quick Exchange if NOT already shown in primary action AND user has access
    # Primary action shows Quick Exchange for experienced users (total_trades > 0)
    # So DON'T add it again if primary action already shows it
    already_shown_in_primary = (total_trades > 0 and has_exchange_access and Config.ENABLE_EXCHANGE_FEATURES)
    if not already_shown_in_primary and has_exchange_access and Config.ENABLE_EXCHANGE_FEATURES:
        core_row.append(
            InlineKeyboardButton("🔄 Quick Exchange", callback_data="start_exchange")
        )

    # Trade button - only for experienced users with exchange access (to be paired with Quick Exchange)
    # If user doesn't have exchange access, they already got "Create New Trade" as primary action (line 45)
    if total_trades > 0 and has_exchange_access and Config.ENABLE_EXCHANGE_FEATURES:
        core_row.append(
            InlineKeyboardButton("🤝 Create New Trade", callback_data="menu_create")
        )

    # Only add core row if it has buttons
    if core_row:
        keyboard_rows.append(core_row)

    # Utility row 1 - Consolidated Trades & Messages
    utility_row_1 = []

    # My Trades with unified consistent badge format
    if active_escrows > 0:
        utility_row_1.append(
            InlineKeyboardButton(
                f"📋 My Trades ({active_escrows})",
                callback_data="trades_messages_hub",
            )
        )
    else:
        utility_row_1.append(
            InlineKeyboardButton(
                "📋 My Trades", callback_data="trades_messages_hub"
            )
        )

    keyboard_rows.append(utility_row_1)
    
    # Add active disputes button if user has disputes (Option 1 - Direct Dispute Access)
    if active_disputes > 0:
        keyboard_rows.append([
            InlineKeyboardButton(
                f"⚠️ Active Disputes ({active_disputes})",
                callback_data="view_disputes"
            )
        ])
    
    # Add invitation button in separate row for sellers with pending invitations
    if pending_invitations > 0:
        keyboard_rows.append([
            InlineKeyboardButton(
                f"⚡ View {pending_invitations} Invitation{'s' if pending_invitations != 1 else ''}",
                callback_data="view_pending_invitations",
            )
        ])

    # Utility row 2 - Wallet (separate row for better visibility)
    utility_row_2 = []

    # Wallet with smart text
    if balance >= 10.0:
        utility_row_2.append(
            InlineKeyboardButton("💰 My Wallet", callback_data=CallbackData.MENU_WALLET)
        )
    elif balance > 0:
        utility_row_2.append(
            InlineKeyboardButton("💰 Wallet", callback_data=CallbackData.MENU_WALLET)
        )
    else:
        utility_row_2.append(
            InlineKeyboardButton("➕ Add Funds", callback_data=CallbackData.MENU_WALLET)
        )

    # Combine wallet and referral buttons in one row
    if referral_count > 0:
        utility_row_2.append(
            InlineKeyboardButton(f"🎁 Referrals ({referral_count})", callback_data="invite_friends")
        )
    else:
        utility_row_2.append(
            InlineKeyboardButton("🎁 Invite Friends", callback_data="invite_friends")
        )

    keyboard_rows.append(utility_row_2)

    # IMPROVED: Support & Settings row with clearer labels
    keyboard_rows.append([
        InlineKeyboardButton("🎧 Support", callback_data="menu_support"),
        InlineKeyboardButton("⚙️ Settings & Help", callback_data="hamburger_menu")
    ])
    
    # Partner Program row (for group/channel owners)
    keyboard_rows.append([
        InlineKeyboardButton("🤝 Partner Program", callback_data="partner_program")
    ])

    return InlineKeyboardMarkup(keyboard_rows)


def hamburger_menu_keyboard():
    """IMPROVED: Clear settings menu with better organization"""
    keyboard = [
        [
            InlineKeyboardButton("👤 My Profile", callback_data="menu_profile"),
            InlineKeyboardButton("🔔 Notifications", callback_data="user_settings"),
        ],
        [
            InlineKeyboardButton("📋 Transaction History", callback_data="transaction_history"),
            InlineKeyboardButton("⭐ Rating System", callback_data="rating_discovery"),
        ],
        [
            InlineKeyboardButton("🔍 Browse Sellers", callback_data="browse_sellers"),
        ],
        [
            InlineKeyboardButton("📞 Support Chat", callback_data="start_support_chat"),
            InlineKeyboardButton("❓ Help & FAQ", callback_data=CallbackData.MENU_HELP),
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def currency_selection_keyboard():
    """Mobile-optimized cryptocurrency selection keyboard"""
    keyboard = []
    currencies = Config.SUPPORTED_CURRENCIES

    # Group currencies in rows of 3 for better mobile UX with shorter labels
    for i in range(0, len(currencies), 3):
        row = []
        for currency in currencies[i : i + 3]:
            emoji = CURRENCY_EMOJIS.get(currency, "💰")
            # Mobile-optimized shorter button text
            if currency == "USDT-ERC20":
                button_text = f"{emoji} USDT-E20"
            elif currency == "USDT-TRC20":
                button_text = f"{emoji} USDT-T20"
            else:
                button_text = f"{emoji} {currency}"
            callback_data = f"{CallbackData.CURRENCY_SELECT}:{currency}"
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        keyboard.append(row)

    # Universal navigation pattern
    keyboard.append(
        [
            InlineKeyboardButton("⬅️ Back", callback_data=CallbackData.BACK),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
        ]
    )
    return InlineKeyboardMarkup(keyboard)


def network_selection_keyboard(currency):
    """Mobile-optimized network selection keyboard"""
    keyboard = []
    networks = Config.CURRENCY_NETWORKS.get(currency, [])

    # Group networks in rows of 2 for better mobile UX
    for i in range(0, len(networks), 2):
        row = []
        for network in networks[i : i + 2]:
            # Add emoji for better visual recognition
            if "TRC20" in network:
                display_text = f"⚡ {network}"
            elif "ERC20" in network:
                display_text = f"🔷 {network}"
            else:
                display_text = f"🔗 {network}"
            callback_data = f"{CallbackData.NETWORK_SELECT}:{network}"
            row.append(InlineKeyboardButton(display_text, callback_data=callback_data))
        keyboard.append(row)

    # Universal navigation pattern
    keyboard.append(
        [
            InlineKeyboardButton("⬅️ Back", callback_data=CallbackData.BACK),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
        ]
    )
    return InlineKeyboardMarkup(keyboard)


def timeout_selection_keyboard():
    """Mobile-optimized timeout selection with clear recommendations"""
    keyboard = []
    # Group timeouts in rows of 2 for mobile-friendly layout
    timeout_items = list(TIMEOUT_OPTIONS.items())
    for i in range(0, len(timeout_items), 2):
        row = []
        for hours, display in timeout_items[i : i + 2]:
            callback_data = f"timeout:{hours}"
            # Shorter display text for mobile with better icons
            short_display = (
                display.replace("(recommended)", "⭐")
                .replace(" days", "d")
                .replace(" hours", "h")
            )
            row.append(InlineKeyboardButton(short_display, callback_data=callback_data))
        keyboard.append(row)

    # Universal navigation pattern
    keyboard.append(
        [
            InlineKeyboardButton("⬅️ Back", callback_data=CallbackData.BACK),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
        ]
    )
    return InlineKeyboardMarkup(keyboard)


def escrow_confirmation_keyboard(can_pay_from_wallet=False, payment_method="crypto"):
    """Simplified trade confirmation keyboard with clear CTAs"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Create Trade", callback_data=CallbackData.ESCROW_CONFIRM
            )
        ],
        [
            InlineKeyboardButton("⚙️ Edit Details", callback_data="edit_trade_details"),
            InlineKeyboardButton("⏰ Timeout", callback_data="change_timeout"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data=CallbackData.ESCROW_CANCEL),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def seller_invitation_keyboard():
    """Seller invitation acceptance keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Accept & Start", callback_data=CallbackData.ESCROW_ACCEPT
            ),
            InlineKeyboardButton("❌ Pass", callback_data=CallbackData.ESCROW_DECLINE),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def buyer_action_keyboard(escrow_id):
    """Compact buyer action keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Release", callback_data=f"{CallbackData.ESCROW_RELEASE}:{escrow_id}"
            ),
            InlineKeyboardButton(
                "⚠️ Dispute", callback_data=f"{CallbackData.ESCROW_DISPUTE}:{escrow_id}"
            ),
            InlineKeyboardButton(
                "💬 Message", callback_data=f"{CallbackData.ESCROW_MESSAGE}:{escrow_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "📎 Files", callback_data=f"{CallbackData.ESCROW_FILES}:{escrow_id}"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def escrow_list_keyboard(escrows, page=0, per_page=5):
    """Keyboard for trade list with pagination"""
    keyboard = []
    start_idx = page * per_page
    end_idx = start_idx + per_page

    for escrow in escrows[start_idx:end_idx]:
        status_emoji = STATUS_EMOJIS.get(escrow.status, "❓")
        currency_emoji = CURRENCY_EMOJIS.get(escrow.currency, "💰")
        button_text = f"{status_emoji} #{escrow.escrow_id} - {currency_emoji}{escrow.amount} {escrow.currency}"
        callback_data = f"{CallbackData.ESCROW_VIEW}:{escrow.id}"
        keyboard.append(
            [InlineKeyboardButton(button_text, callback_data=callback_data)]
        )

    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("⬅️ Previous", callback_data=f"escrows_page:{page-1}")
        )
    if end_idx < len(escrows):
        nav_buttons.append(
            InlineKeyboardButton("➡️ Next", callback_data=f"escrows_page:{page+1}")
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def wallet_menu_keyboard(user_wallets, total_balance=0):
    """Compact wallet menu keyboard with add funds option"""
    # Action buttons in compact layout with dynamic balance display
    if total_balance >= 10:
        cashout_text = f"💸 Cash Out (${total_balance:.2f})"
    elif total_balance > 0:
        cashout_text = f"💸 Cash Out (${total_balance:.2f})"
    else:
        cashout_text = "💸 Cash Out"
    
    keyboard = [
        [
            InlineKeyboardButton(
                cashout_text, callback_data=CallbackData.WALLET_WITHDRAW
            ),
            InlineKeyboardButton(
                "📜 History", callback_data=CallbackData.WALLET_HISTORY
            ),
        ],
        [InlineKeyboardButton("💰 Add Funds", callback_data="wallet_add_funds")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="cashout_settings")],
        [InlineKeyboardButton("⬅️ Back", callback_data=CallbackData.BACK)],
    ]
    return InlineKeyboardMarkup(keyboard)


def wallet_menu_keyboard_usd(total_balance=0):
    """Simplified USD wallet menu keyboard with dynamic balance"""
    # Smart cashout button text
    if total_balance >= 10:
        cashout_text = f"💸 Cash Out (${total_balance:.2f})"
    elif total_balance > 0:
        cashout_text = f"💸 Cash Out (${total_balance:.2f})"
    else:
        cashout_text = "💸 Cash Out"
    
    keyboard = [
        [
            InlineKeyboardButton("💰 Add Funds", callback_data="wallet_add_funds"),
            InlineKeyboardButton(
                cashout_text, callback_data=CallbackData.WALLET_WITHDRAW
            ),
        ],
        [
            InlineKeyboardButton(
                "📜 History", callback_data=CallbackData.WALLET_HISTORY
            ),
            InlineKeyboardButton("⚙️ Settings", callback_data="cashout_settings"),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back to Main", callback_data=CallbackData.BACK_TO_MAIN
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def cashout_confirmation_keyboard():
    """CashOut confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_cashout"),
            InlineKeyboardButton("❌ Cancel", callback_data=CallbackData.CANCEL),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def dispute_reason_keyboard():
    """Compact dispute reason selection keyboard"""
    keyboard = []
    reasons = list(DISPUTE_REASONS.items())

    # Group reasons in rows of 2 for mobile-friendly layout
    for i in range(0, len(reasons), 2):
        row = []
        for reason, display in reasons[i : i + 2]:
            callback_data = f"{CallbackData.DISPUTE_REASON}:{reason}"
            # Shorter display text
            short_display = display.replace("Service", "").replace("issues", "").strip()
            row.append(InlineKeyboardButton(short_display, callback_data=callback_data))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=CallbackData.BACK)])
    return InlineKeyboardMarkup(keyboard)


def rating_keyboard():
    """Rating selection keyboard"""
    keyboard = []
    for i in range(1, 6):
        stars = "⭐" * i
        callback_data = f"{CallbackData.RATING_GIVE}:{i}"
        keyboard.append(
            [InlineKeyboardButton(f"{stars} ({i}/5)", callback_data=callback_data)]
        )

    keyboard.append(
        [
            InlineKeyboardButton("⏭️ Skip", callback_data=CallbackData.RATING_SKIP),
            InlineKeyboardButton("⬅️ Back", callback_data=CallbackData.BACK),
        ]
    )
    return InlineKeyboardMarkup(keyboard)


def admin_resolve_keyboard(dispute_id):
    """Admin dispute resolution keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Release to Seller",
                callback_data=f"{CallbackData.ADMIN_RESOLVE}:{dispute_id}:release",
            ),
            InlineKeyboardButton(
                "🔄 Refund to Buyer",
                callback_data=f"{CallbackData.ADMIN_RESOLVE}:{dispute_id}:refund",
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 Split 50/50",
                callback_data=f"{CallbackData.ADMIN_RESOLVE}:{dispute_id}:split",
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def yes_no_keyboard(action):
    """Simple Yes/No keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ No", callback_data=f"cancel_{action}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard():
    """Simple back keyboard"""
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data=CallbackData.BACK)]]
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard():
    """Simple cancel keyboard"""
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data=CallbackData.CANCEL)]]
    return InlineKeyboardMarkup(keyboard)


# Active escrow management keyboards
def active_escrow_buyer_keyboard(escrow_id):
    """Keyboard for buyer managing active escrow"""
    keyboard = [
        [
            InlineKeyboardButton(
                "💬 Message Seller",
                callback_data=f"{CallbackData.ESCROW_MESSAGE}:{escrow_id}",
            ),
            InlineKeyboardButton(
                "📁 Files & Chat", callback_data=f"escrow_files:{escrow_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "✅ Release Payment", callback_data=f"escrow_release:{escrow_id}"
            ),
            InlineKeyboardButton(
                "🚨 Open Dispute", callback_data=f"escrow_dispute:{escrow_id}"
            ),
        ],
        [
            InlineKeyboardButton("📂 My Escrows", callback_data="my_escrows"),
            InlineKeyboardButton("🏠 Main Menu", callback_data=CallbackData.BACK),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def active_escrow_seller_keyboard(escrow_id):
    """Keyboard for seller managing active escrow"""
    keyboard = [
        [
            InlineKeyboardButton(
                "💬 Message Buyer",
                callback_data=f"{CallbackData.ESCROW_MESSAGE}:{escrow_id}",
            ),
            InlineKeyboardButton(
                "📁 Files & Chat", callback_data=f"escrow_files:{escrow_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🚨 Open Dispute", callback_data=f"escrow_dispute:{escrow_id}"
            )
        ],
        [
            InlineKeyboardButton("📂 My Escrows", callback_data="my_escrows"),
            InlineKeyboardButton("🏠 Main Menu", callback_data=CallbackData.BACK),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def post_acceptance_navigation_keyboard(escrow_id, is_buyer=True, escrow_status=None):
    """Advanced role-based navigation for escrow management"""
    keyboard = []

    # First row - Communication (always available)
    if is_buyer:
        first_row = [
            InlineKeyboardButton(
                "💬 Message Seller",
                callback_data=f"{CallbackData.ESCROW_MESSAGE}:{escrow_id}",
            ),
            InlineKeyboardButton(
                "📋 Details", callback_data=f"escrow_details:{escrow_id}"
            ),
        ]
    else:  # seller
        first_row = [
            InlineKeyboardButton(
                "💬 Message Buyer",
                callback_data=f"{CallbackData.ESCROW_MESSAGE}:{escrow_id}",
            ),
            InlineKeyboardButton(
                "📋 Details", callback_data=f"escrow_details:{escrow_id}"
            ),
        ]

    keyboard.append(first_row)

    # Second row - Role-specific actions based on status
    action_row = []

    if escrow_status in ["ACTIVE", "FUNDED", "PAYMENT_CONFIRMED"]:
        if is_buyer:
            # Buyer can release payment or open dispute
            action_row.extend(
                [
                    InlineKeyboardButton(
                        "✅ Release Payment",
                        callback_data=f"escrow_release:{escrow_id}",
                    ),
                    InlineKeyboardButton(
                        "🚨 Dispute", callback_data=f"escrow_dispute:{escrow_id}"
                    ),
                ]
            )
        else:  # seller
            # Seller can only open dispute (cannot self-release)
            action_row.append(
                InlineKeyboardButton(
                    "🚨 Open Dispute", callback_data=f"escrow_dispute:{escrow_id}"
                )
            )

    elif escrow_status == "PENDING" and not is_buyer:
        # Only sellers see accept/decline for pending escrows
        action_row.extend(
            [
                InlineKeyboardButton(
                    "✅ Accept", callback_data=f"escrow_accept:{escrow_id}"
                ),
                InlineKeyboardButton(
                    "❌ Decline", callback_data=f"escrow_decline:{escrow_id}"
                ),
            ]
        )

    if action_row:
        keyboard.append(action_row)

    # Final row - Navigation (always present)
    nav_row = [
        InlineKeyboardButton("🔔 My Trades", callback_data="my_escrows"),
        InlineKeyboardButton("🏠 Main Menu", callback_data=CallbackData.BACK),
    ]
    keyboard.append(nav_row)

    return InlineKeyboardMarkup(keyboard)


# Alias for backward compatibility
cryptocurrency_selection_keyboard = currency_selection_keyboard

"""
Markdown escaping utilities to prevent injection attacks
Provides safe handling of user-generated content in Telegram messages
"""

import html
from typing import Optional, Any

# Characters that need escaping in Telegram MarkdownV2
MARKDOWN_V2_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!"

# Characters that need escaping in legacy Markdown
MARKDOWN_ESCAPE_CHARS = r"_*`["


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2 format
    Prevents markdown injection while preserving message readability
    """
    if not text:
        return ""

    # Convert to string and handle None
    text = str(text) if text is not None else ""

    # Escape each special character
    for char in MARKDOWN_V2_ESCAPE_CHARS:
        text = text.replace(char, f"\\{char}")

    return text


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram legacy Markdown format
    Used when parse_mode='Markdown' is specified
    """
    if not text:
        return ""

    # Convert to string and handle None
    text = str(text) if text is not None else ""

    # Escape each special character
    for char in MARKDOWN_ESCAPE_CHARS:
        text = text.replace(char, f"\\{char}")

    return text


def escape_html(text: str) -> str:
    """
    Escape HTML special characters for Telegram HTML format
    Used when parse_mode='HTML' is specified
    """
    if not text:
        return ""

    # Convert to string and handle None
    text = str(text) if text is not None else ""

    # Use Python's html.escape for proper HTML escaping
    return html.escape(text, quote=True)


def safe_format_user_display(
    first_name: Optional[str],
    username: Optional[str] = None,
    fallback: str = "User",
    escape_func=escape_markdown,
) -> str:
    """
    Safely format user display name with proper escaping
    Prevents markdown injection in user-generated names
    """
    # Get display name with fallback
    display_name = first_name or fallback

    # Escape the display name
    safe_name = escape_func(str(display_name))

    # Add username if available
    if username:
        safe_username = escape_func(str(username))
        return f"{safe_name} • @{safe_username}"

    return safe_name


def safe_format_amount(
    amount: Any, currency: str = "USD", escape_func=escape_markdown
) -> str:
    """
    Safely format monetary amounts with proper escaping
    """
    try:
        # Convert to float and format
        amount_float = float(amount) if amount is not None else 0.0
        formatted = f"${amount_float:.2f} {currency}"
        return escape_func(formatted)
    except (ValueError, TypeError):
        return escape_func(f"$0.00 {currency}")


def safe_format_trade_id(trade_id: Any, escape_func=escape_markdown) -> str:
    """
    Safely format trade IDs with proper escaping
    """
    if not trade_id:
        return escape_func("Unknown")

    return escape_func(str(trade_id))


def safe_format_bank_details(
    bank_name: Optional[str],
    account_number: Optional[str],
    account_name: Optional[str],
    escape_func=escape_markdown,
) -> str:
    """
    Safely format bank account details with proper escaping and masking
    """
    # Escape bank name
    safe_bank = (
        escape_func(str(bank_name)) if bank_name else escape_func("Unknown Bank")
    )

    # Mask and escape account number
    if account_number and len(str(account_number)) >= 4:
        masked_account = f"***{str(account_number)[-4:]}"
        safe_account = escape_func(masked_account)
    else:
        safe_account = escape_func("***")

    # Escape account name
    safe_name = (
        escape_func(str(account_name)) if account_name else escape_func("Unknown")
    )

    return f"{safe_bank}: {safe_account} ({safe_name})"


def safe_format_crypto_address(
    address: Optional[str], currency: Optional[str] = None, escape_func=escape_markdown
) -> str:
    """
    Safely format cryptocurrency addresses with masking and escaping
    """
    if not address:
        return escape_func("Unknown Address")

    # Mask address for security (show first 6 and last 4 characters)
    address_str = str(address)
    if len(address_str) > 10:
        masked_address = f"{address_str[:6]}...{address_str[-4:]}"
    else:
        masked_address = address_str

    safe_address = escape_func(masked_address)

    if currency:
        safe_currency = escape_func(str(currency))
        return f"{safe_currency}: {safe_address}"

    return safe_address


def sanitize_message_content(content: str, parse_mode: str = "Markdown") -> str:
    """
    Sanitize message content based on the specified parse mode
    Central function for all message sanitization
    """
    if not content:
        return ""

    if parse_mode == "MarkdownV2":
        return escape_markdown_v2(content)
    elif parse_mode == "Markdown":
        return escape_markdown(content)
    elif parse_mode == "HTML":
        return escape_html(content)
    else:
        # No parse mode - still escape basic problematic characters
        return escape_markdown(content)


# Convenience functions for common patterns
def safe_user_mention(user, escape_func=escape_markdown) -> str:
    """Create safe user mention string"""
    first_name = getattr(user, "first_name", None)
    username = getattr(user, "username", None)
    return safe_format_user_display(first_name, username, escape_func=escape_func)


def safe_trade_summary(escrow, escape_func=escape_markdown) -> str:
    """Create safe trade summary string"""
    amount = getattr(escrow, "amount", 0)
    escrow_id = getattr(escrow, "escrow_id", "Unknown")

    safe_amount = safe_format_amount(amount, escape_func=escape_func)
    safe_id = safe_format_trade_id(escrow_id, escape_func=escape_func)

    return f"Trade #{safe_id} • {safe_amount}"


def format_username_html(username: str, include_link: bool = True) -> str:
    """
    Format username for HTML parse mode without backslash escaping
    
    Args:
        username: The username (with or without @)
        include_link: If True, creates clickable link to t.me/username
    
    Returns:
        HTML formatted username: <a href="...">@username</a> or @username
    
    Example:
        >>> format_username_html("john_doe")
        '<a href="https://t.me/john_doe">@john_doe</a>'
        >>> format_username_html("@john_doe", include_link=False)
        '@john_doe'
    """
    if not username:
        return ""
    
    # Remove @ if present and clean backslashes
    clean_username = str(username).lstrip('@').replace('\\', '')
    
    if include_link:
        return f'<a href="https://t.me/{html.escape(clean_username)}">@{html.escape(clean_username)}</a>'
    else:
        return f'@{html.escape(clean_username)}'

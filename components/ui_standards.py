"""
Standardized UI Constants and Patterns for Scene Engine Components

Ensures consistent styling, messaging, and behavior across all component types.
Used by component_renderer.py to maintain uniform user experience.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class StandardButton:
    """Standardized button configuration"""
    text: str
    emoji: str
    callback_data: str
    
    @property
    def display_text(self) -> str:
        return f"{self.emoji} {self.text}"


class UIStandards:
    """Centralized UI standards for consistent component rendering"""
    
    # ===== STANDARDIZED ICONS =====
    ICONS = {
        # Navigation
        'back': '⬅️',
        'cancel': '❌', 
        'confirm': '✅',
        'home': '🏠',
        'retry': '🔄',
        'new': '🆕',
        
        # Status
        'processing': '⏳',
        'completed': '✅',
        'failed': '❌',
        'pending': '🔄',
        'warning': '⚠️',
        'success': '🎉',
        
        # Financial
        'amount': '💰',
        'currency': '💱',
        'fee': '💸',
        'total': '💵',
        'bank': '🏦',
        'crypto': '🪙',
        'address': '🔗',
        'wallet': '👛',
        
        # Actions
        'input': '💬',
        'select': '📋',
        'verify': '🔐',
        'add': '➕',
        'edit': '✏️',
        'save': '💾',
        'delete': '🗑️',
        
        # Information
        'info': 'ℹ️',
        'id': '🆔',
        'time': '⏰',
        'details': '📊',
        'summary': '📋',
        'receipt': '🧾'
    }
    
    # ===== STANDARDIZED BUTTONS =====
    STANDARD_BUTTONS = {
        'back': StandardButton('Back', ICONS['back'], 'scene_back'),
        'cancel': StandardButton('Cancel', ICONS['cancel'], 'scene_cancel'),
        'confirm': StandardButton('Confirm', ICONS['confirm'], 'confirm_yes'),
        'deny': StandardButton('Cancel', ICONS['cancel'], 'confirm_no'),
        'home': StandardButton('Main Menu', ICONS['home'], 'main_menu'),
        'retry': StandardButton('Retry', ICONS['retry'], 'retry_transaction'),
        'new_transaction': StandardButton('New Transaction', ICONS['new'], 'new_transaction'),
        'add_new': StandardButton('Add New', ICONS['add'], 'add_new'),
    }
    
    # ===== MESSAGE TEMPLATES =====
    MESSAGE_TEMPLATES = {
        'header': "{icon} {title}\n\n{description}\n\n",
        'section_header': "{icon} {section_name}:\n",
        'amount_display': "{icon} Amount: {currency_symbol}{amount}",
        'currency_display': "{icon} Currency: {currency}",
        'fee_display': "{icon} Fee: {currency_symbol}{fee}",
        'total_display': "{icon} Total: {currency_symbol}{total}",
        'timeout_warning': "⏱️ Please respond within {minutes} minutes or this session will expire.",
        'input_prompt': "{icon} Please enter {input_type}:",
        'selection_prompt': "{icon} Please choose an option:",
        'confirmation_prompt': "{icon} Please review and confirm:",
        'error_message': "{icon} {error_type}: {message}",
        'success_message': "{icon} Success: {message}",
        'processing_message': "{icon} Processing: {message}"
    }
    
    # ===== TIMEOUT SETTINGS =====
    TIMEOUT_SETTINGS = {
        'amount_input': {'seconds': 300, 'warning_at': 240},  # 5 minutes, warn at 4
        'address_input': {'seconds': 600, 'warning_at': 480}, # 10 minutes, warn at 8
        'bank_selection': {'seconds': 600, 'warning_at': 480}, # 10 minutes, warn at 8
        'otp_verification': {'seconds': 300, 'warning_at': 240}, # 5 minutes, warn at 4
        'confirmation': {'seconds': 120, 'warning_at': 90},   # 2 minutes, warn at 1.5
        'text_input': {'seconds': 300, 'warning_at': 240},   # 5 minutes, warn at 4
        'selection': {'seconds': 300, 'warning_at': 240},    # 5 minutes, warn at 4
        'default': {'seconds': 300, 'warning_at': 240}       # Default fallback
    }
    
    # ===== CURRENCY FORMATTING =====
    CURRENCY_FORMATS = {
        'USD': {'symbol': '$', 'decimals': 2, 'prefix': True},
        'NGN': {'symbol': '₦', 'decimals': 2, 'prefix': True},
        'BTC': {'symbol': '₿', 'decimals': 8, 'prefix': False},
        'ETH': {'symbol': 'Ξ', 'decimals': 6, 'prefix': False},
        'LTC': {'symbol': 'Ł', 'decimals': 6, 'prefix': False},
        'USDT': {'symbol': '₮', 'decimals': 2, 'prefix': False},
    }
    
    # ===== ERROR PATTERNS =====
    ERROR_PATTERNS = {
        'validation_failed': {
            'icon': ICONS['warning'],
            'title': 'Validation Error',
            'retry_allowed': True,
            'show_details': True
        },
        'timeout_expired': {
            'icon': ICONS['warning'], 
            'title': 'Session Timeout',
            'retry_allowed': True,
            'show_details': False
        },
        'processing_failed': {
            'icon': ICONS['failed'],
            'title': 'Processing Failed', 
            'retry_allowed': True,
            'show_details': True
        },
        'network_error': {
            'icon': ICONS['warning'],
            'title': 'Connection Error',
            'retry_allowed': True,
            'show_details': False
        },
        'insufficient_balance': {
            'icon': ICONS['warning'],
            'title': 'Insufficient Balance',
            'retry_allowed': False,
            'show_details': True
        }
    }
    
    @classmethod
    def format_currency(cls, amount: float, currency: str) -> str:
        """Format currency amount according to standards"""
        format_config = cls.CURRENCY_FORMATS.get(currency, cls.CURRENCY_FORMATS['USD'])
        
        # Format the amount with proper decimals
        decimals = format_config['decimals']
        formatted_amount = f"{amount:.{decimals}f}"
        
        # Add currency symbol
        symbol = format_config['symbol']
        if format_config['prefix']:
            return f"{symbol}{formatted_amount}"
        else:
            return f"{formatted_amount} {symbol}"
    
    @classmethod
    def format_address(cls, address: str, currency: str = None) -> str:
        """Format crypto address for display"""
        if len(address) <= 20:
            return address
        # Show first 8 and last 6 characters for long addresses
        return f"{address[:8]}...{address[-6:]}"
    
    @classmethod
    def get_timeout_message(cls, component_type: str, remaining_seconds: int) -> str:
        """Get standardized timeout warning message"""
        minutes = remaining_seconds // 60
        if minutes > 0:
            return cls.MESSAGE_TEMPLATES['timeout_warning'].format(minutes=minutes)
        else:
            return "⚡ Please respond quickly - session expires soon!"
    
    @classmethod
    def get_error_display(cls, error_type: str, message: str, allow_retry: bool = True) -> Dict[str, Any]:
        """Get standardized error display configuration"""
        pattern = cls.ERROR_PATTERNS.get(error_type, cls.ERROR_PATTERNS['processing_failed'])
        
        return {
            'icon': pattern['icon'],
            'title': pattern['title'],
            'message': message,
            'retry_allowed': pattern['retry_allowed'] and allow_retry,
            'show_details': pattern['show_details']
        }
    
    @classmethod 
    def build_keyboard_row(cls, buttons: List[str], max_per_row: int = 2) -> List[List]:
        """Build standardized keyboard rows from button names"""
        from telegram import InlineKeyboardButton
        
        keyboard = []
        row = []
        
        for button_name in buttons:
            if button_name in cls.STANDARD_BUTTONS:
                btn = cls.STANDARD_BUTTONS[button_name]
                row.append(InlineKeyboardButton(btn.display_text, callback_data=btn.callback_data))
            else:
                # Custom button - assume format "text|callback_data"
                if '|' in button_name:
                    text, callback = button_name.split('|', 1)
                    row.append(InlineKeyboardButton(text, callback_data=callback))
            
            if len(row) >= max_per_row:
                keyboard.append(row)
                row = []
        
        if row:  # Add remaining buttons
            keyboard.append(row)
            
        return keyboard
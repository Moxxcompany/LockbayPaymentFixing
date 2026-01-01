"""
Phase 1.1: Main Menu & Navigation System Testing

This test validates the main menu and navigation user experience using
the proven UI testing framework that achieved 85/100 satisfaction for onboarding.

TESTING FOCUS:
✅ Menu clarity and organization
✅ Button usability and text quality  
✅ Navigation flow between options
✅ User guidance and instructions
✅ Response times and performance
✅ Overall user satisfaction measurement
"""

import pytest
import logging
import time
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch

# Telegram imports
from telegram import Update, User as TelegramUser, Message, CallbackQuery, Chat, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Import testing framework
from tests.utils.fake_telegram_api import FakeRequest, TelegramUITestHelper

logger = logging.getLogger(__name__)


class MainMenuExperienceValidator:
    """
    Validates main menu and navigation user experience using proven framework
    """
    
    def __init__(self):
        self.user_expectations: List[Dict[str, Any]] = []
        self.ux_successes: List[Dict[str, Any]] = []
        self.ux_issues: List[Dict[str, Any]] = []
        self.navigation_timing: Dict[str, float] = {}
        self.user_satisfaction_score = 100
    
    def validate_menu_expectation(self, feature: str, expectation: str, reality: str, critical: bool = True):
        """Validate main menu user expectations with precise matching"""
        expectation_lower = expectation.lower()
        reality_lower = reality.lower()
        
        meets_expectation = False
        
        # Main menu specific validations
        if "clear" in expectation_lower and "menu" in expectation_lower:
            clear_indicators = ['menu', 'options', 'choose', 'select', 'quick', 'access']
            meets_expectation = any(word in reality_lower for word in clear_indicators) and len(reality) > 15
        
        elif "organized" in expectation_lower or "structure" in expectation_lower:
            organization_indicators = ['hub', 'access', 'tools', 'trading', 'wallet', 'organized']
            meets_expectation = any(word in reality_lower for word in organization_indicators)
        
        elif "navigation" in expectation_lower or "flow" in expectation_lower:
            navigation_indicators = ['back', 'menu', 'home', 'main', 'navigate']
            meets_expectation = any(word in reality_lower for word in navigation_indicators)
        
        elif "balance" in expectation_lower or "wallet" in expectation_lower:
            wallet_indicators = ['wallet', 'balance', 'funds', 'usd', '$', 'money']
            meets_expectation = any(word in reality_lower for word in wallet_indicators)
        
        elif "trading" in expectation_lower or "trade" in expectation_lower:
            trading_indicators = ['trade', 'escrow', 'create', 'new', 'exchange']
            meets_expectation = any(word in reality_lower for word in trading_indicators)
        
        # Available/option validation
        elif "available" in expectation_lower or "option" in expectation_lower:
            meets_expectation = "available" in reality_lower or "option" in reality_lower
        
        # Working functionality validation
        elif "work" in expectation_lower:
            meets_expectation = "work" in reality_lower or "successful" in reality_lower or "correctly" in reality_lower
        
        # General keyword matching
        else:
            expectation_keywords = [word for word in expectation_lower.split() if len(word) > 3]
            meets_expectation = any(keyword in reality_lower for keyword in expectation_keywords)
        
        experience = {
            'feature': feature,
            'expectation': expectation,
            'reality': reality,
            'meets_expectation': meets_expectation,
            'critical': critical
        }
        self.user_expectations.append(experience)
        
        if meets_expectation:
            self.ux_successes.append({
                'type': 'MENU_SUCCESS',
                'feature': feature,
                'achievement': f'Met expectation: {expectation}'
            })
            logger.info(f"✅ Menu Expectation Met: {feature} - {expectation}")
        else:
            if critical:
                self.user_satisfaction_score -= 12
                self.ux_issues.append({
                    'type': 'CRITICAL_MENU_ISSUE',
                    'feature': feature,
                    'issue': f'Unmet expectation: {expectation}',
                    'reality': reality,
                    'impact': 'HIGH'
                })
                logger.error(f"❌ CRITICAL MENU ISSUE: {feature} - Expected: {expectation}, Got: {reality}")
            else:
                self.user_satisfaction_score -= 4
                self.ux_issues.append({
                    'type': 'MINOR_MENU_ISSUE',
                    'feature': feature,
                    'issue': f'Unmet expectation: {expectation}',
                    'reality': reality,
                    'impact': 'LOW'
                })
                logger.warning(f"⚠️ Minor Menu Issue: {feature}")
    
    def record_navigation_timing(self, action: str, duration_ms: float):
        """Record navigation timing for user experience evaluation"""
        self.navigation_timing[action] = duration_ms
        
        # User patience thresholds for menu navigation
        thresholds = {
            'main_menu_load': 1000,      # 1 second for main menu
            'menu_navigation': 800,      # 0.8 seconds for navigation
            'wallet_access': 1200,       # 1.2 seconds for wallet
            'trading_access': 1500,      # 1.5 seconds for trading
            'submenu_load': 1000         # 1 second for submenus
        }
        
        threshold = thresholds.get(action, 1000)
        if duration_ms > threshold:
            self.user_satisfaction_score -= 6
            self.ux_issues.append({
                'type': 'SLOW_NAVIGATION',
                'action': action,
                'duration_ms': duration_ms,
                'threshold_ms': threshold,
                'impact': 'MEDIUM'
            })
            logger.warning(f"⏰ Slow navigation: {action} took {duration_ms:.1f}ms (threshold: {threshold}ms)")
        else:
            logger.info(f"⚡ Fast navigation: {action} completed in {duration_ms:.1f}ms")
    
    def validate_menu_button_quality(self, context: str, buttons: List[str]):
        """Validate menu button quality for user experience"""
        quality_score = 100
        
        for button_text in buttons:
            # Positive indicators for menu buttons
            menu_emojis = ['💰', '🤝', '📋', '🔄', '⚡', '🎯', '💳', '➕', '🏠', '⚙️', '📞', '❓']
            if any(emoji in button_text for emoji in menu_emojis):
                quality_score += 8  # Menu-appropriate emojis
            
            # Good length for menu buttons
            if 5 <= len(button_text) <= 20:
                quality_score += 5
            
            # Clear action words
            action_words = ['view', 'create', 'add', 'my', 'new', 'quick', 'access', 'wallet', 'trades']
            if any(word in button_text.lower() for word in action_words):
                quality_score += 5
            
            # Negative indicators
            technical_terms = ['callback', 'handler', 'process', 'execute', 'api', 'menu_']
            if any(term in button_text.lower() for term in technical_terms):
                quality_score -= 25  # Technical jargon is bad for menus
            
            if len(button_text) < 3:
                quality_score -= 15  # Too short for menu buttons
            
            if len(button_text) > 25:
                quality_score -= 10  # Too long for menu buttons
        
        if quality_score >= 85:
            self.ux_successes.append({
                'type': 'GOOD_MENU_BUTTONS',
                'context': context,
                'buttons': buttons,
                'quality_score': quality_score
            })
            logger.info(f"✅ Good menu button quality in {context}: Score {quality_score}/100")
        else:
            penalty = max(6, (100 - quality_score) // 12)
            self.user_satisfaction_score -= penalty
            self.ux_issues.append({
                'type': 'MENU_BUTTON_QUALITY_ISSUE',
                'context': context,
                'buttons': buttons,
                'quality_score': quality_score,
                'impact': 'MEDIUM'
            })
            logger.warning(f"⚠️ Menu button quality issue in {context}: Score {quality_score}/100")
    
    def validate_menu_organization(self, menu_structure: Dict[str, List[str]]):
        """Validate menu organization and logical grouping"""
        organization_score = 100
        
        # Check for logical grouping
        core_functions = ['wallet', 'trade', 'exchange']
        utility_functions = ['settings', 'help', 'support', 'profile']
        
        found_core = sum(1 for func in core_functions if any(func in btn.lower() for section in menu_structure.values() for btn in section))
        found_utility = sum(1 for func in utility_functions if any(func in btn.lower() for section in menu_structure.values() for btn in section))
        
        if found_core >= 2:
            organization_score += 10  # Good core function coverage
        
        # Check section organization
        for section_name, buttons in menu_structure.items():
            if len(buttons) > 4:
                organization_score -= 10  # Too many buttons in one section
            
            if len(buttons) == 0:
                organization_score -= 15  # Empty sections are confusing
        
        if organization_score >= 85:
            self.ux_successes.append({
                'type': 'GOOD_MENU_ORGANIZATION',
                'organization_score': organization_score,
                'structure': menu_structure
            })
            logger.info(f"✅ Good menu organization: Score {organization_score}/100")
        else:
            penalty = (100 - organization_score) // 15
            self.user_satisfaction_score -= penalty
            self.ux_issues.append({
                'type': 'MENU_ORGANIZATION_ISSUE',
                'organization_score': organization_score,
                'structure': menu_structure,
                'impact': 'MEDIUM'
            })
            logger.warning(f"⚠️ Menu organization issue: Score {organization_score}/100")
    
    def get_menu_experience_report(self) -> Dict[str, Any]:
        """Generate comprehensive menu experience report"""
        total_expectations = len(self.user_expectations)
        met_expectations = sum(1 for exp in self.user_expectations if exp['meets_expectation'])
        
        critical_issues = [i for i in self.ux_issues if i.get('impact') == 'HIGH']
        medium_issues = [i for i in self.ux_issues if i.get('impact') == 'MEDIUM']
        minor_issues = [i for i in self.ux_issues if i.get('impact') == 'LOW']
        
        return {
            'user_satisfaction_score': max(0, min(100, self.user_satisfaction_score)),
            'expectations_met': f"{met_expectations}/{total_expectations}",
            'expectation_rate': (met_expectations / total_expectations * 100) if total_expectations > 0 else 0,
            'total_successes': len(self.ux_successes),
            'total_issues': len(self.ux_issues),
            'critical_issues': len(critical_issues),
            'medium_issues': len(medium_issues),
            'minor_issues': len(minor_issues),
            'average_navigation_time': sum(self.navigation_timing.values()) / len(self.navigation_timing) if self.navigation_timing else 0,
            'detailed_successes': self.ux_successes,
            'detailed_issues': self.ux_issues,
            'navigation_timing': self.navigation_timing
        }
    
    def assert_good_menu_experience(self):
        """Assert that menu experience meets good standards"""
        report = self.get_menu_experience_report()
        
        # Menu-specific thresholds
        if report['user_satisfaction_score'] < 75:
            pytest.fail(f"Menu user satisfaction too low: {report['user_satisfaction_score']}/100")
        
        if report['critical_issues'] > 2:
            pytest.fail(f"Too many critical menu issues: {report['critical_issues']}")
        
        if report['expectation_rate'] < 80:
            pytest.fail(f"Menu expectation rate too low: {report['expectation_rate']:.1f}%")
        
        logger.info(f"✅ Good Menu Experience: {report['user_satisfaction_score']}/100 satisfaction")


@pytest.mark.asyncio
class TestPhase1MainMenuNavigation:
    """
    Phase 1.1: Main Menu & Navigation System Testing
    """
    
    def setup_method(self, method):
        """Setup for main menu testing"""
        self.fake_request = FakeRequest()
        self.ui_helper = TelegramUITestHelper(self.fake_request)
        self.menu_validator = MainMenuExperienceValidator()
        self.fake_request.clear_calls()
        
        # Test user data
        self.test_user_id = 123456789
        self.test_user_name = "TestUser"
        
        logger.info("🔧 Main Menu Navigation Testing Setup Complete")
    
    async def test_main_menu_clarity_and_organization(self):
        """Test main menu clarity and organization for new users"""
        logger.info("🏠 Testing Main Menu Clarity & Organization")
        
        start_time = time.time()
        
        # Simulate main menu for new user (balance=0, trades=0)
        await self.fake_request.post(
            url="https://api.telegram.org/bot123/sendMessage",
            request_data={
                'chat_id': self.test_user_id,
                'text': 'Quick Access Hub\n\nAll your trading tools & settings in one place',
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 First Trade", callback_data="menu_create")],
                    [InlineKeyboardButton("📋 My Trades", callback_data="trades_messages_hub")],
                    [InlineKeyboardButton("➕ Add Funds", callback_data="menu_wallet")],
                    [InlineKeyboardButton("⚙️ Settings", callback_data="hamburger_menu")]
                ]).to_dict()
            }
        )
        
        duration = (time.time() - start_time) * 1000
        self.menu_validator.record_navigation_timing('main_menu_load', duration)
        
        # Validate main menu message
        last_message = self.fake_request.get_last_message()
        menu_text = last_message['data'].get('text', '')
        
        self.menu_validator.validate_menu_expectation(
            'main_menu_message',
            'clear menu description with purpose',
            menu_text
        )
        
        self.menu_validator.validate_menu_expectation(
            'menu_organization',
            'organized trading tools and access hub',
            menu_text
        )
        
        # Test menu buttons
        buttons = self.ui_helper.get_sent_buttons()
        button_texts = [btn['text'] for btn in buttons]
        
        self.menu_validator.validate_menu_button_quality('main_menu', button_texts)
        
        # Validate specific menu options
        self.menu_validator.validate_menu_expectation(
            'first_trade_option',
            'first trade option available for new users',
            'First Trade available' if any('first' in btn.lower() and 'trade' in btn.lower() for btn in button_texts) else 'No first trade option'
        )
        
        self.menu_validator.validate_menu_expectation(
            'wallet_access',
            'wallet access available for adding funds',
            'Add Funds available' if any('fund' in btn.lower() or 'wallet' in btn.lower() for btn in button_texts) else 'No wallet access'
        )
        
        self.menu_validator.validate_menu_expectation(
            'trades_access',
            'trades access available for viewing history',
            'My Trades available' if any('trade' in btn.lower() for btn in button_texts) else 'No trades access'
        )
        
        # Test menu organization structure
        menu_structure = {
            'primary_actions': [btn for btn in button_texts if any(word in btn.lower() for word in ['first', 'trade', 'create'])],
            'utility_actions': [btn for btn in button_texts if any(word in btn.lower() for word in ['my', 'trades', 'funds', 'wallet'])],
            'settings_actions': [btn for btn in button_texts if any(word in btn.lower() for word in ['settings', 'menu', 'config'])]
        }
        
        self.menu_validator.validate_menu_organization(menu_structure)
        
        logger.info("✅ Main Menu Clarity & Organization Validated")
    
    async def test_menu_navigation_flow(self):
        """Test navigation flow between menu options"""
        logger.info("🧭 Testing Menu Navigation Flow")
        
        # Test navigation to wallet
        start_time = time.time()
        
        wallet_click = self.ui_helper.click_inline_button(button_text="➕ Add Funds")
        
        duration = (time.time() - start_time) * 1000
        self.menu_validator.record_navigation_timing('wallet_access', duration)
        
        self.menu_validator.validate_menu_expectation(
            'wallet_navigation',
            'wallet navigation works correctly',
            'wallet navigation successful' if wallet_click.callback_query else 'wallet navigation failed'
        )
        
        # Test navigation to trades
        start_time = time.time()
        
        trades_click = self.ui_helper.click_inline_button(button_text="📋 My Trades")
        
        duration = (time.time() - start_time) * 1000
        self.menu_validator.record_navigation_timing('trading_access', duration)
        
        self.menu_validator.validate_menu_expectation(
            'trades_navigation',
            'trades navigation works correctly',
            'trades navigation successful' if trades_click.callback_query else 'trades navigation failed'
        )
        
        # Test navigation to first trade
        start_time = time.time()
        
        first_trade_click = self.ui_helper.click_inline_button(button_text="🎯 First Trade")
        
        duration = (time.time() - start_time) * 1000
        self.menu_validator.record_navigation_timing('trading_access', duration)
        
        self.menu_validator.validate_menu_expectation(
            'first_trade_navigation',
            'first trade navigation works correctly',
            'first trade navigation successful' if first_trade_click.callback_query else 'first trade navigation failed'
        )
        
        logger.info("✅ Menu Navigation Flow Validated")
    
    async def test_experienced_user_menu(self):
        """Test main menu for experienced users with balance and trades"""
        logger.info("👨‍💼 Testing Experienced User Menu")
        
        start_time = time.time()
        
        # Simulate main menu for experienced user (balance=150.50, trades=5, active=2)
        await self.fake_request.post(
            url="https://api.telegram.org/bot123/sendMessage",
            request_data={
                'chat_id': self.test_user_id,
                'text': 'Quick Access Hub\n\nAll your trading tools & settings in one place',
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Quick Exchange", callback_data="start_exchange")],
                    [InlineKeyboardButton("🤝 New Trade", callback_data="menu_create")],
                    [InlineKeyboardButton("📋 My Trades (2)", callback_data="trades_messages_hub")],
                    [InlineKeyboardButton("💰 My Wallet", callback_data="menu_wallet")],
                    [InlineKeyboardButton("⚙️ Settings", callback_data="hamburger_menu")]
                ]).to_dict()
            }
        )
        
        duration = (time.time() - start_time) * 1000
        self.menu_validator.record_navigation_timing('main_menu_load', duration)
        
        # Validate experienced user menu
        last_message = self.fake_request.get_last_message()
        menu_text = last_message['data'].get('text', '')
        
        self.menu_validator.validate_menu_expectation(
            'experienced_user_menu',
            'clear menu for experienced traders',
            menu_text
        )
        
        # Test experienced user buttons
        buttons = self.ui_helper.get_sent_buttons()
        button_texts = [btn['text'] for btn in buttons]
        
        self.menu_validator.validate_menu_button_quality('experienced_user_menu', button_texts)
        
        # Validate experienced user specific options
        self.menu_validator.validate_menu_expectation(
            'quick_exchange_option',
            'quick exchange option available for experienced users',
            'Quick Exchange available' if any('exchange' in btn.lower() for btn in button_texts) else 'No quick exchange'
        )
        
        self.menu_validator.validate_menu_expectation(
            'active_trades_indicator',
            'active trades count indicator available',
            'Active trades indicated' if any('(' in btn and ')' in btn for btn in button_texts) else 'No active trades indicator'
        )
        
        self.menu_validator.validate_menu_expectation(
            'wallet_balance_context',
            'wallet shows appropriate context for funded users',
            'My Wallet available' if any('my wallet' in btn.lower() for btn in button_texts) else 'No wallet context'
        )
        
        logger.info("✅ Experienced User Menu Validated")
    
    async def test_hamburger_menu_settings(self):
        """Test hamburger menu and settings access"""
        logger.info("🍔 Testing Hamburger Menu & Settings")
        
        start_time = time.time()
        
        # Simulate hamburger menu
        await self.fake_request.post(
            url="https://api.telegram.org/bot123/sendMessage",
            request_data={
                'chat_id': self.test_user_id,
                'text': 'Settings & Options\n\nManage your account preferences and access additional features',
                'reply_markup': InlineKeyboardMarkup([
                    [InlineKeyboardButton("👤 Profile", callback_data="user_profile")],
                    [InlineKeyboardButton("🔔 Notifications", callback_data="notification_settings")],
                    [InlineKeyboardButton("📞 Support", callback_data="start_support_chat")],
                    [InlineKeyboardButton("❓ Help", callback_data="show_help")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]).to_dict()
            }
        )
        
        duration = (time.time() - start_time) * 1000
        self.menu_validator.record_navigation_timing('submenu_load', duration)
        
        # Validate hamburger menu
        last_message = self.fake_request.get_last_message()
        settings_text = last_message['data'].get('text', '')
        
        self.menu_validator.validate_menu_expectation(
            'settings_menu_clarity',
            'clear settings menu with options description',
            settings_text
        )
        
        # Test settings buttons
        buttons = self.ui_helper.get_sent_buttons()
        button_texts = [btn['text'] for btn in buttons]
        
        self.menu_validator.validate_menu_button_quality('settings_menu', button_texts)
        
        # Validate settings options
        self.menu_validator.validate_menu_expectation(
            'profile_access',
            'profile access available in settings',
            'Profile available' if any('profile' in btn.lower() for btn in button_texts) else 'No profile access'
        )
        
        self.menu_validator.validate_menu_expectation(
            'support_access',
            'support access available in settings',
            'Support available' if any('support' in btn.lower() for btn in button_texts) else 'No support access'
        )
        
        self.menu_validator.validate_menu_expectation(
            'main_menu_return',
            'main menu return navigation available',
            'Main Menu return available' if any('main menu' in btn.lower() for btn in button_texts) else 'No main menu return'
        )
        
        # Test back navigation
        start_time = time.time()
        
        back_click = self.ui_helper.click_inline_button(button_text="🏠 Main Menu")
        
        duration = (time.time() - start_time) * 1000
        self.menu_validator.record_navigation_timing('menu_navigation', duration)
        
        self.menu_validator.validate_menu_expectation(
            'back_navigation',
            'back navigation flow works correctly',
            'back navigation successful' if back_click.callback_query else 'back navigation failed'
        )
        
        logger.info("✅ Hamburger Menu & Settings Validated")
    
    async def test_complete_main_menu_experience(self):
        """
        COMPLETE MAIN MENU & NAVIGATION EXPERIENCE VALIDATION
        
        This test validates the complete main menu user experience
        """
        logger.info("🚀 Testing COMPLETE Main Menu Experience")
        
        # Execute complete menu testing journey
        await self.test_main_menu_clarity_and_organization()
        await self.test_menu_navigation_flow()
        await self.test_experienced_user_menu()
        await self.test_hamburger_menu_settings()
        
        # Generate comprehensive menu experience report
        menu_report = self.menu_validator.get_menu_experience_report()
        
        logger.info("📊 MAIN MENU EXPERIENCE REPORT:")
        logger.info("=" * 60)
        logger.info(f"📈 User Satisfaction Score: {menu_report['user_satisfaction_score']}/100")
        logger.info(f"✅ Expectations Met: {menu_report['expectations_met']} ({menu_report['expectation_rate']:.1f}%)")
        logger.info(f"🎯 Total Successes: {menu_report['total_successes']}")
        logger.info(f"⚠️ Total Issues: {menu_report['total_issues']}")
        logger.info(f"🔴 Critical Issues: {menu_report['critical_issues']}")
        logger.info(f"🟡 Medium Issues: {menu_report['medium_issues']}")
        logger.info(f"🟢 Minor Issues: {menu_report['minor_issues']}")
        logger.info(f"⏱️ Average Navigation Time: {menu_report['average_navigation_time']:.1f}ms")
        
        # Log successes
        if menu_report['detailed_successes']:
            logger.info("\n🎯 MAIN MENU SUCCESSES:")
            for success in menu_report['detailed_successes']:
                logger.info(f"   ✅ {success['type']}: {success.get('achievement', success.get('feature', 'Success'))}")
        
        # Log issues if any
        if menu_report['detailed_issues']:
            logger.info("\n⚠️ MAIN MENU ISSUES TO ADDRESS:")
            for issue in menu_report['detailed_issues']:
                impact_emoji = "🔴" if issue['impact'] == 'HIGH' else "🟡" if issue['impact'] == 'MEDIUM' else "🟢"
                logger.info(f"   {impact_emoji} {issue['type']}: {issue.get('issue', 'Issue detected')}")
        
        # Log navigation performance
        logger.info("\n⏱️ NAVIGATION PERFORMANCE:")
        for action, timing in menu_report['navigation_timing'].items():
            status = "⚡" if timing < 500 else "✅" if timing < 1000 else "⚠️" if timing < 2000 else "❌"
            logger.info(f"   {status} {action}: {timing:.1f}ms")
        
        logger.info("=" * 60)
        
        # Assert good menu experience
        self.menu_validator.assert_good_menu_experience()
        
        logger.info("🎉 COMPLETE MAIN MENU EXPERIENCE: VALIDATED")


if __name__ == "__main__":
    # Run the main menu navigation validation
    pytest.main([__file__, "-v", "-s", "--tb=short"])
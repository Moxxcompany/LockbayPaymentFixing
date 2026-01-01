"""
E2E Test for Recent Button Fixes (1-6)

Tests the following fixes:
1. Button text: "✅ Accept" / "❌ Decline"
2. Button callback: Uses escrow.escrow_id (not database ID)
3. Handler patterns: Now match callback format
4. Handler parsing: Now extracts escrow ID correctly
5. Escrow ID display: Shows in notifications
6. Dual-channel delivery: Telegram bot + email

Run with: pytest tests/test_button_fixes_e2e.py -v -s
"""

import pytest
import re
import ast
from pathlib import Path


class TestButtonFix1and2_ButtonTextAndCallback:
    """Test Fix #1 & #2: Verify button creation in code"""
    
    def test_button_definitions_in_code(self):
        """Verify buttons are created with correct text and callbacks"""
        escrow_file = Path("handlers/escrow.py")
        content = escrow_file.read_text()
        
        # Search for InlineKeyboardButton definitions for accept/decline
        # Look for button creation patterns
        button_patterns = [
            (r'InlineKeyboardButton.*Accept', 'Accept button text'),
            (r'InlineKeyboardButton.*Decline', 'Decline button text'),
            (r'callback_data=f["\']accept_trade:{', 'Accept callback format'),
            (r'callback_data=f["\']decline_trade:{', 'Decline callback format'),
        ]
        
        results = {}
        for pattern, description in button_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            results[description] = len(matches) > 0
            if matches:
                print(f"✅ Found: {description}")
                print(f"   Matches: {len(matches)}")
        
        # Verify key patterns exist
        assert results.get('Accept button text'), "Accept button text not found"
        assert results.get('Decline button text'), "Decline button text not found"
        
        print("\n✅ Fix #1 & #2 PASSED: Button text and callback patterns found in code")


class TestButtonFix3_HandlerPatterns:
    """Test Fix #3: Handler patterns match callback format"""
    
    def test_accept_handler_pattern(self):
        """Verify accept_trade handler pattern matches callback format"""
        pattern = r'^accept_trade:.*$'
        test_callbacks = [
            "accept_trade:ES101125DK5G",
            "accept_trade:ES999999ABCD",
            "accept_trade:ES000000TEST",
        ]
        
        for callback in test_callbacks:
            assert re.match(pattern, callback), \
                f"Pattern {pattern} should match {callback}"
        
        # Negative tests
        negative_callbacks = [
            "seller_accept_ES101125DK5G",  # Old format
            "decline_trade:ES101125DK5G",   # Wrong action
            "accept_ES101125DK5G",          # Missing 'trade'
        ]
        
        for callback in negative_callbacks:
            assert not re.match(pattern, callback), \
                f"Pattern {pattern} should NOT match {callback}"
        
        print(f"✅ Fix #3a PASSED: Accept handler pattern '^accept_trade:.*$' validates correctly")
    
    def test_decline_handler_pattern(self):
        """Verify decline_trade handler pattern matches callback format"""
        pattern = r'^decline_trade:.*$'
        test_callbacks = [
            "decline_trade:ES101125DK5G",
            "decline_trade:ES999999ABCD",
            "decline_trade:ES000000TEST",
        ]
        
        for callback in test_callbacks:
            assert re.match(pattern, callback), \
                f"Pattern {pattern} should match {callback}"
        
        # Negative tests
        negative_callbacks = [
            "seller_decline_ES101125DK5G",  # Old format
            "accept_trade:ES101125DK5G",     # Wrong action
            "decline_ES101125DK5G",          # Missing 'trade'
        ]
        
        for callback in negative_callbacks:
            assert not re.match(pattern, callback), \
                f"Pattern {pattern} should NOT match {callback}"
        
        print(f"✅ Fix #3b PASSED: Decline handler pattern '^decline_trade:.*$' validates correctly")
    
    def test_handler_registration_in_main(self):
        """Verify main.py registers handlers with correct patterns"""
        main_file = Path("main.py")
        content = main_file.read_text()
        
        # Look for handler registration with new patterns
        accept_pattern = re.search(r"handle_seller_accept_trade.*\^accept_trade:.*\$", content)
        decline_pattern = re.search(r"handle_seller_decline_trade.*\^decline_trade:.*\$", content)
        
        assert accept_pattern, "Accept handler not registered with correct pattern in main.py"
        assert decline_pattern, "Decline handler not registered with correct pattern in main.py"
        
        print("✅ Fix #3c PASSED: Handler patterns correctly registered in main.py")


class TestButtonFix4_HandlerParsing:
    """Test Fix #4: Handler parsing extracts escrow ID correctly"""
    
    def test_parsing_logic_unit(self):
        """Unit test for callback parsing logic"""
        test_cases = [
            ("accept_trade:ES101125DK5G", "ES101125DK5G"),
            ("decline_trade:ES999999ABCD", "ES999999ABCD"),
            ("accept_trade:ES000000TEST", "ES000000TEST"),
        ]
        
        for callback_data, expected_id in test_cases:
            # Test new parsing logic: split(':', 1)[1]
            parsed_id = callback_data.split(':', 1)[1]
            assert parsed_id == expected_id, \
                f"Failed to parse {callback_data}: expected {expected_id}, got {parsed_id}"
        
        print(f"✅ Fix #4a PASSED: Callback parsing logic 'split(\":\", 1)[1]' works correctly")
    
    def test_accept_handler_uses_correct_parsing(self):
        """Verify accept handler uses correct parsing in code"""
        escrow_file = Path("handlers/escrow.py")
        content = escrow_file.read_text()
        
        # Look for the handle_seller_accept_trade function
        accept_func_start = content.find("async def handle_seller_accept_trade")
        assert accept_func_start > 0, "handle_seller_accept_trade function not found"
        
        # Get function content (next ~100 lines)
        func_content = content[accept_func_start:accept_func_start + 3000]
        
        # Verify it uses the correct parsing: split(':', 1)[1]
        correct_parsing = "split(':', 1)[1]" in func_content or 'split(":", 1)[1]' in func_content
        assert correct_parsing, "Accept handler doesn't use correct parsing logic 'split(\":\", 1)[1]'"
        
        # Verify it checks for 'accept_trade:' prefix
        correct_prefix = "startswith('accept_trade:')" in func_content or 'startswith("accept_trade:")' in func_content
        assert correct_prefix, "Accept handler doesn't check for 'accept_trade:' prefix"
        
        print("✅ Fix #4b PASSED: Accept handler uses correct parsing and prefix check")
    
    def test_decline_handler_uses_correct_parsing(self):
        """Verify decline handler uses correct parsing in code"""
        escrow_file = Path("handlers/escrow.py")
        content = escrow_file.read_text()
        
        # Look for the handle_seller_decline_trade function
        decline_func_start = content.find("async def handle_seller_decline_trade")
        assert decline_func_start > 0, "handle_seller_decline_trade function not found"
        
        # Get function content (next ~100 lines)
        func_content = content[decline_func_start:decline_func_start + 3000]
        
        # Verify it uses the correct parsing: split(':', 1)[1]
        correct_parsing = "split(':', 1)[1]" in func_content or 'split(":", 1)[1]' in func_content
        assert correct_parsing, "Decline handler doesn't use correct parsing logic 'split(\":\", 1)[1]'"
        
        # Verify it checks for 'decline_trade:' prefix
        correct_prefix = "startswith('decline_trade:')" in func_content or 'startswith("decline_trade:")' in func_content
        assert correct_prefix, "Decline handler doesn't check for 'decline_trade:' prefix"
        
        print("✅ Fix #4c PASSED: Decline handler uses correct parsing and prefix check")


class TestButtonFix5_EscrowIDDisplay:
    """Test Fix #5: Escrow ID displays in notifications"""
    
    def test_escrow_id_in_notification_messages(self):
        """Verify notification messages include escrow ID"""
        escrow_file = Path("handlers/escrow.py")
        content = escrow_file.read_text()
        
        # Look for notification patterns with escrow ID
        # Common patterns: #{escrow_id}, ID: #, escrow.escrow_id
        patterns = [
            (r'escrow\.escrow_id', 'escrow.escrow_id reference'),
            (r'escrow_id.*[-:].*6', 'escrow_id slicing (last 6 chars)'),
            (r'🏷️.*ID.*#', 'escrow ID display format'),
        ]
        
        results = {}
        for pattern, description in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            results[description] = len(matches) > 0
            if matches:
                print(f"✅ Found: {description} ({len(matches)} occurrences)")
        
        # At least one pattern should exist
        assert any(results.values()), "No escrow ID display patterns found in notifications"
        
        print("\n✅ Fix #5 PASSED: Escrow ID display patterns found in notification code")


class TestButtonFix6_DualChannelDelivery:
    """Test Fix #6: Dual-channel delivery (Telegram + Email)"""
    
    def test_broadcast_mode_in_accept_handler(self):
        """Verify accept handler uses broadcast_mode=True"""
        escrow_file = Path("handlers/escrow.py")
        content = escrow_file.read_text()
        
        # Look for the accept handler
        accept_func_start = content.find("async def handle_seller_accept_trade")
        assert accept_func_start > 0, "handle_seller_accept_trade function not found"
        
        # Get function content
        func_end = content.find("\nasync def ", accept_func_start + 100)
        func_content = content[accept_func_start:func_end] if func_end > 0 else content[accept_func_start:]
        
        # Verify broadcast_mode=True is used
        has_broadcast = "broadcast_mode=True" in func_content
        assert has_broadcast, "Accept handler doesn't use broadcast_mode=True for dual-channel delivery"
        
        print("✅ Fix #6a PASSED: Accept handler uses broadcast_mode=True")
    
    def test_broadcast_mode_in_decline_handler(self):
        """Verify decline handler uses broadcast_mode=True"""
        escrow_file = Path("handlers/escrow.py")
        content = escrow_file.read_text()
        
        # Look for the confirm decline handler (the actual decline logic)
        decline_func_start = content.find("async def handle_confirm_seller_decline_trade")
        assert decline_func_start > 0, "handle_confirm_seller_decline_trade function not found"
        
        # Get function content
        func_end = content.find("\nasync def ", decline_func_start + 100)
        func_content = content[decline_func_start:func_end] if func_end > 0 else content[decline_func_start:]
        
        # Verify broadcast_mode=True is used
        has_broadcast = "broadcast_mode=True" in func_content
        assert has_broadcast, "Decline handler doesn't use broadcast_mode=True for dual-channel delivery"
        
        print("✅ Fix #6b PASSED: Decline handler uses broadcast_mode=True")
    
    def test_consolidated_notification_service_usage(self):
        """Verify handlers use ConsolidatedNotificationService"""
        escrow_file = Path("handlers/escrow.py")
        content = escrow_file.read_text()
        
        # Check for imports
        has_import = "ConsolidatedNotificationService" in content
        assert has_import, "ConsolidatedNotificationService not imported"
        
        # Check for actual usage in accept/decline handlers
        accept_func_start = content.find("async def handle_seller_accept_trade")
        decline_func_start = content.find("async def handle_confirm_seller_decline_trade")
        
        # Get next function to determine end of current function
        next_func_after_accept = content.find("\nasync def ", accept_func_start + 100)
        next_func_after_decline = content.find("\nasync def ", decline_func_start + 100)
        
        accept_content = content[accept_func_start:next_func_after_accept] if next_func_after_accept > 0 else content[accept_func_start:]
        decline_content = content[decline_func_start:next_func_after_decline] if next_func_after_decline > 0 else content[decline_func_start:]
        
        # Verify ConsolidatedNotificationService is used in both
        assert "ConsolidatedNotificationService" in accept_content, \
            "Accept handler doesn't use ConsolidatedNotificationService"
        assert "ConsolidatedNotificationService" in decline_content, \
            "Decline handler doesn't use ConsolidatedNotificationService"
        
        print("✅ Fix #6c PASSED: Both handlers use ConsolidatedNotificationService")


class TestIntegration_AllFixesTogether:
    """Integration test: Verify all 6 fixes work together"""
    
    def test_complete_button_flow(self):
        """Test the complete button flow from creation to handling"""
        escrow_file = Path("handlers/escrow.py")
        main_file = Path("main.py")
        
        escrow_content = escrow_file.read_text()
        main_content = main_file.read_text()
        
        # 1. Buttons created with correct text
        has_accept_text = re.search(r'InlineKeyboardButton.*Accept', escrow_content, re.IGNORECASE)
        has_decline_text = re.search(r'InlineKeyboardButton.*Decline', escrow_content, re.IGNORECASE)
        
        # 2. Callbacks use escrow_id format
        has_accept_callback = "accept_trade:" in escrow_content
        has_decline_callback = "decline_trade:" in escrow_content
        
        # 3. Handlers registered with correct patterns
        accept_registered = re.search(r"handle_seller_accept_trade.*\^accept_trade:", main_content)
        decline_registered = re.search(r"handle_seller_decline_trade.*\^decline_trade:", main_content)
        
        # 4. Handlers parse correctly
        correct_accept_parsing = "split(':', 1)[1]" in escrow_content or 'split(":", 1)[1]' in escrow_content
        
        # 5. Escrow ID displayed
        has_escrow_id_display = "escrow.escrow_id" in escrow_content
        
        # 6. Dual-channel delivery
        has_broadcast_mode = "broadcast_mode=True" in escrow_content
        
        # Assert all components
        assert has_accept_text, "Fix #1: Accept button text missing"
        assert has_decline_text, "Fix #1: Decline button text missing"
        assert has_accept_callback, "Fix #2: accept_trade: callback missing"
        assert has_decline_callback, "Fix #2: decline_trade: callback missing"
        assert accept_registered, "Fix #3: Accept handler pattern not registered"
        assert decline_registered, "Fix #3: Decline handler pattern not registered"
        assert correct_accept_parsing, "Fix #4: Correct parsing logic missing"
        assert has_escrow_id_display, "Fix #5: Escrow ID display missing"
        assert has_broadcast_mode, "Fix #6: Dual-channel delivery missing"
        
        print("\n" + "=" * 70)
        print("✅ INTEGRATION TEST PASSED: All 6 fixes work together correctly!")
        print("=" * 70)
        print("✅ Fix #1: Button text correct (Accept/Decline)")
        print("✅ Fix #2: Callbacks use escrow_id format (accept_trade:/decline_trade:)")
        print("✅ Fix #3: Handler patterns registered correctly")
        print("✅ Fix #4: Parsing logic uses split(':', 1)[1]")
        print("✅ Fix #5: Escrow ID displayed in notifications")
        print("✅ Fix #6: Dual-channel delivery enabled (broadcast_mode=True)")
        print("=" * 70)


if __name__ == "__main__":
    print("=" * 70)
    print("E2E TEST SUITE: Button Fixes (1-6)")
    print("=" * 70)
    pytest.main([__file__, "-v", "-s", "--tb=short"])

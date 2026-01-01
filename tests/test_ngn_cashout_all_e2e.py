"""
E2E Tests for NGN "Cash Out All" Implementation
Validates all recent fixes and integrations
"""
import asyncio
import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, CallbackQuery, User as TelegramUser
from telegram.ext import ContextTypes

# Test imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.wallet_direct import (
    get_last_used_cashout_method,
    handle_quick_cashout_all,
    handle_cashout_method_choice,
    handle_quick_ngn_cashout,
    show_saved_bank_accounts
)
from models import Cashout, CashoutStatus, User as DBUser, SavedBankAccount
from database import async_managed_session

class TestNGNCashoutAllE2E:
    """Comprehensive E2E tests for NGN Cash Out All feature"""
    
    @pytest.mark.asyncio
    async def test_get_last_used_cashout_method_crypto(self):
        """TEST 1: get_last_used_cashout_method returns CRYPTO for crypto users"""
        print("\n🧪 TEST 1: Crypto user last method detection")
        
        with patch('handlers.wallet_direct.async_managed_session') as mock_session:
            # Mock user
            mock_user = Mock()
            mock_user.id = 123
            
            # Mock last cashout (crypto)
            mock_cashout = Mock()
            mock_cashout.cashout_type = "crypto"
            mock_cashout.currency = "BTC"
            
            # Setup session mock
            mock_session_instance = AsyncMock()
            mock_session.__aenter__.return_value = mock_session_instance
            mock_session.__aexit__.return_value = None
            
            # Mock execute returns
            mock_execute_1 = AsyncMock()
            mock_execute_1.scalar_one_or_none.return_value = mock_user
            
            mock_execute_2 = AsyncMock()
            mock_execute_2.scalar_one_or_none.return_value = mock_cashout
            
            mock_session_instance.execute.side_effect = [mock_execute_1, mock_execute_2]
            
            # Run test
            result = await get_last_used_cashout_method(123456)
            
            # Assertions
            assert result["method"] == "CRYPTO", "Should detect CRYPTO method"
            assert result["currency"] == "BTC", "Should return BTC currency"
            print("✅ PASSED: Crypto method detection working")
    
    @pytest.mark.asyncio
    async def test_get_last_used_cashout_method_ngn(self):
        """TEST 2: get_last_used_cashout_method returns NGN_BANK for NGN users"""
        print("\n🧪 TEST 2: NGN user last method detection")
        
        with patch('handlers.wallet_direct.async_managed_session') as mock_session:
            # Mock user
            mock_user = Mock()
            mock_user.id = 123
            
            # Mock last cashout (NGN)
            mock_cashout = Mock()
            mock_cashout.cashout_type = "ngn_bank"
            mock_cashout.bank_account_id = 456
            
            # Setup session mock
            mock_session_instance = AsyncMock()
            mock_session.__aenter__.return_value = mock_session_instance
            mock_session.__aexit__.return_value = None
            
            # Mock execute returns
            mock_execute_1 = AsyncMock()
            mock_execute_1.scalar_one_or_none.return_value = mock_user
            
            mock_execute_2 = AsyncMock()
            mock_execute_2.scalar_one_or_none.return_value = mock_cashout
            
            mock_session_instance.execute.side_effect = [mock_execute_1, mock_execute_2]
            
            # Run test
            result = await get_last_used_cashout_method(123456)
            
            # Assertions
            assert result["method"] == "NGN_BANK", "Should detect NGN_BANK method"
            assert result["bank_id"] == 456, "Should return bank_id"
            print("✅ PASSED: NGN method detection working")
    
    @pytest.mark.asyncio
    async def test_get_last_used_cashout_method_no_history(self):
        """TEST 3: get_last_used_cashout_method returns None for new users"""
        print("\n🧪 TEST 3: New user (no history) detection")
        
        with patch('handlers.wallet_direct.async_managed_session') as mock_session:
            # Mock user
            mock_user = Mock()
            mock_user.id = 123
            
            # Setup session mock
            mock_session_instance = AsyncMock()
            mock_session.__aenter__.return_value = mock_session_instance
            mock_session.__aexit__.return_value = None
            
            # Mock execute returns
            mock_execute_1 = AsyncMock()
            mock_execute_1.scalar_one_or_none.return_value = mock_user
            
            mock_execute_2 = AsyncMock()
            mock_execute_2.scalar_one_or_none.return_value = None  # No cashout history
            
            mock_session_instance.execute.side_effect = [mock_execute_1, mock_execute_2]
            
            # Run test
            result = await get_last_used_cashout_method(123456)
            
            # Assertions
            assert result["method"] is None, "Should return None for no history"
            print("✅ PASSED: No history detection working")
    
    @pytest.mark.asyncio
    async def test_quick_cashout_all_crypto_flow(self):
        """TEST 4: handle_quick_cashout_all routes to crypto for crypto users"""
        print("\n🧪 TEST 4: Quick cashout all - crypto user routing")
        
        # Mock update and context
        update = Mock(spec=Update)
        query = Mock(spec=CallbackQuery)
        query.from_user = Mock(spec=TelegramUser)
        query.from_user.id = 123456
        query.data = "quick_cashout_all:25.50"
        update.callback_query = query
        
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        
        with patch('handlers.wallet_direct.get_last_used_cashout_method') as mock_get_method:
            with patch('handlers.wallet_direct.show_crypto_address_selection') as mock_show_crypto:
                with patch('handlers.wallet_direct.safe_answer_callback_query'):
                    with patch('handlers.wallet_direct.get_network_from_currency', return_value='BTC'):
                        # Mock crypto user
                        mock_get_method.return_value = {
                            "method": "CRYPTO",
                            "currency": "BTC"
                        }
                        
                        # Run handler
                        await handle_quick_cashout_all(update, context)
                        
                        # Assertions
                        assert context.user_data["cashout_data"]["method"] == "crypto"
                        assert context.user_data["cashout_data"]["currency"] == "BTC"
                        assert mock_show_crypto.called, "Should show crypto address selection"
                        print("✅ PASSED: Crypto routing working")
    
    @pytest.mark.asyncio
    async def test_quick_cashout_all_ngn_flow(self):
        """TEST 5: handle_quick_cashout_all routes to NGN for NGN users"""
        print("\n🧪 TEST 5: Quick cashout all - NGN user routing")
        
        # Mock update and context
        update = Mock(spec=Update)
        query = Mock(spec=CallbackQuery)
        query.from_user = Mock(spec=TelegramUser)
        query.from_user.id = 123456
        query.data = "quick_cashout_all:25.50"
        update.callback_query = query
        
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        
        with patch('handlers.wallet_direct.get_last_used_cashout_method') as mock_get_method:
            with patch('handlers.wallet_direct.async_managed_session') as mock_session:
                with patch('handlers.wallet_direct.show_saved_bank_accounts') as mock_show_banks:
                    with patch('handlers.wallet_direct.safe_answer_callback_query'):
                        # Mock NGN user
                        mock_get_method.return_value = {
                            "method": "NGN_BANK",
                            "bank_id": 456
                        }
                        
                        # Mock session
                        mock_session_instance = AsyncMock()
                        mock_session.__aenter__.return_value = mock_session_instance
                        mock_session.__aexit__.return_value = None
                        
                        mock_user = Mock()
                        mock_user.id = 123
                        
                        mock_execute_1 = AsyncMock()
                        mock_execute_1.scalar_one_or_none.return_value = mock_user
                        
                        mock_execute_2 = AsyncMock()
                        mock_execute_2.scalars.return_value.all.return_value = []
                        
                        mock_session_instance.execute.side_effect = [mock_execute_1, mock_execute_2]
                        
                        # Run handler
                        await handle_quick_cashout_all(update, context)
                        
                        # Assertions
                        assert context.user_data["cashout_data"]["method"] == "ngn_bank"
                        assert mock_show_banks.called, "Should show bank accounts"
                        print("✅ PASSED: NGN routing working")
    
    @pytest.mark.asyncio
    async def test_quick_cashout_all_first_time_user(self):
        """TEST 6: handle_quick_cashout_all shows method selection for new users"""
        print("\n🧪 TEST 6: Quick cashout all - first-time user flow")
        
        # Mock update and context
        update = Mock(spec=Update)
        query = Mock(spec=CallbackQuery)
        query.from_user = Mock(spec=TelegramUser)
        query.from_user.id = 123456
        query.data = "quick_cashout_all:25.50"
        update.callback_query = query
        
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        
        with patch('handlers.wallet_direct.get_last_used_cashout_method') as mock_get_method:
            with patch('handlers.wallet_direct.show_cashout_method_selection') as mock_show_selection:
                with patch('handlers.wallet_direct.safe_answer_callback_query'):
                    # Mock new user (no history)
                    mock_get_method.return_value = {"method": None}
                    
                    # Run handler
                    await handle_quick_cashout_all(update, context)
                    
                    # Assertions
                    assert mock_show_selection.called, "Should show method selection"
                    assert context.user_data["cashout_data"]["amount"] == "25.50"
                    print("✅ PASSED: First-time user flow working")
    
    @pytest.mark.asyncio
    async def test_method_choice_crypto(self):
        """TEST 7: handle_cashout_method_choice routes crypto correctly"""
        print("\n🧪 TEST 7: Method choice - crypto selection")
        
        # Mock update and context
        update = Mock(spec=Update)
        query = Mock(spec=CallbackQuery)
        query.data = "cashout_method:crypto:25.50"
        update.callback_query = query
        
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        
        with patch('handlers.wallet_direct.show_crypto_currency_selection') as mock_show_crypto:
            with patch('handlers.wallet_direct.safe_answer_callback_query'):
                # Run handler
                await handle_cashout_method_choice(update, context)
                
                # Assertions
                assert context.user_data["cashout_data"]["method"] == "crypto"
                assert context.user_data["cashout_data"]["amount"] == "25.50"
                assert mock_show_crypto.called, "Should show crypto selection"
                print("✅ PASSED: Crypto method choice working")
    
    @pytest.mark.asyncio
    async def test_method_choice_ngn(self):
        """TEST 8: handle_cashout_method_choice routes NGN correctly"""
        print("\n🧪 TEST 8: Method choice - NGN selection")
        
        # Mock update and context
        update = Mock(spec=Update)
        query = Mock(spec=CallbackQuery)
        query.data = "cashout_method:ngn:25.50"
        update.callback_query = query
        update.effective_user = Mock(spec=TelegramUser)
        update.effective_user.id = 123456
        
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        
        with patch('handlers.wallet_direct.async_managed_session') as mock_session:
            with patch('handlers.wallet_direct.show_saved_bank_accounts') as mock_show_banks:
                with patch('handlers.wallet_direct.safe_answer_callback_query'):
                    # Mock session
                    mock_session_instance = AsyncMock()
                    mock_session.__aenter__.return_value = mock_session_instance
                    mock_session.__aexit__.return_value = None
                    
                    mock_user = Mock()
                    mock_user.id = 123
                    
                    mock_execute_1 = AsyncMock()
                    mock_execute_1.scalar_one_or_none.return_value = mock_user
                    
                    mock_execute_2 = AsyncMock()
                    mock_execute_2.scalars.return_value.all.return_value = []
                    
                    mock_session_instance.execute.side_effect = [mock_execute_1, mock_execute_2]
                    
                    # Run handler
                    await handle_cashout_method_choice(update, context)
                    
                    # Assertions
                    assert context.user_data["cashout_data"]["method"] == "ngn_bank"
                    assert context.user_data["cashout_data"]["amount"] == "25.50"
                    assert mock_show_banks.called, "Should show bank accounts"
                    print("✅ PASSED: NGN method choice working")
    
    def test_callback_registrations(self):
        """TEST 9: Verify all callback patterns are registered"""
        print("\n🧪 TEST 9: Callback pattern registrations")
        
        from handlers.wallet_direct import DIRECT_WALLET_HANDLERS
        
        # Check for required patterns
        patterns = [h['pattern'] for h in DIRECT_WALLET_HANDLERS if isinstance(h, dict)]
        
        required_patterns = [
            r'^quick_ngn$',
            r'^cashout_method:(crypto|ngn):.+$',
            r'^quick_cashout_all:.+$'
        ]
        
        for pattern in required_patterns:
            assert pattern in patterns, f"Pattern {pattern} not registered"
        
        print("✅ PASSED: All callback patterns registered")
    
    def test_handler_functions_exist(self):
        """TEST 10: Verify all handler functions exist"""
        print("\n🧪 TEST 10: Handler function existence")
        
        from handlers.wallet_direct import (
            handle_quick_ngn_cashout,
            handle_cashout_method_choice,
            handle_quick_cashout_all,
            show_cashout_method_selection,
            get_last_used_cashout_method
        )
        
        # Check functions exist and are callable
        assert callable(handle_quick_ngn_cashout), "handle_quick_ngn_cashout not callable"
        assert callable(handle_cashout_method_choice), "handle_cashout_method_choice not callable"
        assert callable(handle_quick_cashout_all), "handle_quick_cashout_all not callable"
        assert callable(show_cashout_method_selection), "show_cashout_method_selection not callable"
        assert callable(get_last_used_cashout_method), "get_last_used_cashout_method not callable"
        
        print("✅ PASSED: All handler functions exist and callable")


async def run_all_tests():
    """Run all E2E tests"""
    print("\n" + "="*80)
    print("🚀 RUNNING COMPREHENSIVE E2E TESTS - NGN CASH OUT ALL")
    print("="*80)
    
    test_suite = TestNGNCashoutAllE2E()
    
    async_tests = [
        ("Crypto Method Detection", test_suite.test_get_last_used_cashout_method_crypto()),
        ("NGN Method Detection", test_suite.test_get_last_used_cashout_method_ngn()),
        ("No History Detection", test_suite.test_get_last_used_cashout_method_no_history()),
        ("Quick Cashout - Crypto Flow", test_suite.test_quick_cashout_all_crypto_flow()),
        ("Quick Cashout - NGN Flow", test_suite.test_quick_cashout_all_ngn_flow()),
        ("Quick Cashout - First Time", test_suite.test_quick_cashout_all_first_time_user()),
        ("Method Choice - Crypto", test_suite.test_method_choice_crypto()),
        ("Method Choice - NGN", test_suite.test_method_choice_ngn())
    ]
    
    sync_tests = [
        ("Callback Registrations", test_suite.test_callback_registrations),
        ("Handler Functions", test_suite.test_handler_functions_exist)
    ]
    
    passed = 0
    failed = 0
    
    # Run async tests
    for test_name, test_coro in async_tests:
        try:
            await test_coro
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {test_name}")
            print(f"   Error: {str(e)}")
            failed += 1
    
    # Run sync tests
    for test_name, test_func in sync_tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {test_name}")
            print(f"   Error: {str(e)}")
            failed += 1
    
    print("\n" + "="*80)
    print(f"📊 TEST RESULTS: {passed} PASSED, {failed} FAILED")
    print("="*80)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - 100% SUCCESS!")
        return True
    else:
        print(f"❌ {failed} TESTS FAILED - NEEDS ATTENTION")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)

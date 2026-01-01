"""
Crypto Operations Critical Scenarios
Top 5 crypto scenarios: Kraken withdrawals with success/failure/retry/idempotency testing
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from tests.harness.test_harness import comprehensive_test_harness
from models import CashoutRequest, CashoutStatus, User, Wallet
from services.kraken_service import KrakenService


@pytest.mark.asyncio
@pytest.mark.integration
class CryptoScenarios:
    """
    Critical Scenario Matrix: Crypto Operations
    
    Scenarios covered:
    1. Successful Kraken withdrawal (BTC/ETH)
    2. Kraken API failures and retry logic
    3. Insufficient balance handling
    4. Address validation failures
    5. Withdrawal idempotency protection
    """
    
    async def test_scenario_1_successful_kraken_withdrawal(self):
        """
        Scenario 1: Complete successful Kraken withdrawal
        Flow: initiate → validate → execute → confirm → update balance
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 20001
            withdrawal_amount = Decimal("0.01")
            crypto_currency = "BTC"
            destination_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Example BTC address
            
            # Set up user with sufficient balance
            harness.kraken.set_balance("BTC", Decimal("0.05"))  # More than withdrawal amount
            
            # Step 1: User initiates withdrawal
            withdraw_update = harness.create_user_update(
                user_id=user_id,
                message_text=f"/withdraw {withdrawal_amount} {crypto_currency} {destination_address}"
            )
            context = harness.create_context()
            
            from handlers.wallet_direct import handle_withdrawal_request
            await handle_withdrawal_request(withdraw_update, context)
            
            # Verify withdrawal confirmation request
            messages = harness.telegram.get_sent_messages(user_id)
            confirm_messages = [msg for msg in messages if "confirm" in msg.get("text", "").lower()]
            assert len(confirm_messages) >= 1
            
            # Step 2: User confirms withdrawal
            confirm_callback = harness.create_callback_update(
                user_id=user_id,
                callback_data=f"withdraw_confirm_{crypto_currency}_{withdrawal_amount}_{user_id}"
            )
            
            await handle_withdrawal_request(confirm_callback, context)
            
            # Verify processing message
            processing_messages = harness.telegram.get_sent_messages(user_id)
            process_msg = [msg for msg in processing_messages if "processing" in msg.get("text", "").lower()]
            assert len(process_msg) >= 1
            
            # Step 3: Verify Kraken API call made
            kraken_history = harness.kraken.get_request_history()
            withdraw_requests = [req for req in kraken_history if req["method"] == "withdraw_crypto"]
            assert len(withdraw_requests) >= 1
            
            withdrawal_request = withdraw_requests[-1]
            assert withdrawal_request["currency"] == crypto_currency
            assert Decimal(str(withdrawal_request["amount"])) == withdrawal_amount
            assert withdrawal_request["address"] == destination_address
            
            # Step 4: Verify withdrawal record created
            kraken_withdrawals = harness.kraken.get_withdrawal_history()
            assert len(kraken_withdrawals) >= 1
            
            withdrawal = kraken_withdrawals[-1]
            assert withdrawal["currency"] == crypto_currency
            assert withdrawal["status"] == "success"
            assert "txid" in withdrawal
            
            # Step 5: Verify success notification
            success_messages = harness.telegram.get_sent_messages(user_id)
            success_msg = [msg for msg in success_messages if "successful" in msg.get("text", "").lower() or "completed" in msg.get("text", "").lower()]
            assert len(success_msg) >= 1
            
            # Step 6: Verify balance updated
            final_balance = harness.kraken.balances[crypto_currency]
            expected_balance = Decimal("0.05") - withdrawal_amount
            assert final_balance == expected_balance
    
    async def test_scenario_2_kraken_api_failures_retry(self):
        """
        Scenario 2: Kraken API failures and intelligent retry logic
        Flow: initiate → API fails → retry → eventual success/failure
        """
        
        # Start with network failures, then recover
        with comprehensive_test_harness(scenario="network_failures") as harness:
            user_id = 20002
            withdrawal_amount = Decimal("0.005")
            crypto_currency = "ETH"
            destination_address = "0x742d35Cc6634C0532925a3b8D7C28De27C52F5b6"
            
            harness.kraken.set_balance("ETH", Decimal("1.0"))
            
            # Attempt withdrawal during network issues
            withdraw_update = harness.create_user_update(
                user_id=user_id,
                message_text=f"/withdraw {withdrawal_amount} {crypto_currency} {destination_address}"
            )
            context = harness.create_context()
            
            from handlers.wallet_direct import handle_withdrawal_request
            await handle_withdrawal_request(withdraw_update, context)
            
            # User confirms
            confirm_callback = harness.create_callback_update(
                user_id=user_id,
                callback_data=f"withdraw_confirm_{crypto_currency}_{withdrawal_amount}_{user_id}"
            )
            
            await handle_withdrawal_request(confirm_callback, context)
            
            # Should get error message due to API failure
            error_messages = harness.telegram.get_sent_messages(user_id)
            error_msg = [msg for msg in error_messages if "error" in msg.get("text", "").lower() or "try again" in msg.get("text", "").lower()]
            assert len(error_msg) >= 1
            
            # Verify no withdrawal executed due to failure
            kraken_withdrawals = harness.kraken.get_withdrawal_history()
            assert len(kraken_withdrawals) == 0
        
        # Recover network and retry
        with comprehensive_test_harness(scenario="success") as harness:
            harness.kraken.set_balance("ETH", Decimal("1.0"))
            
            # Retry withdrawal
            retry_update = harness.create_user_update(
                user_id=user_id,
                message_text=f"/withdraw {withdrawal_amount} {crypto_currency} {destination_address}"
            )
            retry_context = harness.create_context()
            
            await handle_withdrawal_request(retry_update, retry_context)
            
            # Confirm again
            retry_confirm = harness.create_callback_update(
                user_id=user_id,
                callback_data=f"withdraw_confirm_{crypto_currency}_{withdrawal_amount}_{user_id}"
            )
            
            await handle_withdrawal_request(retry_confirm, retry_context)
            
            # Should succeed now
            success_messages = harness.telegram.get_sent_messages(user_id)
            success_msg = [msg for msg in success_messages if "successful" in msg.get("text", "").lower()]
            assert len(success_msg) >= 1
    
    async def test_scenario_3_insufficient_balance_handling(self):
        """
        Scenario 3: Insufficient balance error handling
        Flow: initiate large withdrawal → balance check → error → suggestion
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 20003
            withdrawal_amount = Decimal("10.0")  # Large amount
            crypto_currency = "BTC"
            destination_address = "3FUpjcWpM15FqfMosgGMxk7Z9B7SZHvVoT"
            
            # Set insufficient balance
            harness.kraken.set_balance("BTC", Decimal("0.001"))  # Much less than requested
            
            withdraw_update = harness.create_user_update(
                user_id=user_id,
                message_text=f"/withdraw {withdrawal_amount} {crypto_currency} {destination_address}"
            )
            context = harness.create_context()
            
            from handlers.wallet_direct import handle_withdrawal_request
            await handle_withdrawal_request(withdraw_update, context)
            
            # Should get insufficient balance error
            messages = harness.telegram.get_sent_messages(user_id)
            balance_error = [msg for msg in messages if "insufficient" in msg.get("text", "").lower() or "balance" in msg.get("text", "").lower()]
            assert len(balance_error) >= 1
            
            # Should show available balance
            balance_msg = balance_error[-1]
            assert "0.001" in balance_msg["text"]  # Current balance shown
            
            # Verify no Kraken API call made for insufficient balance
            kraken_history = harness.kraken.get_request_history()
            withdraw_requests = [req for req in kraken_history if req["method"] == "withdraw_crypto"]
            assert len(withdraw_requests) == 0
    
    async def test_scenario_4_address_validation_failures(self):
        """
        Scenario 4: Address validation failures and corrections
        Flow: invalid address → validation error → corrected address → success
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 20004
            withdrawal_amount = Decimal("0.01")
            crypto_currency = "BTC"
            
            harness.kraken.set_balance("BTC", Decimal("1.0"))
            
            invalid_addresses = [
                "invalid_address",
                "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfN",  # Too short
                "2A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", # Invalid checksum
                "",  # Empty
                "0x742d35Cc6634C0532925a3b8D7C28De27C52F5b6"  # ETH address for BTC
            ]
            
            for invalid_address in invalid_addresses:
                withdraw_update = harness.create_user_update(
                    user_id=user_id,
                    message_text=f"/withdraw {withdrawal_amount} {crypto_currency} {invalid_address}"
                )
                context = harness.create_context()
                
                from handlers.wallet_direct import handle_withdrawal_request
                await handle_withdrawal_request(withdraw_update, context)
                
                # Should get validation error
                messages = harness.telegram.get_sent_messages(user_id)
                validation_errors = [msg for msg in messages if "invalid" in msg.get("text", "").lower() or "address" in msg.get("text", "").lower()]
                assert len(validation_errors) >= 1, f"No validation error for address: {invalid_address}"
                
                # Clear messages for next iteration
                harness.telegram.clear_history()
            
            # Finally try valid address
            valid_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
            valid_update = harness.create_user_update(
                user_id=user_id,
                message_text=f"/withdraw {withdrawal_amount} {crypto_currency} {valid_address}"
            )
            
            await handle_withdrawal_request(valid_update, context)
            
            # Should proceed to confirmation
            final_messages = harness.telegram.get_sent_messages(user_id)
            confirm_msg = [msg for msg in final_messages if "confirm" in msg.get("text", "").lower()]
            assert len(confirm_msg) >= 1
    
    async def test_scenario_5_withdrawal_idempotency_protection(self):
        """
        Scenario 5: Withdrawal idempotency protection
        Flow: confirm withdrawal → duplicate confirmation → prevent double spend
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 20005
            withdrawal_amount = Decimal("0.1")
            crypto_currency = "ETH"
            destination_address = "0x742d35Cc6634C0532925a3b8D7C28De27C52F5b6"
            
            harness.kraken.set_balance("ETH", Decimal("1.0"))
            
            # Start withdrawal process
            withdraw_update = harness.create_user_update(
                user_id=user_id,
                message_text=f"/withdraw {withdrawal_amount} {crypto_currency} {destination_address}"
            )
            context = harness.create_context()
            
            from handlers.wallet_direct import handle_withdrawal_request
            await handle_withdrawal_request(withdraw_update, context)
            
            # Get confirmation callback data
            callback_data = f"withdraw_confirm_{crypto_currency}_{withdrawal_amount}_{user_id}"
            
            # Create multiple simultaneous confirmations (simulate rapid clicking)
            concurrent_confirmations = []
            for i in range(5):
                confirm_callback = harness.create_callback_update(
                    user_id=user_id,
                    callback_data=callback_data
                )
                context_copy = harness.create_context()
                
                task = asyncio.create_task(handle_withdrawal_request(confirm_callback, context_copy))
                concurrent_confirmations.append(task)
            
            # Execute all confirmations concurrently
            results = await asyncio.gather(*concurrent_confirmations, return_exceptions=True)
            
            # Verify no exceptions
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 0, f"Concurrent confirmations failed: {exceptions}"
            
            # Verify only ONE withdrawal was executed despite multiple confirmations
            kraken_withdrawals = harness.kraken.get_withdrawal_history()
            assert len(kraken_withdrawals) == 1, f"Expected 1 withdrawal, got {len(kraken_withdrawals)}"
            
            # Verify correct balance deduction (only once)
            final_balance = harness.kraken.balances["ETH"]
            expected_balance = Decimal("1.0") - withdrawal_amount
            assert final_balance == expected_balance
            
            # Verify user got appropriate messages (success + idempotency warnings)
            messages = harness.telegram.get_sent_messages(user_id)
            success_msgs = [msg for msg in messages if "successful" in msg.get("text", "").lower()]
            duplicate_msgs = [msg for msg in messages if "already" in msg.get("text", "").lower() or "duplicate" in msg.get("text", "").lower()]
            
            # Should have 1 success and potentially some duplicate warnings
            assert len(success_msgs) >= 1
            
            # Test additional attempt after completion
            final_attempt = harness.create_callback_update(
                user_id=user_id,
                callback_data=callback_data
            )
            
            await handle_withdrawal_request(final_attempt, harness.create_context())
            
            # Should get "already processed" message
            final_messages = harness.telegram.get_sent_messages(user_id)
            already_processed = [msg for msg in final_messages if "already" in msg.get("text", "").lower()]
            assert len(already_processed) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
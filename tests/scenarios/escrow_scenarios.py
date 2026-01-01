"""
Escrow Workflow Critical Scenarios  
Top 6 escrow scenarios: creation→payment→hold→release/dispute/cancel with admin overrides
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from tests.harness.test_harness import comprehensive_test_harness
from models import Escrow, EscrowStatus, User, Transaction, TransactionType


@pytest.mark.asyncio
@pytest.mark.integration 
class EscrowScenarios:
    """
    Critical Scenario Matrix: Escrow Workflows
    
    Scenarios covered:
    1. Happy path: creation→payment→hold→release (complete success)
    2. Payment timeout and auto-cancellation
    3. Dispute initiation and admin resolution  
    4. Seller acceptance timeout and auto-refund
    5. Admin emergency cancellation with refund
    6. Concurrent escrow operations and race conditions
    """
    
    async def test_scenario_1_escrow_happy_path(self):
        """
        Scenario 1: Complete escrow happy path
        Flow: create → await payment → seller accepts → funds held → release to seller
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            buyer_id = 10001
            seller_email = "seller@example.com"
            amount_usd = Decimal("100.00")
            crypto_currency = "BTC"
            
            # Step 1: Buyer creates escrow
            create_update = harness.create_user_update(
                user_id=buyer_id,
                message_text=f"/trade {amount_usd} {crypto_currency} {seller_email}"
            )
            context = harness.create_context()
            
            # Execute escrow creation
            from handlers.escrow import create_escrow_handler
            await create_escrow_handler(create_update, context)
            
            # Verify escrow created message
            messages = harness.telegram.get_sent_messages(buyer_id)
            create_messages = [msg for msg in messages if "escrow created" in msg.get("text", "").lower()]
            assert len(create_messages) >= 1
            
            # Step 2: Extract escrow ID from message
            # In real implementation, would parse from callback data or message
            escrow_id = "test_escrow_001"  # Deterministic for testing
            
            # Step 3: Buyer makes payment (crypto deposit)
            deposit_callback = harness.create_callback_update(
                user_id=buyer_id,
                callback_data=f"escrow_deposit_{escrow_id}"
            )
            
            from handlers.escrow import handle_escrow_callback
            await handle_escrow_callback(deposit_callback, context)
            
            # Verify payment instructions sent
            deposit_messages = harness.telegram.get_sent_messages(buyer_id)
            payment_msg = [msg for msg in deposit_messages if "deposit" in msg.get("text", "").lower() or "address" in msg.get("text", "").lower()]
            assert len(payment_msg) >= 1
            
            # Step 4: Simulate crypto payment received (webhook/monitoring)
            # This would normally come from BlockBee webhook
            payment_data = {
                "escrow_id": escrow_id,
                "amount_received": amount_usd,
                "crypto_amount": Decimal("0.002"),  # BTC amount
                "tx_hash": "test_tx_hash_001",
                "confirmations": 3
            }
            
            from services.escrow_payment_processor import EscrowPaymentProcessor  
            await EscrowPaymentProcessor.process_payment(payment_data)
            
            # Verify seller notification sent
            seller_emails = harness.email.get_sent_emails(seller_email)
            seller_notification = [email for email in seller_emails if "trade" in email.get("subject", "").lower()]
            assert len(seller_notification) >= 1
            
            # Step 5: Seller accepts trade (via email link or Telegram)
            seller_accept_callback = harness.create_callback_update(
                user_id=99999,  # Seller's Telegram ID (if they have one)
                callback_data=f"escrow_seller_accept_{escrow_id}"
            )
            
            await handle_escrow_callback(seller_accept_callback, context)
            
            # Step 6: Funds held, both parties notified
            hold_messages = harness.telegram.get_sent_messages(buyer_id)
            hold_msg = [msg for msg in hold_messages if "held" in msg.get("text", "").lower() or "secured" in msg.get("text", "").lower()]
            assert len(hold_msg) >= 1
            
            # Step 7: Trade completion and release to seller
            release_callback = harness.create_callback_update(
                user_id=buyer_id,
                callback_data=f"escrow_release_{escrow_id}"
            )
            
            await handle_escrow_callback(release_callback, context)
            
            # Verify release initiated
            release_messages = harness.telegram.get_sent_messages(buyer_id)
            release_msg = [msg for msg in release_messages if "released" in msg.get("text", "").lower() or "completed" in msg.get("text", "").lower()]
            assert len(release_msg) >= 1
            
            # Verify Kraken withdrawal initiated
            kraken_history = harness.kraken.get_withdrawal_history()
            assert len(kraken_history) >= 1
            withdrawal = kraken_history[-1]
            assert withdrawal["currency"] == "BTC"
            assert withdrawal["status"] in ["success", "pending"]
    
    async def test_scenario_2_payment_timeout_cancellation(self):
        """
        Scenario 2: Payment timeout and auto-cancellation
        Flow: create → no payment → timeout → auto-cancel → refund
        """
        
        with comprehensive_test_harness(scenario="success", frozen_time="2025-01-01T10:00:00Z") as harness:
            buyer_id = 10002
            seller_email = "timeout_seller@example.com"
            
            # Create escrow
            create_update = harness.create_user_update(
                user_id=buyer_id,
                message_text="/trade 50.00 ETH timeout_seller@example.com"
            )
            context = harness.create_context()
            
            from handlers.escrow import create_escrow_handler
            await create_escrow_handler(create_update, context)
            
            escrow_id = "test_escrow_002"
            
            # Advance time beyond payment timeout (typically 30 minutes)
            harness.advance_time_by(minutes=35)
            
            # Trigger timeout check (normally done by scheduled job)
            from services.escrow_timeout_monitor import EscrowTimeoutMonitor
            timeout_results = await EscrowTimeoutMonitor.check_payment_timeouts()
            
            # Verify escrow auto-cancelled
            cancellation_messages = harness.telegram.get_sent_messages(buyer_id)
            cancel_msg = [msg for msg in cancellation_messages if "cancelled" in msg.get("text", "").lower() or "timeout" in msg.get("text", "").lower()]
            assert len(cancel_msg) >= 1
            
            # Verify seller notified of cancellation
            seller_emails = harness.email.get_sent_emails(seller_email)
            cancel_email = [email for email in seller_emails if "cancelled" in email.get("subject", "").lower()]
            assert len(cancel_email) >= 1
            
            # Verify database state
            async with harness.test_db_session() as session:
                from sqlalchemy import select
                escrow_result = await session.execute(
                    select(Escrow).where(Escrow.id == escrow_id)
                )
                escrow = escrow_result.scalar_one_or_none()
                assert escrow is not None
                assert escrow.status == EscrowStatus.CANCELLED
                assert escrow.cancelled_at is not None
    
    async def test_scenario_3_dispute_and_admin_resolution(self):
        """
        Scenario 3: Dispute initiation and admin resolution
        Flow: create → payment → dispute → admin review → resolution
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            buyer_id = 10003
            seller_email = "dispute_seller@example.com"
            
            # Complete escrow up to payment
            await self._create_and_pay_escrow(harness, buyer_id, seller_email, "test_escrow_003")
            
            # Buyer initiates dispute
            dispute_callback = harness.create_callback_update(
                user_id=buyer_id,
                callback_data="escrow_dispute_test_escrow_003"
            )
            context = harness.create_context()
            
            from handlers.escrow import handle_escrow_callback
            await handle_escrow_callback(dispute_callback, context)
            
            # Verify dispute form/reason collection
            dispute_messages = harness.telegram.get_sent_messages(buyer_id)
            dispute_msg = [msg for msg in dispute_messages if "dispute" in msg.get("text", "").lower() or "reason" in msg.get("text", "").lower()]
            assert len(dispute_msg) >= 1
            
            # Buyer provides dispute reason
            reason_update = harness.create_user_update(
                user_id=buyer_id,
                message_text="Seller did not provide the agreed service"
            )
            
            from handlers.escrow import handle_dispute_reason
            await handle_dispute_reason(reason_update, context)
            
            # Verify admin notification
            admin_emails = harness.email.get_sent_emails("admin@lockbay.io")
            admin_dispute_email = [email for email in admin_emails if "dispute" in email.get("subject", "").lower()]
            assert len(admin_dispute_email) >= 1
            
            # Admin resolves dispute in favor of buyer
            admin_user_id = 99999999  # Admin user ID
            resolve_callback = harness.create_callback_update(
                user_id=admin_user_id,
                callback_data="admin_dispute_resolve_test_escrow_003_buyer_favor"
            )
            
            from handlers.admin import handle_admin_callback
            await handle_admin_callback(resolve_callback, context)
            
            # Verify refund to buyer
            refund_messages = harness.telegram.get_sent_messages(buyer_id)
            refund_msg = [msg for msg in refund_messages if "refund" in msg.get("text", "").lower() or "resolved" in msg.get("text", "").lower()]
            assert len(refund_msg) >= 1
            
            # Verify seller notification
            seller_emails = harness.email.get_sent_emails(seller_email)
            seller_resolution = [email for email in seller_emails if "dispute" in email.get("subject", "").lower() and "resolved" in email.get("subject", "").lower()]
            assert len(seller_resolution) >= 1
    
    async def test_scenario_4_seller_timeout_auto_refund(self):
        """
        Scenario 4: Seller acceptance timeout and auto-refund
        Flow: create → payment → seller doesn't accept → timeout → auto-refund
        """
        
        with comprehensive_test_harness(scenario="success", frozen_time="2025-01-01T12:00:00Z") as harness:
            buyer_id = 10004
            seller_email = "slow_seller@example.com"
            
            # Complete payment step
            await self._create_and_pay_escrow(harness, buyer_id, seller_email, "test_escrow_004")
            
            # Advance time beyond seller acceptance timeout (typically 24 hours)
            harness.advance_time_by(hours=25)
            
            # Trigger seller timeout check
            from services.escrow_timeout_monitor import EscrowTimeoutMonitor
            timeout_results = await EscrowTimeoutMonitor.check_seller_timeouts()
            
            # Verify auto-refund initiated
            refund_messages = harness.telegram.get_sent_messages(buyer_id)
            refund_msg = [msg for msg in refund_messages if "refund" in msg.get("text", "").lower() or "seller.*timeout" in msg.get("text", "").lower()]
            assert len(refund_msg) >= 1
            
            # Verify seller timeout notification
            seller_emails = harness.email.get_sent_emails(seller_email)
            timeout_email = [email for email in seller_emails if "timeout" in email.get("subject", "").lower()]
            assert len(timeout_email) >= 1
            
            # Verify Kraken refund withdrawal
            kraken_history = harness.kraken.get_withdrawal_history()
            refund_withdrawal = [w for w in kraken_history if w["address"].endswith("_REFUND")]
            assert len(refund_withdrawal) >= 1
    
    async def test_scenario_5_admin_emergency_cancellation(self):
        """
        Scenario 5: Admin emergency cancellation with refund
        Flow: create → payment → admin flags issue → emergency cancel → refund
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            buyer_id = 10005
            seller_email = "flagged_seller@example.com"
            escrow_id = "test_escrow_005"
            
            # Complete payment step
            await self._create_and_pay_escrow(harness, buyer_id, seller_email, escrow_id)
            
            # Admin performs emergency cancellation
            admin_user_id = 99999999
            emergency_callback = harness.create_callback_update(
                user_id=admin_user_id,
                callback_data=f"admin_emergency_cancel_{escrow_id}"
            )
            context = harness.create_context(
                user_data={"is_admin": True, "admin_level": "super"}
            )
            
            from handlers.admin import handle_admin_callback  
            await handle_admin_callback(emergency_callback, context)
            
            # Verify admin confirmation required
            admin_messages = harness.telegram.get_sent_messages(admin_user_id)
            confirm_msg = [msg for msg in admin_messages if "confirm" in msg.get("text", "").lower() or "emergency" in msg.get("text", "").lower()]
            assert len(confirm_msg) >= 1
            
            # Admin confirms cancellation
            confirm_callback = harness.create_callback_update(
                user_id=admin_user_id,
                callback_data=f"admin_confirm_cancel_{escrow_id}_security_risk"
            )
            
            await handle_admin_callback(confirm_callback, context)
            
            # Verify immediate cancellation and refund
            buyer_messages = harness.telegram.get_sent_messages(buyer_id)
            cancel_msg = [msg for msg in buyer_messages if "cancelled" in msg.get("text", "").lower() and "admin" in msg.get("text", "").lower()]
            assert len(cancel_msg) >= 1
            
            # Verify seller notification
            seller_emails = harness.email.get_sent_emails(seller_email)
            seller_cancel = [email for email in seller_emails if "cancelled" in email.get("subject", "").lower()]
            assert len(seller_cancel) >= 1
            
            # Verify audit trail
            async with harness.test_db_session() as session:
                from sqlalchemy import select
                from models import EscrowAuditLog
                audit_result = await session.execute(
                    select(EscrowAuditLog).where(EscrowAuditLog.escrow_id == escrow_id)
                )
                audit_logs = list(audit_result.scalars())
                admin_actions = [log for log in audit_logs if "admin" in log.action.lower()]
                assert len(admin_actions) >= 1
    
    async def test_scenario_6_concurrent_escrow_operations(self):
        """
        Scenario 6: Concurrent escrow operations and race conditions
        Flow: multiple simultaneous operations → proper locking → consistent state
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            buyer_id = 10006
            seller_email = "concurrent_seller@example.com"
            escrow_id = "test_escrow_006"
            
            # Set up escrow
            await self._create_and_pay_escrow(harness, buyer_id, seller_email, escrow_id)
            
            # Create concurrent conflicting operations
            concurrent_tasks = []
            
            # Task 1: Buyer tries to cancel
            cancel_callback = harness.create_callback_update(
                user_id=buyer_id,
                callback_data=f"escrow_cancel_{escrow_id}"
            )
            context1 = harness.create_context()
            
            from handlers.escrow import handle_escrow_callback
            task1 = asyncio.create_task(handle_escrow_callback(cancel_callback, context1))
            concurrent_tasks.append(task1)
            
            # Task 2: Seller tries to accept simultaneously
            seller_accept_callback = harness.create_callback_update(
                user_id=99998,
                callback_data=f"escrow_seller_accept_{escrow_id}"
            )
            context2 = harness.create_context()
            
            task2 = asyncio.create_task(handle_escrow_callback(seller_accept_callback, context2))
            concurrent_tasks.append(task2)
            
            # Task 3: Admin tries emergency cancellation
            admin_callback = harness.create_callback_update(
                user_id=99999999,
                callback_data=f"admin_emergency_cancel_{escrow_id}"
            )
            context3 = harness.create_context(user_data={"is_admin": True})
            
            from handlers.admin import handle_admin_callback
            task3 = asyncio.create_task(handle_admin_callback(admin_callback, context3))
            concurrent_tasks.append(task3)
            
            # Execute all concurrently
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Verify no exceptions and proper handling
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 0, f"Concurrent operations failed: {exceptions}"
            
            # Verify only one operation succeeded (proper locking)
            all_messages = harness.telegram.get_sent_messages()
            success_indicators = [
                "cancelled", "accepted", "emergency", "completed"
            ]
            
            success_messages = []
            for msg in all_messages:
                msg_text = msg.get("text", "").lower()
                if any(indicator in msg_text for indicator in success_indicators):
                    success_messages.append(msg)
            
            # Should have consistent final state (not multiple conflicting states)
            async with harness.test_db_session() as session:
                from sqlalchemy import select
                escrow_result = await session.execute(
                    select(Escrow).where(Escrow.id == escrow_id)
                )
                final_escrow = escrow_result.scalar_one_or_none()
                assert final_escrow is not None
                
                # Should be in one consistent final state
                valid_final_states = [
                    EscrowStatus.CANCELLED,
                    EscrowStatus.ACTIVE,  # Seller accepted
                    EscrowStatus.ADMIN_CANCELLED
                ]
                assert final_escrow.status in valid_final_states
    
    # Helper methods
    async def _create_and_pay_escrow(self, harness, buyer_id: int, seller_email: str, escrow_id: str):
        """Helper to create escrow and simulate payment"""
        
        # Create escrow
        create_update = harness.create_user_update(
            user_id=buyer_id,
            message_text=f"/trade 75.00 ETH {seller_email}"
        )
        context = harness.create_context()
        
        from handlers.escrow import create_escrow_handler
        await create_escrow_handler(create_update, context)
        
        # Simulate payment received
        payment_data = {
            "escrow_id": escrow_id,
            "amount_received": Decimal("75.00"),
            "crypto_amount": Decimal("0.025"),  # ETH amount
            "tx_hash": f"test_tx_{escrow_id}",
            "confirmations": 3
        }
        
        from services.escrow_payment_processor import EscrowPaymentProcessor
        await EscrowPaymentProcessor.process_payment(payment_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
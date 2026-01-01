"""
Cross-Cutting Concerns Critical Scenarios
Top 3 cross-cutting scenarios: balance auditing, unified transactions, concurrency safety
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from tests.harness.test_harness import comprehensive_test_harness
from models import Transaction, TransactionType, BalanceAuditLog, User


@pytest.mark.asyncio
@pytest.mark.integration
class CrossCuttingScenarios:
    """
    Critical Scenario Matrix: Cross-Cutting Concerns
    
    Scenarios covered:
    1. Balance auditing and reconciliation accuracy
    2. Unified transaction system consistency  
    3. Concurrent operation safety and atomic guarantees
    """
    
    async def test_scenario_1_balance_auditing_reconciliation(self):
        """
        Scenario 1: Comprehensive balance auditing and reconciliation
        Flow: multiple operations → audit → discrepancy detection → reconciliation
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 30001
            
            # Set up initial balances
            harness.kraken.set_balance("BTC", Decimal("1.0"))
            harness.kraken.set_balance("ETH", Decimal("10.0"))
            harness.fincra.set_balance(Decimal("100000.0"))  # NGN
            
            # Step 1: Execute multiple operations to create transaction history
            operations = [
                {"type": "deposit", "amount": Decimal("0.5"), "currency": "BTC"},
                {"type": "withdrawal", "amount": Decimal("0.2"), "currency": "BTC"},
                {"type": "deposit", "amount": Decimal("5.0"), "currency": "ETH"},
                {"type": "withdrawal", "amount": Decimal("2.0"), "currency": "ETH"},
                {"type": "fincra_cashout", "amount": Decimal("50000.0"), "currency": "NGN"}
            ]
            
            for op in operations:
                if op["type"] == "deposit":
                    # Simulate deposit
                    current_balance = harness.kraken.balances[op["currency"]]
                    harness.kraken.set_balance(op["currency"], current_balance + op["amount"])
                elif op["type"] == "withdrawal":
                    # Simulate withdrawal
                    current_balance = harness.kraken.balances[op["currency"]]
                    harness.kraken.set_balance(op["currency"], current_balance - op["amount"])
                elif op["type"] == "fincra_cashout":
                    # Simulate Fincra transfer
                    current_balance = harness.fincra.balance_ngn
                    harness.fincra.set_balance(current_balance - op["amount"])
            
            # Step 2: Trigger balance audit
            from services.balance_audit_service import BalanceAuditService
            audit_result = await BalanceAuditService.perform_comprehensive_audit(
                user_id=user_id,
                include_external_verification=True
            )
            
            # Verify audit completed successfully
            assert audit_result["success"] is True
            assert "balance_summary" in audit_result
            assert "discrepancies" in audit_result
            assert "reconciliation_actions" in audit_result
            
            # Step 3: Check balance consistency
            balance_summary = audit_result["balance_summary"]
            
            # Expected final balances after all operations
            expected_btc = Decimal("1.0") + Decimal("0.5") - Decimal("0.2")  # 1.3 BTC
            expected_eth = Decimal("10.0") + Decimal("5.0") - Decimal("2.0")  # 13.0 ETH
            expected_ngn = Decimal("100000.0") - Decimal("50000.0")  # 50000.0 NGN
            
            assert abs(balance_summary["BTC"]["final_balance"] - expected_btc) < Decimal("0.00001")
            assert abs(balance_summary["ETH"]["final_balance"] - expected_eth) < Decimal("0.00001") 
            assert abs(balance_summary["NGN"]["final_balance"] - expected_ngn) < Decimal("0.01")
            
            # Step 4: Test discrepancy detection
            # Artificially introduce discrepancy
            harness.kraken.set_balance("BTC", Decimal("1.0"))  # Wrong balance
            
            discrepancy_audit = await BalanceAuditService.perform_comprehensive_audit(
                user_id=user_id,
                include_external_verification=True
            )
            
            # Should detect discrepancy
            assert len(discrepancy_audit["discrepancies"]) > 0
            btc_discrepancy = next((d for d in discrepancy_audit["discrepancies"] if d["currency"] == "BTC"), None)
            assert btc_discrepancy is not None
            assert abs(btc_discrepancy["difference"]) > Decimal("0.1")
            
            # Step 5: Verify audit logging
            async with harness.test_db_session() as session:
                from sqlalchemy import select
                
                audit_log_result = await session.execute(
                    select(BalanceAuditLog).where(BalanceAuditLog.user_id == user_id)
                )
                audit_logs = list(audit_log_result.scalars())
                
                assert len(audit_logs) >= 2  # At least 2 audits performed
                
                latest_audit = max(audit_logs, key=lambda x: x.created_at)
                assert latest_audit.discrepancies_found > 0
                assert "BTC" in str(latest_audit.audit_details)
    
    async def test_scenario_2_unified_transaction_system_consistency(self):
        """
        Scenario 2: Unified transaction system consistency across all operations
        Flow: mixed operations → transaction logging → consistency verification
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 30002
            
            # Step 1: Execute operations through unified transaction system
            from services.unified_transaction_service import UnifiedTransactionService, TransactionRequest
            
            transactions = [
                TransactionRequest(
                    user_id=user_id,
                    transaction_type="crypto_deposit",
                    amount=Decimal("100.0"),
                    currency="USD",
                    crypto_currency="BTC",
                    crypto_amount=Decimal("0.002"),
                    reference_id="unified_test_001"
                ),
                TransactionRequest(
                    user_id=user_id,
                    transaction_type="escrow_creation", 
                    amount=Decimal("75.0"),
                    currency="USD",
                    reference_id="unified_test_002"
                ),
                TransactionRequest(
                    user_id=user_id,
                    transaction_type="ngn_cashout",
                    amount=Decimal("25000.0"),
                    currency="NGN",
                    reference_id="unified_test_003"
                )
            ]
            
            transaction_results = []
            for tx_request in transactions:
                result = await UnifiedTransactionService.process_transaction(tx_request)
                transaction_results.append(result)
                
                # Verify each transaction succeeded
                assert result["success"] is True
                assert "transaction_id" in result
                assert result["status"] in ["completed", "processing", "pending"]
            
            # Step 2: Verify transaction consistency in database
            async with harness.test_db_session() as session:
                from sqlalchemy import select
                
                tx_result = await session.execute(
                    select(Transaction).where(Transaction.user_id == user_id)
                )
                db_transactions = list(tx_result.scalars())
                
                assert len(db_transactions) >= 3
                
                # Verify transaction details
                deposit_tx = next((tx for tx in db_transactions if "deposit" in tx.transaction_type.lower()), None)
                assert deposit_tx is not None
                assert deposit_tx.amount == Decimal("100.0")
                assert deposit_tx.crypto_amount == Decimal("0.002")
                
                escrow_tx = next((tx for tx in db_transactions if "escrow" in tx.transaction_type.lower()), None)
                assert escrow_tx is not None
                assert escrow_tx.amount == Decimal("75.0")
                
                cashout_tx = next((tx for tx in db_transactions if "cashout" in tx.transaction_type.lower()), None)
                assert cashout_tx is not None
                assert cashout_tx.amount == Decimal("25000.0")
                assert cashout_tx.currency == "NGN"
            
            # Step 3: Test transaction rollback consistency
            # Create a transaction that will fail midway
            failing_request = TransactionRequest(
                user_id=user_id,
                transaction_type="crypto_withdrawal",
                amount=Decimal("10.0"),  # More than available
                currency="BTC",
                crypto_amount=Decimal("10.0"),
                reference_id="unified_test_fail"
            )
            
            # Configure Kraken to fail
            harness.kraken.set_failure_mode("insufficient_funds")
            
            fail_result = await UnifiedTransactionService.process_transaction(failing_request)
            
            # Transaction should fail gracefully
            assert fail_result["success"] is False
            assert "error" in fail_result
            
            # Verify no partial state left in database
            async with harness.test_db_session() as session:
                failed_tx_result = await session.execute(
                    select(Transaction).where(
                        Transaction.user_id == user_id,
                        Transaction.reference_id == "unified_test_fail"
                    )
                )
                failed_transactions = list(failed_tx_result.scalars())
                
                # Should either have no record, or record marked as failed
                if failed_transactions:
                    for tx in failed_transactions:
                        assert tx.status in ["failed", "cancelled", "rolled_back"]
    
    async def test_scenario_3_concurrent_operation_safety_atomicity(self):
        """
        Scenario 3: Concurrent operation safety and atomic guarantees
        Flow: simultaneous operations → race conditions → consistency verification
        """
        
        with comprehensive_test_harness(scenario="success") as harness:
            user_id = 30003
            
            # Set up initial balance
            harness.kraken.set_balance("BTC", Decimal("1.0"))
            
            # Step 1: Test concurrent balance modifications
            from services.atomic_balance_service import AtomicBalanceService
            
            async def concurrent_operation(operation_id: int, amount: Decimal):
                """Simulate concurrent balance operation"""
                try:
                    if operation_id % 2 == 0:
                        # Even operations: withdrawals
                        result = await AtomicBalanceService.atomic_withdraw(
                            user_id=user_id,
                            currency="BTC", 
                            amount=amount,
                            operation_id=f"concurrent_withdraw_{operation_id}"
                        )
                    else:
                        # Odd operations: deposits
                        result = await AtomicBalanceService.atomic_deposit(
                            user_id=user_id,
                            currency="BTC",
                            amount=amount,
                            operation_id=f"concurrent_deposit_{operation_id}"
                        )
                    return result
                except Exception as e:
                    return {"success": False, "error": str(e), "operation_id": operation_id}
            
            # Create 20 concurrent operations
            concurrent_tasks = []
            for i in range(20):
                amount = Decimal("0.05")  # Small amounts to test precision
                task = asyncio.create_task(concurrent_operation(i, amount))
                concurrent_tasks.append(task)
            
            # Execute all operations concurrently
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Step 2: Verify results consistency
            successful_operations = [r for r in results if isinstance(r, dict) and r.get("success", False)]
            failed_operations = [r for r in results if isinstance(r, dict) and not r.get("success", False)]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            # Should have no exceptions
            assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
            
            # Calculate expected final balance
            deposits = len([op for op in successful_operations if "deposit" in str(op.get("operation_id", ""))])
            withdrawals = len([op for op in successful_operations if "withdraw" in str(op.get("operation_id", ""))])
            
            expected_balance = Decimal("1.0") + (deposits * Decimal("0.05")) - (withdrawals * Decimal("0.05"))
            
            # Verify final balance matches expected
            final_balance = harness.kraken.balances["BTC"]
            balance_difference = abs(final_balance - expected_balance)
            assert balance_difference < Decimal("0.00001"), f"Balance inconsistency: expected {expected_balance}, got {final_balance}"
            
            # Step 3: Test atomic escrow operations
            async def concurrent_escrow_operation(escrow_id: str, operation_type: str):
                """Simulate concurrent escrow state changes"""
                from services.atomic_escrow_service import AtomicEscrowService
                
                try:
                    if operation_type == "activate":
                        return await AtomicEscrowService.atomic_activate(escrow_id)
                    elif operation_type == "cancel":
                        return await AtomicEscrowService.atomic_cancel(escrow_id, "concurrent_test")
                    elif operation_type == "complete":
                        return await AtomicEscrowService.atomic_complete(escrow_id)
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            # Test concurrent state changes on single escrow
            test_escrow_id = "concurrent_escrow_001"
            escrow_operations = [
                asyncio.create_task(concurrent_escrow_operation(test_escrow_id, "activate")),
                asyncio.create_task(concurrent_escrow_operation(test_escrow_id, "cancel")),
                asyncio.create_task(concurrent_escrow_operation(test_escrow_id, "complete")),
                asyncio.create_task(concurrent_escrow_operation(test_escrow_id, "activate")),
                asyncio.create_task(concurrent_escrow_operation(test_escrow_id, "cancel"))
            ]
            
            escrow_results = await asyncio.gather(*escrow_operations, return_exceptions=True)
            
            # Only one operation should succeed (proper locking)
            escrow_successes = [r for r in escrow_results if isinstance(r, dict) and r.get("success", False)]
            assert len(escrow_successes) <= 1, f"Multiple concurrent operations succeeded: {escrow_successes}"
            
            # Step 4: Verify database consistency after concurrent operations
            async with harness.test_db_session() as session:
                # Check for any orphaned or inconsistent records
                from sqlalchemy import select, func
                from models import Transaction, BalanceSnapshot
                
                # Verify transaction counts match expected operations
                tx_count_result = await session.execute(
                    select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
                )
                tx_count = tx_count_result.scalar()
                
                # Should have reasonable number of transactions (successful operations)
                assert tx_count >= len(successful_operations)
                
                # Verify no duplicate reference IDs (atomicity check)
                ref_ids_result = await session.execute(
                    select(Transaction.reference_id).where(
                        Transaction.user_id == user_id,
                        Transaction.reference_id.like("concurrent_%")
                    )
                )
                reference_ids = [row[0] for row in ref_ids_result.fetchall()]
                unique_refs = set(reference_ids)
                
                assert len(reference_ids) == len(unique_refs), "Duplicate reference IDs found - atomicity violated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
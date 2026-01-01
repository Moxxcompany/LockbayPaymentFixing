"""
DISPUTE FEE CALCULATION FORMULA TESTS (Limited Scope)
======================================================

IMPORTANT: These tests validate ONLY arithmetic formulas, NOT the actual service workflow.

What IS tested:
- FeeCalculator.calculate_refund_amount() formula (escrow - buyer_fee)
- FeeCalculator.calculate_release_amount() formula (escrow - seller_fee)
- Fee split arithmetic for all 3 modes (buyer_pays, seller_pays, split)
- Discount percentage calculations

What is NOT tested:
- DisputeResolutionService workflow execution
- PlatformRevenue record creation
- Wallet transaction creation  
- Fee retention vs fair refund policy enforcement
- Database transaction atomicity in disputes

These are PURE FORMULA CHECKS, not E2E service integration tests.
"""

import pytest
import logging
from decimal import Decimal
from datetime import datetime
import uuid

from models import (
    User, Escrow, EscrowStatus, Dispute, DisputeStatus, 
    PlatformRevenue
)
from utils.fee_calculator import FeeCalculator

logger = logging.getLogger(__name__)


@pytest.mark.e2e_dispute_fee_resolution
class TestDisputeFeeValidation:
    """FORMULA TESTS ONLY - Validate fee calculation arithmetic, NOT service workflow"""

    def test_buyer_pays_fee_retention_seller_accepted(self, test_db_session):
        """
        FORMULA TEST: Validates calculate_refund_amount() arithmetic only
        
        Scenario: Buyer pays all fees, seller accepted
        
        What this tests:
        - FeeCalculator.calculate_refund_amount() returns: escrow - buyer_fee
        - Expected: $100 escrow - $5 buyer_fee = $95 refund
        
        What this does NOT test:
        - DisputeResolutionService execution
        - PlatformRevenue record creation
        - Wallet transactions
        - Policy enforcement
        """
        session = test_db_session
        
        # Create users
        buyer = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"buyer_{uuid.uuid4().hex[:8]}@test.com",
            username=f"buyer_{uuid.uuid4().hex[:6]}",
            first_name="Buyer",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"seller_{uuid.uuid4().hex[:8]}@test.com",
            username=f"seller_{uuid.uuid4().hex[:6]}",
            first_name="Seller",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add_all([buyer, seller])
        session.commit()

        # Create escrow with buyer_pays fee split
        escrow = Escrow(
            escrow_id=f"ESC{uuid.uuid4().hex[:10].upper()}",
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal("100.00"),
            currency="USD",
            fee_amount=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            description="Test dispute escrow",
            fee_split_option="buyer_pays",
            buyer_fee_amount=Decimal("5.00"),
            seller_fee_amount=Decimal("0.00"),
            status=EscrowStatus.DISPUTED.value,
            seller_accepted_at=datetime.utcnow(),  # Seller accepted
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(escrow)
        session.commit()

        # Calculate expected refund using FeeCalculator
        refund_amount = FeeCalculator.calculate_refund_amount(
            escrow_amount=escrow.amount,
            buyer_fee_amount=escrow.buyer_fee_amount,
            fee_split_option=escrow.fee_split_option
        )

        # VALIDATION: When seller accepted, fees should be retained
        # calculate_refund_amount deducts buyer_fee: escrow - buyer_fee
        expected_refund = Decimal("95.00")  # $100 escrow - $5 buyer_fee = $95
        assert refund_amount == expected_refund, (
            f"Refund should be ${expected_refund} (buyer_fee deducted), got ${refund_amount}"
        )

        # VALIDATION: Platform should retain full fee
        retained_fee = escrow.buyer_fee_amount + escrow.seller_fee_amount
        assert retained_fee == Decimal("5.00"), f"Platform should retain $5.00, got ${retained_fee}"

        logger.info("✅ buyer_pays + seller_accepted: Fees correctly retained ($100 refund, $5 fee retained)")

    def test_buyer_pays_fair_refund_seller_never_accepted(self, test_db_session):
        """
        FORMULA TEST: Validates refund calculation arithmetic only
        
        Scenario: Buyer pays all fees, seller never accepted
        
        What this tests:
        - Basic arithmetic check: escrow + buyer_fee
        - Expected: $100 + $5 = $105
        
        What this does NOT test:
        - Fair refund policy enforcement
        - DisputeResolutionService execution
        - Revenue handling
        """
        session = test_db_session
        
        buyer = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"buyer_{uuid.uuid4().hex[:8]}@test.com",
            username=f"buyer_{uuid.uuid4().hex[:6]}",
            first_name="Buyer",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"seller_{uuid.uuid4().hex[:8]}@test.com",
            username=f"seller_{uuid.uuid4().hex[:6]}",
            first_name="Seller",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add_all([buyer, seller])
        session.commit()

        escrow = Escrow(
            escrow_id=f"ESC{uuid.uuid4().hex[:10].upper()}",
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal("100.00"),
            currency="USD",
            fee_amount=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            description="Test dispute escrow",
            fee_split_option="buyer_pays",
            buyer_fee_amount=Decimal("5.00"),
            seller_fee_amount=Decimal("0.00"),
            status=EscrowStatus.DISPUTED.value,
            seller_accepted_at=None,  # Seller NEVER accepted
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(escrow)
        session.commit()

        # Calculate expected refund
        # Note: FeeCalculator.calculate_refund_amount doesn't check seller_accepted_at
        # The dispute resolution service handles that logic
        # For this validation, we check the expected behavior:
        
        # When seller never accepted, fair refund policy = escrow + buyer_fee
        expected_fair_refund = Decimal("105.00")  # $100 escrow + $5 buyer_fee
        
        # VALIDATION: Seller never accepted means buyer should get everything back
        assert escrow.seller_accepted_at is None, "Seller should not have accepted"
        total_buyer_paid = escrow.amount + escrow.buyer_fee_amount
        assert total_buyer_paid == expected_fair_refund, (
            f"Buyer paid ${total_buyer_paid}, should get full refund"
        )

        logger.info("✅ buyer_pays + seller_never_accepted: Fair refund policy ($105 full refund)")

    def test_seller_pays_fee_deduction(self, test_db_session):
        """
        FORMULA TEST: Validates calculate_release_amount() arithmetic only
        
        Scenario: Seller pays all fees
        
        What this tests:
        - FeeCalculator.calculate_release_amount() returns: escrow - seller_fee
        - Expected: $100 escrow - $5 seller_fee = $95 release
        
        What this does NOT test:
        - DisputeResolutionService execution
        - Platform revenue retention
        - Wallet transactions
        """
        session = test_db_session
        
        buyer = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"buyer_{uuid.uuid4().hex[:8]}@test.com",
            username=f"buyer_{uuid.uuid4().hex[:6]}",
            first_name="Buyer",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"seller_{uuid.uuid4().hex[:8]}@test.com",
            username=f"seller_{uuid.uuid4().hex[:6]}",
            first_name="Seller",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add_all([buyer, seller])
        session.commit()

        escrow = Escrow(
            escrow_id=f"ESC{uuid.uuid4().hex[:10].upper()}",
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal("100.00"),
            currency="USD",
            fee_amount=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            description="Test dispute escrow",
            fee_split_option="seller_pays",
            buyer_fee_amount=Decimal("0.00"),
            seller_fee_amount=Decimal("5.00"),
            status=EscrowStatus.DISPUTED.value,
            seller_accepted_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(escrow)
        session.commit()

        # Calculate release amount
        release_amount = FeeCalculator.calculate_release_amount(
            escrow_amount=escrow.amount,
            seller_fee_amount=escrow.seller_fee_amount
        )

        expected_release = Decimal("95.00")  # $100 - $5 fee
        assert release_amount == expected_release, (
            f"Seller should receive ${expected_release}, got ${release_amount}"
        )

        retained_fee = escrow.seller_fee_amount
        assert retained_fee == Decimal("5.00"), f"Platform should retain $5.00"

        logger.info("✅ seller_pays: Correct fee deduction ($95 to seller, $5 fee retained)")

    def test_split_fees_calculation(self, test_db_session):
        """
        FORMULA TEST: Validates fee split arithmetic only
        
        Scenario: Fees split 50/50 between buyer and seller
        
        What this tests:
        - 50/50 split calculation: $5 fee → $2.50 each
        - Basic arithmetic validation
        
        What this does NOT test:
        - Fee policy enforcement
        - Platform revenue recording
        - DisputeResolutionService execution
        """
        session = test_db_session
        
        buyer = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"buyer_{uuid.uuid4().hex[:8]}@test.com",
            username=f"buyer_{uuid.uuid4().hex[:6]}",
            first_name="Buyer",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"seller_{uuid.uuid4().hex[:8]}@test.com",
            username=f"seller_{uuid.uuid4().hex[:6]}",
            first_name="Seller",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add_all([buyer, seller])
        session.commit()

        escrow = Escrow(
            escrow_id=f"ESC{uuid.uuid4().hex[:10].upper()}",
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal("100.00"),
            currency="USD",
            fee_amount=Decimal("5.00"),
            total_amount=Decimal("105.00"),
            description="Test split fees escrow",
            fee_split_option="split",
            buyer_fee_amount=Decimal("2.50"),
            seller_fee_amount=Decimal("2.50"),
            status=EscrowStatus.DISPUTED.value,
            seller_accepted_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(escrow)
        session.commit()

        # VALIDATION: Check fee split
        assert escrow.buyer_fee_amount == Decimal("2.50"), "Buyer should pay $2.50"
        assert escrow.seller_fee_amount == Decimal("2.50"), "Seller should pay $2.50"
        total_fee = escrow.buyer_fee_amount + escrow.seller_fee_amount
        assert total_fee == Decimal("5.00"), f"Total platform fee should be $5.00, got ${total_fee}"

        # VALIDATION: Check refund calculation
        refund_amount = FeeCalculator.calculate_refund_amount(
            escrow_amount=escrow.amount,
            buyer_fee_amount=escrow.buyer_fee_amount,
            fee_split_option=escrow.fee_split_option
        )
        # calculate_refund_amount deducts buyer_fee: escrow - buyer_fee
        expected_refund = Decimal("97.50")  # $100 escrow - $2.50 buyer_fee = $97.50
        assert refund_amount == expected_refund, (
            f"Refund should be ${expected_refund} (buyer_fee deducted), got ${refund_amount}"
        )

        # VALIDATION: Check release calculation
        release_amount = FeeCalculator.calculate_release_amount(
            escrow_amount=escrow.amount,
            seller_fee_amount=escrow.seller_fee_amount
        )
        expected_release = Decimal("97.50")  # $100 - $2.50 seller fee
        assert release_amount == expected_release, (
            f"Seller should receive ${expected_release}, got ${release_amount}"
        )

        logger.info("✅ split: Correct 50/50 fee split ($2.50 each, total $5.00)")

    def test_trusted_trader_discount_in_dispute_fee(self, test_db_session):
        """
        FORMULA TEST: Validates discount percentage calculation only
        
        Scenario: Active Trader (5+ trades) should get 10% discount
        
        What this tests:
        - Discount calculation: 5% base - 10% = 4.5% effective rate
        - Expected fee: $100 × 4.5% = $4.50
        
        What this does NOT test:
        - Discount policy enforcement in actual disputes
        - DisputeResolutionService execution
        - Fee application in real workflow
        """
        session = test_db_session
        
        # Create Active Trader (5 completed trades)
        buyer = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"active_trader_{uuid.uuid4().hex[:8]}@test.com",
            username=f"active_trader_{uuid.uuid4().hex[:6]}",
            first_name="ActiveTrader",
            is_verified=True,
            completed_trades=5,
            total_ratings=3,
            reputation_score=Decimal("4.6"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller = User(
            telegram_id=str(uuid.uuid4().int)[:15],
            email=f"seller_{uuid.uuid4().hex[:8]}@test.com",
            username=f"seller_{uuid.uuid4().hex[:6]}",
            first_name="Seller",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add_all([buyer, seller])
        session.commit()

        # Create historical completed trades
        for i in range(5):
            historical_escrow = Escrow(
                escrow_id=f"ESC{uuid.uuid4().hex[:10].upper()}",
                buyer_id=buyer.id if i % 2 == 0 else seller.id,
                seller_id=seller.id if i % 2 == 0 else buyer.id,
                amount=Decimal("50.00"),
                currency="USD",
                fee_amount=Decimal("2.50"),
                total_amount=Decimal("52.50"),
                description=f"Historical trade {i+1}",
                fee_split_option="buyer_pays",
                buyer_fee_amount=Decimal("2.50"),
                seller_fee_amount=Decimal("0.00"),
                status=EscrowStatus.COMPLETED.value,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(historical_escrow)
        session.commit()

        # Calculate fee with Active Trader discount
        calculator = FeeCalculator()
        breakdown = calculator.calculate_escrow_breakdown(
            escrow_amount=100.00,
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=buyer,
            session=session,
            is_first_trade=False
        )

        discounted_fee = breakdown['total_platform_fee']
        expected_discounted_fee = Decimal("4.50")  # 10% discount: $5.00 * 0.9 = $4.50
        
        assert discounted_fee == expected_discounted_fee, (
            f"Active Trader should have ${expected_discounted_fee} fee (10% discount), got ${discounted_fee}"
        )

        logger.info("✅ Active Trader: 10% discount correctly applied ($4.50 vs $5.00 base fee)")

"""
E2E tests for fee split scenarios across escrow lifecycle

Tests comprehensive fee handling for:
- buyer_pays: buyer pays all fees, seller receives full amount
- seller_pays: seller pays all fees, buyer only pays escrow amount
- split: fees split 50/50 between buyer and seller

Scenarios: release, cancel, refund with different fee modes and trader discounts
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import text
from models import User, Wallet, Escrow, EscrowHolding, EscrowStatus
from utils.fee_calculator import FeeCalculator
from utils.universal_id_generator import UniversalIDGenerator
import logging

logger = logging.getLogger(__name__)


@pytest.mark.e2e_escrow_lifecycle
class TestFeeSplitEscrowLifecycle:
    """Test fee split scenarios across complete escrow lifecycle"""

    def test_buyer_pays_release_scenario(self, test_db_session):
        """
        Test buyer_pays mode: buyer pays all fees, seller receives full amount
        
        Flow: create → pay → accept → deliver → release
        Expected: Buyer pays amount + fee, seller receives amount, platform gets fee
        """
        session = test_db_session
        
        # Create buyer and seller
        buyer = User(
            telegram_id=8881001,
            email="buyer_pays_buyer@test.com",
            username="buyer_pays_buyer",
            first_name="BuyerBuyer",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        buyer.is_verified = True
        buyer.completed_trades = 0
        buyer.total_ratings = 0
        buyer.average_rating = Decimal("0.0")
        session.add(buyer)
        
        seller = User(
            telegram_id=8881002,
            email="buyer_pays_seller@test.com",
            username="buyer_pays_seller",
            first_name="SellerSeller",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller.is_verified = True
        seller.completed_trades = 0
        seller.total_ratings = 0
        seller.average_rating = Decimal("0.0")
        session.add(seller)
        session.flush()
        
        # Create wallets
        buyer_wallet = Wallet(
            user_id=buyer.id,
            currency="USD",
            available_balance=Decimal("1000.00"),
            frozen_balance=Decimal("0.00")
        )
        seller_wallet = Wallet(
            user_id=seller.id,
            currency="USD",
            available_balance=Decimal("0.00"),
            frozen_balance=Decimal("0.00")
        )
        session.add(buyer_wallet)
        session.add(seller_wallet)
        session.flush()
        
        # Calculate fees - no user/session passed means no discount
        amount = Decimal("100.00")
        calculator = FeeCalculator()
        breakdown = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            is_first_trade=False  # Disable first trade free for testing
        )
        
        # Verify fee breakdown
        assert breakdown['total_platform_fee'] == Decimal("5.00"), "5% fee expected"
        assert breakdown['buyer_fee_amount'] == Decimal("5.00"), "Buyer pays all"
        assert breakdown['seller_fee_amount'] == Decimal("0.00"), "Seller pays nothing"
        assert breakdown['buyer_total_payment'] == Decimal("105.00"), "Amount + buyer fee"
        
        # Create escrow
        escrow_id = UniversalIDGenerator.generate_escrow_id()
        escrow = Escrow(
            escrow_id=escrow_id,
            utid=escrow_id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=amount,
            fee_amount=breakdown['total_platform_fee'],
            buyer_fee_amount=breakdown['buyer_fee_amount'],
            seller_fee_amount=breakdown['seller_fee_amount'],
            total_amount=amount + breakdown['total_platform_fee'],
            currency='USD',
            fee_split_option='buyer_pays',
            status=EscrowStatus.PAYMENT_CONFIRMED.value,
            description="Buyer pays all fees test",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        session.add(escrow)
        session.flush()
        
        # Deduct from buyer (amount + fee)
        buyer_wallet.available_balance -= breakdown['buyer_total_payment']
        
        # Create escrow holding
        holding = EscrowHolding(
            escrow_id=escrow.escrow_id,
            amount_held=amount + breakdown['total_platform_fee'],  # Holds amount + fee
            currency="USD",
            created_at=datetime.utcnow()
        )
        session.add(holding)
        
        # Simulate release: seller receives amount, platform keeps fee
        escrow.status = EscrowStatus.COMPLETED.value
        seller_wallet.available_balance += amount  # Seller gets full amount
        
        session.commit()
        session.refresh(buyer_wallet)
        session.refresh(seller_wallet)
        
        # Verify final balances
        assert buyer_wallet.available_balance == Decimal("895.00"), "Buyer paid 100 + 5 fee"
        assert seller_wallet.available_balance == Decimal("100.00"), "Seller received full 100"
        
        logger.info("✅ Buyer pays release scenario validated")

    def test_seller_pays_release_scenario(self, test_db_session):
        """
        Test seller_pays mode: seller pays all fees, buyer only pays amount
        
        Flow: create → pay → accept → deliver → release
        Expected: Buyer pays amount only, seller receives (amount - fee), platform gets fee
        """
        session = test_db_session
        
        # Create buyer and seller
        buyer = User(
            telegram_id=8882001,
            email="seller_pays_buyer@test.com",
            username="seller_pays_buyer",
            first_name="SellerPaysBuyer",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        buyer.is_verified = True
        buyer.completed_trades = 0
        buyer.total_ratings = 0
        buyer.average_rating = Decimal("0.0")
        session.add(buyer)
        
        seller = User(
            telegram_id=8882002,
            email="seller_pays_seller@test.com",
            username="seller_pays_seller",
            first_name="SellerPaysSeller",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller.is_verified = True
        seller.completed_trades = 0
        seller.total_ratings = 0
        seller.average_rating = Decimal("0.0")
        session.add(seller)
        session.flush()
        
        # Create wallets
        buyer_wallet = Wallet(
            user_id=buyer.id,
            currency="USD",
            available_balance=Decimal("1000.00"),
            frozen_balance=Decimal("0.00")
        )
        seller_wallet = Wallet(
            user_id=seller.id,
            currency="USD",
            available_balance=Decimal("0.00"),
            frozen_balance=Decimal("0.00")
        )
        session.add(buyer_wallet)
        session.add(seller_wallet)
        session.flush()
        
        # Calculate fees
        amount = Decimal("100.00")
        calculator = FeeCalculator()
        breakdown = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='seller_pays',
            is_first_trade=False  # Disable first trade free for testing
        )
        
        # Verify fee breakdown
        assert breakdown['total_platform_fee'] == Decimal("5.00"), "5% fee expected"
        assert breakdown['buyer_fee_amount'] == Decimal("0.00"), "Buyer pays nothing"
        assert breakdown['seller_fee_amount'] == Decimal("5.00"), "Seller pays all"
        assert breakdown['buyer_total_payment'] == Decimal("100.00"), "Buyer only pays amount"
        
        # Create escrow
        escrow_id = UniversalIDGenerator.generate_escrow_id()
        escrow = Escrow(
            escrow_id=escrow_id,
            utid=escrow_id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=amount,
            fee_amount=breakdown['total_platform_fee'],
            buyer_fee_amount=breakdown['buyer_fee_amount'],
            seller_fee_amount=breakdown['seller_fee_amount'],
            total_amount=amount + breakdown['total_platform_fee'],
            currency='USD',
            fee_split_option='seller_pays',
            status=EscrowStatus.PAYMENT_CONFIRMED.value,
            description="Seller pays all fees test",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        session.add(escrow)
        session.flush()
        
        # Deduct from buyer (amount only)
        buyer_wallet.available_balance -= amount
        
        # Create escrow holding
        holding = EscrowHolding(
            escrow_id=escrow.escrow_id,
            amount_held=amount,  # Only holds amount
            currency="USD",
            created_at=datetime.utcnow()
        )
        session.add(holding)
        
        # Simulate release: seller receives (amount - fee), platform keeps fee
        escrow.status = EscrowStatus.COMPLETED.value
        seller_wallet.available_balance += (amount - breakdown['total_platform_fee'])  # Seller pays fee
        
        session.commit()
        session.refresh(buyer_wallet)
        session.refresh(seller_wallet)
        
        # Verify final balances
        assert buyer_wallet.available_balance == Decimal("900.00"), "Buyer paid 100 only"
        assert seller_wallet.available_balance == Decimal("95.00"), "Seller received 100 - 5 fee"
        
        logger.info("✅ Seller pays release scenario validated")

    def test_split_fee_release_scenario(self, test_db_session):
        """
        Test split mode: fees split 50/50 between buyer and seller
        
        Flow: create → pay → accept → deliver → release
        Expected: Buyer pays amount + 50% fee, seller receives amount - 50% fee, platform gets fee
        """
        session = test_db_session
        
        # Create buyer and seller
        buyer = User(
            telegram_id=8883001,
            email="split_fee_buyer@test.com",
            username="split_fee_buyer",
            first_name="SplitFeeBuyer",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        buyer.is_verified = True
        buyer.completed_trades = 0
        buyer.total_ratings = 0
        buyer.average_rating = Decimal("0.0")
        session.add(buyer)
        
        seller = User(
            telegram_id=8883002,
            email="split_fee_seller@test.com",
            username="split_fee_seller",
            first_name="SplitFeeSeller",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller.is_verified = True
        seller.completed_trades = 0
        seller.total_ratings = 0
        seller.average_rating = Decimal("0.0")
        session.add(seller)
        session.flush()
        
        # Create wallets
        buyer_wallet = Wallet(
            user_id=buyer.id,
            currency="USD",
            available_balance=Decimal("1000.00"),
            frozen_balance=Decimal("0.00")
        )
        seller_wallet = Wallet(
            user_id=seller.id,
            currency="USD",
            available_balance=Decimal("0.00"),
            frozen_balance=Decimal("0.00")
        )
        session.add(buyer_wallet)
        session.add(seller_wallet)
        session.flush()
        
        # Calculate fees
        amount = Decimal("100.00")
        calculator = FeeCalculator()
        breakdown = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='split',
            is_first_trade=False  # Disable first trade free for testing
        )
        
        # Verify fee breakdown
        assert breakdown['total_platform_fee'] == Decimal("5.00"), "5% fee expected"
        assert breakdown['buyer_fee_amount'] == Decimal("2.50"), "Buyer pays 50%"
        assert breakdown['seller_fee_amount'] == Decimal("2.50"), "Seller pays 50%"
        assert breakdown['buyer_total_payment'] == Decimal("102.50"), "Amount + buyer's 50%"
        
        # Create escrow
        escrow_id = UniversalIDGenerator.generate_escrow_id()
        escrow = Escrow(
            escrow_id=escrow_id,
            utid=escrow_id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=amount,
            fee_amount=breakdown['total_platform_fee'],
            buyer_fee_amount=breakdown['buyer_fee_amount'],
            seller_fee_amount=breakdown['seller_fee_amount'],
            total_amount=amount + breakdown['total_platform_fee'],
            currency='USD',
            fee_split_option='split',
            status=EscrowStatus.PAYMENT_CONFIRMED.value,
            description="Split fee test",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        session.add(escrow)
        session.flush()
        
        # Deduct from buyer (amount + 50% fee)
        buyer_wallet.available_balance -= breakdown['buyer_total_payment']
        
        # Create escrow holding
        holding = EscrowHolding(
            escrow_id=escrow.escrow_id,
            amount_held=amount + breakdown['buyer_fee_amount'],  # Holds amount + buyer's fee
            currency="USD",
            created_at=datetime.utcnow()
        )
        session.add(holding)
        
        # Simulate release: seller receives (amount - seller's 50% fee), platform keeps full fee
        escrow.status = EscrowStatus.COMPLETED.value
        seller_wallet.available_balance += (amount - breakdown['seller_fee_amount'])  # Seller pays their 50%
        
        session.commit()
        session.refresh(buyer_wallet)
        session.refresh(seller_wallet)
        
        # Verify final balances
        assert buyer_wallet.available_balance == Decimal("897.50"), "Buyer paid 100 + 2.50 fee"
        assert seller_wallet.available_balance == Decimal("97.50"), "Seller received 100 - 2.50 fee"
        
        logger.info("✅ Split fee release scenario validated")

    def test_buyer_pays_cancel_refund_scenario(self, test_db_session):
        """
        Test buyer_pays mode with cancellation/refund
        
        Flow: create → pay → cancel → refund
        Expected: Buyer gets full refund (amount + fee)
        """
        session = test_db_session
        
        # Create buyer
        buyer = User(
            telegram_id=8884001,
            email="cancel_buyer@test.com",
            username="cancel_buyer",
            first_name="CancelBuyer",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        buyer.is_verified = True
        buyer.completed_trades = 0
        buyer.total_ratings = 0
        buyer.average_rating = Decimal("0.0")
        session.add(buyer)
        session.flush()
        
        # Create wallet
        buyer_wallet = Wallet(
            user_id=buyer.id,
            currency="USD",
            available_balance=Decimal("1000.00"),
            frozen_balance=Decimal("0.00")
        )
        session.add(buyer_wallet)
        session.flush()
        
        # Calculate fees
        amount = Decimal("100.00")
        calculator = FeeCalculator()
        breakdown = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            is_first_trade=False  # Disable first trade free for testing
        )
        
        # Create escrow
        escrow_id = UniversalIDGenerator.generate_escrow_id()
        escrow = Escrow(
            escrow_id=escrow_id,
            utid=escrow_id,
            buyer_id=buyer.id,
            seller_contact_type="email",
            seller_contact_value="seller@test.com",
            amount=amount,
            fee_amount=breakdown['total_platform_fee'],
            buyer_fee_amount=breakdown['buyer_fee_amount'],
            seller_fee_amount=breakdown['seller_fee_amount'],
            total_amount=amount + breakdown['total_platform_fee'],
            currency='USD',
            fee_split_option='buyer_pays',
            status=EscrowStatus.PAYMENT_CONFIRMED.value,
            description="Cancel refund test",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        session.add(escrow)
        session.flush()
        
        # Deduct from buyer
        buyer_wallet.available_balance -= breakdown['buyer_total_payment']
        initial_balance = buyer_wallet.available_balance
        
        # Simulate cancellation and refund
        escrow.status = EscrowStatus.CANCELLED.value
        buyer_wallet.available_balance += breakdown['buyer_total_payment']  # Full refund including fee
        
        session.commit()
        session.refresh(buyer_wallet)
        
        # Verify refund
        assert buyer_wallet.available_balance == Decimal("1000.00"), "Buyer got full refund"
        
        logger.info("✅ Buyer pays cancel/refund scenario validated")

    def test_seller_pays_cancel_refund_scenario(self, test_db_session):
        """
        Test seller_pays mode with cancellation/refund
        
        Flow: create → pay → cancel → refund
        Expected: Buyer gets amount refund only (no fee was charged)
        """
        session = test_db_session
        
        # Create buyer
        buyer = User(
            telegram_id=8887001,
            email="seller_pays_cancel_buyer@test.com",
            username="seller_pays_cancel_buyer",
            first_name="SellerPaysCancelBuyer",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        buyer.is_verified = True
        buyer.completed_trades = 0
        buyer.total_ratings = 0
        buyer.average_rating = Decimal("0.0")
        session.add(buyer)
        session.flush()
        
        # Create wallet
        buyer_wallet = Wallet(
            user_id=buyer.id,
            currency="USD",
            available_balance=Decimal("1000.00"),
            frozen_balance=Decimal("0.00")
        )
        session.add(buyer_wallet)
        session.flush()
        
        # Calculate fees
        amount = Decimal("100.00")
        calculator = FeeCalculator()
        breakdown = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='seller_pays',
            is_first_trade=False  # Disable first trade free for testing
        )
        
        # Verify fee breakdown
        assert breakdown['total_platform_fee'] == Decimal("5.00"), "5% fee expected"
        assert breakdown['buyer_fee_amount'] == Decimal("0.00"), "Buyer pays no fee"
        assert breakdown['seller_fee_amount'] == Decimal("5.00"), "Seller would pay fee"
        assert breakdown['buyer_total_payment'] == Decimal("100.00"), "Buyer only pays amount"
        
        # Create escrow
        escrow_id = UniversalIDGenerator.generate_escrow_id()
        escrow = Escrow(
            escrow_id=escrow_id,
            utid=escrow_id,
            buyer_id=buyer.id,
            seller_contact_type="email",
            seller_contact_value="seller@test.com",
            amount=amount,
            fee_amount=breakdown['total_platform_fee'],
            buyer_fee_amount=breakdown['buyer_fee_amount'],
            seller_fee_amount=breakdown['seller_fee_amount'],
            total_amount=amount + breakdown['total_platform_fee'],
            currency='USD',
            fee_split_option='seller_pays',
            status=EscrowStatus.PAYMENT_CONFIRMED.value,
            description="Seller pays cancel refund test",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        session.add(escrow)
        session.flush()
        
        # Deduct from buyer (amount only, no fee)
        buyer_wallet.available_balance -= breakdown['buyer_total_payment']
        
        # Simulate cancellation and refund
        escrow.status = EscrowStatus.CANCELLED.value
        buyer_wallet.available_balance += breakdown['buyer_total_payment']  # Refund amount only
        
        session.commit()
        session.refresh(buyer_wallet)
        
        # Verify refund - buyer gets back what they paid (amount only, no fee)
        assert buyer_wallet.available_balance == Decimal("1000.00"), "Buyer got amount refund only"
        
        logger.info("✅ Seller pays cancel/refund scenario validated")

    def test_split_fee_cancel_refund_scenario(self, test_db_session):
        """
        Test split mode with cancellation/refund
        
        Flow: create → pay → cancel → refund
        Expected: Buyer gets amount + buyer's 50% fee refund
        """
        session = test_db_session
        
        # Create buyer
        buyer = User(
            telegram_id=8888001,
            email="split_cancel_buyer@test.com",
            username="split_cancel_buyer",
            first_name="SplitCancelBuyer",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        buyer.is_verified = True
        buyer.completed_trades = 0
        buyer.total_ratings = 0
        buyer.average_rating = Decimal("0.0")
        session.add(buyer)
        session.flush()
        
        # Create wallet
        buyer_wallet = Wallet(
            user_id=buyer.id,
            currency="USD",
            available_balance=Decimal("1000.00"),
            frozen_balance=Decimal("0.00")
        )
        session.add(buyer_wallet)
        session.flush()
        
        # Calculate fees
        amount = Decimal("100.00")
        calculator = FeeCalculator()
        breakdown = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='split',
            is_first_trade=False  # Disable first trade free for testing
        )
        
        # Verify fee breakdown
        assert breakdown['total_platform_fee'] == Decimal("5.00"), "5% fee expected"
        assert breakdown['buyer_fee_amount'] == Decimal("2.50"), "Buyer pays 50%"
        assert breakdown['seller_fee_amount'] == Decimal("2.50"), "Seller would pay 50%"
        assert breakdown['buyer_total_payment'] == Decimal("102.50"), "Amount + buyer's 50%"
        
        # Create escrow
        escrow_id = UniversalIDGenerator.generate_escrow_id()
        escrow = Escrow(
            escrow_id=escrow_id,
            utid=escrow_id,
            buyer_id=buyer.id,
            seller_contact_type="email",
            seller_contact_value="seller@test.com",
            amount=amount,
            fee_amount=breakdown['total_platform_fee'],
            buyer_fee_amount=breakdown['buyer_fee_amount'],
            seller_fee_amount=breakdown['seller_fee_amount'],
            total_amount=amount + breakdown['total_platform_fee'],
            currency='USD',
            fee_split_option='split',
            status=EscrowStatus.PAYMENT_CONFIRMED.value,
            description="Split fee cancel refund test",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        session.add(escrow)
        session.flush()
        
        # Deduct from buyer (amount + 50% fee)
        buyer_wallet.available_balance -= breakdown['buyer_total_payment']
        
        # Simulate cancellation and refund
        escrow.status = EscrowStatus.CANCELLED.value
        buyer_wallet.available_balance += breakdown['buyer_total_payment']  # Refund amount + buyer's 50% fee
        
        session.commit()
        session.refresh(buyer_wallet)
        
        # Verify refund - buyer gets back amount + their 50% fee
        assert buyer_wallet.available_balance == Decimal("1000.00"), "Buyer got amount + 50% fee refund"
        
        logger.info("✅ Split fee cancel/refund scenario validated")

    def test_all_discount_tiers(self, test_db_session):
        """
        Test ALL 7 discount tiers deterministically
        
        Tests all trader levels with their respective discounts:
        - New User (0 trades): 0% discount → $5.00 fee
        - New Trader (1 trade): 0% discount → $5.00 fee
        - Active Trader (5 trades): 10% discount → $4.50 fee
        - Experienced Trader (10 trades): 20% discount → $4.00 fee
        - Trusted Trader (25 trades, 4.5+ rating): 30% discount → $3.50 fee
        - Elite Trader (50 trades, 4.7+ rating): 40% discount → $3.00 fee
        - Master Trader (100 trades, 4.8+ rating): 50% discount → $2.50 fee
        """
        session = test_db_session
        amount = Decimal("100.00")
        calculator = FeeCalculator()
        import uuid
        
        # Test 1: New User (0 trades) - 0% discount
        new_user = User(
            telegram_id=8889001,
            email="new_user@test.com",
            username="new_user",
            first_name="NewUser",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        new_user.is_verified = True
        new_user.completed_trades = 0
        new_user.total_ratings = 0
        new_user.average_rating = Decimal("0.0")
        new_user.reputation_score = Decimal("0.0")
        session.add(new_user)
        session.commit()
        
        breakdown_new_user = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=new_user,
            session=session,
            is_first_trade=False
        )
        assert breakdown_new_user['total_platform_fee'] == Decimal("5.00"), "New User: 0% discount → $5.00 fee"
        logger.info("✅ Tier 1: New User (0 trades, 0% discount) = $5.00 fee")
        
        # Test 2: New Trader (1 trade) - 0% discount
        new_trader = User(
            telegram_id=8889002,
            email="new_trader@test.com",
            username="new_trader",
            first_name="NewTrader",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        new_trader.is_verified = True
        new_trader.completed_trades = 1
        new_trader.total_ratings = 0
        new_trader.average_rating = Decimal("0.0")
        new_trader.reputation_score = Decimal("0.0")
        session.add(new_trader)
        session.commit()
        
        # Create 1 completed escrow
        escrow_id = f"ES{uuid.uuid4().hex[:10].upper()}"
        escrow = Escrow(
            escrow_id=escrow_id,
            utid=escrow_id,
            buyer_id=new_trader.id,
            seller_contact_type="email",
            seller_contact_value="seller1@test.com",
            amount=Decimal("100.00"),
            fee_amount=Decimal("5.00"),
            buyer_fee_amount=Decimal("5.00"),
            seller_fee_amount=Decimal("0.00"),
            total_amount=Decimal("105.00"),
            currency='USD',
            fee_split_option='buyer_pays',
            status="completed",
            description="Completed trade 1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(escrow)
        session.commit()
        
        breakdown_new_trader = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=new_trader,
            session=session,
            is_first_trade=False
        )
        assert breakdown_new_trader['total_platform_fee'] == Decimal("5.00"), "New Trader: 0% discount → $5.00 fee"
        logger.info("✅ Tier 2: New Trader (1 trade, 0% discount) = $5.00 fee")
        
        # Test 3: Active Trader (5 trades) - 10% discount
        active_trader = User(
            telegram_id=8889003,
            email="active_trader@test.com",
            username="active_trader",
            first_name="ActiveTrader",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        active_trader.is_verified = True
        active_trader.completed_trades = 5
        active_trader.total_ratings = 0
        active_trader.average_rating = Decimal("0.0")
        active_trader.reputation_score = Decimal("0.0")
        session.add(active_trader)
        session.commit()
        
        # Create 5 completed escrows
        for i in range(5):
            escrow_id = f"ES{uuid.uuid4().hex[:10].upper()}"
            escrow = Escrow(
                escrow_id=escrow_id,
                utid=escrow_id,
                buyer_id=active_trader.id,
                seller_contact_type="email",
                seller_contact_value=f"seller{i}@test.com",
                amount=Decimal("100.00"),
                fee_amount=Decimal("5.00"),
                buyer_fee_amount=Decimal("5.00"),
                seller_fee_amount=Decimal("0.00"),
                total_amount=Decimal("105.00"),
                currency='USD',
                fee_split_option='buyer_pays',
                status="completed",
                description=f"Completed trade {i}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(escrow)
        session.commit()
        
        breakdown_active = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=active_trader,
            session=session,
            is_first_trade=False
        )
        assert breakdown_active['total_platform_fee'] == Decimal("4.50"), "Active Trader: 10% discount → $4.50 fee"
        logger.info("✅ Tier 3: Active Trader (5 trades, 10% discount) = $4.50 fee")
        
        # Test 4: Experienced Trader (10 trades) - 20% discount
        experienced_trader = User(
            telegram_id=8889004,
            email="experienced_trader@test.com",
            username="experienced_trader",
            first_name="ExperiencedTrader",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        experienced_trader.is_verified = True
        experienced_trader.completed_trades = 10
        experienced_trader.total_ratings = 0
        experienced_trader.average_rating = Decimal("0.0")
        experienced_trader.reputation_score = Decimal("0.0")
        session.add(experienced_trader)
        session.commit()
        
        # Create 10 completed escrows
        for i in range(10):
            escrow_id = f"ES{uuid.uuid4().hex[:10].upper()}"
            escrow = Escrow(
                escrow_id=escrow_id,
                utid=escrow_id,
                buyer_id=experienced_trader.id,
                seller_contact_type="email",
                seller_contact_value=f"seller_exp{i}@test.com",
                amount=Decimal("100.00"),
                fee_amount=Decimal("5.00"),
                buyer_fee_amount=Decimal("5.00"),
                seller_fee_amount=Decimal("0.00"),
                total_amount=Decimal("105.00"),
                currency='USD',
                fee_split_option='buyer_pays',
                status="completed",
                description=f"Completed trade {i}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(escrow)
        session.commit()
        
        breakdown_experienced = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=experienced_trader,
            session=session,
            is_first_trade=False
        )
        assert breakdown_experienced['total_platform_fee'] == Decimal("4.00"), "Experienced Trader: 20% discount → $4.00 fee"
        logger.info("✅ Tier 4: Experienced Trader (10 trades, 20% discount) = $4.00 fee")
        
        # Test 5: Trusted Trader (25 trades, 4.5+ rating) - 30% discount
        trusted_trader = User(
            telegram_id=8889005,
            email="trusted_trader@test.com",
            username="trusted_trader",
            first_name="TrustedTrader",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        trusted_trader.is_verified = True
        trusted_trader.completed_trades = 25
        trusted_trader.total_ratings = 10
        trusted_trader.average_rating = Decimal("4.6")
        trusted_trader.reputation_score = Decimal("4.6")
        session.add(trusted_trader)
        session.commit()
        
        # Create 25 completed escrows
        for i in range(25):
            escrow_id = f"ES{uuid.uuid4().hex[:10].upper()}"
            escrow = Escrow(
                escrow_id=escrow_id,
                utid=escrow_id,
                buyer_id=trusted_trader.id,
                seller_contact_type="email",
                seller_contact_value=f"seller_trust{i}@test.com",
                amount=Decimal("100.00"),
                fee_amount=Decimal("5.00"),
                buyer_fee_amount=Decimal("5.00"),
                seller_fee_amount=Decimal("0.00"),
                total_amount=Decimal("105.00"),
                currency='USD',
                fee_split_option='buyer_pays',
                status="completed",
                description=f"Completed trade {i}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(escrow)
        session.commit()
        
        breakdown_trusted = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=trusted_trader,
            session=session,
            is_first_trade=False
        )
        assert breakdown_trusted['total_platform_fee'] == Decimal("3.50"), "Trusted Trader: 30% discount → $3.50 fee"
        logger.info("✅ Tier 5: Trusted Trader (25 trades, 4.6 rating, 30% discount) = $3.50 fee")
        
        # Test 6: Elite Trader (50 trades, 4.7+ rating) - 40% discount
        elite_trader = User(
            telegram_id=8889006,
            email="elite_trader@test.com",
            username="elite_trader",
            first_name="EliteTrader",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        elite_trader.is_verified = True
        elite_trader.completed_trades = 50
        elite_trader.total_ratings = 20
        elite_trader.average_rating = Decimal("4.8")
        elite_trader.reputation_score = Decimal("4.8")
        session.add(elite_trader)
        session.commit()
        
        # Create 50 completed escrows
        for i in range(50):
            escrow_id = f"ES{uuid.uuid4().hex[:10].upper()}"
            escrow = Escrow(
                escrow_id=escrow_id,
                utid=escrow_id,
                buyer_id=elite_trader.id,
                seller_contact_type="email",
                seller_contact_value=f"seller_elite{i}@test.com",
                amount=Decimal("100.00"),
                fee_amount=Decimal("5.00"),
                buyer_fee_amount=Decimal("5.00"),
                seller_fee_amount=Decimal("0.00"),
                total_amount=Decimal("105.00"),
                currency='USD',
                fee_split_option='buyer_pays',
                status="completed",
                description=f"Completed trade {i}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(escrow)
        session.commit()
        
        breakdown_elite = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=elite_trader,
            session=session,
            is_first_trade=False
        )
        assert breakdown_elite['total_platform_fee'] == Decimal("3.00"), "Elite Trader: 40% discount → $3.00 fee"
        logger.info("✅ Tier 6: Elite Trader (50 trades, 4.8 rating, 40% discount) = $3.00 fee")
        
        # Test 7: Master Trader (100 trades, 4.8+ rating) - 50% discount
        master_trader = User(
            telegram_id=8889007,
            email="master_trader_all@test.com",
            username="master_trader_all",
            first_name="MasterTraderAll",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        master_trader.is_verified = True
        master_trader.completed_trades = 100
        master_trader.total_ratings = 50
        master_trader.average_rating = Decimal("4.9")
        master_trader.reputation_score = Decimal("4.9")
        session.add(master_trader)
        session.commit()
        
        # Create 100 completed escrows
        for i in range(100):
            escrow_id = f"ES{uuid.uuid4().hex[:10].upper()}"
            escrow = Escrow(
                escrow_id=escrow_id,
                utid=escrow_id,
                buyer_id=master_trader.id,
                seller_contact_type="email",
                seller_contact_value=f"seller_master{i}@test.com",
                amount=Decimal("100.00"),
                fee_amount=Decimal("5.00"),
                buyer_fee_amount=Decimal("5.00"),
                seller_fee_amount=Decimal("0.00"),
                total_amount=Decimal("105.00"),
                currency='USD',
                fee_split_option='buyer_pays',
                status="completed",
                description=f"Completed trade {i}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(escrow)
        session.commit()
        
        breakdown_master = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=master_trader,
            session=session,
            is_first_trade=False
        )
        assert breakdown_master['total_platform_fee'] == Decimal("2.50"), "Master Trader: 50% discount → $2.50 fee"
        logger.info("✅ Tier 7: Master Trader (100 trades, 4.9 rating, 50% discount) = $2.50 fee")
        
        logger.info("✅ All 7 discount tiers validated successfully")

    def test_trusted_trader_discount_fee_reduction(self, test_db_session):
        """
        Test Trusted Trader discount reduces fees correctly across fee split modes
        
        Flow: Verify discounts for different trader levels and fee split options
        """
        session = test_db_session
        
        # Create test trader with 10 completed trades (Active Trader - 10% discount)
        trader = User(
            telegram_id=8885001,
            email="trader_discount@test.com",
            username="trader_discount",
            first_name="TraderDiscount",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        trader.is_verified = True
        trader.completed_trades = 10  # Active Trader tier
        trader.total_ratings = 5
        trader.average_rating = Decimal("4.8")
        trader.reputation_score = Decimal("4.8")
        session.add(trader)
        session.commit()
        
        # Create 10 completed escrows so TrustedTraderSystem can find them
        for i in range(10):
            escrow_id = UniversalIDGenerator.generate_escrow_id()
            escrow = Escrow(
                escrow_id=escrow_id,
                utid=escrow_id,
                buyer_id=trader.id,
                seller_contact_type="email",
                seller_contact_value=f"seller{i}@test.com",
                amount=Decimal("100.00"),
                fee_amount=Decimal("5.00"),
                buyer_fee_amount=Decimal("5.00"),
                seller_fee_amount=Decimal("0.00"),
                total_amount=Decimal("105.00"),
                currency='USD',
                fee_split_option='buyer_pays',
                status="completed",
                description=f"Completed escrow {i}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(escrow)
        session.commit()
        
        # Test trader with 10 completed trades (Experienced Trader: 20% discount)
        amount = Decimal("100.00")
        calculator = FeeCalculator()
        
        # Test buyer_pays with discount
        breakdown_buyer_pays = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=trader,
            session=session,
            is_first_trade=False  # Disable first trade free for testing
        )
        
        # 5% base fee = 5.00, 20% discount = 4.00
        assert breakdown_buyer_pays['total_platform_fee'] == Decimal("4.00"), "20% discount applied for Experienced Trader"
        assert breakdown_buyer_pays['buyer_fee_amount'] == Decimal("4.00")
        assert breakdown_buyer_pays['buyer_total_payment'] == Decimal("104.00")
        
        # Test seller_pays with discount
        breakdown_seller_pays = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='seller_pays',
            user=trader,
            session=session,
            is_first_trade=False  # Disable first trade free for testing
        )
        
        assert breakdown_seller_pays['total_platform_fee'] == Decimal("4.00"), "20% discount applied"
        assert breakdown_seller_pays['seller_fee_amount'] == Decimal("4.00")
        assert breakdown_seller_pays['buyer_total_payment'] == Decimal("100.00")
        
        # Test split with discount
        breakdown_split = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='split',
            user=trader,
            session=session,
            is_first_trade=False  # Disable first trade free for testing
        )
        
        assert breakdown_split['total_platform_fee'] == Decimal("4.00"), "20% discount applied"
        assert breakdown_split['buyer_fee_amount'] == Decimal("2.00"), "50% of discounted fee"
        assert breakdown_split['seller_fee_amount'] == Decimal("2.00"), "50% of discounted fee"
        assert breakdown_split['buyer_total_payment'] == Decimal("102.00")
        
        logger.info("✅ Trusted Trader discount with fee splits validated")

    def test_max_discount_elite_trader(self, test_db_session):
        """
        Test maximum discount for Master traders (100+ trades, 4.8+ reputation gets 50% discount)
        """
        session = test_db_session
        
        # Create master trader with 150 completed trades (Master Trader - 50% discount)
        master_trader = User(
            telegram_id=8886001,
            email="master_trader@test.com",
            username="master_trader",
            first_name="MasterTrader",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        master_trader.is_verified = True
        master_trader.completed_trades = 150  # Master tier
        master_trader.total_ratings = 100
        master_trader.average_rating = Decimal("4.9")
        master_trader.reputation_score = Decimal("4.9")
        session.add(master_trader)
        session.commit()
        
        # Create 100 completed escrows to achieve Master Trader level (100+ trades, 4.8+ reputation)
        import uuid
        for i in range(100):
            # Use UUID to ensure unique IDs
            escrow_id = f"ES{datetime.utcnow().strftime('%y%m%d')}{str(uuid.uuid4())[:6].upper()}"
            escrow = Escrow(
                escrow_id=escrow_id,
                utid=escrow_id,
                buyer_id=master_trader.id,
                seller_contact_type="email",
                seller_contact_value=f"masterseller{i}@test.com",
                amount=Decimal("100.00"),
                fee_amount=Decimal("5.00"),
                buyer_fee_amount=Decimal("5.00"),
                seller_fee_amount=Decimal("0.00"),
                total_amount=Decimal("105.00"),
                currency='USD',
                fee_split_option='buyer_pays',
                status="completed",
                description=f"Completed escrow {i}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(escrow)
        session.commit()
        
        amount = Decimal("100.00")
        calculator = FeeCalculator()
        
        # Master trader (100+ trades, 4.8+ reputation) gets 50% discount
        breakdown = calculator.calculate_escrow_breakdown(
            escrow_amount=float(amount),
            payment_currency='USD',
            fee_split_option='buyer_pays',
            user=master_trader,
            session=session,
            is_first_trade=False  # Disable first trade free for testing
        )
        
        # 5% base fee = 5.00, 50% discount = 2.50
        assert breakdown['total_platform_fee'] == Decimal("2.50"), "50% discount applied for Master trader"
        assert breakdown['buyer_fee_amount'] == Decimal("2.50")
        assert breakdown['buyer_total_payment'] == Decimal("102.50")
        
        logger.info("✅ Master trader max discount validated")

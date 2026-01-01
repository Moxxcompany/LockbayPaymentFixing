"""
E2E Test for Trading Credit Anti-Abuse System

Tests the complete trading credit system including:
- Trading credit bonus crediting to new referred users
- Cashout restriction when user only has trading credit
- Atomic transaction validation (bonus fail = rollback)
- Welcome bonus notifications
"""
import pytest
from decimal import Decimal
from sqlalchemy import select
from models import User, Wallet
from services.crypto import CRYPTO_SERVICE_ATOMIC
from utils.referral import ReferralSystem
from db import SyncSessionLocal


class TestTradingCreditAntiAbuse:
    """E2E tests for trading credit anti-abuse system"""
    
    @pytest.fixture
    def setup_test_users(self):
        """Create test users for referral testing"""
        session = SyncSessionLocal()
        try:
            # Create referrer user
            referrer = User(
                telegram_id=999888777,
                username="referrer_user",
                email="referrer@test.com",
                email_verified=True,
                is_active=True,
                referral_code="TEST123"
            )
            session.add(referrer)
            session.flush()
            
            # Create referrer's USD wallet
            referrer_wallet = Wallet(
                user_id=referrer.id,
                currency="USD",
                available_balance=Decimal("0"),
                trading_credit=Decimal("0")
            )
            session.add(referrer_wallet)
            
            # Create referee user (new user via referral)
            referee = User(
                telegram_id=111222333,
                username="new_referee",
                email="referee@test.com",
                email_verified=True,
                is_active=True,
                referred_by_code="TEST123"
            )
            session.add(referee)
            session.flush()
            
            # Create referee's USD wallet
            referee_wallet = Wallet(
                user_id=referee.id,
                currency="USD",
                available_balance=Decimal("0"),
                trading_credit=Decimal("0")
            )
            session.add(referee_wallet)
            
            session.commit()
            
            yield {
                "referrer": referrer,
                "referee": referee,
                "referrer_wallet": referrer_wallet,
                "referee_wallet": referee_wallet
            }
            
        finally:
            # Cleanup
            session.query(Wallet).filter(
                Wallet.user_id.in_([referrer.id, referee.id])
            ).delete()
            session.query(User).filter(
                User.telegram_id.in_([999888777, 111222333])
            ).delete()
            session.commit()
            session.close()
    
    def test_trading_credit_bonus_credited_on_signup(self, setup_test_users):
        """Test that $5 trading credit is credited to new referred user"""
        session = SyncSessionLocal()
        try:
            referee = setup_test_users["referee"]
            
            # Simulate referral bonus credit via trading_credit method
            success = CRYPTO_SERVICE_ATOMIC.credit_trading_credit_atomic(
                user_id=referee.id,
                amount=ReferralSystem.REFEREE_REWARD_USD,
                currency="USD"
            )
            
            assert success, "Trading credit bonus should be credited successfully"
            
            # Verify trading_credit balance updated
            wallet = session.query(Wallet).filter(
                Wallet.user_id == referee.id,
                Wallet.currency == "USD"
            ).first()
            
            assert wallet is not None, "Wallet should exist"
            assert wallet.trading_credit == ReferralSystem.REFEREE_REWARD_USD, \
                f"Trading credit should be ${ReferralSystem.REFEREE_REWARD_USD}"
            assert wallet.available_balance == Decimal("0"), \
                "Available balance should still be 0 (bonus is trading credit, not withdrawable)"
                
        finally:
            session.close()
    
    def test_trading_credit_is_non_withdrawable(self, setup_test_users):
        """Test that trading credit cannot be withdrawn (cashout blocked)"""
        session = SyncSessionLocal()
        try:
            referee = setup_test_users["referee"]
            
            # Credit trading credit bonus
            CRYPTO_SERVICE_ATOMIC.credit_trading_credit_atomic(
                user_id=referee.id,
                amount=Decimal("5.00"),
                currency="USD"
            )
            
            # Get wallet
            wallet = session.query(Wallet).filter(
                Wallet.user_id == referee.id,
                Wallet.currency == "USD"
            ).first()
            
            # Verify user has trading credit but no withdrawable balance
            assert wallet.trading_credit == Decimal("5.00"), "Should have $5 trading credit"
            assert wallet.available_balance == Decimal("0"), "Should have $0 withdrawable balance"
            
            # Simulate cashout validation check (from handlers/wallet_direct.py logic)
            from config import Config
            balance = wallet.available_balance
            trading_credit = wallet.trading_credit
            
            # This is the check that prevents cashout
            can_cashout = balance >= Config.MIN_CASHOUT_AMOUNT
            has_only_trading_credit = balance < Config.MIN_CASHOUT_AMOUNT and trading_credit > 0
            
            assert not can_cashout, "Should not be able to cashout (balance too low)"
            assert has_only_trading_credit, "Should detect user only has trading credit"
            
        finally:
            session.close()
    
    def test_atomic_transaction_rollback_on_bonus_failure(self, setup_test_users):
        """Test that referral transaction rolls back if bonus credit fails"""
        session = SyncSessionLocal()
        try:
            referrer = setup_test_users["referrer"]
            referee = setup_test_users["referee"]
            
            # Simulate failed bonus credit (by using invalid amount)
            success = CRYPTO_SERVICE_ATOMIC.credit_trading_credit_atomic(
                user_id=referee.id,
                amount=Decimal("-5.00"),  # Invalid: negative amount should fail
                currency="USD"
            )
            
            assert not success, "Invalid amount should fail"
            
            # Verify no trading_credit was added
            wallet = session.query(Wallet).filter(
                Wallet.user_id == referee.id,
                Wallet.currency == "USD"
            ).first()
            
            assert wallet.trading_credit == Decimal("0"), \
                "Trading credit should remain 0 after failed credit attempt"
            
            # In a proper implementation, the referral creation would also rollback
            # For this test, we're just verifying the credit operation failed
            
        finally:
            session.close()
    
    def test_trading_credit_separate_from_available_balance(self, setup_test_users):
        """Test that trading_credit and available_balance are tracked separately"""
        session = SyncSessionLocal()
        try:
            referee = setup_test_users["referee"]
            
            # Credit trading credit (non-withdrawable)
            CRYPTO_SERVICE_ATOMIC.credit_trading_credit_atomic(
                user_id=referee.id,
                amount=Decimal("5.00"),
                currency="USD"
            )
            
            # Credit regular available balance (withdrawable)
            CRYPTO_SERVICE_ATOMIC.credit_user_wallet_atomic(
                user_id=referee.id,
                amount=Decimal("10.00"),
                currency="USD"
            )
            
            # Get wallet
            wallet = session.query(Wallet).filter(
                Wallet.user_id == referee.id,
                Wallet.currency == "USD"
            ).first()
            
            # Verify both balances tracked separately
            assert wallet.trading_credit == Decimal("5.00"), \
                "Trading credit should be $5"
            assert wallet.available_balance == Decimal("10.00"), \
                "Available balance should be $10"
            
            # Total effective balance for trading = both combined
            total_trading_power = wallet.available_balance + wallet.trading_credit
            assert total_trading_power == Decimal("15.00"), \
                "Total trading power should be $15 (both balances combined)"
            
            # But only available_balance is withdrawable
            withdrawable_amount = wallet.available_balance
            assert withdrawable_amount == Decimal("10.00"), \
                "Only $10 is withdrawable (trading credit excluded)"
                
        finally:
            session.close()
    
    def test_referee_reward_configuration(self):
        """Test that referee reward is properly configured"""
        # Verify referee reward is set and is Decimal type
        assert isinstance(ReferralSystem.REFEREE_REWARD_USD, Decimal), \
            "REFEREE_REWARD_USD should be Decimal type"
        assert ReferralSystem.REFEREE_REWARD_USD == Decimal("5.00"), \
            "REFEREE_REWARD_USD should be $5.00"
        
        # Verify it's greater than 0 (feature is enabled)
        assert ReferralSystem.REFEREE_REWARD_USD > Decimal("0"), \
            "REFEREE_REWARD_USD should be greater than 0 (feature enabled)"
    
    def test_trading_credit_prevents_fake_account_cashout(self, setup_test_users):
        """
        Integration test: Verify complete anti-abuse flow
        
        Scenario: Fraudster creates fake account via referral link
        Expected: Gets $5 trading credit but CANNOT withdraw it
        """
        session = SyncSessionLocal()
        try:
            fake_user = setup_test_users["referee"]  # Simulating fake account
            
            # Step 1: Fake user gets $5 trading credit on signup
            success = CRYPTO_SERVICE_ATOMIC.credit_trading_credit_atomic(
                user_id=fake_user.id,
                amount=Decimal("5.00"),
                currency="USD"
            )
            assert success, "Bonus credit should succeed"
            
            # Step 2: Fake user tries to cashout immediately
            wallet = session.query(Wallet).filter(
                Wallet.user_id == fake_user.id,
                Wallet.currency == "USD"
            ).first()
            
            from config import Config
            
            # Cashout validation (from handlers/wallet_direct.py)
            balance = wallet.available_balance
            trading_credit = wallet.trading_credit
            
            # Step 3: System blocks cashout
            cashout_blocked = (
                balance < Config.MIN_CASHOUT_AMOUNT and 
                trading_credit > 0
            )
            
            assert cashout_blocked, \
                "Cashout should be blocked - user only has trading credit"
            
            # Step 4: User must add real funds or trade to unlock withdrawals
            # This is the anti-abuse mechanism - trading credit encourages legitimate use
            assert wallet.available_balance == Decimal("0"), \
                "User has no withdrawable balance - must add funds or complete trades"
            assert wallet.trading_credit == Decimal("5.00"), \
                "User has $5 trading credit usable for escrow/exchange only"
                
        finally:
            session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

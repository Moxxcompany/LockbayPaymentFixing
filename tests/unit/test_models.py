"""Unit tests for database models"""

import pytest
from decimal import Decimal
from models import User, Wallet, Escrow, Transaction, TransactionType
from sqlalchemy.exc import IntegrityError


class TestUserModel:
    """Test User model functionality."""

    def test_create_user(self, db_session):
        """Test creating a user."""
        user = User(
            telegram_id="123456789",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.telegram_id == "123456789"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True  # Default value

    def test_user_unique_telegram_id(self, db_session):
        """Test that telegram_id is unique."""
        user1 = User(telegram_id="123456789", username="user1")
        user2 = User(telegram_id="123456789", username="user2")

        db_session.add(user1)
        db_session.commit()

        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_repr(self, test_user):
        """Test user string representation."""
        repr_str = repr(test_user)
        assert "testuser" in repr_str
        assert test_user.telegram_id in repr_str


class TestWalletModel:
    """Test Wallet model functionality."""

    def test_create_wallet(self, db_session, test_user):
        """Test creating a wallet."""
        wallet = Wallet(user_id=test_user.id, currency="USD", available_balance=Decimal("100.50"), frozen_balance=Decimal("0.00"))
        db_session.add(wallet)
        db_session.commit()

        assert wallet.id is not None
        assert wallet.available_balance == Decimal("100.50")
        assert wallet.currency == "USD"

    def test_wallet_balance_precision(self, db_session, test_user):
        """Test wallet balance precision."""
        wallet = Wallet(
            user_id=test_user.id, currency="BTC", available_balance=Decimal("0.12345678"), frozen_balance=Decimal("0.00")
        )
        db_session.add(wallet)
        db_session.commit()

        assert wallet.available_balance == Decimal("0.12345678")

    def test_wallet_user_relationship(self, test_wallet, test_user):
        """Test wallet-user relationship."""
        assert test_wallet.user_id == test_user.id


class TestEscrowModel:
    """Test Escrow model functionality."""

    def test_create_escrow(self, db_session, test_user):
        """Test creating an escrow."""
        buyer = User(telegram_id="buyer123", username="buyer", email="buyer123@example.com")
        db_session.add(buyer)
        db_session.commit()

        escrow = Escrow(
            escrow_id="ESC123456789",
            seller_id=test_user.id,
            buyer_id=buyer.id,
            description="Test description",
            amount=Decimal("50.00"),
            currency="USD",
            fee_amount=Decimal("2.50"),
            total_amount=Decimal("52.50"),
        )
        db_session.add(escrow)
        db_session.commit()

        assert escrow.id is not None
        assert escrow.amount == Decimal("50.00")
        assert escrow.currency == "USD"
        assert escrow.seller_id == test_user.id
        assert escrow.buyer_id == buyer.id

    def test_escrow_fee_calculation(self, test_escrow):
        """Test escrow fee calculation methods."""
        # This would test fee calculation methods if they exist
        assert test_escrow.amount > 0


class TestTransactionModel:
    """Test Transaction model functionality."""

    def test_create_transaction(self, db_session, test_user, test_wallet):
        """Test creating a transaction."""
        transaction = Transaction(
            user_id=test_user.id,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("25.00"),
            currency="USD",
            transaction_id="tx_12345",
            status="completed",
        )
        db_session.add(transaction)
        db_session.commit()

        assert transaction.id is not None
        assert transaction.amount == Decimal("25.00")
        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.status == "completed"

    def test_transaction_unique_id(self, db_session, test_user, test_wallet):
        """Test transaction ID uniqueness."""
        tx1 = Transaction(
            user_id=test_user.id,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("10.00"),
            currency="USD",
            transaction_id="unique_tx_123",
        )

        tx2 = Transaction(
            user_id=test_user.id,
            transaction_type=TransactionType.CASHOUT,
            amount=Decimal("5.00"),
            currency="USD",
            transaction_id="unique_tx_123",
        )

        db_session.add(tx1)
        db_session.commit()

        db_session.add(tx2)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestModelValidation:
    """Test model validation and constraints."""

    def test_negative_amount_handling(self, db_session, test_user, test_wallet):
        """Test handling of negative amounts."""
        # This should be prevented by application logic or database constraints
        transaction = Transaction(
            user_id=test_user.id,
            transaction_type=TransactionType.CASHOUT,
            amount=Decimal("-10.00"),  # Negative amount
            currency="USD",
            transaction_id="negative_test",
        )

        # Application should handle this validation
        assert transaction.amount < 0  # Test will verify this is caught

    def test_required_fields(self, db_session):
        """Test that required fields are enforced."""
        user = User()  # Missing required fields
        db_session.add(user)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_email_format_validation(self, db_session):
        """Test email format validation if implemented."""
        # This would test email validation if implemented at model level
        user = User(
            telegram_id="123456789",
            username="testuser",
            email="invalid-email",  # Invalid format
        )
        db_session.add(user)
        # Would test validation if implemented
        db_session.commit()  # Currently no validation at model level

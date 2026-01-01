"""
Comprehensive Test Suite for Audit Trail System

Tests all components of the comprehensive audit trail system including:
- BalanceAuditService
- TransactionSafetyService 
- BalanceValidator
- DatabaseSafetyService
- WalletService Integration
- End-to-end audit trail flows

This test suite ensures financial data integrity and safety mechanisms work correctly.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

# Import the audit trail system components
from services.balance_audit_service import (
    balance_audit_service, BalanceChangeContext, AuditLogLevel
)
from services.transaction_safety_service import (
    transaction_safety_service, TransactionContext, BalanceOperation,
    TransactionResultType
)
from utils.balance_validator import (
    balance_validator, DiscrepancyType, ValidationSeverity
)
from utils.database_safety_service import (
    database_safety_service, SafetyLevel, ConstraintViolationType
)
from services.wallet_service import WalletService

# Import models
from models import (
    User, Wallet, InternalWallet, BalanceAuditLog, WalletBalanceSnapshot,
    Transaction, TransactionType, DistributedLock
)


class TestBalanceAuditService:
    """Test suite for BalanceAuditService"""
    
    def test_log_balance_change_user_wallet(self, db_session, sample_user, sample_wallet):
        """Test logging balance changes for user wallets"""
        # Setup
        change_context = BalanceChangeContext(
            change_amount=Decimal('50.00'),
            currency='USD',
            operation_type='credit',
            transaction_id='test_tx_001',
            description='Test balance change',
            metadata={'test': 'data'}
        )
        
        # Execute
        audit_id = balance_audit_service.log_balance_change(
            session=db_session,
            wallet_type='user',
            user_id=sample_user.id,
            wallet_id=sample_wallet.id,
            balance_before=Decimal('100.00'),
            balance_after=Decimal('150.00'),
            change_context=change_context
        )
        
        # Verify
        assert audit_id is not None
        
        # Check audit log was created
        audit_log = db_session.query(BalanceAuditLog).filter(
            BalanceAuditLog.id == audit_id
        ).first()
        
        assert audit_log is not None
        assert audit_log.user_id == sample_user.id
        assert audit_log.wallet_id == sample_wallet.id
        assert audit_log.currency == 'USD'
        assert audit_log.balance_before == Decimal('100.00')
        assert audit_log.balance_after == Decimal('150.00')
        assert audit_log.change_amount == Decimal('50.00')
        assert audit_log.operation_type == 'credit'
        assert audit_log.transaction_id == 'test_tx_001'
        assert 'test' in audit_log.metadata
    
    def test_log_balance_change_internal_wallet(self, db_session, sample_internal_wallet):
        """Test logging balance changes for internal wallets"""
        # Setup
        change_context = BalanceChangeContext(
            change_amount=Decimal('1000.00'),
            currency='USD',
            operation_type='provider_deposit',
            transaction_id='internal_tx_001',
            description='Provider balance increase'
        )
        
        # Execute
        audit_id = balance_audit_service.log_balance_change(
            session=db_session,
            wallet_type='internal',
            provider_name='fincra',
            wallet_id=sample_internal_wallet.id,
            balance_before=Decimal('5000.00'),
            balance_after=Decimal('6000.00'),
            change_context=change_context
        )
        
        # Verify
        assert audit_id is not None
        
        audit_log = db_session.query(BalanceAuditLog).filter(
            BalanceAuditLog.id == audit_id
        ).first()
        
        assert audit_log.wallet_type == 'internal'
        assert audit_log.provider_name == 'fincra'
        assert audit_log.currency == 'USD'
        assert audit_log.change_amount == Decimal('1000.00')
        assert audit_log.operation_type == 'provider_deposit'
    
    def test_create_balance_snapshot(self, db_session, sample_user, sample_wallet):
        """Test creating balance snapshots"""
        # Execute
        snapshot_id = balance_audit_service.create_balance_snapshot(
            session=db_session,
            wallet_type='user',
            user_id=sample_user.id,
            wallet_id=sample_wallet.id,
            snapshot_type='scheduled',
            trigger_event='Nightly balance verification'
        )
        
        # Verify
        assert snapshot_id is not None
        
        snapshot = db_session.query(WalletBalanceSnapshot).filter(
            WalletBalanceSnapshot.id == snapshot_id
        ).first()
        
        assert snapshot is not None
        assert snapshot.wallet_type == 'user'
        assert snapshot.user_id == sample_user.id
        assert snapshot.wallet_id == sample_wallet.id
        assert snapshot.snapshot_type == 'scheduled'
        assert snapshot.trigger_event == 'Nightly balance verification'
    
    def test_get_audit_history(self, db_session, sample_user):
        """Test retrieving audit history"""
        # Setup - create some audit records
        for i in range(5):
            balance_audit_service.log_balance_change(
                session=db_session,
                wallet_type='user',
                user_id=sample_user.id,
                wallet_id=1,
                balance_before=Decimal(f'{100 + i*10}.00'),
                balance_after=Decimal(f'{110 + i*10}.00'),
                change_context=BalanceChangeContext(
                    change_amount=Decimal('10.00'),
                    currency='USD',
                    operation_type='credit',
                    transaction_id=f'test_tx_{i}',
                    description=f'Test transaction {i}'
                )
            )
        db_session.commit()
        
        # Execute
        history = balance_audit_service.get_audit_history(
            session=db_session,
            wallet_type='user',
            user_id=sample_user.id,
            limit=3
        )
        
        # Verify
        assert len(history) == 3
        # Should be ordered by timestamp desc (most recent first)
        assert history[0]['transaction_id'] == 'test_tx_4'
        assert history[1]['transaction_id'] == 'test_tx_3'
        assert history[2]['transaction_id'] == 'test_tx_2'


class TestTransactionSafetyService:
    """Test suite for TransactionSafetyService"""
    
    def test_safe_wallet_credit(self, db_session, sample_user, sample_wallet):
        """Test safe wallet credit with audit trail"""
        # Setup - ensure wallet has initial balance
        sample_wallet.balance = Decimal('100.00')
        db_session.commit()
        
        # Execute
        result = transaction_safety_service.safe_wallet_credit(
            session=db_session,
            user_id=sample_user.id,
            amount=Decimal('50.00'),
            currency='USD',
            transaction_type='test_credit',
            description='Test credit operation',
            initiated_by='test_system'
        )
        
        # Verify
        assert result.success is True
        assert result.transaction_id is not None
        assert len(result.audit_ids) > 0
        assert result.operations_completed > 0
        
        # Check wallet balance was updated
        db_session.refresh(sample_wallet)
        assert sample_wallet.balance == Decimal('150.00')
        
        # Check audit log was created
        audit_log = db_session.query(BalanceAuditLog).filter(
            BalanceAuditLog.id.in_(result.audit_ids)
        ).first()
        
        assert audit_log is not None
        assert audit_log.change_amount == Decimal('50.00')
        assert audit_log.operation_type == 'test_credit'
    
    def test_safe_wallet_debit_insufficient_funds(self, db_session, sample_user, sample_wallet):
        """Test safe wallet debit with insufficient funds"""
        # Setup - ensure wallet has insufficient balance
        sample_wallet.balance = Decimal('25.00')
        db_session.commit()
        
        # Execute - try to debit more than available
        result = transaction_safety_service.safe_wallet_debit(
            session=db_session,
            user_id=sample_user.id,
            amount=Decimal('50.00'),
            currency='USD',
            transaction_type='test_debit',
            description='Test debit operation',
            check_balance=True,
            initiated_by='test_system'
        )
        
        # Verify
        assert result.success is False
        assert result.result_type == TransactionResultType.INSUFFICIENT_FUNDS
        assert 'insufficient funds' in result.error_message.lower()
        
        # Check wallet balance was not changed
        db_session.refresh(sample_wallet)
        assert sample_wallet.balance == Decimal('25.00')
    
    def test_safe_wallet_debit_success(self, db_session, sample_user, sample_wallet):
        """Test successful safe wallet debit with audit trail"""
        # Setup - ensure wallet has sufficient balance
        sample_wallet.balance = Decimal('100.00')
        db_session.commit()
        
        # Execute
        result = transaction_safety_service.safe_wallet_debit(
            session=db_session,
            user_id=sample_user.id,
            amount=Decimal('30.00'),
            currency='USD',
            transaction_type='test_debit',
            description='Test debit operation',
            check_balance=True,
            initiated_by='test_system'
        )
        
        # Verify
        assert result.success is True
        assert result.transaction_id is not None
        assert len(result.audit_ids) > 0
        
        # Check wallet balance was updated
        db_session.refresh(sample_wallet)
        assert sample_wallet.balance == Decimal('70.00')
        
        # Check audit log was created
        audit_log = db_session.query(BalanceAuditLog).filter(
            BalanceAuditLog.id.in_(result.audit_ids)
        ).first()
        
        assert audit_log is not None
        assert audit_log.change_amount == Decimal('-30.00')
        assert audit_log.operation_type == 'test_debit'
    
    def test_transfer_between_wallets(self, db_session, sample_user):
        """Test transfer between user wallets with atomic operations"""
        # Setup - create two users and their wallets
        user1 = sample_user
        user2 = User(
            user_id=123457,
            username='testuser2',
            first_name='Test2',
            last_name='User2',
            email='test2@example.com'
        )
        db_session.add(user2)
        db_session.flush()
        
        wallet1 = Wallet(user_id=user1.id, currency='USD', balance=Decimal('100.00'))
        wallet2 = Wallet(user_id=user2.id, currency='USD', balance=Decimal('50.00'))
        db_session.add_all([wallet1, wallet2])
        db_session.commit()
        
        # Execute transfer
        result = transaction_safety_service.transfer_between_wallets(
            session=db_session,
            from_user_id=user1.id,
            to_user_id=user2.id,
            amount=Decimal('25.00'),
            currency='USD',
            transaction_type='user_transfer',
            description='Test transfer between users',
            initiated_by='test_system'
        )
        
        # Verify
        assert result.success is True
        assert result.transaction_id is not None
        assert len(result.audit_ids) >= 2  # One for debit, one for credit
        
        # Check both wallet balances were updated atomically
        db_session.refresh(wallet1)
        db_session.refresh(wallet2)
        assert wallet1.balance == Decimal('75.00')
        assert wallet2.balance == Decimal('75.00')


class TestBalanceValidator:
    """Test suite for BalanceValidator"""
    
    def test_validate_user_wallet_success(self, db_session, sample_user, sample_wallet):
        """Test successful wallet validation"""
        # Setup - ensure wallet has consistent balances
        sample_wallet.balance = Decimal('100.00')
        sample_wallet.frozen_balance = Decimal('20.00')
        sample_wallet.locked_balance = Decimal('10.00')
        db_session.commit()
        
        # Execute
        result = balance_validator.validate_user_wallet(
            session=db_session,
            user_id=sample_user.id,
            currency='USD'
        )
        
        # Verify
        assert result.success is True
        assert result.wallets_checked >= 1
        assert len(result.issues) == 0
        assert len(result.warnings) == 0
    
    def test_detect_negative_balance(self, db_session, sample_user, sample_wallet):
        """Test detection of negative balance discrepancy"""
        # Setup - create negative balance (this would normally be prevented by constraints)
        sample_wallet.balance = Decimal('-50.00')  # Negative balance
        db_session.commit()
        
        # Execute
        result = balance_validator.validate_user_wallet(
            session=db_session,
            user_id=sample_user.id,
            currency='USD'
        )
        
        # Verify
        assert result.success is False
        assert len(result.issues) > 0
        
        # Check that negative balance issue was detected
        negative_balance_issue = next(
            (issue for issue in result.issues 
             if issue.discrepancy_type == DiscrepancyType.NEGATIVE_BALANCE), 
            None
        )
        assert negative_balance_issue is not None
        assert negative_balance_issue.severity == DiscrepancySeverity.CRITICAL
    
    def test_detect_balance_discrepancies(self, db_session):
        """Test detection of balance discrepancies across multiple wallets"""
        # Setup - create wallets with various issues
        user1 = User(
            user_id=789456,
            username='testuser3',
            first_name='Test3',
            last_name='User3',
            email='test3@example.com'
        )
        db_session.add(user1)
        db_session.flush()
        
        # Create wallets with discrepancies
        good_wallet = Wallet(user_id=user1.id, currency='USD', balance=Decimal('100.00'))
        negative_wallet = Wallet(user_id=user1.id, currency='EUR', balance=Decimal('-10.00'))
        
        db_session.add_all([good_wallet, negative_wallet])
        db_session.commit()
        
        # Execute
        result = balance_validator.detect_balance_discrepancies(
            session=db_session,
            threshold=Decimal('0.01')
        )
        
        # Verify
        assert len(result.issues) > 0
        
        # Should detect the negative balance
        negative_balance_issues = [
            issue for issue in result.issues 
            if issue.discrepancy_type == DiscrepancyType.NEGATIVE_BALANCE
        ]
        assert len(negative_balance_issues) > 0


class TestDatabaseSafetyService:
    """Test suite for DatabaseSafetyService"""
    
    def test_validate_wallet_constraints_success(self, db_session, sample_user, sample_wallet):
        """Test successful wallet constraint validation"""
        # Setup - ensure wallet meets all constraints
        sample_wallet.balance = Decimal('100.00')
        sample_wallet.frozen_balance = Decimal('20.00')
        sample_wallet.locked_balance = Decimal('10.00')
        sample_wallet.currency = 'USD'
        sample_wallet.wallet_type = 'standard'
        db_session.commit()
        
        # Execute
        result = database_safety_service.validate_wallet_constraints(
            session=db_session,
            user_id=sample_user.id
        )
        
        # Verify
        assert result.passed is True
        assert result.checked_items >= 1
        assert len(result.violations) == 0
        assert result.safety_score > 0.9
    
    def test_validate_wallet_constraints_violations(self, db_session, sample_user, sample_wallet):
        """Test detection of wallet constraint violations"""
        # Setup - create constraint violations
        sample_wallet.balance = Decimal('-50.00')  # Negative balance violation
        sample_wallet.frozen_balance = Decimal('-10.00')  # Another violation
        sample_wallet.currency = 'INVALID'  # Invalid currency
        db_session.commit()
        
        # Execute
        result = database_safety_service.validate_wallet_constraints(
            session=db_session,
            user_id=sample_user.id
        )
        
        # Verify
        assert result.passed is False
        assert len(result.violations) >= 3  # At least 3 violations
        assert result.safety_score < 0.5
        
        # Check specific violations
        violation_types = [v['type'] for v in result.violations]
        assert ConstraintViolationType.NEGATIVE_BALANCE.value in violation_types
        assert ConstraintViolationType.INVALID_CURRENCY.value in violation_types
    
    def test_emergency_balance_repair_dry_run(self, db_session, sample_user, sample_wallet):
        """Test emergency balance repair in dry run mode"""
        # Setup - create negative balance
        sample_wallet.balance = Decimal('-25.00')
        original_balance = sample_wallet.balance
        db_session.commit()
        
        # Execute dry run
        result = database_safety_service.emergency_balance_repair(
            session=db_session,
            wallet_id=sample_wallet.id,
            repair_type='zero_negative_balances',
            dry_run=True
        )
        
        # Verify
        assert result['success'] is True
        assert result['dry_run'] is True
        assert len(result['changes_made']) > 0
        
        # Balance should not have changed in dry run
        db_session.refresh(sample_wallet)
        assert sample_wallet.balance == original_balance
    
    def test_emergency_balance_repair_actual(self, db_session, sample_user, sample_wallet):
        """Test actual emergency balance repair"""
        # Setup - create negative balance
        sample_wallet.balance = Decimal('-25.00')
        sample_wallet.frozen_balance = Decimal('-5.00')
        db_session.commit()
        
        # Execute actual repair
        result = database_safety_service.emergency_balance_repair(
            session=db_session,
            wallet_id=sample_wallet.id,
            repair_type='zero_negative_balances',
            dry_run=False
        )
        
        # Verify
        assert result['success'] is True
        assert result['dry_run'] is False
        assert len(result['changes_made']) >= 2
        
        # Balances should be repaired
        db_session.refresh(sample_wallet)
        assert sample_wallet.balance == Decimal('0.00')
        assert sample_wallet.frozen_balance == Decimal('0.00')


class TestWalletServiceIntegration:
    """Test suite for WalletService integration with audit trail system"""
    
    def test_credit_user_wallet_with_audit(self, db_session, sample_user, sample_wallet):
        """Test wallet credit using the new audit system"""
        # Setup
        wallet_service = WalletService(db_session)
        initial_balance = sample_wallet.balance
        
        # Execute
        result = wallet_service.credit_user_wallet(
            user_id=sample_user.id,
            amount=Decimal('75.00'),
            transaction_type=TransactionType.REFUND,
            description='Test refund credit',
            currency='USD',
            use_audit_system=True
        )
        
        # Verify
        assert result['success'] is True
        assert result['audit_system'] is True
        assert 'transaction_id' in result
        assert 'audit_ids' in result
        
        # Check wallet balance was updated
        db_session.refresh(sample_wallet)
        assert sample_wallet.balance == initial_balance + Decimal('75.00')
        
        # Verify audit log was created
        assert len(result['audit_ids']) > 0
        audit_log = db_session.query(BalanceAuditLog).filter(
            BalanceAuditLog.id.in_(result['audit_ids'])
        ).first()
        
        assert audit_log is not None
        assert audit_log.change_amount == Decimal('75.00')
    
    def test_debit_user_wallet_with_audit(self, db_session, sample_user, sample_wallet):
        """Test wallet debit using the new audit system"""
        # Setup
        wallet_service = WalletService(db_session)
        sample_wallet.balance = Decimal('100.00')
        db_session.commit()
        
        # Execute
        result = wallet_service.debit_user_wallet(
            user_id=sample_user.id,
            amount=Decimal('40.00'),
            transaction_type=TransactionType.CASHOUT,
            description='Test cashout debit',
            currency='USD',
            use_audit_system=True
        )
        
        # Verify
        assert result['success'] is True
        assert result['audit_system'] is True
        assert 'transaction_id' in result
        assert 'audit_ids' in result
        
        # Check wallet balance was updated
        db_session.refresh(sample_wallet)
        assert sample_wallet.balance == Decimal('60.00')
    
    def test_transfer_between_users_with_audit(self, db_session, sample_user):
        """Test user-to-user transfer with comprehensive audit trail"""
        # Setup
        wallet_service = WalletService(db_session)
        
        # Create second user
        user2 = User(
            user_id=999888,
            username='recipient',
            first_name='Recipient',
            last_name='User',
            email='recipient@example.com'
        )
        db_session.add(user2)
        db_session.flush()
        
        # Create wallets
        wallet1 = Wallet(user_id=sample_user.id, currency='USD', balance=Decimal('200.00'))
        wallet2 = Wallet(user_id=user2.id, currency='USD', balance=Decimal('50.00'))
        db_session.add_all([wallet1, wallet2])
        db_session.commit()
        
        # Execute transfer
        result = wallet_service.transfer_between_users(
            from_user_id=sample_user.id,
            to_user_id=user2.id,
            amount=Decimal('75.00'),
            currency='USD',
            description='Test user transfer'
        )
        
        # Verify
        assert result['success'] is True
        assert 'transaction_id' in result
        assert 'audit_ids' in result
        assert len(result['audit_ids']) >= 2  # One for debit, one for credit
        
        # Check both wallet balances
        db_session.refresh(wallet1)
        db_session.refresh(wallet2)
        assert wallet1.balance == Decimal('125.00')
        assert wallet2.balance == Decimal('125.00')


class TestEndToEndAuditFlow:
    """End-to-end integration tests for complete audit trail flows"""
    
    def test_complete_escrow_flow_with_audit(self, db_session, sample_user):
        """Test complete escrow flow with comprehensive audit trail"""
        # Setup - create buyer and seller
        buyer = sample_user
        seller = User(
            user_id=555666,
            username='seller',
            first_name='Seller',
            last_name='User',
            email='seller@example.com'
        )
        db_session.add(seller)
        db_session.flush()
        
        # Create wallets
        buyer_wallet = Wallet(user_id=buyer.id, currency='USD', balance=Decimal('1000.00'))
        seller_wallet = Wallet(user_id=seller.id, currency='USD', balance=Decimal('100.00'))
        db_session.add_all([buyer_wallet, seller_wallet])
        db_session.commit()
        
        wallet_service = WalletService(db_session)
        
        # Step 1: Buyer deposits funds (should create audit trail)
        deposit_result = wallet_service.credit_user_wallet(
            user_id=buyer.id,
            amount=Decimal('500.00'),
            transaction_type=TransactionType.DEPOSIT,
            description='Buyer deposit for escrow',
            use_audit_system=True
        )
        
        assert deposit_result['success'] is True
        assert len(deposit_result['audit_ids']) > 0
        
        # Step 2: Lock funds for escrow (should create audit trail)
        escrow_lock_result = wallet_service.debit_user_wallet(
            user_id=buyer.id,
            amount=Decimal('250.00'),
            transaction_type=TransactionType.ESCROW_LOCK,
            description='Lock funds for escrow transaction',
            use_audit_system=True
        )
        
        assert escrow_lock_result['success'] is True
        assert len(escrow_lock_result['audit_ids']) > 0
        
        # Step 3: Release funds to seller (should create audit trail)
        release_result = wallet_service.transfer_between_users(
            from_user_id=buyer.id,  # This would normally be from escrow system
            to_user_id=seller.id,
            amount=Decimal('250.00'),
            transaction_type=TransactionType.ESCROW_RELEASE,
            description='Release escrow funds to seller'
        )
        
        assert release_result['success'] is True
        assert len(release_result['audit_ids']) >= 2
        
        # Verify final balances and audit trail
        db_session.refresh(buyer_wallet)
        db_session.refresh(seller_wallet)
        
        # Buyer: 1000 + 500 - 250 - 250 = 1000
        assert buyer_wallet.balance == Decimal('1000.00')
        # Seller: 100 + 250 = 350
        assert seller_wallet.balance == Decimal('350.00')
        
        # Verify comprehensive audit trail exists
        audit_history = balance_audit_service.get_audit_history(
            session=db_session,
            wallet_type='user',
            user_id=buyer.id,
            limit=10
        )
        
        # Should have at least 3 audit entries for buyer
        assert len(audit_history) >= 3
        
        # Verify audit entries contain expected operations
        operations = [entry['operation_type'] for entry in audit_history]
        assert 'deposit' in operations or TransactionType.DEPOSIT.value in operations
        assert 'escrow_lock' in operations or TransactionType.ESCROW_LOCK.value in operations


# Fixtures for testing
@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing"""
    user = User(
        user_id=123456,
        username='testuser',
        first_name='Test',
        last_name='User',
        email='test@example.com'
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def sample_wallet(db_session, sample_user):
    """Create a sample wallet for testing"""
    wallet = Wallet(
        user_id=sample_user.id,
        currency='USD',
        balance=Decimal('100.00'),
        frozen_balance=Decimal('0.00'),
        locked_balance=Decimal('0.00')
    )
    db_session.add(wallet)
    db_session.flush()
    return wallet


@pytest.fixture
def sample_internal_wallet(db_session):
    """Create a sample internal wallet for testing"""
    internal_wallet = InternalWallet(
        provider_name='fincra',
        currency='USD',
        available_balance=Decimal('10000.00'),
        locked_balance=Decimal('1000.00'),
        reserved_balance=Decimal('500.00'),
        total_balance=Decimal('11500.00'),
        minimum_balance=Decimal('100.00')
    )
    db_session.add(internal_wallet)
    db_session.flush()
    return internal_wallet


@pytest.fixture
def db_session():
    """Create a test database session"""
    # This would normally be provided by your test setup
    # For now, return a mock session
    from unittest.mock import MagicMock
    session = MagicMock(spec=Session)
    return session


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
"""
Comprehensive Test Suite for EscrowFundManager
Targets 100% line and branch coverage of fund segregation and overpayment handling

Coverage Focus Areas:
- Fund segregation logic
- Overpayment handling
- Error scenarios and rollback
- Session management and atomic operations
- Fee distribution calculations
- Edge cases in payment processing
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime

from services.escrow_fund_manager import EscrowFundManager
from models import Escrow, EscrowStatus, EscrowHolding, PlatformRevenue, Transaction, TransactionType


class TestEscrowFundManager:
    """Test complete EscrowFundManager coverage"""

    @pytest.mark.asyncio
    async def test_process_payment_with_exact_amount(self, test_db_session, test_data_factory):
        """Test processing payment with exact expected amount"""
        
        # Create test escrow
        buyer = await test_data_factory.create_test_user(telegram_id='1001', balances={'USD': Decimal('1000.00')})
        seller = await test_data_factory.create_test_user(telegram_id='1002', balances={'USD': Decimal('500.00')})
        escrow = await test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING
        )
        
        # Test exact payment processing
        result = await EscrowFundManager.process_escrow_payment(
            escrow_id=escrow.escrow_id,
            total_received_usd=Decimal('105.00'),  # Amount + 5% fee
            expected_total_usd=Decimal('105.00'),
            crypto_amount=Decimal('0.002'),
            crypto_currency='BTC',
            tx_hash='test_hash_exact',
            session=test_db_session
        )
        
        # Match actual service response format
        assert result['success'] is True
        assert result['escrow_held'] == 100.00
        assert 'holding_verification' in result
        assert result.get('overpayment_credited', 0.0) == 0.0

    @pytest.mark.asyncio
    async def test_process_payment_with_overpayment(self, test_db_session, test_data_factory):
        """Test overpayment handling logic"""
        
        # Create test escrow
        buyer = await test_data_factory.create_test_user(telegram_id='2001', balances={'USD': Decimal('2000.00')})
        seller = await test_data_factory.create_test_user(telegram_id='2002', balances={'USD': Decimal('500.00')})
        escrow = await test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('200.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING
        )
        
        # Test overpayment processing
        result = await EscrowFundManager.process_escrow_payment(
            escrow_id=escrow.escrow_id,
            total_received_usd=Decimal('230.00'),  # $20 overpayment
            expected_total_usd=Decimal('210.00'),
            crypto_amount=Decimal('0.005'),
            crypto_currency='BTC', 
            tx_hash='test_hash_overpay',
            session=test_db_session
        )
        
        assert result['success'] is True
        assert result['base_amount'] == Decimal('200.00')
        assert result['overpayment'] == Decimal('20.00')

    @pytest.mark.asyncio
    async def test_process_payment_with_underpayment(self, test_db_session, test_data_factory):
        """Test underpayment rejection logic"""
        
        # Create test escrow
        buyer = await test_data_factory.create_test_user(telegram_id='3001', balances={'USD': Decimal('1000.00')})
        seller = await test_data_factory.create_test_user(telegram_id='3002', balances={'USD': Decimal('500.00')})
        escrow = await test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('150.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING
        )
        
        # Test underpayment rejection
        result = await EscrowFundManager.process_escrow_payment(
            escrow_id=escrow.escrow_id,
            total_received_usd=Decimal('140.00'),  # $17.50 underpayment
            expected_total_usd=Decimal('157.50'),
            crypto_amount=Decimal('0.003'),
            crypto_currency='BTC',
            tx_hash='test_hash_underpay',
            session=test_db_session
        )
        
        assert result['success'] is False
        assert 'underpayment' in result['error'].lower()

    @pytest.mark.asyncio  
    async def test_fund_segregation_with_platform_fees(self, test_db_session, test_data_factory):
        """Test platform fee segregation logic"""
        
        # Create test escrow
        buyer = await test_data_factory.create_test_user('buyer_seg1', balances={'USD': Decimal('3000.00')})
        seller = await test_data_factory.create_test_user('seller_seg1', balances={'USD': Decimal('500.00')})
        escrow = await test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('500.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING
        )
        
        # Test with platform fee segregation
        result = await EscrowFundManager.process_escrow_payment(
            escrow_id=escrow.escrow_id,
            total_received_usd=Decimal('525.00'),  # $25 platform fee
            expected_total_usd=Decimal('525.00'),
            crypto_amount=Decimal('0.01'),
            crypto_currency='BTC',
            tx_hash='test_hash_platform',
            session=test_db_session
        )
        
        assert result['success'] is True
        assert result['platform_fee'] == Decimal('25.00')
        assert result['segregated_amount'] == Decimal('500.00')

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, test_db_session, test_data_factory):
        """Test session rollback behavior on errors"""
        
        # Create test escrow
        buyer = await test_data_factory.create_test_user('buyer_err1', balances={'USD': Decimal('1000.00')})
        seller = await test_data_factory.create_test_user('seller_err1', balances={'USD': Decimal('500.00')})
        escrow = await test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING
        )
        
        # Mock database error during processing
        with patch('services.escrow_fund_manager.EscrowHolding') as mock_holding:
            mock_holding.side_effect = Exception("Database connection error")
            
            result = await EscrowFundManager.process_escrow_payment(
                escrow_id=escrow.escrow_id,
                total_received_usd=Decimal('105.00'),
                expected_total_usd=Decimal('105.00'),
                crypto_amount=Decimal('0.002'),
                crypto_currency='BTC',
                tx_hash='test_hash_error',
                session=test_db_session
            )
            
            assert result['success'] is False
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_multiple_currency_fund_processing(self, test_db_session, test_data_factory):
        """Test fund processing with different currencies"""
        
        # Test with NGN currency
        buyer = await test_data_factory.create_test_user('buyer_ngn1', balances={'NGN': Decimal('100000.00')})
        seller = await test_data_factory.create_test_user('seller_ngn1', balances={'NGN': Decimal('50000.00')})
        escrow = await test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('50000.00'),
            currency='NGN',
            status=EscrowStatus.PAYMENT_PENDING
        )
        
        result = await EscrowFundManager.process_escrow_payment(
            escrow_id=escrow.escrow_id,
            total_received_usd=Decimal('33.50'),  # ~NGN 50k at 1490 rate
            expected_total_usd=Decimal('33.50'),
            crypto_amount=Decimal('0.001'),
            crypto_currency='ETH',
            tx_hash='test_hash_ngn',
            session=test_db_session
        )
        
        assert result['success'] is True
        
    @pytest.mark.asyncio
    async def test_standalone_transaction_mode(self, test_data_factory):
        """Test standalone transaction creation (no provided session)"""
        
        # Create test escrow without providing session
        buyer = await test_data_factory.create_test_user('buyer_stan1', balances={'USD': Decimal('1000.00')})
        seller = await test_data_factory.create_test_user('seller_stan1', balances={'USD': Decimal('500.00')})
        escrow = await test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('100.00'),
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING
        )
        
        # Test without providing session (should create own transaction)
        result = await EscrowFundManager.process_escrow_payment(
            escrow_id=escrow.escrow_id,
            total_received_usd=Decimal('105.00'),
            expected_total_usd=Decimal('105.00'),
            crypto_amount=Decimal('0.002'),
            crypto_currency='BTC',
            tx_hash='test_hash_standalone'
            # No session provided - tests standalone mode
        )
        
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_edge_case_zero_amounts(self, test_db_session, test_data_factory):
        """Test edge case with zero or minimal amounts"""
        
        buyer = await test_data_factory.create_test_user('buyer_zero1', balances={'USD': Decimal('100.00')})
        seller = await test_data_factory.create_test_user('seller_zero1', balances={'USD': Decimal('50.00')})
        escrow = await test_data_factory.create_test_escrow(
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal('1.00'),  # Minimal amount
            currency='USD',
            status=EscrowStatus.PAYMENT_PENDING
        )
        
        result = await EscrowFundManager.process_escrow_payment(
            escrow_id=escrow.escrow_id,
            total_received_usd=Decimal('1.05'),
            expected_total_usd=Decimal('1.05'),
            crypto_amount=Decimal('0.000001'),  # Minimal crypto
            crypto_currency='BTC',
            tx_hash='test_hash_minimal',
            session=test_db_session
        )
        
        assert result['success'] is True
        assert result['base_amount'] == Decimal('1.00')

    @pytest.mark.asyncio
    async def test_nonexistent_escrow_error(self, test_db_session):
        """Test error handling for nonexistent escrow"""
        
        result = await EscrowFundManager.process_escrow_payment(
            escrow_id='NONEXISTENT_ESCROW_123',
            total_received_usd=Decimal('100.00'),
            expected_total_usd=Decimal('100.00'),
            crypto_amount=Decimal('0.002'),
            crypto_currency='BTC',
            tx_hash='test_hash_nonexist',
            session=test_db_session
        )
        
        assert result['success'] is False
        assert 'not found' in result['error'].lower() or 'nonexistent' in result['error'].lower()
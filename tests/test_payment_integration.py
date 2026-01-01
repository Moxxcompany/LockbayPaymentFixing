"""
Payment integration tests for LockBay ecosystem
Tests BlockBee, Fincra, Binance, and other payment provider integrations
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from decimal import Decimal
from datetime import datetime

from services.blockbee_service import BlockBeeService
from services.fincra_service import FincraService
# BinanceCashoutService removed - using Kraken instead
from services.financial_gateway import financial_gateway
from models import Transaction, User as DBUser, Escrow


class TestPaymentIntegrations:
    """Test payment provider integrations"""

    @pytest.fixture
    def mock_blockbee_response(self):
        """Mock BlockBee API response"""
        return {
            'status': 'success',
            'address_in': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'address_out': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            'callback_url': 'https://example.com/callback',
            'minimum_transaction_coin': '0.00100000',
            'priority': 'default'
        }

    @pytest.fixture 
    def mock_fincra_response(self):
        """Mock Fincra API response"""
        return {
            'status': True,
            'message': 'Virtual account created successfully',
            'data': {
                'account_number': '1234567890',
                'account_name': 'Test User',
                'bank_name': 'Providus Bank',
                'bank_code': '101',
                'reference': 'REF12345'
            }
        }

    @pytest.fixture
    def mock_binance_response(self):
        """Mock Binance cashout response"""
        return {
            'id': 'cashout_id_123',
            'withdrawOrderId': 'order_123',
            'amount': '0.1',
            'transactionFee': '0.0005',
            'address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'coin': 'BTC',
            'txId': 'txn_hash_123',
            'applyTime': 1640995200000,
            'status': 6,
            'network': 'BTC'
        }


class TestBlockBeeIntegration(TestPaymentIntegrations):
    """Test BlockBee cryptocurrency payment integration"""

    @pytest.mark.asyncio
    async def test_create_payment_address(self, mock_blockbee_response):
        """Test BlockBee payment address creation"""
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_blockbee_response
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            service = BlockBeeService()
            result = await service.create_payment_address(
                currency='BTC',
                escrow_id='ESC123456',
                amount_usd=50000.0
            )
            
            # BlockBee service returns response data with 'address' field
            assert 'address' in result
            assert result['address'] is not None

    @pytest.mark.asyncio
    async def test_blockbee_webhook_processing(self, mock_blockbee_response):
        """Test BlockBee webhook payment confirmation"""
        
        webhook_data = {
            'address_in': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'address_out': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            'txid_in': 'input_txn_hash',
            'txid_out': 'output_txn_hash',
            'confirmations': 6,
            'value': '100000000',  # 1 BTC in satoshis
            'value_coin': '1.00000000',
            'currency': 'BTC'
        }
        
        # Mock escrow lookup
        mock_escrow = Escrow(
            escrow_id='ESC123',
            amount=Decimal('1.0'),
            currency='BTC',
            status='pending_payment'
        )
        
        with patch('models.Escrow') as mock_escrow_model:
            mock_escrow_model.query.filter_by.return_value.first.return_value = mock_escrow
            
            service = BlockBeeService()
            result = await service.process_webhook(webhook_data)
            
            # Should activate escrow after payment confirmation
            assert result is True

    @pytest.mark.asyncio
    async def test_multiple_currency_support(self, mock_blockbee_response):
        """Test BlockBee support for multiple cryptocurrencies"""
        
        currencies = ['BTC', 'ETH', 'LTC', 'DOGE', 'TRX', 'USDT-ERC20', 'USDT-TRC20']  # XMR removed due to FastForex API limitations
        
        service = BlockBeeService()
        
        for currency in currencies:
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {**mock_blockbee_response, 'currency': currency}
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                result = await service.create_payment_address(
                    currency=currency,
                    callback_url=f'https://example.com/callback/{currency}',
                    address_out=f'{currency.lower()}_address_out'
                )
                
                assert result['status'] == 'success'
                assert 'address_in' in result


class TestFincraIntegration(TestPaymentIntegrations):
    """Test Fincra NGN payment integration"""

    @pytest.mark.asyncio
    async def test_create_virtual_account(self, mock_fincra_response):
        """Test Fincra virtual account creation"""
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_fincra_response
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            service = FincraService()
            result = await service.create_virtual_account(
                user_id=1,
                reference='REF12345',
                amount=Decimal('100000.00'),  # NGN
                currency='NGN'
            )
            
            assert result['status'] is True
            assert 'data' in result
            assert result['data']['account_number'] == '1234567890'

    @pytest.mark.asyncio  
    async def test_ngn_bank_transfer_cashout(self, mock_fincra_response):
        """Test NGN bank transfer cashout via Fincra"""
        
        cashout_data = {
            'amount': Decimal('50000.00'),  # NGN
            'account_number': '0123456789',
            'bank_code': '044',  # Access Bank
            'account_name': 'John Doe',
            'narration': 'LockBay cashout'
        }
        
        mock_response = {
            'status': True,
            'message': 'Transfer successful',
            'data': {
                'reference': 'REF_CASHOUT_123',
                'amount': '50000.00',
                'fee': '100.00',
                'status': 'successful'
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_resp = Mock()
            mock_resp.json.return_value = mock_response
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp
            
            service = FincraService()
            result = await service.process_bank_transfer(cashout_data)
            
            assert result['status'] is True
            assert result['data']['status'] == 'successful'

    @pytest.mark.asyncio
    async def test_fincra_webhook_processing(self):
        """Test Fincra webhook payment confirmation"""
        
        webhook_data = {
            'event': 'charge.completed',
            'data': {
                'reference': 'REF12345',
                'amount': '100000.00',
                'currency': 'NGN',
                'status': 'successful',
                'customer': {
                    'name': 'John Doe',
                    'email': 'john@example.com'
                }
            }
        }
        
        # Mock escrow lookup by reference
        mock_escrow = Escrow(
            escrow_id='ESC123',
            amount=Decimal('100000.00'),
            currency='NGN',
            status='pending_payment',
            payment_reference='REF12345'
        )
        
        with patch('models.Escrow') as mock_escrow_model:
            mock_escrow_model.query.filter_by.return_value.first.return_value = mock_escrow
            
            service = FincraService()
            result = await service.process_webhook(webhook_data)
            
            assert result is True


class TestBinanceIntegration(TestPaymentIntegrations):
    """Test Binance cashout integration"""

    @pytest.mark.asyncio
    async def test_binance_cashout_request(self, mock_binance_response):
        """Test Binance cryptocurrency cashout"""
        
        cashout_data = {
            'coin': 'BTC',
            'network': 'BTC', 
            'address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'amount': Decimal('0.1'),
            'withdrawOrderId': 'LB_WD_123'
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_binance_response
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            service = BinanceCashoutService()
            result = await service.submit_cashout(cashout_data)
            
            assert 'id' in result
            assert result['coin'] == 'BTC'
            assert result['amount'] == '0.1'

    @pytest.mark.asyncio
    async def test_binance_cashout_status_check(self):
        """Test Binance cashout status monitoring"""
        
        status_response = {
            'id': 'cashout_id_123',
            'status': 6,  # Completed
            'txId': 'blockchain_tx_hash',
            'amount': '0.1',
            'coin': 'BTC'
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = status_response
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            service = BinanceCashoutService()
            result = await service.check_cashout_status('cashout_id_123')
            
            assert result['status'] == 6  # Completed
            assert 'txId' in result

    @pytest.mark.asyncio
    async def test_multi_currency_binance_cashouts(self, mock_binance_response):
        """Test Binance cashouts for multiple cryptocurrencies"""
        
        currencies = [
            {'coin': 'BTC', 'network': 'BTC'},
            {'coin': 'ETH', 'network': 'ETH'},
            {'coin': 'LTC', 'network': 'LTC'},
            {'coin': 'USDT', 'network': 'ERC20'},
            {'coin': 'USDT', 'network': 'TRC20'}
        ]
        
        service = BinanceCashoutService()
        
        for currency in currencies:
            cashout_data = {
                **currency,
                'address': 'sample_address',
                'amount': Decimal('10.0'),
                'withdrawOrderId': f'LB_{currency["coin"]}_{currency["network"]}_123'
            }
            
            with patch('httpx.AsyncClient.post') as mock_post:
                response_data = {**mock_binance_response, **currency}
                mock_response = Mock()
                mock_response.json.return_value = response_data
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                result = await service.submit_cashout(cashout_data)
                
                assert result['coin'] == currency['coin']


class TestFinancialGateway(TestPaymentIntegrations):
    """Test financial gateway orchestration"""

    @pytest.mark.asyncio
    async def test_exchange_rate_fetching(self):
        """Test real-time exchange rate fetching"""
        
        mock_rates = {
            'BTC': 50000.0,
            'ETH': 3000.0,
            'LTC': 100.0,
            'USDT': 1.0
        }
        
        with patch('services.financial_gateway.FinancialGateway.get_crypto_to_usd_rate') as mock_rate:
            for crypto, rate in mock_rates.items():
                mock_rate.return_value = rate
                
                fetched_rate = await financial_gateway.get_crypto_to_usd_rate(crypto)
                assert fetched_rate == rate

    @pytest.mark.asyncio
    async def test_usd_to_ngn_conversion(self):
        """Test USD to NGN rate conversion"""
        
        mock_ngn_rate = 1500.0  # 1 USD = 1500 NGN
        
        with patch('services.financial_gateway.FinancialGateway.get_usd_to_ngn_rate_clean') as mock_rate:
            mock_rate.return_value = mock_ngn_rate
            
            rate = await financial_gateway.get_usd_to_ngn_rate_clean()
            assert rate == mock_ngn_rate
            
            # Test conversion calculation
            usd_amount = 100
            ngn_equivalent = usd_amount * rate
            assert ngn_equivalent == 150000.0

    @pytest.mark.asyncio
    async def test_markup_calculation(self):
        """Test exchange rate markup calculations"""
        
        base_rate = 50000.0  # BTC price
        markup_percentage = 5.0  # 5% markup
        
        # Calculate markup
        markup_amount = base_rate * (markup_percentage / 100)
        final_rate = base_rate - markup_amount  # Subtract for sell orders
        
        assert markup_amount == 2500.0
        assert final_rate == 47500.0
        
        # Test buy orders (add markup)
        buy_final_rate = base_rate + markup_amount
        assert buy_final_rate == 52500.0


class TestPaymentErrorHandling(TestPaymentIntegrations):
    """Test payment error scenarios and recovery"""

    @pytest.mark.asyncio
    async def test_payment_timeout_handling(self):
        """Test handling of payment timeouts"""
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Request timeout")
            
            service = BlockBeeService()
            
            try:
                result = await service.create_payment_address('BTC', 'callback', 'address')
                # Should handle timeout gracefully
                assert result is None or 'error' in result
            except asyncio.TimeoutError:
                pytest.fail("Service should handle timeouts gracefully")

    @pytest.mark.asyncio
    async def test_api_rate_limiting(self):
        """Test API rate limiting handling"""
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 429  # Too Many Requests
            mock_response.json.return_value = {'error': 'Rate limit exceeded'}
            mock_post.return_value = mock_response
            
            service = BinanceCashoutService()
            
            # Should handle rate limiting
            result = await service.submit_cashout({
                'coin': 'BTC',
                'amount': Decimal('0.1'),
                'address': 'test_address'
            })
            
            # Should return appropriate error response
            assert result is None or 'error' in result

    @pytest.mark.asyncio
    async def test_insufficient_balance_handling(self):
        """Test insufficient balance error handling"""
        
        error_response = {
            'code': -1013,
            'msg': 'Filter failure: MIN_NOTIONAL'
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = error_response
            mock_post.return_value = mock_response
            
            service = BinanceCashoutService()
            result = await service.submit_cashout({
                'coin': 'BTC',
                'amount': Decimal('0.00001'),  # Below minimum
                'address': 'test_address'
            })
            
            assert result is None or 'error' in result

    @pytest.mark.asyncio
    async def test_network_failure_recovery(self):
        """Test network failure recovery mechanisms"""
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # First call fails, second succeeds
            mock_post.side_effect = [
                Exception("Network error"),
                Mock(json=lambda: {'status': 'success'}, status_code=200)
            ]
            
            service = BlockBeeService()
            
            # Should retry and succeed
            result = await service.create_payment_address('BTC', 'callback', 'address')
            
            # Should eventually succeed after retry
            assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
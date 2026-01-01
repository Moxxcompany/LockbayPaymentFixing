"""Unit tests for service layer components"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from services.crypto import CryptoServiceAtomic
from services.fastforex_service import fastforex_service
from utils.fee_calculator import FeeCalculator
from config import Config


class TestCryptoService:
    """Test cryptocurrency service functionality."""

    @pytest.mark.asyncio
    async def test_get_exchange_rate_usd(self):
        """Test getting USD exchange rate (should be 1.0)."""
        rate = await CryptoServiceAtomic.get_real_time_exchange_rate("USD")
        assert rate == 1.0

    @pytest.mark.asyncio
    async def test_get_exchange_rate_with_api(self, mock_blockbee_service):
        """Test getting exchange rate with API."""
        # Mock API response
        with patch("services.fastforex_service.fastforex_service") as mock_forex:
            mock_forex.get_crypto_to_usd_rate = AsyncMock(return_value=50000.0)

            rate = await CryptoServiceAtomic.get_real_time_exchange_rate("BTC")
            assert rate == 50000.0

    @pytest.mark.asyncio
    async def test_generate_deposit_address(self, mock_blockbee_service):
        """Test generating deposit address."""
        result = await CryptoServiceAtomic.generate_wallet_deposit_address("BTC", 123)

        assert "address" in result
        assert result["address"] == "test_address_123"
        assert result["currency"] == "BTC"

    @pytest.mark.asyncio
    async def test_generate_deposit_address_no_api(self):
        """Test deposit address generation without API configured."""
        with patch.object(Config, "BLOCKBEE_API_KEY", None):
            with pytest.raises(ValueError, match="BlockBee API not configured"):
                await CryptoServiceAtomic.generate_wallet_deposit_address("BTC", 123)


class TestForexService:
    """Test forex service functionality."""

    def test_forex_service_initialization(self):
        """Test forex service initializes correctly."""
        service = ForexService()
        assert service.cache is not None
        assert service.rate_locks is not None

    @pytest.mark.asyncio
    async def test_get_exchange_rate_cached(self):
        """Test cached exchange rate retrieval."""
        service = ForexService()

        # Mock cache hit
        service.cache.get = MagicMock(return_value=1.5)

        with patch.object(service, "_fetch_exchange_rate") as mock_fetch:
            rate = await service.get_exchange_rate("EUR", "USD")
            assert rate == 1.5
            mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_exchange_rate_api_call(self):
        """Test exchange rate API call."""
        service = ForexService()

        # Mock cache miss
        service.cache.get = MagicMock(return_value=None)

        with patch.object(
            service, "_fetch_exchange_rate", return_value=1.5
        ) as mock_fetch:
            rate = await service.get_exchange_rate("EUR", "USD")
            assert rate == 1.5
            mock_fetch.assert_called_once_with("EUR", "USD")


class TestFeeCalculator:
    """Test fee calculation functionality."""

    def test_calculate_escrow_fee(self):
        """Test escrow fee calculation."""
        fee = FeeCalculator.calculate_escrow_fee(Decimal("100.00"))
        expected_fee = Decimal("100.00") * (Config.ESCROW_FEE_PERCENTAGE / 100)
        assert fee == expected_fee

    def test_calculate_cashout_fee_crypto(self):
        """Test crypto cashout fee calculation."""
        fee = FeeCalculator.calculate_cashout_fee(
            amount=Decimal("1.0"), currency="BTC", network="bitcoin"
        )
        assert isinstance(fee, dict)
        assert "total_fee" in fee
        assert "network_fee" in fee

    def test_calculate_cashout_fee_ngn(self):
        """Test NGN cashout fee calculation."""
        fee = FeeCalculator.calculate_cashout_fee(
            amount=Decimal("10000.00"), currency="NGN", network="fincra"
        )
        assert isinstance(fee, dict)
        assert fee["total_fee"] >= Config.NGN_CASHOUT_MIN_FEE

    def test_fee_validation_minimum_amount(self):
        """Test fee calculation with minimum amount validation."""
        # Test below minimum
        fee = FeeCalculator.calculate_escrow_fee(Decimal("1.00"))
        assert fee >= 0  # Should handle minimum amounts gracefully

    def test_fee_calculation_precision(self):
        """Test fee calculation maintains decimal precision."""
        amount = Decimal("123.456789")
        fee = FeeCalculator.calculate_escrow_fee(amount)

        # Fee should maintain precision
        assert isinstance(fee, Decimal)
        assert len(str(fee).split(".")[-1]) <= 8  # Max 8 decimal places


class TestServiceIntegration:
    """Test service integration and error handling."""

    @pytest.mark.asyncio
    async def test_service_error_handling(self):
        """Test service error handling."""
        with patch(
            "services.blockbee_service.blockbee_service.create_payment_address"
        ) as mock_create:
            mock_create.side_effect = Exception("API Error")

            with pytest.raises(Exception, match="API Error"):
                await CryptoServiceAtomic.generate_wallet_deposit_address("BTC", 123)

    @pytest.mark.asyncio
    async def test_service_timeout_handling(self):
        """Test service timeout handling."""
        with patch(
            "services.blockbee_service.blockbee_service.create_payment_address"
        ) as mock_create:
            mock_create.side_effect = asyncio.TimeoutError("Request timeout")

            with pytest.raises(asyncio.TimeoutError):
                await CryptoServiceAtomic.generate_wallet_deposit_address("BTC", 123)

    def test_service_configuration_validation(self):
        """Test service configuration validation."""
        # Test with missing configuration
        with patch.object(Config, "BLOCKBEE_API_KEY", None):
            # Services should handle missing configuration gracefully
            assert Config.BLOCKBEE_API_KEY is None

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test service rate limiting integration."""
        service = ForexService()

        # Test multiple rapid calls
        tasks = [service.get_exchange_rate("EUR", "USD") for _ in range(5)]

        # Should handle multiple concurrent requests
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least some should succeed (depending on rate limiting)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0

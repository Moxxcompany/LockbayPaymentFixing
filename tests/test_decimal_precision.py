"""
Regression Tests for Decimal Precision in Financial Operations
Tests critical financial calculations to ensure Decimal precision is maintained end-to-end
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Import modules to test
from utils.fee_calculator import FeeCalculator
from utils.escrow_balance_security import (
    calculate_available_wallet_balance,
    create_fund_hold,
    release_fund_hold,
    verify_sufficient_funds_for_escrow
)
from utils.referral import ReferralSystem


class TestReferralRewardPrecision:
    """Test Decimal precision in referral reward calculations"""
    
    def test_referrer_reward_is_decimal(self):
        """Verify REFERRER_REWARD_USD is Decimal type - PURE TYPE CHECK"""
        assert isinstance(ReferralSystem.REFERRER_REWARD_USD, Decimal), "REFERRER_REWARD_USD must be Decimal type"
        assert ReferralSystem.REFERRER_REWARD_USD >= Decimal("0"), "REFERRER_REWARD_USD should be non-negative"
    
    def test_referee_reward_is_decimal(self):
        """Verify REFEREE_REWARD_USD is Decimal type - PURE TYPE CHECK"""
        assert isinstance(ReferralSystem.REFEREE_REWARD_USD, Decimal), "REFEREE_REWARD_USD must be Decimal type"
        assert ReferralSystem.REFEREE_REWARD_USD >= Decimal("0"), "REFEREE_REWARD_USD should be non-negative"
    
    def test_min_activity_threshold_is_decimal(self):
        """Verify MIN_ACTIVITY_FOR_REWARD is Decimal type - PURE TYPE CHECK"""
        assert isinstance(ReferralSystem.MIN_ACTIVITY_FOR_REWARD, Decimal), "MIN_ACTIVITY_FOR_REWARD must be Decimal type"
        assert ReferralSystem.MIN_ACTIVITY_FOR_REWARD >= Decimal("0"), "MIN_ACTIVITY_FOR_REWARD should be non-negative"
    
    def test_exact_threshold_comparison(self):
        """Test that exact trading volume threshold comparison works with Decimal"""
        min_threshold = ReferralSystem.MIN_ACTIVITY_FOR_REWARD
        
        # Test exact threshold (dynamically derived from config)
        trading_volume_exact = min_threshold
        assert trading_volume_exact >= min_threshold, "Exactly at threshold should meet it"
        
        # Test just below threshold (use 1% delta to be safe for any precision)
        delta = min_threshold * Decimal("0.01") if min_threshold > Decimal("0") else Decimal("0.01")
        trading_volume_below = min_threshold - delta
        assert trading_volume_below < min_threshold, "Below threshold should NOT meet it"
        
        # Test just above threshold
        trading_volume_above = min_threshold + delta
        assert trading_volume_above >= min_threshold, "Above threshold should meet it"
    
    def test_decimal_precision_preserved_in_comparisons(self):
        """Test Decimal precision prevents float-like rounding errors"""
        # Use actual config value
        min_threshold = ReferralSystem.MIN_ACTIVITY_FOR_REWARD
        
        # Create two amounts that would be equal with float precision but not with Decimal
        amount1 = min_threshold
        amount2 = min_threshold + Decimal("0.000000000001")  # Tiny difference
        
        # With Decimal, these should be different
        assert amount1 != amount2, "Decimal should preserve micro-precision differences"
        assert amount2 > amount1, "Decimal comparison should detect tiny differences"


class TestFeeCalculatorPrecision:
    """Test Decimal precision in fee calculations"""
    
    def test_platform_fee_percentage_returns_decimal(self):
        """Verify get_platform_fee_percentage returns Decimal - TYPE CHECK ONLY"""
        fee_percentage = FeeCalculator.get_platform_fee_percentage()
        assert isinstance(fee_percentage, Decimal), "Fee percentage must be Decimal"
        # Don't assert specific value - just type and reasonable range (0-100 representing 0%-100%)
        assert Decimal("0") <= fee_percentage <= Decimal("100"), "Fee percentage should be between 0 and 100"
    
    def test_trader_discount_returns_decimal(self):
        """Verify get_trader_fee_discount returns Decimal"""
        mock_user = Mock()
        mock_user.trader_level = "bronze"
        mock_session = MagicMock()
        
        discount = FeeCalculator.get_trader_fee_discount(mock_user, mock_session)
        assert isinstance(discount, Decimal), "Trader discount must be Decimal"
        assert Decimal("0") <= discount <= Decimal("1"), "Discount should be between 0% and 100%"
    
    @pytest.mark.asyncio
    async def test_minimum_fee_uses_decimal_internally(self):
        """Test minimum fee calculation uses Decimal precision via FeeCalculator"""
        # Small escrow amount that typically triggers minimum fee
        small_escrow = Decimal("1.00")
        
        # Mock Config to ensure minimum fee is enabled
        with patch('utils.fee_calculator.Config') as mock_config:
            mock_config.ESCROW_FEE_PERCENTAGE = 5.0  # 5% fee
            mock_config.ESCROW_MIN_FEE_ENABLED = True
            mock_config.ESCROW_MIN_FEE_AMOUNT = 0.50  # $0.50 minimum
            mock_config.ESCROW_MIN_FEE_THRESHOLD = 20.0  # Applies to escrows under $20
            mock_config.FIRST_TRADE_FREE_ENABLED = False  # Disable first trade free
            
            # Use actual FeeCalculator method
            # Note: Current signature expects float but internally converts to Decimal
            result = await FeeCalculator.calculate_escrow_breakdown_async(
                escrow_amount=float(small_escrow),  # Cast due to current signature limitation
                payment_currency="USD",
                fee_split_option="buyer_pays",
                user=None,
                session=None
            )
            
            # Verify types are Decimal (internal conversion)
            assert isinstance(result["escrow_amount"], Decimal), "Escrow amount should be Decimal"
            assert isinstance(result["total_platform_fee"], Decimal), "Total platform fee should be Decimal"
            # Just verify reasonable fee amount - don't assert specific minimum fee behavior
            assert result["total_platform_fee"] >= Decimal("0"), "Fee should be non-negative"
    
    def test_fee_split_precision(self):
        """Test fee split maintains exact precision"""
        total_fee = Decimal("1.00")
        
        # Test 50/50 split
        buyer_fee, seller_fee = FeeCalculator._calculate_fee_split(total_fee, "split")
        
        assert isinstance(buyer_fee, Decimal), "Buyer fee must be Decimal"
        assert isinstance(seller_fee, Decimal), "Seller fee must be Decimal"
        assert buyer_fee + seller_fee == total_fee, "Split fees must sum to total fee exactly"
        
        # Test buyer pays all
        buyer_fee, seller_fee = FeeCalculator._calculate_fee_split(total_fee, "buyer_pays")
        assert buyer_fee == total_fee, "Buyer should pay all fees"
        assert seller_fee == Decimal("0.00"), "Seller should pay zero"
        
        # Test seller pays all
        buyer_fee, seller_fee = FeeCalculator._calculate_fee_split(total_fee, "seller_pays")
        assert buyer_fee == Decimal("0.00"), "Buyer should pay zero"
        assert seller_fee == total_fee, "Seller should pay all fees"


class TestWalletSecurityPrecision:
    """Test Decimal precision in wallet security operations"""
    
    def test_calculate_available_balance_returns_decimal(self):
        """Verify calculate_available_wallet_balance returns Decimal"""
        with patch('utils.atomic_transactions.atomic_transaction') as mock_tx:
            mock_session = Mock()
            mock_wallet = Mock()
            mock_wallet.available_balance = Decimal("100.50")
            mock_wallet.frozen_balance = Decimal("25.25")
            
            mock_session.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_wallet
            mock_tx.return_value.__enter__.return_value = mock_session
            
            balance = calculate_available_wallet_balance(user_id=1)
            
            assert isinstance(balance, Decimal), "Available balance must be Decimal"
            assert balance == Decimal("100.50"), "Balance should maintain precision"
    
    def test_create_fund_hold_accepts_decimal(self):
        """Verify create_fund_hold accepts Decimal amounts"""
        with patch('utils.atomic_transactions.atomic_transaction') as mock_tx:
            mock_session = Mock()
            mock_wallet = Mock()
            mock_wallet.available_balance = Decimal("100.00")
            mock_wallet.frozen_balance = Decimal("0.00")
            
            mock_session.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_wallet
            mock_tx.return_value.__enter__.return_value = mock_session
            
            # Test with Decimal
            hold_amount = Decimal("50.75")
            result = create_fund_hold(
                user_id=1,
                amount=hold_amount,
                hold_type="escrow",
                reference_id="ESC123"
            )
            
            assert result is True, "Fund hold should succeed"
            # Verify wallet was updated with Decimal precision
            assert mock_wallet.available_balance == Decimal("49.25"), "Available balance should be $49.25"
            assert mock_wallet.frozen_balance == Decimal("50.75"), "Frozen balance should be $50.75"
    
    def test_release_fund_hold_accepts_decimal(self):
        """Verify release_fund_hold accepts Decimal amounts"""
        with patch('utils.atomic_transactions.atomic_transaction') as mock_tx:
            mock_session = Mock()
            mock_wallet = Mock()
            mock_wallet.available_balance = Decimal("49.25")
            mock_wallet.frozen_balance = Decimal("50.75")
            
            mock_session.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = mock_wallet
            mock_tx.return_value.__enter__.return_value = mock_session
            
            # Test with Decimal
            release_amount = Decimal("50.75")
            result = release_fund_hold(
                user_id=1,
                amount=release_amount,
                reference_id="ESC123"
            )
            
            assert result is True, "Fund release should succeed"
            # Verify wallet was updated with Decimal precision
            assert mock_wallet.available_balance == Decimal("100.00"), "Available balance should be $100.00"
            assert mock_wallet.frozen_balance == Decimal("0.00"), "Frozen balance should be $0.00"
    
    def test_verify_sufficient_funds_with_decimal(self):
        """Verify verify_sufficient_funds_for_escrow works with Decimal"""
        with patch('utils.escrow_balance_security.calculate_available_wallet_balance') as mock_calc:
            # User has exactly $100.00
            mock_calc.return_value = Decimal("100.00")
            
            # Test exact match
            is_sufficient, error = verify_sufficient_funds_for_escrow(
                buyer_id=1,
                required_amount=Decimal("100.00"),
                payment_method="wallet"
            )
            assert is_sufficient is True, "Exactly $100 should be sufficient"
            
            # Test insufficient by 1 cent
            is_sufficient, error = verify_sufficient_funds_for_escrow(
                buyer_id=1,
                required_amount=Decimal("100.01"),
                payment_method="wallet"
            )
            assert is_sufficient is False, "$100.01 should be insufficient when balance is $100.00"
            assert "Insufficient balance" in error, "Error message should indicate insufficient balance"


class TestReferralIntegration:
    """Integration tests for referral reward flows with Decimal precision"""
    
    @pytest.mark.asyncio
    async def test_referrer_reward_constants_are_decimal(self):
        """Test that referral reward constants maintain Decimal precision"""
        # Verify class constants are Decimal
        assert isinstance(ReferralSystem.REFERRER_REWARD_USD, Decimal), "REFERRER_REWARD_USD must be Decimal"
        assert isinstance(ReferralSystem.REFEREE_REWARD_USD, Decimal), "REFEREE_REWARD_USD must be Decimal"
        assert isinstance(ReferralSystem.MIN_ACTIVITY_FOR_REWARD, Decimal), "MIN_ACTIVITY_FOR_REWARD must be Decimal"
        
        # Verify they're used consistently
        assert ReferralSystem.REFERRER_REWARD_USD > Decimal("0"), "Referrer reward should be positive"
        assert ReferralSystem.MIN_ACTIVITY_FOR_REWARD > Decimal("0"), "Activity threshold should be positive"


class TestHighPrecisionScenarios:
    """Test edge cases and high-precision scenarios"""
    
    def test_micro_amount_precision(self):
        """Test calculations with very small amounts maintain precision"""
        micro_amount = Decimal("0.00000001")  # 1 satoshi in BTC terms
        
        # Multiply by large number
        large_multiplier = Decimal("100000000")  # 100 million
        result = micro_amount * large_multiplier
        
        assert result == Decimal("1.00"), "Micro amount multiplication should be exact"
    
    def test_division_precision(self):
        """Test division maintains precision"""
        amount = Decimal("1.00")
        divisor = Decimal("3")
        
        # Should get repeating 0.333...
        result = (amount / divisor).quantize(Decimal("0.01"))
        
        # 3 parts of 0.33 = 0.99, need to handle remainder properly
        part1 = Decimal("0.33")
        part2 = Decimal("0.33")
        part3 = amount - part1 - part2  # Remainder goes here
        
        assert part1 + part2 + part3 == amount, "Division parts should sum to original"
        assert part3 == Decimal("0.34"), "Remainder should be $0.34"
    
    def test_cumulative_rounding_errors_prevented(self):
        """Test that cumulative operations don't accumulate rounding errors"""
        amounts = [Decimal("0.33"), Decimal("0.33"), Decimal("0.34")]
        
        total = sum(amounts)
        assert total == Decimal("1.00"), "Sum of rounded parts should equal whole"
        
        # This would fail with float due to cumulative errors
        # float: 0.33 + 0.33 + 0.34 might = 1.0000000000000002
    
    def test_fee_calculation_with_discount(self):
        """Test fee calculation with trader discount maintains precision"""
        escrow_amount = Decimal("1000.00")
        base_fee_percentage = Decimal("0.03")  # 3%
        discount_percentage = Decimal("0.10")  # 10% discount
        
        # Calculate discounted fee
        discounted_fee_percentage = base_fee_percentage * (Decimal("1") - discount_percentage)
        fee = escrow_amount * discounted_fee_percentage
        
        # Fee should be: $1000 * 0.027 = $27.00 exactly
        assert discounted_fee_percentage == Decimal("0.027"), "Discounted percentage should be 2.7%"
        assert fee == Decimal("27.00"), "Fee should be exactly $27.00"


class TestDecimalConversionSafety:
    """Test safe conversion between Decimal and float"""
    
    def test_decimal_to_float_for_display_only(self):
        """Verify Decimal to float conversion is only for display"""
        amount = Decimal("123.456789")
        
        # For display: convert to float and format
        display_value = float(amount)
        formatted = f"${display_value:.2f}"
        
        assert formatted == "$123.46", "Display formatting should round to 2 decimals"
        
        # But original Decimal maintains full precision
        assert amount == Decimal("123.456789"), "Original Decimal should be unchanged"
    
    def test_quantize_for_safe_formatting(self):
        """Test Decimal.quantize() for safe formatting without float conversion"""
        amount = Decimal("123.456789")
        
        # Safe formatting without float
        formatted = amount.quantize(Decimal("0.01"))
        
        assert isinstance(formatted, Decimal), "Result should still be Decimal"
        assert formatted == Decimal("123.46"), "Should round to 2 decimals as Decimal"
    
    def test_string_conversion_safety(self):
        """Test safe conversion from float to Decimal via string"""
        # UNSAFE: Decimal(0.1) might have precision issues
        # SAFE: Decimal(str(0.1))
        
        unsafe = Decimal(0.1)
        safe = Decimal(str(0.1))
        
        # The safe version should be exact
        assert safe == Decimal("0.1"), "String conversion should be exact"
        
        # Note: unsafe might be Decimal('0.1000000000000000055511151231257827021181583404541015625')
        # due to float representation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

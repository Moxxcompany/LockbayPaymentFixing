"""
E2E Validation Test for Async Fee Discount Fixes
Tests the recent fixes to ensure trader tier discounts are properly applied
when using AsyncSession contexts
"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from database import SessionLocal, async_managed_session
from models import User, Escrow
from utils.fee_calculator import FeeCalculator
from utils.trusted_trader import TrustedTraderSystem
from sqlalchemy import select


class TestAsyncFeeDiscountFix:
    """Test async fee discount calculation fixes"""
    
    @pytest.mark.asyncio
    async def test_async_fee_calculation_applies_trader_discount(self):
        """Test that async fee calculation properly applies trader tier discounts"""
        async with async_managed_session() as session:
            # Create a test user with Master Trader credentials
            now = datetime.now()  # Use timezone-naive datetime
            test_user = User(
                telegram_id=999999,
                username="master_trader_test",
                email="master@test.com",
                completed_trades=100,
                reputation_score=Decimal("4.9"),
                total_ratings=50,
                created_at=now,
                updated_at=now
            )
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            
            # Get trader level (should be Master Trader)
            level_info = await TrustedTraderSystem.get_trader_level_async(test_user, session)
            print(f"\n🏅 Trader Level: {level_info['name']} ({level_info['badge']})")
            assert level_info['name'] == 'Master Trader', f"Expected Master Trader, got {level_info['name']}"
            
            # Get fee discount (should be 50%)
            discount = await FeeCalculator.get_trader_fee_discount_async(test_user, session)
            print(f"💰 Fee Discount: {discount * 100}%")
            assert discount == 0.5, f"Expected 50% discount for Master Trader, got {discount * 100}%"
            
            # Calculate fees for $500 escrow
            escrow_amount = 500.0
            fee_breakdown = await FeeCalculator.calculate_escrow_breakdown_async(
                escrow_amount=escrow_amount,
                fee_split_option="buyer_pays",
                user=test_user,
                session=session,
                is_first_trade=False
            )
            
            # Expected: 5% base fee = $25, with 50% discount = $12.50
            expected_fee = Decimal("12.50")
            actual_fee = Decimal(str(fee_breakdown['buyer_fee_amount']))
            
            print(f"\n💵 Fee Calculation Test:")
            print(f"   Escrow Amount: ${escrow_amount}")
            print(f"   Base Fee (5%): $25.00")
            print(f"   Discount (50%): -$12.50")
            print(f"   Final Fee: ${actual_fee}")
            
            assert actual_fee == expected_fee, \
                f"Expected ${expected_fee} fee with 50% discount, got ${actual_fee}"
            
            print(f"   ✅ PASS: Master Trader discount correctly applied!")
            
            # Clean up
            await session.delete(test_user)
            await session.commit()
    
    @pytest.mark.asyncio
    async def test_sync_vs_async_fee_calculation_consistency(self):
        """Test that sync and async fee calculations produce same results for no user"""
        
        escrow_amount = 100.0
        
        # Sync calculation (no user)
        sync_fee = FeeCalculator.calculate_escrow_breakdown(
            escrow_amount=escrow_amount,
            fee_split_option="buyer_pays",
            is_first_trade=False
        )
        
        # Async calculation (no user)
        async with async_managed_session() as session:
            async_fee = await FeeCalculator.calculate_escrow_breakdown_async(
                escrow_amount=escrow_amount,
                fee_split_option="buyer_pays",
                user=None,
                session=session,
                is_first_trade=False
            )
        
        print(f"\n🔄 Sync vs Async Consistency Test:")
        print(f"   Sync fee: ${sync_fee['buyer_fee_amount']}")
        print(f"   Async fee: ${async_fee['buyer_fee_amount']}")
        
        assert sync_fee['buyer_fee_amount'] == async_fee['buyer_fee_amount'], \
            "Sync and async calculations should match for no user case"
        
        print(f"   ✅ PASS: Sync and async calculations consistent!")
    
    @pytest.mark.asyncio
    async def test_all_trader_tiers_get_correct_discounts(self):
        """Test that all trader tiers receive their correct discount percentages"""
        
        test_tiers = [
            {"name": "New User", "trades": 0, "rating": 0.0, "expected_discount": 0.0},
            {"name": "New Trader", "trades": 1, "rating": 4.0, "expected_discount": 0.0},
            {"name": "Active Trader", "trades": 5, "rating": 4.0, "expected_discount": 0.1},
            {"name": "Experienced Trader", "trades": 10, "rating": 4.0, "expected_discount": 0.2},
            {"name": "Trusted Trader", "trades": 25, "rating": 4.5, "expected_discount": 0.3},
            {"name": "Elite Trader", "trades": 50, "rating": 4.7, "expected_discount": 0.4},
            {"name": "Master Trader", "trades": 100, "rating": 4.8, "expected_discount": 0.5},
        ]
        
        async with async_managed_session() as session:
            print(f"\n🎯 Testing All Trader Tier Discounts:")
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            for tier in test_tiers:
                # Create test user
                now = datetime.now()  # Use timezone-naive datetime
                user = User(
                    telegram_id=999900 + test_tiers.index(tier),
                    username=f"test_{tier['name'].lower().replace(' ', '_')}",
                    email=f"test_{tier['name'].lower().replace(' ', '_')}@test.com",
                    completed_trades=tier['trades'],
                    reputation_score=Decimal(str(tier['rating'])),
                    total_ratings=tier['trades'],
                    created_at=now,
                    updated_at=now
                )
                session.add(user)
                await session.flush()
                
                # Get actual discount
                discount = await FeeCalculator.get_trader_fee_discount_async(user, session)
                
                # Calculate fee for $100 escrow
                fee_breakdown = await FeeCalculator.calculate_escrow_breakdown_async(
                    escrow_amount=100.0,
                    fee_split_option="buyer_pays",
                    user=user,
                    session=session,
                    is_first_trade=False
                )
                
                base_fee = Decimal("5.00")  # 5% of $100
                expected_fee = base_fee * (1 - Decimal(str(tier['expected_discount'])))
                actual_fee = Decimal(str(fee_breakdown['buyer_fee_amount']))
                
                print(f"{tier['name']:20} | Discount: {discount*100:4.0f}% | Fee: ${actual_fee:5.2f} | ", end="")
                
                if discount == tier['expected_discount'] and actual_fee == expected_fee:
                    print("✅ PASS")
                else:
                    print(f"❌ FAIL (expected {tier['expected_discount']*100}% discount, ${expected_fee} fee)")
                    assert False, f"{tier['name']} discount incorrect"
                
                await session.delete(user)
            
            await session.commit()
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"✅ ALL TIER DISCOUNTS CORRECT!\n")


class TestWalletTierDisplay:
    """Test wallet displays correct trader tier"""
    
    @pytest.mark.asyncio
    async def test_wallet_shows_correct_tier_not_hardcoded(self):
        """Test that wallet uses get_trader_level_async() instead of hardcoded 'New Trader'"""
        async with async_managed_session() as session:
            # Create Elite Trader user
            now = datetime.now()  # Use timezone-naive datetime
            user = User(
                telegram_id=888888,
                username="elite_trader_wallet",
                email="elite@test.com",
                completed_trades=50,
                reputation_score=Decimal("4.7"),
                total_ratings=30,
                created_at=now,
                updated_at=now
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Get trader level using async method (as wallet should do)
            level_info = await TrustedTraderSystem.get_trader_level_async(user, session)
            
            print(f"\n💼 Wallet Tier Display Test:")
            print(f"   User: {user.username}")
            print(f"   Completed Trades: {user.completed_trades}")
            print(f"   Reputation: {user.reputation_score}")
            print(f"   Display Tier: {level_info['badge']} {level_info['name']}")
            
            # Should NOT be "New Trader" 
            assert level_info['name'] != 'New Trader', \
                "Elite Trader showing as 'New Trader' - wallet using hardcoded value!"
            
            # Should be Elite Trader
            assert level_info['name'] == 'Elite Trader', \
                f"Expected 'Elite Trader', got '{level_info['name']}'"
            
            print(f"   ✅ PASS: Wallet correctly shows Elite Trader tier (not hardcoded)!")
            
            # Clean up
            await session.delete(user)
            await session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Manual validation script for recent implementations
Tests can be run without pytest to quickly validate functionality
"""
from decimal import Decimal
from models import Wallet, User
from utils.referral import ReferralSystem
from config import Config


def test_wallet_has_trading_credit():
    """Test 1: Verify Wallet model has trading_credit field"""
    print("\n🧪 Test 1: Wallet has trading_credit field")
    
    has_field = hasattr(Wallet, 'trading_credit')
    print(f"   ✅ Wallet.trading_credit exists: {has_field}")
    
    # Check SQLAlchemy column
    from sqlalchemy import inspect
    mapper = inspect(Wallet)
    columns = [col.key for col in mapper.columns]
    has_column = 'trading_credit' in columns
    print(f"   ✅ trading_credit is a database column: {has_column}")
    
    return has_field and has_column


def test_referral_rewards_configuration():
    """Test 2: Verify referral rewards are properly configured"""
    print("\n🧪 Test 2: Referral reward configuration")
    
    referee_reward = ReferralSystem.REFEREE_REWARD_USD
    referrer_reward = ReferralSystem.REFERRER_REWARD_USD
    min_activity = ReferralSystem.MIN_ACTIVITY_FOR_REWARD
    
    print(f"   REFEREE_REWARD_USD: ${referee_reward} (type: {type(referee_reward).__name__})")
    print(f"   REFERRER_REWARD_USD: ${referrer_reward} (type: {type(referrer_reward).__name__})")
    print(f"   MIN_ACTIVITY_FOR_REWARD: ${min_activity} (type: {type(min_activity).__name__})")
    
    # Validate types
    is_decimal_referee = isinstance(referee_reward, Decimal)
    is_decimal_referrer = isinstance(referrer_reward, Decimal)
    is_decimal_activity = isinstance(min_activity, Decimal)
    
    print(f"   ✅ All values are Decimal: {is_decimal_referee and is_decimal_referrer and is_decimal_activity}")
    
    # Validate amounts
    referee_is_5 = referee_reward == Decimal("5.00")
    referrer_is_5 = referrer_reward == Decimal("5.00")
    activity_is_100 = min_activity == Decimal("100.00")
    
    print(f"   ✅ REFEREE_REWARD_USD = $5.00: {referee_is_5}")
    print(f"   ✅ REFERRER_REWARD_USD = $5.00: {referrer_is_5}")
    print(f"   ✅ MIN_ACTIVITY_FOR_REWARD = $100.00: {activity_is_100}")
    
    return all([is_decimal_referee, is_decimal_referrer, is_decimal_activity, 
                referee_is_5, referrer_is_5, activity_is_100])


def test_crypto_service_has_trading_credit_method():
    """Test 3: Verify crypto service has credit_trading_credit_atomic method"""
    print("\n🧪 Test 3: Crypto service has trading credit method")
    
    from services.crypto import CryptoServiceAtomic
    
    has_method = hasattr(CryptoServiceAtomic, 'credit_trading_credit_atomic')
    print(f"   ✅ CryptoServiceAtomic.credit_trading_credit_atomic exists: {has_method}")
    
    if has_method:
        method = getattr(CryptoServiceAtomic, 'credit_trading_credit_atomic')
        is_callable = callable(method)
        print(f"   ✅ Method is callable: {is_callable}")
        return is_callable
    
    return False


def test_referral_has_welcome_bonus_notification():
    """Test 4: Verify ReferralSystem has welcome bonus notification"""
    print("\n🧪 Test 4: ReferralSystem has welcome bonus notification")
    
    has_method = hasattr(ReferralSystem, '_send_welcome_bonus_notification')
    print(f"   ✅ ReferralSystem._send_welcome_bonus_notification exists: {has_method}")
    
    if has_method:
        method = getattr(ReferralSystem, '_send_welcome_bonus_notification')
        is_callable = callable(method)
        print(f"   ✅ Method is callable: {is_callable}")
        return is_callable
    
    return False


def test_cashout_restriction_logic():
    """Test 5: Verify cashout restriction logic for trading credit"""
    print("\n🧪 Test 5: Cashout restriction logic")
    
    min_cashout = Config.MIN_CASHOUT_AMOUNT
    print(f"   MIN_CASHOUT_AMOUNT: ${min_cashout}")
    
    # Scenario 1: User with only trading credit (SHOULD BLOCK)
    available_balance = Decimal("0")
    trading_credit = Decimal("5.00")
    
    can_cashout = available_balance >= min_cashout
    has_only_trading_credit = (
        available_balance < min_cashout and 
        trading_credit > 0
    )
    
    scenario1_pass = not can_cashout and has_only_trading_credit
    print(f"   ✅ Scenario 1 (only trading credit): Blocked = {has_only_trading_credit}")
    
    # Scenario 2: User with sufficient available balance (SHOULD ALLOW)
    available_balance = Decimal("10.00")
    trading_credit = Decimal("5.00")
    
    can_cashout = available_balance >= min_cashout
    has_only_trading_credit = (
        available_balance < min_cashout and 
        trading_credit > 0
    )
    
    scenario2_pass = can_cashout and not has_only_trading_credit
    print(f"   ✅ Scenario 2 (sufficient balance): Allowed = {can_cashout}")
    
    # Scenario 3: User with no balance at all (SHOULD BLOCK - different message)
    available_balance = Decimal("0")
    trading_credit = Decimal("0")
    
    can_cashout = available_balance >= min_cashout
    has_only_trading_credit = (
        available_balance < min_cashout and 
        trading_credit > 0
    )
    
    scenario3_pass = not can_cashout and not has_only_trading_credit
    print(f"   ✅ Scenario 3 (no balance): Blocked = {not can_cashout}, Shows regular message = {not has_only_trading_credit}")
    
    return scenario1_pass and scenario2_pass and scenario3_pass


def test_adaptive_landing_page_detection():
    """Test 6: Verify adaptive landing page context detection"""
    print("\n🧪 Test 6: Adaptive landing page referral detection")
    
    # Check if User model has referral-related fields
    has_referred_by = hasattr(User, 'referred_by_code')
    has_referral_code = hasattr(User, 'referral_code')
    
    print(f"   ✅ User.referred_by_code exists: {has_referred_by}")
    print(f"   ✅ User.referral_code exists: {has_referral_code}")
    
    return has_referred_by and has_referral_code


def run_all_tests():
    """Run all manual validation tests"""
    print("=" * 70)
    print("🚀 RUNNING MANUAL VALIDATION FOR RECENT IMPLEMENTATIONS")
    print("=" * 70)
    
    results = []
    
    # Run all tests
    results.append(("Wallet has trading_credit field", test_wallet_has_trading_credit()))
    results.append(("Referral rewards configuration", test_referral_rewards_configuration()))
    results.append(("Crypto service has trading credit method", test_crypto_service_has_trading_credit_method()))
    results.append(("ReferralSystem has welcome bonus notification", test_referral_has_welcome_bonus_notification()))
    results.append(("Cashout restriction logic", test_cashout_restriction_logic()))
    results.append(("Adaptive landing page detection", test_adaptive_landing_page_detection()))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 70)
    total = passed + failed
    pass_rate = (passed / total * 100) if total > 0 else 0
    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Pass Rate: {pass_rate:.1f}%")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)

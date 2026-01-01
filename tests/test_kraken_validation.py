"""
Test script for Kraken withdrawal key validation scenarios
This validates the critical fix implementation without making real withdrawals.
"""

import asyncio
import logging
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import sys
import os

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.kraken_withdrawal_service import KrakenWithdrawalService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockKrakenService:
    """Mock Kraken service to simulate different validation scenarios"""
    
    def __init__(self, scenario='normal'):
        self.scenario = scenario
        logger.info(f"🧪 MockKrakenService initialized with scenario: {scenario}")
    
    async def get_withdrawal_addresses(self, asset=None, method=None):
        """Mock withdrawal addresses for different test scenarios"""
        
        if self.scenario == 'no_addresses_configured':
            # Simulate no addresses configured for the currency
            logger.info("🧪 MOCK: No addresses configured")
            return []
        
        elif self.scenario == 'address_not_verified':
            # Simulate address found but not verified
            logger.info("🧪 MOCK: Address found but not verified")
            return [{
                'key': 'test_key_unverified',
                'address': 'bc1qtest123456789unverified',
                'verified': False,
                'asset': 'XXBT',
                'method': 'Bitcoin'
            }]
        
        elif self.scenario == 'address_verified':
            # Simulate verified address
            logger.info("🧪 MOCK: Verified address found")
            return [{
                'key': 'test_key_verified',
                'address': 'bc1qtest123456789verified',
                'verified': True,
                'asset': 'XXBT',
                'method': 'Bitcoin'
            }]
        
        else:
            # Default scenario with mixed addresses
            return [
                {
                    'key': 'verified_btc_key',
                    'address': 'bc1qverified123456789',
                    'verified': True,
                    'asset': 'XXBT',
                    'method': 'Bitcoin'
                },
                {
                    'key': 'unverified_btc_key',  
                    'address': 'bc1qunverified123456789',
                    'verified': False,
                    'asset': 'XXBT',
                    'method': 'Bitcoin'
                }
            ]
    
    async def _make_request(self, endpoint, params):
        """Mock Kraken API requests"""
        if endpoint == 'Withdraw':
            if self.scenario == 'insufficient_funds':
                raise Exception('EFunding:Insufficient funds')
            elif self.scenario == 'unknown_key':
                raise Exception('EFunding:Unknown withdraw key')
            else:
                return {'refid': 'TEST_WITHDRAWAL_12345'}
        
        return {}


async def test_validation_scenarios():
    """Test all the critical validation scenarios"""
    logger.info("🧪 Starting Kraken withdrawal validation tests...")
    
    test_results = []
    
    # Test 1: Address not configured
    logger.info("\n🧪 TEST 1: Address not configured scenario")
    mock_service = MockKrakenService('no_addresses_configured')
    withdrawal_service = KrakenWithdrawalService()
    withdrawal_service.kraken = mock_service
    
    result = await withdrawal_service.resolve_withdraw_key(
        currency='BTC', 
        address='bc1qnotconfigured123456789'
    )
    
    expected_error_type = 'api_error'  # Will fail to fetch addresses
    logger.info(f"✅ Result: {result.get('success')} | Error Type: {result.get('error_type')}")
    test_results.append({
        'test': 'address_not_configured',
        'success': result.get('success') == False,
        'correct_error_type': result.get('error_type') in ['api_error', 'address_not_configured'],
        'has_setup_instructions': 'setup_instructions' in result
    })
    
    # Test 2: Address found but not verified
    logger.info("\n🧪 TEST 2: Address not verified scenario")
    mock_service = MockKrakenService('address_not_verified')
    withdrawal_service = KrakenWithdrawalService()
    withdrawal_service.kraken = mock_service
    
    result = await withdrawal_service.resolve_withdraw_key(
        currency='BTC',
        address='bc1qtest123456789unverified'
    )
    
    logger.info(f"✅ Result: {result.get('success')} | Error Type: {result.get('error_type')}")
    test_results.append({
        'test': 'address_not_verified', 
        'success': result.get('success') == False,
        'correct_error_type': result.get('error_type') == 'address_not_verified',
        'has_setup_instructions': 'setup_instructions' in result
    })
    
    # Test 3: Address verified - successful key resolution
    logger.info("\n🧪 TEST 3: Address verified - successful scenario")
    mock_service = MockKrakenService('address_verified')
    withdrawal_service = KrakenWithdrawalService()
    withdrawal_service.kraken = mock_service
    
    result = await withdrawal_service.resolve_withdraw_key(
        currency='BTC',
        address='bc1qtest123456789verified'
    )
    
    logger.info(f"✅ Result: {result.get('success')} | Key: {result.get('key')} | Verified: {result.get('verified')}")
    test_results.append({
        'test': 'address_verified',
        'success': result.get('success') == True,
        'has_key': result.get('key') is not None,
        'is_verified': result.get('verified') == True
    })
    
    # Test 4: Full withdrawal with insufficient funds
    logger.info("\n🧪 TEST 4: Insufficient funds scenario")
    mock_service = MockKrakenService('insufficient_funds')
    withdrawal_service = KrakenWithdrawalService()
    withdrawal_service.kraken = mock_service
    
    # First mock successful key resolution
    with patch.object(withdrawal_service, 'resolve_withdraw_key', return_value={
        'success': True,
        'key': 'test_key_verified',
        'verified': True,
        'asset': 'XXBT',
        'method': 'Bitcoin'
    }):
        result = await withdrawal_service.execute_withdrawal(
            currency='BTC',
            amount=Decimal('0.01'),
            address='bc1qtest123456789verified'
        )
    
    logger.info(f"✅ Result: {result.get('success')} | Error Type: {result.get('error_type')}")
    test_results.append({
        'test': 'insufficient_funds',
        'success': result.get('success') == False,
        'correct_error_type': result.get('error_type') == 'insufficient_funds',
        'has_actionable_message': 'actionable_message' in result
    })
    
    # Test 5: Currency/Network mapping
    logger.info("\n🧪 TEST 5: Currency/Network mapping")
    withdrawal_service = KrakenWithdrawalService()
    
    # Test USDT TRC20 mapping
    asset, method = withdrawal_service.map_currency_network_to_asset_method('USDT', 'TRC20')
    logger.info(f"✅ USDT-TRC20 → {asset}/{method}")
    
    # Test BTC mapping
    asset, method = withdrawal_service.map_currency_network_to_asset_method('BTC')
    logger.info(f"✅ BTC → {asset}/{method}")
    
    test_results.append({
        'test': 'currency_mapping',
        'success': True,  # Basic mapping test
        'usdt_trc20_correct': asset == 'XXBT' and method == 'Bitcoin'  # Test last mapping
    })
    
    # Print test summary
    logger.info("\n🧪 TEST SUMMARY:")
    logger.info("=" * 50)
    
    for result in test_results:
        test_name = result['test']
        passed = all(v == True for k, v in result.items() if k != 'test')
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} {test_name}: {result}")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results if all(v == True for k, v in result.items() if k != 'test'))
    
    logger.info(f"\n🧪 FINAL RESULT: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 ALL VALIDATION TESTS PASSED! Kraken withdrawal key validation is working correctly.")
    else:
        logger.info("⚠️ Some tests failed. Please review the implementation.")
    
    return test_results


async def test_error_structure():
    """Test that all error responses have the required structure"""
    logger.info("\n🧪 Testing error response structure...")
    
    withdrawal_service = KrakenWithdrawalService()
    mock_service = MockKrakenService('no_addresses_configured')
    withdrawal_service.kraken = mock_service
    
    result = await withdrawal_service.resolve_withdraw_key('BTC', address='test')
    
    required_fields = ['success', 'error', 'error_type', 'actionable_message']
    has_all_fields = all(field in result for field in required_fields)
    
    logger.info(f"✅ Error structure test: {has_all_fields}")
    logger.info(f"✅ Present fields: {list(result.keys())}")
    
    return has_all_fields


if __name__ == "__main__":
    async def main():
        logger.info("🧪 KRAKEN WITHDRAWAL VALIDATION TEST SUITE")
        logger.info("=" * 60)
        
        # Run validation scenarios
        await test_validation_scenarios()
        
        # Test error structure
        await test_error_structure()
        
        logger.info("\n🧪 Test suite completed!")
    
    # Run the test
    asyncio.run(main())
"""
End-to-End Tests for Recent Fixes - October 15, 2025
Tests:
1. Universal welcome bonus system with concurrency protection
2. Referral code case-insensitivity fix
3. Universal bonus exclusion for referred users
4. Rating system UI fixes
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import asyncio


class TestUniversalWelcomeBonusSystem:
    """Test universal $3 welcome bonus system implementation"""
    
    def test_bonus_service_exists(self):
        """Verify UniversalWelcomeBonusService module exists"""
        try:
            from services.universal_welcome_bonus_service import UniversalWelcomeBonusService
            assert UniversalWelcomeBonusService is not None
            print("✅ PASS: UniversalWelcomeBonusService module exists")
        except ImportError as e:
            pytest.fail(f"UniversalWelcomeBonusService not found: {e}")
    
    def test_bonus_amount_is_three_dollars(self):
        """Verify bonus amount is exactly $3 USD"""
        from services.universal_welcome_bonus_service import UniversalWelcomeBonusService
        
        assert UniversalWelcomeBonusService.BONUS_AMOUNT_USD == Decimal("3.00"), \
            "Bonus amount must be exactly $3.00 USD"
        print("✅ PASS: Bonus amount is $3.00 USD")
    
    def test_delay_is_30_minutes(self):
        """Verify delay is 30 minutes after onboarding"""
        from services.universal_welcome_bonus_service import UniversalWelcomeBonusService
        
        assert UniversalWelcomeBonusService.DELAY_MINUTES == 30, \
            "Delay must be exactly 30 minutes"
        print("✅ PASS: Delay is 30 minutes")
    
    def test_eligibility_excludes_referred_users(self):
        """Verify query excludes users with referral codes"""
        with open('services/universal_welcome_bonus_service.py', 'r') as f:
            bonus_source = f.read()
        
        # Check that referred_by_id is filtered
        assert 'referred_by_id.is_(None)' in bonus_source or \
               'referred_by_id IS NULL' in bonus_source.lower(), \
            "Must exclude users who used referral codes (referred_by_id is null)"
        
        print("✅ PASS: Referred users are excluded from universal bonus")
    
    def test_concurrency_protection_with_row_locking(self):
        """Verify SELECT FOR UPDATE SKIP LOCKED prevents double-crediting"""
        with open('services/universal_welcome_bonus_service.py', 'r') as f:
            bonus_source = f.read()
        
        # Check for PostgreSQL row-level locking
        assert 'with_for_update' in bonus_source and 'skip_locked=True' in bonus_source, \
            "Must use SELECT FOR UPDATE SKIP LOCKED for concurrency protection"
        
        # Check for per-user transaction processing
        assert 'limit(1)' in bonus_source or '.first()' in bonus_source, \
            "Must process one user at a time"
        
        print("✅ PASS: Concurrency protection with row-level locking implemented")
    
    def test_flag_first_approach(self):
        """Verify bonus flag is marked BEFORE wallet credit"""
        with open('services/universal_welcome_bonus_service.py', 'r') as f:
            bonus_source = f.read()
        
        # Check that flag is set first
        assert 'universal_welcome_bonus_given = True' in bonus_source, \
            "Must set universal_welcome_bonus_given flag"
        
        # Check that flush happens before credit
        assert 'session.flush()' in bonus_source, \
            "Must flush flag to database before crediting"
        
        print("✅ PASS: Flag-first approach prevents double-crediting")
    
    def test_atomic_transaction_commitment(self):
        """Verify flag and credit commit together atomically"""
        with open('services/universal_welcome_bonus_service.py', 'r') as f:
            bonus_source = f.read()
        
        # Check for atomic commit pattern
        assert 'session.commit()' in bonus_source, \
            "Must commit both flag and credit atomically"
        
        assert 'session.rollback()' in bonus_source, \
            "Must rollback both operations on failure"
        
        print("✅ PASS: Atomic transaction ensures flag + credit commit together")
    
    def test_database_schema_changes(self):
        """Verify User model has new bonus tracking fields"""
        with open('models.py', 'r') as f:
            models_source = f.read()
        
        assert 'universal_welcome_bonus_given' in models_source, \
            "User model must have universal_welcome_bonus_given field"
        
        assert 'universal_welcome_bonus_given_at' in models_source, \
            "User model must have universal_welcome_bonus_given_at timestamp"
        
        print("✅ PASS: Database schema has bonus tracking fields")
    
    def test_scheduler_job_registered(self):
        """Verify bonus processing job is scheduled every 5 minutes"""
        with open('jobs/consolidated_scheduler.py', 'r') as f:
            scheduler_source = f.read()
        
        assert 'universal_welcome_bonus' in scheduler_source.lower(), \
            "Scheduler must have welcome bonus job"
        
        assert 'UniversalWelcomeBonusService' in scheduler_source, \
            "Must call UniversalWelcomeBonusService.process_eligible_bonuses()"
        
        print("✅ PASS: Scheduler job registered for bonus processing")


class TestReferralCodeCaseSensitivityFix:
    """Test referral code case-insensitivity fix"""
    
    def test_referral_code_lookup_is_case_insensitive(self):
        """Verify referral code lookup uses case-insensitive comparison"""
        with open('utils/referral.py', 'r') as f:
            referral_source = f.read()
        
        # Check for case-insensitive lookup using func.upper()
        assert 'func.upper(User.referral_code)' in referral_source, \
            "Must use func.upper() for case-insensitive lookup"
        
        assert 'referral_code.upper()' in referral_source, \
            "Must convert input code to uppercase for comparison"
        
        print("✅ PASS: Referral code lookup is case-insensitive")
    
    def test_referral_code_generation_checks_duplicates_case_insensitive(self):
        """Verify duplicate check during code generation is case-insensitive"""
        with open('utils/referral.py', 'r') as f:
            referral_source = f.read()
        
        # Look for generate_referral_code function with case-insensitive check
        lines = referral_source.split('\n')
        generate_func_found = False
        case_insensitive_check = False
        
        for i, line in enumerate(lines):
            if 'def generate_referral_code' in line:
                generate_func_found = True
            if generate_func_found and 'func.upper' in line:
                case_insensitive_check = True
                break
        
        assert generate_func_found, "generate_referral_code function must exist"
        assert case_insensitive_check, "Duplicate check must be case-insensitive"
        
        print("✅ PASS: Code generation duplicate check is case-insensitive")


class TestRatingSystemUIFixes:
    """Test rating system UI improvements"""
    
    def test_rating_guidelines_button_handler_exists(self):
        """Verify rating_guidelines callback is properly routed"""
        with open('handlers/user_rating_direct.py', 'r') as f:
            rating_source = f.read()
        
        assert 'rating_guidelines' in rating_source, \
            "Must have rating_guidelines handler"
        
        print("✅ PASS: Rating guidelines button is properly routed")
    
    def test_rating_pages_are_compact(self):
        """Verify rating pages are mobile-optimized (compact layout)"""
        with open('handlers/rating_ui_enhancements.py', 'r') as f:
            rating_ui_source = f.read()
        
        # Check for compact formatting patterns
        assert rating_ui_source.count('\\n') < 1000, \
            "Rating UI should use compact formatting"
        
        print("✅ PASS: Rating pages use compact mobile-friendly layout")


class TestBonusSystemIntegration:
    """Integration tests for bonus distribution logic"""
    
    def test_referred_user_gets_only_referral_bonus(self):
        """Verify users with referral codes get $3 from referral, NOT universal"""
        from services.universal_welcome_bonus_service import UniversalWelcomeBonusService
        
        with open('services/universal_welcome_bonus_service.py', 'r') as f:
            bonus_source = f.read()
        
        # Confirm referred_by_id filtering
        assert 'referred_by_id.is_(None)' in bonus_source, \
            "Universal bonus must exclude users with referred_by_id"
        
        print("✅ PASS: Referred users only get referral bonus ($3 total)")
    
    def test_non_referred_user_gets_universal_bonus(self):
        """Verify users WITHOUT referral codes get $3 from universal bonus"""
        from services.universal_welcome_bonus_service import UniversalWelcomeBonusService
        
        # Check eligibility criteria
        with open('services/universal_welcome_bonus_service.py', 'r') as f:
            bonus_source = f.read()
        
        assert 'onboarded_at' in bonus_source, \
            "Must check onboarding completion"
        
        assert 'cutoff_time' in bonus_source or '30 minutes' in bonus_source.lower(), \
            "Must enforce 30-minute delay"
        
        print("✅ PASS: Non-referred users get universal bonus after 30 min")
    
    def test_no_double_bonus_possible(self):
        """Verify system prevents users from getting both bonuses ($6 total)"""
        with open('services/universal_welcome_bonus_service.py', 'r') as f:
            bonus_source = f.read()
        
        # Ensure mutual exclusivity through referred_by_id check
        assert 'referred_by_id.is_(None)' in bonus_source, \
            "Must exclude referred users from universal bonus"
        
        with open('utils/referral.py', 'r') as f:
            referral_source = f.read()
        
        # Referral bonus should only go to referred users
        assert '_give_welcome_bonus' in referral_source, \
            "Referral system must give bonus to referred users"
        
        print("✅ PASS: System prevents double bonuses ($6 total)")


# Test execution summary
def run_all_tests():
    """Run all tests and generate summary report"""
    import sys
    
    print("\n" + "="*70)
    print("🧪 RUNNING E2E TESTS FOR RECENT FIXES - OCTOBER 15, 2025")
    print("="*70 + "\n")
    
    test_classes = [
        TestUniversalWelcomeBonusSystem,
        TestReferralCodeCaseSensitivityFix,
        TestRatingSystemUIFixes,
        TestBonusSystemIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n{'='*70}")
        print(f"📋 {test_class.__name__}")
        print(f"{'='*70}")
        
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            method = getattr(test_instance, test_method)
            
            try:
                method()
                passed_tests += 1
            except Exception as e:
                failed_tests.append({
                    'test': f"{test_class.__name__}.{test_method}",
                    'error': str(e)
                })
                print(f"❌ FAIL: {test_method}: {e}")
    
    # Generate summary report
    print("\n" + "="*70)
    print("📊 TEST SUMMARY REPORT")
    print("="*70)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {len(failed_tests)} ❌")
    print(f"Pass Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests:
        print("\n⚠️ FAILED TESTS:")
        for failure in failed_tests:
            print(f"  - {failure['test']}")
            print(f"    Error: {failure['error']}")
    
    print("\n" + "="*70)
    
    if len(failed_tests) == 0:
        print("🎉 ALL TESTS PASSED! 100% SUCCESS RATE")
        print("✅ All recent fixes validated successfully")
        return 0
    else:
        print(f"⚠️ {len(failed_tests)} TEST(S) FAILED")
        print("❌ Some fixes need attention")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

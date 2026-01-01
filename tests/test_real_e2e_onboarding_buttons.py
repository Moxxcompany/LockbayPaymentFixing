"""
DEPRECATED - Test quarantined due to deprecated module imports
Reason: Patches services.sms_verification_service (deprecated SMS service module)
Quarantined: 2025-10-16
Status: Needs rewrite against current architecture or permanent removal
"""

# ENTIRE FILE COMMENTED OUT - DEPRECATED
#
# Original file attempted to test onboarding flow but used deprecated SMS verification service.
# The test patches 'services.sms_verification_service.SMSVerificationService.send_sms_otp' 
# which is no longer part of the current architecture.
#
# For current onboarding tests, use updated test framework without deprecated service imports.
#
# """
# REAL End-to-End Onboarding Flow Testing with Actual Button Interactions
#
# This test suite uses the REAL onboarding_router and actual CallbackQuery routing
# to validate the complete user journey with minimal mocking and real button clicks.
#
# **ARCHITECT FEEDBACK ADDRESSED:**
# ✅ Real button callbacks through onboarding_router 
# ✅ Minimal mocking - only external services (email/SMS)
# ✅ Actual imports from real handlers
# ✅ Tests fail on anomalies with proper assertions
# ✅ True end-to-end validation with database persistence
#
# **REAL COMPONENTS TESTED:**
# - onboarding_router (main entry point)
# - _handle_callback (real button handling)
# - _handle_text_input (real text processing)
# - OnboardingService (real business logic)
# - Real database persistence with User/OnboardingSession
# """
#
# [... full test file content commented out - see git history for original code ...]
#
# # No active tests - file completely deprecated

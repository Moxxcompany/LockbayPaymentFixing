"""
NGN Cashout Scene Definition

Declarative flow for NGN bank cashouts using the Scene Engine.
Replaces wallet_direct.py NGN cashout handlers with simple configuration.

Flow: Method Selection → Amount Input → Bank Selection → OTP Verification → Confirmation → Processing → Status
"""

from services.scene_engine import SceneDefinition, SceneStep, ComponentConfig, ComponentType

# Step 1: Payment Method Selection
method_selection_step = SceneStep(
    step_id="method_selection",
    title="💳 Select Payment Method",
    description="Choose your preferred cashout method for converting USD to Nigerian Naira.",
    components=[
        ComponentConfig(
            component_type=ComponentType.SELECTION_MENU,
            config={
                "options": [
                    {"label": "🏦 NGN Bank Transfer", "value": "ngn_bank_transfer", "description": "Direct transfer to your Nigerian bank account"}
                ],
                "max_per_row": 1,
                "show_fees": True,
                "show_processing_time": True,
                "default_selection": "ngn_bank_transfer"
            },
            validation={
                "required": True
            },
            on_success="amount_input",
            on_error="method_selection"
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 2: Amount Input
amount_input_step = SceneStep(
    step_id="amount_input",
    title="💰 NGN Cashout Amount",
    description="Enter the USD amount you want to convert to NGN and cashout to your bank account.",
    components=[
        ComponentConfig(
            component_type=ComponentType.AMOUNT_INPUT,
            config={
                "currency": "USD",
                "min_amount": 2.0,
                "max_amount": 10000.0,
                "quick_amounts": [10, 25, 50, 100, 250, 500],
                "convert_to": "NGN",
                "show_conversion_rate": True,
                "include_fee_calculation": True
            },
            validation={
                "required": True,
                "decimal_places": 2
            },
            on_success="bank_selection",
            on_error="amount_input"
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 2: Bank Account Selection
bank_selection_step = SceneStep(
    step_id="bank_selection",
    title="🏦 Select Bank Account",
    description="Choose your NGN bank account for the cashout.",
    components=[
        ComponentConfig(
            component_type=ComponentType.BANK_SELECTOR,
            config={
                "currency": "NGN",
                "country": "NG",
                "provider": "fincra",
                "allow_save": True,
                "require_verification": True,
                "show_saved_first": True
            },
            validation={
                "account_number_length": 10,
                "require_verification": True
            },
            on_success="otp_verification",
            on_error="bank_selection"
        )
    ],
    timeout_seconds=600,
    can_go_back=True
)

# Step 3: OTP Verification
otp_verification_step = SceneStep(
    step_id="otp_verification",
    title="🔐 OTP Verification",
    description="For your security, please verify this transaction with OTP.",
    components=[
        ComponentConfig(
            component_type=ComponentType.TEXT_INPUT,
            config={
                "input_type": "otp",
                "length": 6,
                "placeholder": "123456",
                "auto_send": True,
                "resend_timeout": 60,
                "max_attempts": 3
            },
            validation={
                "required": True,
                "format": "numeric",
                "length": 6
            },
            on_success="final_confirmation",
            on_error="otp_verification"
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 4: Final Confirmation
final_confirmation_step = SceneStep(
    step_id="final_confirmation",
    title="✅ Confirm NGN Cashout",
    description="Please review and confirm your NGN cashout details.",
    components=[
        ComponentConfig(
            component_type=ComponentType.CONFIRMATION,
            config={
                "show_summary": True,
                "include_fees": True,
                "include_rates": True,
                "require_otp": False,  # Already done in previous step
                "confirmation_method": "ngn_cashout",
                "include_risk_assessment": True
            },
            validation={
                "require_consent": True
            },
            on_success="processing",
            on_error="final_confirmation"
        )
    ],
    timeout_seconds=120,
    can_go_back=True
)

# Step 5: Processing
processing_step = SceneStep(
    step_id="processing",
    title="⏳ Processing NGN Cashout",
    description="Your NGN cashout is being processed. This usually takes 5-15 minutes.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "ngn_cashout",
                "show_progress": True,
                "auto_refresh": True,
                "refresh_interval": 30,
                "estimated_time": "5-15 minutes",
                "provider": "fincra"
            },
            on_success="completed",
            on_error="failed"
        )
    ],
    timeout_seconds=1800  # 30 minutes
)

# Step 6: Completed
completed_step = SceneStep(
    step_id="completed",
    title="🎉 NGN Cashout Completed",
    description="Your NGN cashout has been completed successfully!",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "ngn_cashout",
                "status": "completed",
                "show_receipt": True,
                "allow_new_transaction": True,
                "show_transaction_history": True
            }
        )
    ]
)

# Step 7: Failed
failed_step = SceneStep(
    step_id="failed",
    title="❌ NGN Cashout Failed",
    description="Your NGN cashout could not be processed. Don't worry, your funds are safe.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "ngn_cashout",
                "status": "failed",
                "allow_retry": True,
                "show_support_contact": True,
                "show_error_details": True
            }
        )
    ]
)

# Complete NGN Cashout Scene Definition
ngn_cashout_scene = SceneDefinition(
    scene_id="ngn_cashout",
    name="NGN Bank Cashout",
    description="Complete flow for cashing out USD to NGN bank accounts using Fincra",
    steps=[
        method_selection_step,
        amount_input_step,
        bank_selection_step,
        otp_verification_step,
        final_confirmation_step,
        processing_step,
        completed_step,
        failed_step
    ],
    initial_step="method_selection",
    final_steps=["completed", "failed"],
    integrations=[
        "fincra_service",
        "fastforex_service", 
        "unified_transaction_engine",
        "conditional_otp_service",
        "percentage_cashout_fee_service"
    ]
)
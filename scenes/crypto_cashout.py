"""
Crypto Cashout Scene Definition

Declarative flow for cryptocurrency cashouts using the Scene Engine.
Replaces wallet_direct.py crypto cashout handlers with simple configuration.

Flow: Currency Selection → Amount Input → Address Selection → OTP Verification → Confirmation → Processing → Status
"""

from services.scene_engine import SceneDefinition, SceneStep, ComponentConfig, ComponentType

# Step 1: Currency Selection
currency_selection_step = SceneStep(
    step_id="currency_selection",
    title="🪙 Select Cryptocurrency",
    description="Choose the cryptocurrency you want to cash out.",
    components=[
        ComponentConfig(
            component_type=ComponentType.SELECTION_MENU,
            config={
                "options": [
                    {"label": "₿ Bitcoin (BTC)", "value": "BTC"},
                    {"label": "Ξ Ethereum (ETH)", "value": "ETH"},
                    {"label": "Ł Litecoin (LTC)", "value": "LTC"},
                    {"label": "₮ Tether USDT (TRC20)", "value": "USDT_TRC20"},
                    {"label": "₮ Tether USDT (ERC20)", "value": "USDT_ERC20"}
                ],
                "max_per_row": 1,
                "show_balances": True
            },
            validation={
                "required": True
            },
            on_success="amount_input",
            on_error="currency_selection"
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 2: Amount Input
amount_input_step = SceneStep(
    step_id="amount_input",
    title="💰 Crypto Cashout Amount",
    description="Enter the amount you want to cash out.",
    components=[
        ComponentConfig(
            component_type=ComponentType.AMOUNT_INPUT,
            config={
                "currency": "{selected_crypto}",  # Dynamic based on selection
                "min_amount": 0.001,  # Will be adjusted per crypto
                "max_amount": 100.0,  # Will be adjusted per crypto
                "show_usd_conversion": True,
                "include_fee_calculation": True,
                "fee_type": "percentage_based",
                "show_network_options": True
            },
            validation={
                "required": True,
                "check_balance": True,
                "decimal_places": 8  # Max for crypto
            },
            on_success="address_selection",
            on_error="amount_input"
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 3: Address Selection
address_selection_step = SceneStep(
    step_id="address_selection",
    title="🔗 Destination Address",
    description="Enter or select the cryptocurrency address where you want to receive your funds.",
    components=[
        ComponentConfig(
            component_type=ComponentType.ADDRESS_SELECTOR,
            config={
                "crypto": "{selected_crypto}",  # Dynamic
                "network": "{selected_network}",  # Dynamic
                "allow_save": True,
                "show_saved_first": True,
                "validate_address": True,
                "check_network_compatibility": True,
                "show_qr_scanner": True
            },
            validation={
                "required": True,
                "format_validation": True,
                "network_validation": True
            },
            on_success="final_confirmation",
            on_error="address_selection"
        )
    ],
    timeout_seconds=600,
    can_go_back=True
)

# Step 4: OTP Verification
otp_verification_step = SceneStep(
    step_id="otp_verification",
    title="🔐 OTP Verification",
    description="For your security, please verify this crypto transaction with OTP.",
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

# Step 5: Final Confirmation
final_confirmation_step = SceneStep(
    step_id="final_confirmation",
    title="✅ Confirm Crypto Cashout",
    description="Please review and confirm your cryptocurrency cashout details.",
    components=[
        ComponentConfig(
            component_type=ComponentType.CONFIRMATION,
            config={
                "show_summary": True,
                "include_fees": True,
                "include_network_info": True,
                "require_otp": False,  # OTP handled in separate step
                "confirmation_method": "crypto_cashout",
                "include_risk_assessment": True,
                "show_final_amount": True
            },
            validation={
                "require_consent": True,
                "double_check_address": True
            },
            on_success="processing",
            on_error="final_confirmation"
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 6: Processing
processing_step = SceneStep(
    step_id="processing",
    title="⏳ Processing Crypto Cashout",
    description="Your cryptocurrency cashout is being processed. This may take 30-60 minutes.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "crypto_cashout",
                "show_progress": True,
                "auto_refresh": True,
                "refresh_interval": 60,
                "estimated_time": "30-60 minutes",
                "provider": "kraken",
                "show_blockchain_link": True
            },
            on_success="completed",
            on_error="failed"
        )
    ],
    timeout_seconds=7200  # 2 hours
)

# Step 7: Completed
completed_step = SceneStep(
    step_id="completed",
    title="🎉 Crypto Cashout Completed",
    description="Your cryptocurrency cashout has been completed successfully!",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "crypto_cashout",
                "status": "completed",
                "show_receipt": True,
                "show_blockchain_link": True,
                "allow_new_transaction": True,
                "show_transaction_history": True
            }
        )
    ]
)

# Step 8: Failed
failed_step = SceneStep(
    step_id="failed",
    title="❌ Crypto Cashout Failed",
    description="Your cryptocurrency cashout could not be processed. Your funds remain in your wallet.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "crypto_cashout",
                "status": "failed",
                "allow_retry": True,
                "show_support_contact": True,
                "show_error_details": True,
                "refund_status": True
            }
        )
    ]
)

# Complete Crypto Cashout Scene Definition  
crypto_cashout_scene = SceneDefinition(
    scene_id="crypto_cashout",
    name="Cryptocurrency Cashout",
    description="Complete flow for cashing out cryptocurrencies using Kraken",
    steps=[
        currency_selection_step,
        amount_input_step,
        address_selection_step,
        otp_verification_step,
        final_confirmation_step,
        processing_step,
        completed_step,
        failed_step
    ],
    initial_step="currency_selection",
    final_steps=["completed", "failed"],
    integrations=[
        "kraken_service",
        "financial_gateway",
        "unified_transaction_engine", 
        "conditional_otp_service",
        "percentage_cashout_fee_service",
        "crypto_address_validator"
    ]
)
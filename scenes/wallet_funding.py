"""
Wallet Funding Scene Definition

Declarative flow for wallet funding using the Scene Engine.
Replaces complex wallet funding handlers with simple configuration.

Flow: Currency Selection → Amount Input → Address Generation → Payment Monitoring → Completion
"""

from services.scene_engine import SceneDefinition, SceneStep, ComponentConfig, ComponentType

# Step 1: Currency Selection
currency_selection_step = SceneStep(
    step_id="currency_selection",
    title="💱 Select Funding Currency",
    description="Choose how you want to fund your LockBay wallet.",
    components=[
        ComponentConfig(
            component_type=ComponentType.SELECTION_MENU,
            config={
                "options": [
                    {"label": "₿ Bitcoin (BTC)", "value": "BTC"},
                    {"label": "Ξ Ethereum (ETH)", "value": "ETH"},
                    {"label": "₳ Litecoin (LTC)", "value": "LTC"},
                    {"label": "₮ Tether USDT (TRC20)", "value": "USDT_TRC20"},
                    {"label": "₮ Tether USDT (ERC20)", "value": "USDT_ERC20"},
                    {"label": "💰 Direct Deposit (Bank)", "value": "BANK_DEPOSIT"}
                ],
                "max_per_row": 1,
                "show_fees": True,
                "show_processing_time": True
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
    title="💰 Funding Amount",
    description="Enter the amount you want to add to your wallet.",
    components=[
        ComponentConfig(
            component_type=ComponentType.AMOUNT_INPUT,
            config={
                "currency": "{selected_currency}",  # Dynamic
                "min_amount": 2.0,   # USD equivalent
                "max_amount": 5000.0,  # USD equivalent
                "quick_amounts": [2, 10, 25, 50, 100, 250, 500],
                "show_usd_conversion": True,
                "include_processing_fee": True,
                "show_final_amount": True
            },
            validation={
                "required": True,
                "decimal_places": 8  # Max precision
            },
            on_success="address_generation",
            on_error="amount_input"
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 3: Address Generation & Instructions
address_generation_step = SceneStep(
    step_id="address_generation",
    title="📍 Payment Address",
    description="Send your payment to this address to fund your wallet.",
    components=[
        ComponentConfig(
            component_type=ComponentType.CUSTOM_KEYBOARD,
            config={
                "buttons": [
                    {"text": "📱 Show QR Code", "data": "show_qr"},
                    {"text": "💬 WhatsApp Share", "data": "share_whatsapp"},
                    {"text": "📧 Email Instructions", "data": "email_instructions"},
                    {"text": "🔄 Generate New Address", "data": "new_address"},
                    {"text": "✅ I've Sent Payment", "data": "payment_sent"}
                ],
                "max_per_row": 2,
                "show_address": True,
                "show_qr_code": True,
                "show_amount": True,
                "show_instructions": True,
                "address_timeout": 3600  # 1 hour
            },
            on_success="payment_monitoring",
            on_error="address_generation"
        )
    ],
    timeout_seconds=3600  # 1 hour for payment
)

# Step 4: Payment Monitoring
payment_monitoring_step = SceneStep(
    step_id="payment_monitoring",
    title="⏳ Monitoring Payment",
    description="We're monitoring the blockchain for your payment. You'll be notified when it's confirmed.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "wallet_funding",
                "show_progress": True,
                "auto_refresh": True,
                "refresh_interval": 30,
                "show_confirmations": True,
                "required_confirmations": 3,
                "estimated_time": "10-30 minutes",
                "show_blockchain_link": True,
                "allow_manual_check": True
            },
            on_success="processing",
            on_error="payment_failed"
        )
    ],
    timeout_seconds=7200  # 2 hours
)

# Step 5: Processing
processing_step = SceneStep(
    step_id="processing", 
    title="⚡ Processing Payment",
    description="Your payment has been detected and is being processed.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "wallet_funding",
                "status": "processing",
                "show_progress": True,
                "auto_refresh": True,
                "refresh_interval": 15,
                "estimated_time": "2-5 minutes"
            },
            on_success="completed",
            on_error="processing_failed"
        )
    ],
    timeout_seconds=600  # 10 minutes
)

# Step 6: Completed
completed_step = SceneStep(
    step_id="completed",
    title="🎉 Wallet Funded Successfully!",
    description="Your LockBay wallet has been funded successfully!",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "wallet_funding",
                "status": "completed",
                "show_receipt": True,
                "show_new_balance": True,
                "show_transaction_history": True,
                "allow_new_funding": True,
                "show_next_actions": True
            }
        )
    ]
)

# Step 7: Payment Failed
payment_failed_step = SceneStep(
    step_id="payment_failed",
    title="❌ Payment Not Detected",
    description="We haven't detected your payment yet. Don't worry, your funds are safe.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "wallet_funding",
                "status": "failed",
                "show_troubleshooting": True,
                "allow_manual_check": True,
                "show_support_contact": True,
                "allow_retry": True,
                "show_payment_instructions": True
            }
        )
    ]
)

# Step 8: Processing Failed
processing_failed_step = SceneStep(
    step_id="processing_failed",
    title="⚠️ Processing Issue",
    description="There was an issue processing your payment. Our team has been notified.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "wallet_funding",
                "status": "processing_failed",
                "show_support_contact": True,
                "show_error_details": True,
                "auto_escalate": True,
                "show_refund_info": True
            }
        )
    ]
)

# Complete Wallet Funding Scene Definition
wallet_funding_scene = SceneDefinition(
    scene_id="wallet_funding",
    name="Wallet Funding",
    description="Complete flow for funding LockBay wallets with cryptocurrency or bank deposits",
    steps=[
        currency_selection_step,
        amount_input_step,
        address_generation_step,
        payment_monitoring_step,
        processing_step,
        completed_step,
        payment_failed_step,
        processing_failed_step
    ],
    initial_step="currency_selection",
    final_steps=["completed", "payment_failed", "processing_failed"],
    integrations=[
        "crypto_address_generator",
        "blockchain_monitor_service",
        "unified_transaction_engine",
        "financial_gateway",
        "kraken_service",
        "blockbee_service"
    ]
)
"""
Escrow Creation Scene Definition

Declarative flow for creating escrow transactions using the Scene Engine.
Replaces complex escrow handlers with simple configuration.

Flow: Escrow Details → Terms Setup → Buyer Contact → Confirmation → Active Escrow
"""

from services.scene_engine import SceneDefinition, SceneStep, ComponentConfig, ComponentType

# Step 1: Escrow Details
escrow_details_step = SceneStep(
    step_id="escrow_details",
    title="📋 Escrow Details",
    description="Enter the details for your escrow transaction.",
    components=[
        ComponentConfig(
            component_type=ComponentType.TEXT_INPUT,
            config={
                "fields": [
                    {
                        "name": "title",
                        "label": "Escrow Title",
                        "placeholder": "iPhone 15 Pro Max Sale",
                        "required": True,
                        "max_length": 100
                    },
                    {
                        "name": "description", 
                        "label": "Description",
                        "placeholder": "Brand new iPhone 15 Pro Max, 256GB, Space Gray...",
                        "required": True,
                        "max_length": 500,
                        "multiline": True
                    }
                ],
                "validation_rules": {
                    "title": {"min_length": 5, "max_length": 100},
                    "description": {"min_length": 20, "max_length": 500}
                }
            },
            validation={
                "required": True
            },
            on_success="amount_and_terms",
            on_error="escrow_details"
        )
    ],
    timeout_seconds=600,
    can_go_back=True
)

# Step 2: Amount and Terms
amount_and_terms_step = SceneStep(
    step_id="amount_and_terms",
    title="💰 Amount & Terms",
    description="Set the escrow amount and payment terms.",
    components=[
        ComponentConfig(
            component_type=ComponentType.AMOUNT_INPUT,
            config={
                "currency": "USD",
                "min_amount": 1.0,
                "max_amount": 10000.0,
                "quick_amounts": [25, 50, 100, 250, 500, 1000],
                "show_escrow_fee": True,
                "fee_percentage": 2.5,
                "show_total": True
            },
            validation={
                "required": True,
                "decimal_places": 2
            },
            on_success="terms_setup",
            on_error="amount_and_terms"
        ),
        ComponentConfig(
            component_type=ComponentType.SELECTION_MENU,
            config={
                "title": "⏰ Payment Timeout",
                "options": [
                    {"label": "🕐 1 Hour", "value": "1h"},
                    {"label": "🕕 6 Hours", "value": "6h"},
                    {"label": "🕛 24 Hours", "value": "24h"},
                    {"label": "📅 3 Days", "value": "3d"},
                    {"label": "📅 7 Days", "value": "7d"}
                ],
                "default": "24h",
                "description": "How long should the buyer have to pay?"
            },
            validation={
                "required": True
            }
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 3: Terms Setup
terms_setup_step = SceneStep(
    step_id="terms_setup",
    title="📜 Escrow Terms",
    description="Configure the terms and conditions for this escrow.",
    components=[
        ComponentConfig(
            component_type=ComponentType.SELECTION_MENU,
            config={
                "title": "🚚 Delivery Method",
                "options": [
                    {"label": "📦 Physical Shipping", "value": "shipping"},
                    {"label": "🤝 In-Person Meetup", "value": "meetup"},
                    {"label": "📧 Digital Delivery", "value": "digital"},
                    {"label": "🔗 Online Service", "value": "service"}
                ],
                "description": "How will the item/service be delivered?"
            },
            validation={
                "required": True
            }
        ),
        ComponentConfig(
            component_type=ComponentType.SELECTION_MENU,
            config={
                "title": "⏱️ Release Timeout",
                "options": [
                    {"label": "🕐 1 Hour", "value": "1h"},
                    {"label": "🕕 6 Hours", "value": "6h"},
                    {"label": "🕛 24 Hours", "value": "24h"},
                    {"label": "📅 3 Days", "value": "3d"},
                    {"label": "📅 7 Days", "value": "7d"},
                    {"label": "📅 14 Days", "value": "14d"}
                ],
                "default": "3d",
                "description": "Auto-release funds after delivery confirmation timeout"
            },
            validation={
                "required": True
            },
            on_success="buyer_contact",
            on_error="terms_setup"
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 4: Buyer Contact
buyer_contact_step = SceneStep(
    step_id="buyer_contact",
    title="👤 Buyer Information",
    description="Provide the buyer's contact information to invite them to the escrow.",
    components=[
        ComponentConfig(
            component_type=ComponentType.SELECTION_MENU,
            config={
                "title": "📞 Contact Method",
                "options": [
                    {"label": "📱 Telegram Username", "value": "telegram"},
                    {"label": "📧 Email Address", "value": "email"},
                    {"label": "📞 Phone Number", "value": "phone"},
                    {"label": "🔗 Share Link Only", "value": "link"}
                ],
                "description": "How should we contact the buyer?"
            },
            validation={
                "required": True
            }
        ),
        ComponentConfig(
            component_type=ComponentType.TEXT_INPUT,
            config={
                "dynamic_field": True,  # Field changes based on contact method
                "fields": {
                    "telegram": {
                        "label": "Telegram Username",
                        "placeholder": "@username or full name",
                        "validation": "telegram_user"
                    },
                    "email": {
                        "label": "Email Address", 
                        "placeholder": "buyer@example.com",
                        "validation": "email"
                    },
                    "phone": {
                        "label": "Phone Number",
                        "placeholder": "+1234567890",
                        "validation": "phone"
                    },
                    "link": {
                        "label": "Notes (Optional)",
                        "placeholder": "Any notes for sharing the link...",
                        "required": False
                    }
                }
            },
            validation={
                "required": True  # Except for link option
            },
            on_success="final_confirmation",
            on_error="buyer_contact"
        )
    ],
    timeout_seconds=300,
    can_go_back=True
)

# Step 5: Final Confirmation
final_confirmation_step = SceneStep(
    step_id="final_confirmation",
    title="✅ Confirm Escrow Creation",
    description="Please review and confirm your escrow details before creating.",
    components=[
        ComponentConfig(
            component_type=ComponentType.CONFIRMATION,
            config={
                "show_summary": True,
                "include_fees": True,
                "show_terms": True,
                "require_agreement": True,
                "confirmation_method": "escrow_creation",
                "agreement_text": "I agree to the LockBay Escrow Terms of Service",
                "include_risk_assessment": False  # Escrows are safer
            },
            validation={
                "require_consent": True,
                "require_terms_agreement": True
            },
            on_success="creating",
            on_error="final_confirmation"
        )
    ],
    timeout_seconds=180,
    can_go_back=True
)

# Step 6: Creating Escrow
creating_step = SceneStep(
    step_id="creating",
    title="⚡ Creating Escrow",
    description="Your escrow is being created and the buyer is being contacted.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "escrow_creation",
                "status": "creating",
                "show_progress": True,
                "estimated_time": "30 seconds",
                "show_next_steps": True
            },
            on_success="active",
            on_error="creation_failed"
        )
    ],
    timeout_seconds=60
)

# Step 7: Active Escrow
active_step = SceneStep(
    step_id="active",
    title="🎉 Escrow Created Successfully!",
    description="Your escrow is now active and the buyer has been contacted.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "escrow_creation",
                "status": "active",
                "show_escrow_details": True,
                "show_share_link": True,
                "show_management_options": True,
                "allow_modifications": True,
                "show_chat_access": True
            }
        )
    ]
)

# Step 8: Creation Failed
creation_failed_step = SceneStep(
    step_id="creation_failed",
    title="❌ Escrow Creation Failed",
    description="There was an issue creating your escrow. Please try again.",
    components=[
        ComponentConfig(
            component_type=ComponentType.STATUS_DISPLAY,
            config={
                "transaction_type": "escrow_creation",
                "status": "failed",
                "show_error_details": True,
                "allow_retry": True,
                "show_support_contact": True,
                "preserve_data": True  # Keep form data for retry
            }
        )
    ]
)

# Complete Escrow Creation Scene Definition
escrow_creation_scene = SceneDefinition(
    scene_id="escrow_creation",
    name="Escrow Creation",
    description="Complete flow for creating secure escrow transactions",
    steps=[
        escrow_details_step,
        amount_and_terms_step,
        terms_setup_step,
        buyer_contact_step,
        final_confirmation_step,
        creating_step,
        active_step,
        creation_failed_step
    ],
    initial_step="escrow_details",
    final_steps=["active", "creation_failed"],
    integrations=[
        "unified_transaction_engine",
        "escrow_management_service",
        "notification_service",
        "telegram_contact_service",
        "email_service",
        "sms_service"
    ]
)
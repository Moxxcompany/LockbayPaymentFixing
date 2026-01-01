"""Email templates for user engagement and retention"""

from config import Config
from typing import Dict, Any


def create_unified_email_template(title: str, content: str, otp_code: str = None, expiry_minutes: int = 10) -> str:
    """
    Create a unified email template with consistent styling
    
    Args:
        title: Email title/subject
        content: Main email content
        otp_code: Optional OTP code to display prominently
        expiry_minutes: OTP expiry time in minutes
    
    Returns:
        HTML email content with consistent styling
    """
    otp_section = ""
    if otp_code:
        otp_section = f"""
        <div style="margin: 30px 0; text-align: center;">
            <p style="font-size: 16px; color: #374151; margin-bottom: 15px;">Your verification code is:</p>
            <div style="background: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                <h1 style="font-family: monospace; font-size: 32px; letter-spacing: 5px; color: #1f2937; margin: 0;">{otp_code}</h1>
            </div>
            <p style="font-size: 14px; color: #6b7280;">This code will expire in {expiry_minutes} minutes.</p>
        </div>
        """
    
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f9fafb;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 30px 40px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 600;">{Config.PLATFORM_NAME}</h1>
                <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">{title}</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px;">
                {content}
                {otp_section}
                
                <!-- Footer -->
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center;">
                    <p style="font-size: 14px; color: #6b7280; margin: 0;">
                        If you didn't request this, please ignore this email.
                    </p>
                    <p style="font-size: 12px; color: #9ca3af; margin: 10px 0 0 0;">
                        © 2025 {Config.PLATFORM_NAME}. All rights reserved.
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


def get_welcome_email_template(user_name: str, user_email: str, membership_number: str = None) -> dict:
    """
    Generate a feature-aware welcome email that only shows enabled features
    
    Args:
        user_name: User's first name
        user_email: User's email address
        membership_number: User's membership ID
    
    Returns:
        dict: Email template with subject and html content
    """
    
    subject = f"Welcome to {Config.PLATFORM_NAME} - Secure Escrow Trading Starts Now! 🔒"
    
    # Format membership number with leading zeros
    membership_display = f"MB{membership_number.zfill(6)}" if membership_number else "MB000000"
    
    # Build feature sections based on what's enabled
    features_section = _build_features_section()
    coming_soon_section = _build_coming_soon_section()
    
    content = f"""
    <h2 style="color: #1e40af; margin-bottom: 10px;">Welcome to {Config.PLATFORM_NAME}, {user_name}! 🎉</h2>
    <p style="color: #374151; font-size: 16px;">You've joined a secure platform where EVERY transaction is protected by escrow. No more worrying about scams or payment disputes!</p>
    
    <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #0ea5e9;">
        <h3 style="color: #0369a1; margin-top: 0; font-size: 18px;">👤 Your Membership Details</h3>
        <p style="color: #0c4a6e; margin: 5px 0; font-size: 16px; font-weight: 600;">Membership ID: {membership_display}</p>
        <p style="color: #075985; margin: 5px 0; font-size: 14px;">Status: Active ✅</p>
    </div>
    
    <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #f59e0b;">
        <h3 style="color: #92400e; margin-top: 0; font-size: 18px;">🔒 Why LockBay is Different</h3>
        <p style="color: #78350f; margin: 8px 0; line-height: 1.6;">Unlike regular exchanges, <strong>every trade is protected by escrow</strong>:</p>
        <ul style="color: #78350f; line-height: 1.8; margin: 10px 0; padding-left: 20px;">
            <li>Funds held securely until both parties confirm</li>
            <li>Zero risk of "send first" scams</li>
            <li>Dispute resolution if issues arise</li>
            <li>Admin oversight for extra security</li>
        </ul>
    </div>
    
    <h3 style="color: #1e40af; margin-top: 30px; font-size: 20px;">🚀 What You Can Do Right Now</h3>
    {features_section}
    
    <div style="background: #ecfdf5; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #10b981;">
        <h3 style="color: #065f46; margin-top: 0; font-size: 18px;">💡 Safety Tips</h3>
        <ul style="color: #064e3b; line-height: 1.8; margin: 10px 0; padding-left: 20px;">
            <li><strong>All funds are held in escrow</strong> - never send outside the platform</li>
            <li><strong>Confirm receipt</strong> before releasing escrow funds</li>
            <li><strong>Use disputes</strong> if anything goes wrong - our team reviews personally</li>
            <li><strong>Rate your trades</strong> to help build a trusted community</li>
        </ul>
    </div>
    
    {coming_soon_section}
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="https://t.me/{Config.BOT_USERNAME}" style="background: #1e40af; color: white; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; display: inline-block;">
            Start Your First Trade →
        </a>
    </div>
    
    <p style="color: #4b5563; font-size: 15px; line-height: 1.6; margin-top: 25px;">
        <strong>Need Help?</strong><br>
        Type <code style="background: #f3f4f6; padding: 2px 6px; border-radius: 4px;">/support</code> in the bot or reply to this email - our team is here 24/7.
    </p>
    
    <p style="color: #374151; font-size: 15px; margin-top: 20px;">
        Trade safely with escrow protection,<br>
        <strong>The {Config.PLATFORM_NAME} Team</strong>
    </p>
    
    <p style="color: #9ca3af; font-size: 13px; font-style: italic; margin-top: 20px;">
        P.S. Your user agreement PDF is attached for your records.
    </p>
    """
    
    html_content = create_unified_email_template(
        title="Your Escrow-Protected Trading Journey Begins",
        content=content
    )
    
    return {"subject": subject, "html_content": html_content}


def _build_features_section() -> str:
    """Build features section based on enabled features"""
    
    features_html = """
    <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
    """
    
    # Always show: Escrow Trading (core feature)
    features_html += """
        <div style="margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #e2e8f0;">
            <h4 style="color: #1e40af; margin: 0 0 10px 0; font-size: 16px;">⚖️ Escrow-Protected Trading</h4>
            <p style="color: #475569; margin: 5px 0; line-height: 1.6; font-size: 14px;">Create secure buy/sell trades with automatic escrow protection. Your funds stay locked until both parties confirm completion.</p>
            <p style="color: #64748b; margin: 8px 0 0 0; font-size: 13px;"><strong>Try it:</strong> Type <code style="background: #e2e8f0; padding: 2px 6px; border-radius: 3px;">/escrow</code> to start</p>
        </div>
    """
    
    # Always show: Wallet & Cashout
    features_html += """
        <div style="margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #e2e8f0;">
            <h4 style="color: #1e40af; margin: 0 0 10px 0; font-size: 16px;">💰 Crypto Wallet & Cashout</h4>
            <p style="color: #475569; margin: 5px 0; line-height: 1.6; font-size: 14px;">Manage your balance and cash out to your crypto addresses. Track all transactions in one place.</p>
            <p style="color: #64748b; margin: 8px 0 0 0; font-size: 13px;"><strong>Try it:</strong> Type <code style="background: #e2e8f0; padding: 2px 6px; border-radius: 3px;">/wallet</code> to view balance</p>
        </div>
    """
    
    # Always show: Dispute Resolution
    features_html += """
        <div style="margin-bottom: 0;">
            <h4 style="color: #1e40af; margin: 0 0 10px 0; font-size: 16px;">🛡️ Dispute Resolution</h4>
            <p style="color: #475569; margin: 5px 0; line-height: 1.6; font-size: 14px;">If issues arise, open a dispute. Our admin team reviews evidence and makes fair decisions to protect both parties.</p>
            <p style="color: #64748b; margin: 8px 0 0 0; font-size: 13px;"><strong>Access:</strong> Available in active trades if needed</p>
        </div>
    """
    
    features_html += """
    </div>
    """
    
    return features_html


def _build_coming_soon_section() -> str:
    """Build coming soon section for disabled features"""
    
    coming_soon_features = []
    
    # Check which features are disabled
    if not Config.ENABLE_EXCHANGE_FEATURES:
        coming_soon_features.append("⚡ Quick Exchange - Instant crypto-to-cash conversion")
    
    if not Config.ENABLE_NGN_FEATURES:
        coming_soon_features.append("🇳🇬 NGN Bank Transfers - Direct naira deposits and withdrawals")
    
    if not Config.ENABLE_AUTO_CASHOUT_FEATURES:
        coming_soon_features.append("🤖 Auto-Cashout - Automatic processing of withdrawal requests")
    
    if not coming_soon_features:
        return ""  # No disabled features, skip this section
    
    features_list = "".join([f"<li>{feature}</li>" for feature in coming_soon_features])
    
    return f"""
    <div style="background: #fef2f2; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #ef4444;">
        <h3 style="color: #991b1b; margin-top: 0; font-size: 18px;">🚀 Coming Soon</h3>
        <p style="color: #7f1d1d; margin: 8px 0;">We're constantly improving! Here's what's launching next:</p>
        <ul style="color: #7f1d1d; line-height: 1.8; margin: 10px 0; padding-left: 20px;">
            {features_list}
        </ul>
        <p style="color: #991b1b; margin: 12px 0 0 0; font-size: 14px; font-style: italic;">Stay tuned for updates!</p>
    </div>
    """


def render_template(template_name: str, template_data: Dict[str, Any]) -> str:
    """
    Render email template by name with provided data - for integration tests
    
    Args:
        template_name: Name of the template to render
        template_data: Data to populate the template
        
    Returns:
        Rendered HTML template content
    """
    # Map template names to functions
    template_map = {
        "escrow_created": _render_escrow_created_template,
        "payment_confirmation": _render_payment_confirmation_template,
        "welcome": _render_welcome_template,
    }
    
    if template_name not in template_map:
        # Fallback to unified template
        title = template_data.get("title", "Notification")
        content = template_data.get("content", "You have a new notification.")
        otp_code = template_data.get("otp_code")
        return create_unified_email_template(title, content, otp_code)
    
    return template_map[template_name](template_data)

def _render_escrow_created_template(data: Dict[str, Any]) -> str:
    """Render escrow created email template"""
    content = f"""
    <p>Hello {data.get('user_name', 'User')},</p>
    <p>Your escrow transaction has been created successfully.</p>
    <p><strong>Escrow ID:</strong> {data.get('escrow_id', 'N/A')}</p>
    <p><strong>Amount:</strong> {data.get('amount', 'N/A')} {data.get('currency', 'USD')}</p>
    <p>Please follow the instructions to complete your transaction.</p>
    """
    return create_unified_email_template("Escrow Created", content)

def _render_payment_confirmation_template(data: Dict[str, Any]) -> str:
    """Render payment confirmation email template"""
    content = f"""
    <p>Hello {data.get('user_name', 'User')},</p>
    <p>Your payment has been confirmed.</p>
    <p><strong>Transaction ID:</strong> {data.get('transaction_id', 'N/A')}</p>
    <p><strong>Amount:</strong> {data.get('amount', 'N/A')} {data.get('currency', 'USD')}</p>
    <p>Thank you for using our service.</p>
    """
    return create_unified_email_template("Payment Confirmed", content)

def _render_welcome_template(data: Dict[str, Any]) -> str:
    """Render welcome email template"""
    content = f"""
    <p>Welcome {data.get('user_name', 'User')}!</p>
    <p>Thank you for joining our platform.</p>
    <p>Your account has been successfully created.</p>
    <p>Start exploring our features and enjoy secure transactions.</p>
    """
    return create_unified_email_template("Welcome to LockBay", content)

def get_reactivation_email_template(user_name: str, user_email: str) -> dict:
    """
    Generate retention email for inactive users
    
    Args:
        user_name: User's first name  
        user_email: User's email address
    
    Returns:
        dict: Email template with subject and html content
    """
    
    subject = f"We miss you at {Config.PLATFORM_NAME}! 💎 Your secure trades await"
    
    content = f"""
    <h2>Hey {user_name}, we noticed you've been away! 👋</h2>
    
    <p>Your escrow-protected trading account is ready whenever you are. We've made improvements to keep your transactions even safer.</p>
    
    <div style="background: #ecfdf5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981;">
        <h3 style="color: #065f46; margin-top: 0;">🎯 What's New</h3>
        <ul style="color: #064e3b; line-height: 1.6;">
            <li>Faster dispute resolution</li>
            <li>Enhanced security features</li>
            <li>Better transaction tracking</li>
        </ul>
    </div>
    
    <p style="text-align: center; margin: 30px 0;">
        <a href="https://t.me/{Config.BOT_USERNAME}" style="background: #10b981; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; font-weight: 600;">
            Resume Trading
        </a>
    </p>
    
    <p>Ready to get back to secure trading?</p>
    
    <p>Best regards,<br>
    The {Config.PLATFORM_NAME} Team</p>
    """
    
    html_content = create_unified_email_template(
        title="We Miss You!",
        content=content
    )
    
    return {"subject": subject, "html_content": html_content}

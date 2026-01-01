"""
Trust-Focused Branding System for {Config.PLATFORM_NAME}
Implements psychology-based color scheme and visual elements
"""


class BrandColors:
    """Psychology-based color palette for financial trust"""

    # Primary colors (research-backed for financial services)
    DEEP_TRUST_BLUE = "#1E3A8A"  # 47% trust increase, institutional credibility
    SUCCESS_GREEN = "#059669"  # Positive outcomes, completions only
    WARM_GRAY = "#6B7280"  # Professional secondary text
    CAUTIONARY_AMBER = "#D97706"  # Pending states, important notices
    ALERT_RED = "#DC2626"  # Disputes, critical errors

    # Support colors
    LIGHT_BLUE = "#3B82F6"  # Secondary actions
    SOFT_GREEN = "#10B981"  # Subtle positive indicators
    NEUTRAL_GRAY = "#9CA3AF"  # Disabled states


class SecurityIcons:
    """Security-focused iconography for trust building"""

    SHIELD = "🛡️"  # Primary security symbol
    LOCK = "🔒"  # Secure transactions
    VERIFIED = "✅"  # Completed/verified actions
    STAR = "⭐"  # Reputation/ratings
    SECURE_WALLET = "💰"  # Wallet/financial operations
    PROGRESS = "📊"  # Transaction progress
    TRUSTED_USER = "🏅"  # Achievement/trusted status
    PROTECTION = "🔐"  # Enhanced security features


class TrustMessages:
    """Trust-building messaging templates"""

    # Security assurances
    FUNDS_PROTECTED = (
        f"{SecurityIcons.SHIELD} Your funds are protected by our secure trade system"
    )
    TRANSACTION_SECURED = (
        f"{SecurityIcons.LOCK} This transaction is secured and monitored"
    )
    VERIFIED_USER = f"{SecurityIcons.VERIFIED} Verified user with strong reputation"

    # Progress indicators
    TRADE_ACTIVE = f"{SecurityIcons.PROGRESS} Trade is active and secure"
    FUNDS_RELEASED = f"{SecurityIcons.VERIFIED} Funds successfully released"

    # Achievement messages
    TRUSTED_TRADER = f"{SecurityIcons.TRUSTED_USER} You're now a Trusted Trader!"
    REPUTATION_INCREASED = f"{SecurityIcons.STAR} Your reputation has increased"


class BrandedTemplates:
    """Branded message templates with consistent styling"""

    @staticmethod
    def success_message(
        title: str, content: str, icon: str = SecurityIcons.VERIFIED
    ) -> str:
        """Format success messages with brand consistency"""
        return f"""
{icon} {title}

{content}

{TrustMessages.FUNDS_PROTECTED}
"""

    @staticmethod
    def security_notice(title: str, content: str) -> str:
        """Format security-focused notices"""
        return f"""
{SecurityIcons.SHIELD} {title}

{content}

{TrustMessages.TRANSACTION_SECURED}
"""

    @staticmethod
    def progress_update(
        stage: str, description: str, progress_icon: str = SecurityIcons.PROGRESS
    ) -> str:
        """Format progress updates with trust indicators"""
        return f"""
{progress_icon} {stage}

{description}

{TrustMessages.TRADE_ACTIVE}
"""


class UserRetentionElements:
    """Gamification and retention psychology elements"""

    # Achievement levels
    ACHIEVEMENT_LEVELS = {
        1: f"{SecurityIcons.STAR} New Trader",
        5: f"{SecurityIcons.STAR}{SecurityIcons.STAR} Active Trader",
        10: f"{SecurityIcons.STAR}{SecurityIcons.STAR}{SecurityIcons.STAR} Experienced Trader",
        25: f"{SecurityIcons.TRUSTED_USER} Trusted Trader",
        50: f"{SecurityIcons.SHIELD} Elite Trader",
    }

    # Progress celebrations
    MILESTONE_MESSAGES = {
        "first_completion": f"{SecurityIcons.VERIFIED} Congratulations on your first successful trade!",
        "reputation_milestone": f"{SecurityIcons.STAR} You've earned a reputation milestone!",
        "trusted_status": f"{SecurityIcons.TRUSTED_USER} You've achieved Trusted Trader status!",
        "volume_milestone": f"{SecurityIcons.PROGRESS} You've reached a new volume milestone!",
    }

    @staticmethod
    def get_reputation_display(score: float, total_ratings: int) -> str:
        """Generate reputation display with visual elements"""
        if score == 0.0 or total_ratings == 0:
            return f"{SecurityIcons.STAR} New Trader"

        stars = min(5, max(1, int(score + 0.5)))
        star_display = SecurityIcons.STAR * stars
        return f"{star_display} ({score:.1f}/5 from {total_ratings} ratings)"

    @staticmethod
    def get_achievement_badge(transaction_count: int) -> str:
        """Get achievement badge based on transaction count"""
        for threshold, badge in sorted(
            UserRetentionElements.ACHIEVEMENT_LEVELS.items(), reverse=True
        ):
            if transaction_count >= threshold:
                return badge
        return UserRetentionElements.ACHIEVEMENT_LEVELS[1]


# Color application helpers
def format_with_trust_colors(text: str, color_type: str = "primary") -> str:
    """Apply trust-focused color formatting (for HTML/Markdown contexts)"""

    # For Telegram, we use emoji-based visual hierarchy instead of colors
    # This function provides structure for future HTML implementations
    return text


def create_trust_header(title: str, subtitle: str = "") -> str:
    """Create branded header with security emphasis"""
    if subtitle:
        return f"""
{SecurityIcons.SHIELD} {title}
{subtitle}

{TrustMessages.FUNDS_PROTECTED}
"""
    return f"{SecurityIcons.SHIELD} {title}\n\n{TrustMessages.FUNDS_PROTECTED}"

"""Configuration validation system with comprehensive schema validation"""

import os
import logging
from typing import Any, Optional, List, Union, Dict
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import re

logger = logging.getLogger(__name__)


class ProfitProtector:
    """Emergency profit protection for markup configurations"""
    
    MIN_EXCHANGE_MARKUP = Decimal("0.01")  # 0.01% minimum
    MAX_EXCHANGE_MARKUP = Decimal("50.0")   # 50% maximum
    MIN_ESCROW_FEE = Decimal("0.01")       # 0.01% minimum
    MAX_ESCROW_FEE = Decimal("20.0")       # 20% maximum
    
    @classmethod
    def validate_profit_configurations(cls) -> Dict[str, any]:
        """Validate all profit-critical configurations"""
        from config import Config
        
        issues = []
        warnings = []
        
        # Check exchange markup
        exchange_markup = Config.EXCHANGE_MARKUP_PERCENTAGE
        if exchange_markup <= 0:
            issues.append(f"🚨 CRITICAL: Exchange markup is {exchange_markup}% - ZERO PROFIT!")
        elif exchange_markup < cls.MIN_EXCHANGE_MARKUP:
            issues.append(f"⚠️ Exchange markup {exchange_markup}% below minimum {cls.MIN_EXCHANGE_MARKUP}%")
        elif exchange_markup > cls.MAX_EXCHANGE_MARKUP:
            warnings.append(f"📊 Exchange markup {exchange_markup:.1f}% exceeds maximum {cls.MAX_EXCHANGE_MARKUP:.1f}%")
        
        # Check escrow fee
        escrow_fee = Config.ESCROW_FEE_PERCENTAGE
        if escrow_fee <= 0:
            issues.append(f"🚨 CRITICAL: Escrow fee is {escrow_fee}% - ZERO PROFIT!")
        elif escrow_fee < cls.MIN_ESCROW_FEE:
            issues.append(f"⚠️ Escrow fee {escrow_fee}% below minimum {cls.MIN_ESCROW_FEE}%")
        elif escrow_fee > cls.MAX_ESCROW_FEE:
            warnings.append(f"📊 Escrow fee {escrow_fee:.1f}% exceeds maximum {cls.MAX_ESCROW_FEE:.1f}%")
        
        return {
            "is_profitable": len(issues) == 0,
            "critical_issues": issues,
            "warnings": warnings,
            "exchange_markup": float(exchange_markup),
            "escrow_fee": float(escrow_fee),
            "validation_timestamp": "real-time"
        }
    
    @classmethod
    def emergency_profit_check(cls) -> bool:
        """Emergency check for profit loss scenarios"""
        validation = cls.validate_profit_configurations()
        
        if not validation["is_profitable"]:
            logger.critical("🚨 EMERGENCY: Profit loss detected!")
            logger.critical(f"Issues: {validation['critical_issues']}")
            return False
        
        return True


class ConfigLevel(Enum):
    """Configuration validation levels"""

    REQUIRED = "required"
    OPTIONAL = "optional"
    DEPRECATED = "deprecated"


class ConfigType(Enum):
    """Configuration data types"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    EMAIL = "email"
    URL = "url"
    API_KEY = "api_key"
    LIST = "list"


@dataclass
class ConfigRule:
    """Configuration validation rule"""

    name: str
    type: ConfigType
    level: ConfigLevel
    description: str
    default: Any = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    choices: Optional[List[str]] = None
    depends_on: Optional[List[str]] = None
    validates_with: Optional[callable] = None


@dataclass
class ValidationResult:
    """Result of configuration validation"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    deprecated_used: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ConfigValidator:
    """Comprehensive configuration validator"""

    def __init__(self):
        self.rules = self._define_validation_rules()

    def _define_validation_rules(self) -> List[ConfigRule]:
        """Define all configuration validation rules"""
        return [
            # Core Bot Configuration
            ConfigRule(
                name="BOT_TOKEN",
                type=ConfigType.API_KEY,
                level=ConfigLevel.REQUIRED,
                description="Telegram Bot API token",
                pattern=r"^\d+:[A-Za-z0-9_-]{35}$",
            ),
            ConfigRule(
                name="BOT_USERNAME",
                type=ConfigType.STRING,
                level=ConfigLevel.OPTIONAL,
                description="Bot username (without @)",
                default="lockbay_bot",
            ),
            # Database Configuration
            ConfigRule(
                name="DATABASE_URL",
                type=ConfigType.URL,
                level=ConfigLevel.REQUIRED,
                description="PostgreSQL database connection URL",
                pattern=r"^postgresql://.*",
            ),
            # Email Configuration
            ConfigRule(
                name="BREVO_API_KEY",
                type=ConfigType.API_KEY,
                level=ConfigLevel.REQUIRED,
                description="Brevo (SendinBlue) API key for email services",
                pattern=r"^xkeysib-[a-f0-9]{64}-.*",
            ),
            ConfigRule(
                name="FROM_EMAIL",
                type=ConfigType.EMAIL,
                level=ConfigLevel.REQUIRED,
                description="Sender email address",
                default="noreply@lockbay.com",
            ),
            ConfigRule(
                name="ADMIN_EMAIL",
                type=ConfigType.EMAIL,
                level=ConfigLevel.REQUIRED,
                description="Admin email for alerts",
                default="admin@lockbay.com",
            ),
            # External API Keys
            ConfigRule(
                name="BLOCKBEE_API_KEY",
                type=ConfigType.API_KEY,
                level=ConfigLevel.REQUIRED,
                description="BlockBee API key for cryptocurrency operations",
            ),
            ConfigRule(
                name="FINCRA_API_KEY",
                type=ConfigType.API_KEY,
                level=ConfigLevel.REQUIRED,
                description="Fincra API key for NGN payments",
            ),
            ConfigRule(
                name="KRAKEN_API_KEY",
                type=ConfigType.API_KEY,
                level=ConfigLevel.REQUIRED,
                description="Kraken API key for cashouts",
            ),
            ConfigRule(
                name="KRAKEN_SECRET_KEY",
                type=ConfigType.API_KEY,
                level=ConfigLevel.REQUIRED,
                description="Kraken secret key",
                depends_on=["KRAKEN_API_KEY"],
            ),
            ConfigRule(
                name="TWILIO_ACCOUNT_SID",
                type=ConfigType.STRING,
                level=ConfigLevel.OPTIONAL,
                description="Twilio Account SID for SMS verification",
            ),
            ConfigRule(
                name="TWILIO_AUTH_TOKEN",
                type=ConfigType.API_KEY,
                level=ConfigLevel.OPTIONAL,
                description="Twilio Auth Token",
                depends_on=["TWILIO_ACCOUNT_SID"],
            ),
            # Financial Configuration
            ConfigRule(
                name="ESCROW_FEE_PERCENTAGE",
                type=ConfigType.FLOAT,
                level=ConfigLevel.OPTIONAL,
                description="Escrow fee percentage",
                default=5.0,
                min_value=0.0,
                max_value=50.0,
            ),
            ConfigRule(
                name="MIN_ESCROW_AMOUNT_USD",
                type=ConfigType.FLOAT,
                level=ConfigLevel.OPTIONAL,
                description="Minimum escrow amount in USD",
                default=5.0,
                min_value=1.0,
            ),
            ConfigRule(
                name="MAX_ESCROW_AMOUNT_USD",
                type=ConfigType.FLOAT,
                level=ConfigLevel.OPTIONAL,
                description="Maximum escrow amount in USD",
                default=500.0,
                min_value=100.0,
            ),
            ConfigRule(
                name="MIN_CASHOUT_AMOUNT",
                type=ConfigType.FLOAT,
                level=ConfigLevel.OPTIONAL,
                description="Minimum cashout amount",
                default=1.0,
                min_value=0.1,
            ),
            ConfigRule(
                name="MAX_CASHOUT_AMOUNT",
                type=ConfigType.FLOAT,
                level=ConfigLevel.OPTIONAL,
                description="Maximum cashout amount per transaction",
                default=10000.0,
                min_value=100.0,
            ),
            # Security Configuration - Support both ADMIN_IDS (preferred) and ADMIN_USER_IDS (legacy)
            ConfigRule(
                name="ADMIN_IDS",
                type=ConfigType.LIST,
                level=ConfigLevel.OPTIONAL,
                description="Comma-separated list of admin user IDs (preferred)",
            ),
            ConfigRule(
                name="ADMIN_USER_IDS",
                type=ConfigType.LIST,
                level=ConfigLevel.OPTIONAL,
                description="Comma-separated list of admin user IDs (fallback for compatibility)",
            ),
            ConfigRule(
                name="WEBHOOK_SECRET_TOKEN",
                type=ConfigType.API_KEY,
                level=ConfigLevel.OPTIONAL,
                description="Webhook secret token for security",
            ),
            # Feature Flags
            ConfigRule(
                name="AUTO_CASHOUT_ENABLED",
                type=ConfigType.BOOLEAN,
                level=ConfigLevel.OPTIONAL,
                description="Enable automatic cashouts",
                default=True,
            ),
            ConfigRule(
                name="CASHOUT_ADMIN_NOTIFICATIONS",
                type=ConfigType.BOOLEAN,
                level=ConfigLevel.OPTIONAL,
                description="Send admin notifications for cashout processing issues",
                default=True,
            ),
            ConfigRule(
                name="EMAIL_VERIFICATION_REQUIRED",
                type=ConfigType.BOOLEAN,
                level=ConfigLevel.OPTIONAL,
                description="Require email verification for new users",
                default=True,
            ),
            # Environment-Specific
            ConfigRule(
                name="ENVIRONMENT",
                type=ConfigType.STRING,
                level=ConfigLevel.OPTIONAL,
                description="Application environment",
                default="production",
                choices=["development", "staging", "production"],
            ),
            ConfigRule(
                name="DEBUG_MODE",
                type=ConfigType.BOOLEAN,
                level=ConfigLevel.OPTIONAL,
                description="Enable debug mode",
                default=False,
            ),
            ConfigRule(
                name="LOG_LEVEL",
                type=ConfigType.STRING,
                level=ConfigLevel.OPTIONAL,
                description="Logging level",
                default="INFO",
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            ),
            # Performance Configuration
            ConfigRule(
                name="MAX_CONCURRENT_JOBS",
                type=ConfigType.INTEGER,
                level=ConfigLevel.OPTIONAL,
                description="Maximum concurrent background jobs",
                default=10,
                min_value=1,
                max_value=100,
            ),
            ConfigRule(
                name="DATABASE_POOL_SIZE",
                type=ConfigType.INTEGER,
                level=ConfigLevel.OPTIONAL,
                description="Database connection pool size",
                default=20,
                min_value=5,
                max_value=100,
            ),
        ]

    def validate_all(self) -> ValidationResult:
        """Validate all configuration settings"""
        result = ValidationResult(is_valid=True)

        for rule in self.rules:
            value = os.getenv(rule.name)
            validation = self._validate_single(rule, value)

            if not validation.is_valid:
                result.is_valid = False
                result.errors.extend(validation.errors)

            result.warnings.extend(validation.warnings)

            if rule.level == ConfigLevel.REQUIRED and value is None:
                result.missing_required.append(rule.name)
                result.is_valid = False

            if rule.level == ConfigLevel.DEPRECATED and value is not None:
                result.deprecated_used.append(rule.name)

        # Check dependencies
        self._validate_dependencies(result)
        
        # Check admin ID configuration
        self._validate_admin_ids(result)

        # Generate suggestions
        self._generate_suggestions(result)

        return result

    def _validate_single(self, rule: ConfigRule, value: Any) -> ValidationResult:
        """Validate a single configuration value"""
        result = ValidationResult(is_valid=True)

        if value is None:
            if rule.level == ConfigLevel.REQUIRED:
                result.is_valid = False
                result.errors.append(f"{rule.name} is required but not set")
            return result

        # Type validation
        try:
            typed_value = self._convert_type(value, rule.type)
        except ValueError as e:
            result.is_valid = False
            result.errors.append(f"{rule.name}: {str(e)}")
            return result

        # Range validation
        if rule.min_value is not None and typed_value < rule.min_value:
            result.is_valid = False
            result.errors.append(f"{rule.name} must be >= {rule.min_value}")

        if rule.max_value is not None and typed_value > rule.max_value:
            result.is_valid = False
            result.errors.append(f"{rule.name} must be <= {rule.max_value}")

        # Pattern validation
        if rule.pattern and not re.match(rule.pattern, str(value)):
            result.is_valid = False
            result.errors.append(f"{rule.name} does not match required pattern")

        # Choice validation
        if rule.choices and str(typed_value).upper() not in [
            c.upper() for c in rule.choices
        ]:
            result.is_valid = False
            result.errors.append(
                f"{rule.name} must be one of: {', '.join(rule.choices)}"
            )

        # Custom validation
        if rule.validates_with:
            try:
                custom_result = rule.validates_with(typed_value)
                if not custom_result:
                    result.is_valid = False
                    result.errors.append(f"{rule.name} failed custom validation")
            except Exception as e:
                result.is_valid = False
                result.errors.append(f"{rule.name} validation error: {str(e)}")

        return result

    def _convert_type(self, value: str, config_type: ConfigType) -> Any:
        """Convert string value to appropriate type"""
        if config_type == ConfigType.STRING:
            return str(value)
        elif config_type == ConfigType.INTEGER:
            try:
                return int(value)
            except ValueError:
                raise ValueError(f"Invalid integer: {value}")
        elif config_type == ConfigType.FLOAT:
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Invalid float: {value}")
        elif config_type == ConfigType.BOOLEAN:
            return str(value).lower() in ("true", "1", "yes", "on")
        elif config_type == ConfigType.EMAIL:
            if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
                raise ValueError(f"Invalid email format: {value}")
            return str(value)
        elif config_type == ConfigType.URL:
            if not re.match(r"^https?://.*", value):
                raise ValueError(f"Invalid URL format: {value}")
            return str(value)
        elif config_type == ConfigType.API_KEY:
            if len(value) < 10:
                raise ValueError("API key too short")
            return str(value)
        elif config_type == ConfigType.LIST:
            return [item.strip() for item in value.split(",") if item.strip()]
        else:
            return str(value)

    def _validate_dependencies(self, result: ValidationResult):
        """Validate configuration dependencies"""
        for rule in self.rules:
            if rule.depends_on:
                value = os.getenv(rule.name)
                if value is not None:  # If this config is set
                    for dependency in rule.depends_on:
                        dep_value = os.getenv(dependency)
                        if dep_value is None:
                            result.is_valid = False
                            result.errors.append(
                                f"{rule.name} requires {dependency} to be set"
                            )

    def _validate_admin_ids(self, result: ValidationResult):
        """Validate that at least one admin ID configuration is present"""
        admin_ids = os.getenv("ADMIN_IDS")
        admin_user_ids = os.getenv("ADMIN_USER_IDS")
        
        if not admin_ids and not admin_user_ids:
            result.is_valid = False
            result.errors.append("At least one of ADMIN_IDS or ADMIN_USER_IDS must be set")
        elif not admin_ids and admin_user_ids:
            result.warnings.append("Using legacy ADMIN_USER_IDS - consider migrating to ADMIN_IDS")

    def _generate_suggestions(self, result: ValidationResult):
        """Generate helpful suggestions for configuration"""
        if "BOT_TOKEN" in result.missing_required:
            result.suggestions.append("Get BOT_TOKEN from @BotFather on Telegram")

        if "DATABASE_URL" in result.missing_required:
            result.suggestions.append(
                "Set DATABASE_URL to your PostgreSQL connection string"
            )

        if not os.getenv("ENVIRONMENT"):
            result.suggestions.append(
                "Set ENVIRONMENT to 'development', 'staging', or 'production'"
            )

        # Check for common configuration issues
        if (
            os.getenv("DEBUG_MODE") == "true"
            and os.getenv("ENVIRONMENT") == "production"
        ):
            result.warnings.append("DEBUG_MODE is enabled in production environment")

    def get_rule(self, name: str) -> Optional[ConfigRule]:
        """Get validation rule by name"""
        for rule in self.rules:
            if rule.name == name:
                return rule
        return None

    def print_validation_report(self, result: ValidationResult):
        """Print detailed validation report"""
        print("=" * 60)
        print("CONFIGURATION VALIDATION REPORT")
        print("=" * 60)

        if result.is_valid:
            print("✅ All configurations are valid!")
        else:
            print("❌ Configuration validation failed!")

        if result.errors:
            print(f"\n🚨 ERRORS ({len(result.errors)}):")
            for error in result.errors:
                print(f"  • {error}")

        if result.warnings:
            print(f"\n⚠️  WARNINGS ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"  • {warning}")

        if result.missing_required:
            print(f"\n📋 MISSING REQUIRED ({len(result.missing_required)}):")
            for missing in result.missing_required:
                rule = self.get_rule(missing)
                desc = rule.description if rule else "No description"
                print(f"  • {missing}: {desc}")

        if result.deprecated_used:
            print(f"\n🗑️  DEPRECATED USED ({len(result.deprecated_used)}):")
            for deprecated in result.deprecated_used:
                print(f"  • {deprecated}")

        if result.suggestions:
            print(f"\n💡 SUGGESTIONS ({len(result.suggestions)}):")
            for suggestion in result.suggestions:
                print(f"  • {suggestion}")

        print("=" * 60)


# Global validator instance
config_validator = ConfigValidator()


def validate_config() -> ValidationResult:
    """Convenience function to validate configuration"""
    return config_validator.validate_all()


def validate_on_startup():
    """Validate configuration on application startup"""
    logger.info("Validating application configuration...")

    result = validate_config()

    if not result.is_valid:
        logger.error("Configuration validation failed!")
        config_validator.print_validation_report(result)
        raise SystemExit("Invalid configuration. Please fix errors and restart.")

    if result.warnings:
        logger.warning(
            f"Configuration validation completed with {len(result.warnings)} warnings"
        )
        for warning in result.warnings:
            logger.warning(warning)
    else:
        logger.info("✅ Configuration validation completed successfully")

    return result

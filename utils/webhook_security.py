#!/usr/bin/env python3
"""
Webhook Security Utilities
Provides secure webhook signature verification for all payment providers
"""

import logging
import hmac
import hashlib
import json
import time
from typing import Dict, Any, Optional
from config import Config

logger = logging.getLogger(__name__)


class WebhookSecurityError(Exception):
    """Custom exception for webhook security violations"""

    pass


class WebhookSecurity:
    """Unified webhook security verification for all payment providers"""

    @classmethod
    def verify_telegram_webhook(cls, secret_token: str) -> bool:
        """Verify Telegram webhook secret token"""
        try:
            if not Config.WEBHOOK_SECRET_TOKEN:
                logger.warning("WEBHOOK_SECRET_TOKEN not configured for Telegram")
                return False

            if not secret_token:
                logger.warning("No secret token provided for Telegram webhook")
                return False

            # Use timing-safe comparison
            return hmac.compare_digest(Config.WEBHOOK_SECRET_TOKEN, secret_token)
        except Exception as e:
            logger.error(f"Error verifying Telegram webhook token: {e}")
            return False

    @classmethod
    def verify_fincra_webhook(cls, payload: Dict[str, Any], signature: str) -> bool:
        """Verify Fincra webhook signature using HMAC-SHA256"""
        try:
            # SECURITY FIX: Use consistent configuration naming with handlers
            fincra_secret = getattr(Config, "FINCRA_WEBHOOK_ENCRYPTION_KEY", None)
            if not fincra_secret:
                logger.error("FINCRA_WEBHOOK_ENCRYPTION_KEY not configured")
                return False

            if not signature:
                logger.warning("No signature provided for Fincra webhook")
                return False

            # Create signature string from payload (sorted JSON)
            payload_string = json.dumps(payload, separators=(",", ":"), sort_keys=True)
            expected_signature = hmac.new(
                fincra_secret.encode("utf-8"),
                payload_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            # Use timing-safe comparison
            is_valid = hmac.compare_digest(signature, expected_signature)

            if is_valid:
                logger.debug("Fincra webhook signature verified successfully")
            else:
                logger.warning("Fincra webhook signature verification failed")
                logger.debug(
                    f"Expected: {expected_signature[:16]}..., Got: {signature[:16]}..."
                )

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying Fincra webhook signature: {e}")
            return False

    @classmethod
    def verify_blockbee_webhook(cls, payload: Dict[str, Any], signature: str) -> bool:
        """Verify BlockBee webhook signature using HMAC-SHA256"""
        try:
            # Check if BlockBee webhook secret is configured
            blockbee_secret = getattr(Config, "BLOCKBEE_WEBHOOK_SECRET", None)
            is_production = getattr(Config, "ENVIRONMENT", "development").lower() in ["production", "prod"]
            
            if not blockbee_secret:
                if is_production:
                    # CRITICAL SECURITY FIX: Fail-closed in production when secret is missing
                    logger.critical("🚨 PRODUCTION_SECURITY_BREACH: BLOCKBEE_WEBHOOK_SECRET not configured in production")
                    return False
                else:
                    # Development mode: Allow basic validation fallback
                    logger.warning("⚠️ BLOCKBEE_WEBHOOK_SECRET not configured - using basic validation in development")
                    return cls._blockbee_basic_validation(payload, signature)

            if not signature:
                logger.warning("No signature provided for BlockBee webhook")
                return False

            # Create payload string for signature verification
            # BlockBee typically uses query parameter format for signature calculation
            if isinstance(payload, dict):
                # Convert dict to sorted query string format
                query_params = []
                for key, value in sorted(payload.items()):
                    if isinstance(value, dict):
                        for sub_key, sub_value in sorted(value.items()):
                            query_params.append(f"{key}[{sub_key}]={sub_value}")
                    else:
                        query_params.append(f"{key}={value}")
                payload_string = "&".join(query_params)
            else:
                payload_string = str(payload)

            # Calculate expected signature
            expected_signature = hmac.new(
                blockbee_secret.encode("utf-8"),
                payload_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            # Use timing-safe comparison
            is_valid = hmac.compare_digest(
                signature.lower(), expected_signature.lower()
            )

            if is_valid:
                logger.debug("BlockBee webhook signature verified successfully")
            else:
                logger.warning("BlockBee webhook signature verification failed")
                logger.debug(f"Payload string: {payload_string[:100]}...")
                logger.debug(
                    f"Expected: {expected_signature[:16]}..., Got: {signature[:16]}..."
                )

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying BlockBee webhook signature: {e}")
            return False

    @classmethod
    def _blockbee_basic_validation(
        cls, payload: Dict[str, Any], signature: str
    ) -> bool:
        """Basic BlockBee validation when webhook secret is not configured"""
        try:
            if not signature:
                logger.warning("No signature provided for BlockBee callback")
                return False

            # Validate signature format (should be hex)
            if not signature or len(signature) < 32:
                logger.warning(
                    f"Invalid BlockBee signature format: {signature[:20]}..."
                )
                return False

            # Check if signature is valid hex
            try:
                bytes.fromhex(signature)
            except ValueError:
                logger.warning("BlockBee signature is not valid hexadecimal")
                return False

            # Validate payload structure
            if not payload or not isinstance(payload, dict):
                logger.warning("Invalid payload structure for BlockBee callback")
                return False

            # Check for required fields in BlockBee callbacks
            required_fields = ["value", "currency", "confirmations"]
            for field in required_fields:
                if field not in payload:
                    logger.warning(
                        f"Missing required field '{field}' in BlockBee callback"
                    )
                    return False

            logger.info(
                f"BlockBee callback basic validation passed: {signature[:16]}..."
            )
            return True

        except Exception as e:
            logger.error(f"Error in BlockBee basic validation: {e}")
            return False

    @classmethod
    def verify_dynopay_webhook(cls, payload: Dict[str, Any], signature: str) -> bool:
        """Verify DynoPay webhook signature using HMAC-SHA256"""
        try:
            # Check if DynoPay webhook secret is configured
            dynopay_secret = getattr(Config, "DYNOPAY_WEBHOOK_SECRET", None)
            is_production = getattr(Config, "ENVIRONMENT", "development").lower() in ["production", "prod"]
            
            if not dynopay_secret:
                logger.error("DYNOPAY_WEBHOOK_SECRET not configured")
                if is_production:
                    logger.critical("🚨 PRODUCTION SECURITY: DynoPay webhook secret not configured - rejecting")
                    return False
                else:
                    logger.warning("⚠️ DEV SECURITY: DynoPay webhook secret not configured - allowing in development")
                    return True

            if not signature:
                # SECURITY ENHANCEMENT: Different handling for missing signatures
                if is_production:
                    logger.critical("🚨 PRODUCTION SECURITY: No signature provided for DynoPay webhook - rejecting")
                    cls.log_security_violation("dynopay", "unknown", "missing_signature", 
                                             "Production webhook received without required signature")
                    return False
                else:
                    logger.warning("⚠️ DEV SECURITY: No signature provided for DynoPay webhook - allowing in development")
                    logger.info("💡 INTEGRATION NOTE: Configure DynoPay to send signature headers for enhanced security")
                    return True

            # Create signature string from payload (sorted JSON)
            payload_string = json.dumps(payload, separators=(",", ":"), sort_keys=True)
            expected_signature = hmac.new(
                dynopay_secret.encode("utf-8"),
                payload_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            # Use timing-safe comparison to prevent timing attacks
            is_valid = hmac.compare_digest(signature.lower(), expected_signature.lower())

            if is_valid:
                logger.debug("DynoPay webhook signature verified successfully")
            else:
                logger.warning("DynoPay webhook signature verification failed")
                logger.warning(
                    f"Expected: {expected_signature[:16]}..., Got: {signature[:16]}..."
                )

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying DynoPay webhook signature: {e}")
            return False

    @classmethod
    def verify_webhook_signature(
        cls, provider: str, payload: Dict[str, Any], signature: str, **kwargs
    ) -> bool:
        """Universal webhook signature verification"""
        provider = provider.lower()

        try:
            if provider == "telegram":
                return cls.verify_telegram_webhook(signature)
            elif provider == "fincra":
                return cls.verify_fincra_webhook(payload, signature)
            elif provider == "blockbee":
                return cls.verify_blockbee_webhook(payload, signature)
            elif provider == "dynopay":
                return cls.verify_dynopay_webhook(payload, signature)
            else:
                logger.error(f"Unknown webhook provider: {provider}")
                return False

        except Exception as e:
            logger.error(f"Error verifying {provider} webhook signature: {e}")
            return False

    @classmethod
    def extract_webhook_signature(
        cls, headers: Dict[str, str], provider: str
    ) -> Optional[str]:
        """Extract webhook signature from headers based on provider"""
        provider = provider.lower()

        # Normalize headers to lowercase for case-insensitive lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}

        if provider == "telegram":
            return headers_lower.get("x-telegram-bot-api-secret-token")
        elif provider == "fincra":
            return headers_lower.get("x-fincra-signature")
        elif provider == "blockbee":
            # BlockBee may use different header names
            return (
                headers_lower.get("x-blockbee-signature")
                or headers_lower.get("x-signature")
                or headers_lower.get("signature")
            )
        elif provider == "dynopay":
            # DynoPay signature header names
            return (
                headers_lower.get("x-dynopay-signature")
                or headers_lower.get("x-signature")
                or headers_lower.get("signature")
            )
        else:
            logger.warning(f"Unknown provider for signature extraction: {provider}")
            return None

    @classmethod
    def log_security_violation(
        cls, provider: str, ip: str, violation_type: str, details: str = ""
    ) -> None:
        """Log security violations for monitoring and alerting with comprehensive tracking"""
        try:
            # ENHANCED SECURITY MONITORING: Comprehensive violation tracking
            violation_id = f"{provider}_{violation_type}_{int(time.time())}"
            
            logger.critical(
                f"🚨 SECURITY_VIOLATION - ID: {violation_id} | Provider: {provider.upper()} | "
                f"IP: {ip} | Type: {violation_type} | Details: {details}"
            )
            
            # SECURITY METRICS: Track violations for monitoring dashboard
            try:
                from utils.security_metrics import security_metrics_tracker
                security_metrics_tracker.record_violation(
                    provider=provider,
                    ip=ip,
                    violation_type=violation_type,
                    details=details,
                    violation_id=violation_id
                )
            except ImportError:
                logger.debug("Security metrics tracker not available - violation logged only")
            except Exception as metrics_e:
                logger.error(f"Failed to record security metrics: {metrics_e}")
            
            # ADMIN ALERTING: Send critical security alerts
            try:
                from services.admin_alert_service import AdminAlertService
                AdminAlertService.send_security_alert(
                    title=f"Webhook Security Violation - {provider.upper()}",
                    message=f"Violation ID: {violation_id}\nProvider: {provider}\nIP: {ip}\n"
                           f"Type: {violation_type}\nDetails: {details}",
                    priority="high" if violation_type in ["invalid_signature", "missing_signature"] else "medium"
                )
            except ImportError:
                logger.debug("Admin alert service not available - violation logged only")
            except Exception as alert_e:
                logger.error(f"Failed to send security alert: {alert_e}")
            
            # RATE LIMITING: Implement IP-based rate limiting for violations
            try:
                from utils.security_rate_limiter import security_rate_limiter
                should_block = security_rate_limiter.check_violation_rate(ip, violation_type)
                if should_block:
                    logger.critical(f"🛡️ SECURITY_AUTO_BLOCK: IP {ip} blocked due to repeated {violation_type} violations")
            except ImportError:
                logger.debug("Security rate limiter not available")
            except Exception as rate_e:
                logger.error(f"Failed to check violation rate limits: {rate_e}")

        except Exception as e:
            logger.error(f"Critical error in security violation logging: {e}")
            # Ensure violation is still logged even if enhanced features fail
            logger.critical(f"🚨 FALLBACK_SECURITY_LOG - {provider}: {violation_type} from {ip} - {details}")


class WebhookIdempotency:
    """Prevent duplicate webhook processing with idempotency protection"""

    @classmethod
    def generate_idempotency_key(cls, provider: str, payload: Dict[str, Any]) -> str:
        """Generate idempotency key for webhook deduplication"""
        try:
            # Create unique key based on provider and payload content
            key_parts = [provider]

            if provider == "fincra":
                # Use Fincra transaction reference
                key_parts.append(payload.get("data", {}).get("id", ""))
                key_parts.append(payload.get("data", {}).get("merchant_reference", ""))
            elif provider == "blockbee":
                # Use BlockBee transaction details
                key_parts.append(payload.get("txid_in", ""))
                key_parts.append(payload.get("address_in", ""))
                key_parts.append(str(payload.get("value", "")))
            else:
                # Generic approach - hash the entire payload
                payload_str = json.dumps(payload, sort_keys=True)
                key_parts.append(hashlib.sha256(payload_str.encode()).hexdigest()[:16])

            idempotency_key = "_".join(filter(None, key_parts))
            return hashlib.sha256(idempotency_key.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Error generating idempotency key: {e}")
            # Fallback to simple hash
            payload_str = str(payload)
            return hashlib.sha256(f"{provider}_{payload_str}".encode()).hexdigest()

    @classmethod
    def is_duplicate_webhook(cls, idempotency_key: str) -> bool:
        """Check if webhook has already been processed"""
        try:
            from database import SessionLocal
            from models import WebhookLog

            session = SessionLocal()
            try:
                existing = (
                    session.query(WebhookLog)
                    .filter(WebhookLog.idempotency_key == idempotency_key)
                    .first()
                )

                return existing is not None

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error checking webhook idempotency: {e}")
            # Fail safe - allow processing if we can't check
            return False

    @classmethod
    def mark_webhook_processed(
        cls,
        idempotency_key: str,
        provider: str,
        payload: Dict[str, Any],
        success: bool = True,
    ) -> None:
        """Mark webhook as processed to prevent duplicates"""
        try:
            from database import SessionLocal
            from models import WebhookLog
            from datetime import datetime

            session = SessionLocal()
            try:
                webhook_log = WebhookLog(
                    idempotency_key=idempotency_key,
                    provider=provider,
                    payload=payload,
                    processed_at=datetime.utcnow(),
                    success=success,
                )
                session.add(webhook_log)
                session.commit()

                logger.debug(f"Marked webhook as processed: {idempotency_key}")

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error marking webhook as processed: {e}")
            # Non-critical error - don't fail the webhook processing

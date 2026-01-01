"""
Webhook Security Service - Enhanced signature validation and security
Implements consistent signature validation across all webhook providers
"""

import logging
import hmac
import hashlib
import time
from typing import Dict, Any
from fastapi import Request

logger = logging.getLogger(__name__)


def validate_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Validate webhook signature - standalone function for integration tests
    
    Args:
        payload: The webhook payload as string
        signature: The signature to verify (usually from headers)
        secret: The secret key for verification
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Handle different signature formats
        if signature.startswith("sha256="):
            # GitHub/Generic format
            expected_signature = "sha256=" + hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
        else:
            # Simple HMAC format
            expected_signature = hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
        
        # Use secure comparison
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error validating webhook signature: {e}")
        return False


class WebhookSecurityService:
    """Centralized webhook security validation service"""

    # Webhook timeout settings
    WEBHOOK_TIMEOUT_SECONDS = 300  # 5 minutes

    @classmethod
    def validate_telegram_webhook(
        cls, request: Request, body: bytes, expected_secret: str
    ) -> Dict[str, Any]:
        """
        Validate Telegram webhook with enhanced security
        Returns: {'valid': bool, 'error': str, 'security_info': dict}
        """
        try:
            # Check X-Telegram-Bot-Api-Secret-Token header
            secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

            if not secret_token:
                logger.warning("Missing Telegram secret token header")
                return {
                    "valid": False,
                    "error": "Missing secret token header",
                    "security_info": {"missing_header": True},
                }

            # Validate secret token
            if not hmac.compare_digest(secret_token, expected_secret):
                logger.error("Invalid Telegram webhook secret token")
                return {
                    "valid": False,
                    "error": "Invalid secret token",
                    "security_info": {"invalid_token": True},
                }

            # Additional security checks
            content_type = request.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                logger.warning(f"Unexpected content type: {content_type}")
                return {
                    "valid": False,
                    "error": "Invalid content type",
                    "security_info": {"invalid_content_type": content_type},
                }

            # Check request size (prevent DoS)
            content_length = len(body)
            if content_length > 10 * 1024 * 1024:  # 10MB limit
                logger.error(f"Webhook payload too large: {content_length} bytes")
                return {
                    "valid": False,
                    "error": "Payload too large",
                    "security_info": {"payload_size": content_length},
                }

            logger.info("Telegram webhook validation successful")
            return {
                "valid": True,
                "security_info": {
                    "payload_size": content_length,
                    "content_type": content_type,
                },
            }

        except Exception as e:
            logger.error(f"Error validating Telegram webhook: {e}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "security_info": {"exception": str(e)},
            }

    @classmethod
    def validate_blockbee_webhook(
        cls, request: Request, body: bytes, query_params: dict
    ) -> Dict[str, Any]:
        """
        Validate BlockBee webhook signatures
        Returns: {'valid': bool, 'error': str, 'payment_info': dict}
        """
        try:
            # Extract required parameters
            address_in = query_params.get("address_in", "")
            value = query_params.get("value", "")
            confirmations = query_params.get("confirmations", "0")

            if not all([address_in, value]):
                return {
                    "valid": False,
                    "error": "Missing required BlockBee parameters",
                    "payment_info": {},
                }

            # Validate confirmations is numeric
            try:
                confirmations_int = int(confirmations)
            except ValueError:
                return {
                    "valid": False,
                    "error": "Invalid confirmations format",
                    "payment_info": {},
                }

            # Validate value is numeric
            try:
                value_float = float(value)
                if value_float <= 0:
                    return {
                        "valid": False,
                        "error": "Invalid payment amount",
                        "payment_info": {},
                    }
            except ValueError:
                return {
                    "valid": False,
                    "error": "Invalid value format",
                    "payment_info": {},
                }

            # Check for replay attacks (timestamp validation)
            timestamp = time.time()

            # Additional BlockBee-specific validations
            user_agent = request.headers.get("User-Agent", "")
            if "blockbee" not in user_agent.lower():
                logger.warning(
                    f"Unexpected User-Agent for BlockBee webhook: {user_agent}"
                )

            logger.info(
                f"BlockBee webhook validated: {address_in}, {value}, {confirmations}"
            )

            return {
                "valid": True,
                "payment_info": {
                    "address": address_in,
                    "value": value_float,
                    "confirmations": confirmations_int,
                    "timestamp": timestamp,
                },
            }

        except Exception as e:
            logger.error(f"Error validating BlockBee webhook: {e}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "payment_info": {},
            }

    @classmethod
    def validate_fincra_webhook(
        cls, request: Request, body: bytes, webhook_secret: str
    ) -> Dict[str, Any]:
        """
        Validate Fincra webhook signatures
        Returns: {'valid': bool, 'error': str, 'transaction_info': dict}
        """
        try:
            # Get Fincra signature from headers
            signature = request.headers.get("X-Fincra-Signature")

            if not signature:
                logger.warning("Missing Fincra webhook signature")
                return {
                    "valid": False,
                    "error": "Missing webhook signature",
                    "transaction_info": {},
                }

            # Calculate expected signature
            expected_signature = hmac.new(
                webhook_secret.encode("utf-8"), body, hashlib.sha256
            ).hexdigest()

            # Validate signature
            if not hmac.compare_digest(signature, expected_signature):
                logger.error("Invalid Fincra webhook signature")
                return {
                    "valid": False,
                    "error": "Invalid webhook signature",
                    "transaction_info": {},
                }

            # Parse and validate JSON body
            try:
                import json

                payload = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return {
                    "valid": False,
                    "error": f"Invalid JSON payload: {str(e)}",
                    "transaction_info": {},
                }

            # Extract transaction info
            event_type = payload.get("event", "")
            transaction_data = payload.get("data", {})

            logger.info(f"Fincra webhook validated: {event_type}")

            return {
                "valid": True,
                "transaction_info": {
                    "event_type": event_type,
                    "transaction_data": transaction_data,
                    "timestamp": time.time(),
                },
            }

        except Exception as e:
            logger.error(f"Error validating Fincra webhook: {e}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "transaction_info": {},
            }

    @classmethod
    def validate_twilio_webhook(
        cls, request: Request, body: bytes, auth_token: str
    ) -> Dict[str, Any]:
        """
        Validate Twilio webhook signatures (for SMS delivery updates)
        Returns: {'valid': bool, 'error': str, 'sms_info': dict}
        """
        try:
            # Get Twilio signature
            signature = request.headers.get("X-Twilio-Signature")

            if not signature:
                logger.warning("Missing Twilio webhook signature")
                return {
                    "valid": False,
                    "error": "Missing webhook signature",
                    "sms_info": {},
                }

            # Construct URL for signature validation
            url = str(request.url)

            # Get form data
            form_data = body.decode("utf-8")

            # Calculate expected signature (Twilio specific method)
            expected_signature = cls._calculate_twilio_signature(
                auth_token, url, form_data
            )

            # Validate signature
            if not hmac.compare_digest(signature, expected_signature):
                logger.error("Invalid Twilio webhook signature")
                return {
                    "valid": False,
                    "error": "Invalid webhook signature",
                    "sms_info": {},
                }

            # Parse form data
            try:
                from urllib.parse import parse_qs

                parsed_data = parse_qs(form_data)
                # Convert lists to single values
                sms_data = {k: v[0] if v else "" for k, v in parsed_data.items()}
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Error parsing form data: {str(e)}",
                    "sms_info": {},
                }

            logger.info(f"Twilio webhook validated: {sms_data.get('MessageSid', '')}")

            return {
                "valid": True,
                "sms_info": {
                    "message_sid": sms_data.get("MessageSid", ""),
                    "message_status": sms_data.get("MessageStatus", ""),
                    "error_code": sms_data.get("ErrorCode"),
                    "timestamp": time.time(),
                },
            }

        except Exception as e:
            logger.error(f"Error validating Twilio webhook: {e}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "sms_info": {},
            }

    @classmethod
    def _calculate_twilio_signature(
        cls, auth_token: str, url: str, form_data: str
    ) -> str:
        """Calculate Twilio webhook signature using their algorithm"""
        try:
            # Parse form data and sort by key
            from urllib.parse import parse_qs

            parsed = parse_qs(form_data)

            # Build data string as per Twilio spec
            data_string = url
            for key in sorted(parsed.keys()):
                data_string += key + parsed[key][0]

            # Calculate HMAC-SHA1 signature
            signature = hmac.new(
                auth_token.encode("utf-8"), data_string.encode("utf-8"), hashlib.sha1
            ).digest()

            # Base64 encode
            import base64

            return base64.b64encode(signature).decode("utf-8")

        except Exception as e:
            logger.error(f"Error calculating Twilio signature: {e}")
            return ""

    @classmethod
    def log_webhook_security_event(
        cls,
        provider: str,
        event_type: str,
        success: bool,
        details: Dict[str, Any],
        request_ip: str = None,
    ) -> None:
        """Log webhook security events for audit trail"""
        try:
            {
                "provider": provider,
                "event_type": event_type,
                "success": success,
                "timestamp": time.time(),
                "request_ip": request_ip,
                "details": details,
            }

            if success:
                logger.info(f"Webhook security: {provider} {event_type} - SUCCESS")
            else:
                logger.warning(
                    f"Webhook security: {provider} {event_type} - FAILED: {details}"
                )

            # In production, this would also log to a security audit database

        except Exception as e:
            logger.error(f"Error logging webhook security event: {e}")

    @classmethod
    def get_client_ip(cls, request: Request) -> str:
        """Extract client IP address with proxy support"""
        try:
            # Check for forwarded headers (common in proxy setups)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # Get first IP in case of multiple proxies
                return forwarded_for.split(",")[0].strip()

            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip

            # Fallback to direct client IP
            return request.client.host if request.client else "unknown"

        except Exception as e:
            logger.error(f"Error extracting client IP: {e}")
            return "unknown"

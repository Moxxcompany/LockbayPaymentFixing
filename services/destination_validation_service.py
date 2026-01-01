#!/usr/bin/env python3
"""
Comprehensive Destination Validation Service
Handles validation for SavedAddress and SavedBankAccount with security-first approach
"""

import logging
from typing import Dict, Any
from models import SavedAddress, SavedBankAccount, User

logger = logging.getLogger(__name__)


class DestinationValidationService:
    """Centralized validation service for crypto addresses and bank accounts"""

    # Supported cryptocurrency networks - includes both currency codes and full names
    SUPPORTED_NETWORKS = [
        "TRC20", "ERC20", "BTC", "LTC", "DOGE", "BCH", "BSC", "TRX",
        "Bitcoin", "Litecoin", "Dogecoin", "BitcoinCash", "Ethereum", "Tron",
        "USDT-TRC20", "USDT-ERC20"
    ]

    # Nigerian bank account validation rules
    NIGERIAN_ACCOUNT_LENGTH = 10

    @staticmethod
    def validate_saved_address(address: SavedAddress) -> Dict[str, Any]:
        """
        Comprehensive validation of a SavedAddress record
        Returns: {'valid': bool, 'errors': List[str], 'warnings': List[str]}
        """
        result = {"valid": True, "errors": [], "warnings": []}

        try:
            # Check for missing required fields using proper attribute access
            address_value = getattr(address, "address", None)
            currency_value = getattr(address, "currency", None)
            network_value = getattr(address, "network", None)

            if not address_value:
                result["errors"].append("Address field is empty")
                result["valid"] = False

            if not currency_value:
                result["errors"].append("Currency field is empty")
                result["valid"] = False

            if not network_value:
                result["errors"].append("Network field is empty")
                result["valid"] = False

            # If basic fields are missing, skip format validation
            if not result["valid"]:
                return result

            # Validate address format using existing detector
            if address_value:
                try:
                    from utils.address_detector import detect_network_from_address

                    detected_currency, is_valid = detect_network_from_address(address_value)
                    if not is_valid:
                        result["errors"].append(
                            f"Invalid address format: {address_value[:10]}..."
                        )
                        result["valid"] = False
                except ImportError:
                    result["warnings"].append("Address format validation unavailable")

            # Validate network support
            if (
                network_value
                and network_value not in DestinationValidationService.SUPPORTED_NETWORKS
            ):
                result["errors"].append(f"Unsupported network: {network_value}")
                result["valid"] = False

            # Check address length constraints
            if address_value:
                if len(address_value) < 20:
                    result["warnings"].append("Address appears too short")
                elif len(address_value) > 100:
                    result["warnings"].append("Address appears too long")

            # Network-specific validations
            if address_value and network_value:
                if network_value == "BTC" and not address_value.startswith(
                    ("1", "3", "bc1")
                ):
                    result["errors"].append("Invalid Bitcoin address format")
                    result["valid"] = False

                elif network_value in ["ERC20", "BSC"] and not (
                    address_value.startswith("0x") and len(address_value) == 42
                ):
                    result["errors"].append(f"Invalid {network_value} address format")
                    result["valid"] = False

                elif network_value == "TRC20" and not (
                    address_value.startswith("T") and len(address_value) == 34
                ):
                    result["errors"].append("Invalid TRC20 address format")
                    result["valid"] = False

        except Exception as e:
            logger.error(f"Error validating saved address {address.id}: {e}")
            result["errors"].append(f"Validation error: {str(e)}")
            result["valid"] = False

        return result

    @staticmethod
    def validate_saved_bank_account(bank_account: SavedBankAccount) -> Dict[str, Any]:
        """
        Comprehensive validation of a SavedBankAccount record
        Returns: {'valid': bool, 'errors': List[str], 'warnings': List[str]}
        """
        result = {"valid": True, "errors": [], "warnings": []}

        try:
            # Check for missing required fields using proper attribute access
            account_number = getattr(bank_account, "account_number", None)
            bank_code = getattr(bank_account, "bank_code", None)
            account_name = getattr(bank_account, "account_name", None)
            bank_name = getattr(bank_account, "bank_name", None)

            if not account_number:
                result["errors"].append("Account number is empty")
                result["valid"] = False

            if not bank_code:
                result["errors"].append("Bank code is empty")
                result["valid"] = False

            if not account_name:
                result["errors"].append("Account name is empty")
                result["valid"] = False

            if not bank_name:
                result["errors"].append("Bank name is empty")
                result["valid"] = False

            # If basic fields are missing, skip format validation
            if not result["valid"]:
                return result

            # Validate account number format (Nigerian banks)
            if account_number:
                if not account_number.isdigit():
                    result["errors"].append("Account number must contain only digits")
                    result["valid"] = False

                if (
                    len(account_number)
                    != DestinationValidationService.NIGERIAN_ACCOUNT_LENGTH
                ):
                    result["errors"].append(
                        f"Account number must be exactly {DestinationValidationService.NIGERIAN_ACCOUNT_LENGTH} digits"
                    )
                    result["valid"] = False

            # Validate bank code format
            if bank_code and len(bank_code) < 3:
                result["errors"].append("Bank code too short")
                result["valid"] = False

            # Validate account name
            if account_name and len(account_name.strip()) < 3:
                result["errors"].append("Account name too short")
                result["valid"] = False

            # Check for suspicious patterns
            if account_name and account_name.lower() in ["test", "demo", "sample"]:
                result["warnings"].append("Account name appears to be test data")

        except Exception as e:
            logger.error(f"Error validating saved bank account {bank_account.id}: {e}")
            result["errors"].append(f"Validation error: {str(e)}")
            result["valid"] = False

        return result

    @staticmethod
    def validate_user_destinations(user: User, session) -> Dict[str, Any]:
        """
        Validate all saved destinations for a user
        Returns: {'crypto_issues': List, 'bank_issues': List, 'auto_cashout_safe': bool}
        """
        result = {
            "crypto_issues": [],
            "bank_issues": [],
            "auto_cashout_safe": True,
            "total_issues": 0,
        }

        try:
            # Validate saved crypto addresses
            saved_addresses = (
                session.query(SavedAddress)
                .filter(SavedAddress.user_id == user.id)
                .all()
            )

            for address in saved_addresses:
                validation = DestinationValidationService.validate_saved_address(
                    address
                )
                if not validation["valid"]:
                    result["crypto_issues"].append(
                        {
                            "address_id": address.id,
                            "currency": address.currency,
                            "network": address.network,
                            "errors": validation["errors"],
                            "warnings": validation["warnings"],
                        }
                    )
                    result["total_issues"] += 1

            # Validate saved bank accounts
            saved_banks = (
                session.query(SavedBankAccount)
                .filter(SavedBankAccount.user_id == user.id)
                .all()
            )

            for bank in saved_banks:
                validation = DestinationValidationService.validate_saved_bank_account(
                    bank
                )
                if not validation["valid"]:
                    result["bank_issues"].append(
                        {
                            "bank_id": bank.id,
                            "bank_name": bank.bank_name,
                            "account_number": bank.account_number,
                            "errors": validation["errors"],
                            "warnings": validation["warnings"],
                        }
                    )
                    result["total_issues"] += 1

            # Check auto-cashout safety using proper attribute access
            auto_cashout_enabled = getattr(user, "auto_cashout_enabled", False)
            cashout_preference = getattr(user, "cashout_preference", None)
            crypto_address_id = getattr(user, "auto_cashout_crypto_address_id", None)
            bank_account_id = getattr(user, "auto_cashout_bank_account_id", None)

            if auto_cashout_enabled:
                if cashout_preference == "CRYPTO" and crypto_address_id:
                    # Find auto-cashout crypto address in issues
                    for issue in result["crypto_issues"]:
                        if issue["address_id"] == crypto_address_id:
                            result["auto_cashout_safe"] = False
                            break

                elif cashout_preference == "NGN_BANK" and bank_account_id:
                    # Find auto-cashout bank account in issues
                    for issue in result["bank_issues"]:
                        if issue["bank_id"] == bank_account_id:
                            result["auto_cashout_safe"] = False
                            break

        except Exception as e:
            logger.error(f"Error validating user destinations for user {user.id}: {e}")
            result["total_issues"] += 1

        return result

    @staticmethod
    def safe_disable_auto_cashout(user: User, session, reason: str) -> bool:
        """
        Safely disable auto-cashout for a user with logging
        Returns: True if disabled, False if error
        """
        try:
            auto_cashout_enabled = getattr(user, "auto_cashout_enabled", False)
            if auto_cashout_enabled:
                # Use setattr to properly update the attribute
                setattr(user, "auto_cashout_enabled", False)
                session.commit()
                user_id = getattr(user, "id", "unknown")
                logger.warning(f"Auto-cashout disabled for user {user_id}: {reason}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error disabling auto-cashout for user {user.id}: {e}")
            return False

    @staticmethod
    def get_validation_error_message(
        validation_result: Dict[str, Any], destination_type: str
    ) -> str:
        """
        Generate user-friendly error message from validation result
        """
        if validation_result["valid"]:
            return ""

        errors = validation_result.get("errors", [])
        if not errors:
            return f"❌ {destination_type} validation failed"

        if len(errors) == 1:
            return f"❌ {errors[0]}"
        else:
            return "❌ Multiple issues found:\n" + "\n".join(
                f"• {error}" for error in errors[:3]
            )

    @staticmethod
    def clean_invalid_destinations(user: User, session) -> Dict[str, int]:
        """
        Remove invalid destinations and return count of cleaned items
        Returns: {'addresses_removed': int, 'banks_removed': int}
        """
        result = {"addresses_removed": 0, "banks_removed": 0}

        try:
            # Clean invalid addresses
            saved_addresses = (
                session.query(SavedAddress)
                .filter(SavedAddress.user_id == user.id)
                .all()
            )

            for address in saved_addresses:
                validation = DestinationValidationService.validate_saved_address(
                    address
                )
                if not validation["valid"]:
                    # If this was the auto-cashout address, disable auto-cashout
                    if user.auto_cashout_crypto_address_id == address.id:
                        DestinationValidationService.safe_disable_auto_cashout(
                            user,
                            session,
                            f"Invalid crypto address removed: {address.id}",
                        )

                    session.delete(address)
                    result["addresses_removed"] += 1
                    logger.info(
                        f"Removed invalid address {address.id} for user {user.id}"
                    )

            # Clean invalid bank accounts
            saved_banks = (
                session.query(SavedBankAccount)
                .filter(SavedBankAccount.user_id == user.id)
                .all()
            )

            for bank in saved_banks:
                validation = DestinationValidationService.validate_saved_bank_account(
                    bank
                )
                if not validation["valid"]:
                    # If this was the auto-cashout bank account, disable auto-cashout
                    if user.auto_cashout_bank_account_id == bank.id:
                        DestinationValidationService.safe_disable_auto_cashout(
                            user, session, f"Invalid bank account removed: {bank.id}"
                        )

                    session.delete(bank)
                    result["banks_removed"] += 1
                    logger.info(
                        f"Removed invalid bank account {bank.id} for user {user.id}"
                    )

            session.commit()

        except Exception as e:
            logger.error(f"Error cleaning invalid destinations for user {user.id}: {e}")
            session.rollback()

        return result

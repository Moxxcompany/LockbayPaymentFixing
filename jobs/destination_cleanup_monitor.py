#!/usr/bin/env python3
"""
Destination Cleanup Monitor
Periodic job to clean up invalid saved addresses and bank accounts
"""

import logging
from database import SessionLocal
from models import User
from services.destination_validation_service import DestinationValidationService

logger = logging.getLogger(__name__)


class DestinationCleanupMonitor:
    """Monitor and clean up invalid destinations across the system"""

    @staticmethod
    async def run_cleanup():
        """
        Run comprehensive cleanup of invalid destinations
        """
        session = SessionLocal()
        total_cleaned = {"addresses": 0, "banks": 0, "users_affected": 0}

        try:
            # Get all users to check their destinations
            users = session.query(User).all()

            logger.info(f"Starting destination cleanup for {len(users)} users")

            for user in users:
                try:
                    # Clean invalid destinations for this user
                    cleanup_result = (
                        DestinationValidationService.clean_invalid_destinations(
                            user, session
                        )
                    )

                    if (
                        cleanup_result["addresses_removed"] > 0
                        or cleanup_result["banks_removed"] > 0
                    ):
                        total_cleaned["addresses"] += cleanup_result[
                            "addresses_removed"
                        ]
                        total_cleaned["banks"] += cleanup_result["banks_removed"]
                        total_cleaned["users_affected"] += 1

                        logger.info(
                            f"User {user.id}: Cleaned {cleanup_result['addresses_removed']} addresses, {cleanup_result['banks_removed']} banks"
                        )

                except Exception as e:
                    logger.error(f"Error cleaning destinations for user {user.id}: {e}")
                    continue

            logger.info(
                f"Destination cleanup completed: {total_cleaned['addresses']} addresses, {total_cleaned['banks']} banks removed from {total_cleaned['users_affected']} users"
            )

        except Exception as e:
            logger.error(f"Error in destination cleanup monitor: {e}")
        finally:
            session.close()

    @staticmethod
    async def validate_auto_cashout_destinations():
        """
        Validate and fix auto-cashout destination issues
        """
        session = SessionLocal()
        fixed_count = 0

        try:
            # Get users with auto-cashout enabled
            auto_cashout_users = (
                session.query(User).filter(User.auto_cashout_enabled).all()
            )

            logger.info(
                f"Validating auto-cashout destinations for {len(auto_cashout_users)} users"
            )

            for user in auto_cashout_users:
                try:
                    # Run comprehensive validation
                    validation_result = (
                        DestinationValidationService.validate_user_destinations(
                            user, session
                        )
                    )

                    if not validation_result["auto_cashout_safe"]:
                        # Auto-cashout destination is invalid - disable it
                        reason = f"Invalid destination detected: {len(validation_result['crypto_issues'])} crypto issues, {len(validation_result['bank_issues'])} bank issues"
                        success = (
                            DestinationValidationService.safe_disable_auto_cashout(
                                user, session, reason
                            )
                        )

                        if success:
                            fixed_count += 1
                            logger.warning(
                                f"Disabled auto-cashout for user {user.id}: {reason}"
                            )

                except Exception as e:
                    logger.error(
                        f"Error validating auto-cashout for user {user.id}: {e}"
                    )
                    continue

            logger.info(
                f"Auto-cashout validation completed: {fixed_count} users had auto-cashout disabled due to invalid destinations"
            )

        except Exception as e:
            logger.error(f"Error in auto-cashout destination validation: {e}")
        finally:
            session.close()

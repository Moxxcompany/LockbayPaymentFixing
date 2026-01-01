"""
Enhanced Contact Detection Service
Intelligently detects user contact methods and provides smart multi-channel notification routing
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import and_, func
from database import SessionLocal
from models import User, UserContact, NotificationActivity
import re
import phonenumbers

logger = logging.getLogger(__name__)


@dataclass
class ContactInfo:
    """Enhanced contact information with activity metrics"""

    contact_type: str  # telegram, email, phone
    contact_value: str
    is_verified: bool
    is_primary: bool
    avg_response_time: float  # hours
    last_used: Optional[datetime]
    notification_enabled: bool
    user_id: int


@dataclass
class UserContactProfile:
    """Complete contact profile for a user with smart routing suggestions"""

    user_id: int
    telegram_id: Optional[str]
    username: Optional[str]
    primary_email: str
    phone_number: Optional[str]
    additional_contacts: List[ContactInfo]

    # Activity metrics for intelligent routing
    telegram_response_time: float
    email_response_time: float
    sms_response_time: float

    # Smart routing suggestions
    preferred_channel: str
    all_verified_channels: List[str]
    fastest_channel: str


class ContactDetectionService:
    """Service for detecting and managing user contact information with smart routing"""

    def __init__(self):
        self.session = None
    
    def __enter__(self):
        """Context manager entry"""
        self._get_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures session cleanup"""
        self.close_session()
        return False
    
    def _get_session(self):
        """Get or create database session"""
        if self.session is None:
            self.session = SessionLocal()
        return self.session
    
    def close_session(self):
        """Close database session"""
        if self.session:
            try:
                self.session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            finally:
                self.session = None

    def find_user_by_contact(
        self, contact_value: str, contact_type: str = None
    ) -> Optional[UserContactProfile]:
        """
        Find user by email, phone number, or username with complete contact profile

        Args:
            contact_value: Email, phone number, or username
            contact_type: Optional hint about contact type

        Returns:
            Complete UserContactProfile if found, None otherwise
        """
        try:
            contact_value = contact_value.strip().lower()

            # Auto-detect contact type if not provided
            if not contact_type:
                contact_type = self._detect_contact_type(contact_value)

            user = None

            if contact_type == "email":
                user = self._find_user_by_email(contact_value)
            elif contact_type == "phone":
                user = self._find_user_by_phone(contact_value)
            elif contact_type == "username":
                user = self._find_user_by_username(contact_value)

            if user:
                return self._build_contact_profile(user)

            return None

        except Exception as e:
            logger.error(f"Error finding user by contact {contact_value}: {e}")
            return None

    def get_all_linked_contacts(self, user_id: int) -> List[ContactInfo]:
        """Get all verified contact methods for a user"""
        try:
            # Get primary contacts from user table
            user = self._get_session().query(User).filter(User.id == user_id).first()
            if not user:
                return []

            contacts = []

            # Add telegram contact
            if user.telegram_id is not None:
                contacts.append(
                    ContactInfo(
                        contact_type="telegram",
                        contact_value=str(user.telegram_id),
                        is_verified=True,  # Telegram is always verified
                        is_primary=True,
                        avg_response_time=(
                            float(user.telegram_response_time_avg)
                            if user.telegram_response_time_avg
                            else 0.0
                        ),
                        last_used=user.telegram_last_seen,
                        notification_enabled=True,
                        user_id=user_id,
                    )
                )

            # Add primary email
            if user.email is not None and user.email_verified is True:
                contacts.append(
                    ContactInfo(
                        contact_type="email",
                        contact_value=str(user.email),
                        is_verified=bool(user.email_verified),
                        is_primary=True,
                        avg_response_time=(
                            float(user.email_response_time_avg)
                            if user.email_response_time_avg
                            else 24.0
                        ),
                        last_used=user.email_last_opened,
                        notification_enabled=True,
                        user_id=user_id,
                    )
                )

            # Add primary phone
            if user.phone_number is not None and user.phone_verified is True:
                contacts.append(
                    ContactInfo(
                        contact_type="phone",
                        contact_value=str(user.phone_number),
                        is_verified=bool(user.phone_verified),
                        is_primary=True,
                        avg_response_time=(
                            float(user.sms_response_time_avg)
                            if user.sms_response_time_avg
                            else 2.0
                        ),
                        last_used=user.sms_last_received,
                        notification_enabled=True,
                        user_id=user_id,
                    )
                )

            # Add additional verified contacts
            additional = (
                self._get_session().query(UserContact)
                .filter(
                    and_(
                        UserContact.user_id == user_id,
                        UserContact.is_verified,
                        UserContact.is_active,
                        UserContact.notification_enabled,
                    )
                )
                .all()
            )

            for contact in additional:
                contacts.append(
                    ContactInfo(
                        contact_type=str(contact.contact_type),
                        contact_value=str(contact.contact_value),
                        is_verified=bool(contact.is_verified),
                        is_primary=bool(contact.is_primary),
                        avg_response_time=(
                            float(contact.avg_response_time)
                            if contact.avg_response_time
                            else 0.0
                        ),
                        last_used=contact.last_used,
                        notification_enabled=bool(contact.notification_enabled),
                        user_id=user_id,
                    )
                )

            return contacts

        except Exception as e:
            logger.error(f"Error getting linked contacts for user {user_id}: {e}")
            return []

    def get_smart_notification_channels(
        self, user_id: int, specified_contact: str = ""
    ) -> List[Tuple[str, str, int]]:
        """
        Get smart-ordered notification channels for a user

        Args:
            user_id: User ID
            specified_contact: Contact method buyer specified (email/phone/username)

        Returns:
            List of (channel_type, contact_value, priority) tuples ordered by effectiveness
        """
        try:
            contacts = self.get_all_linked_contacts(user_id)
            if not contacts:
                return []

            # Build channel priority list
            channels = []

            # If buyer specified a contact, add it first (highest priority)
            if specified_contact and specified_contact.strip():
                for contact in contacts:
                    if contact.contact_value.lower() == specified_contact.lower():
                        channels.append(
                            (contact.contact_type, contact.contact_value, 1)
                        )
                        break

            # Add channels by response time (fastest first)
            sorted_contacts = sorted(contacts, key=lambda x: x.avg_response_time)

            for i, contact in enumerate(sorted_contacts):
                # Skip if already added as specified contact
                channel_tuple = (contact.contact_type, contact.contact_value, i + 2)
                if channel_tuple not in channels:
                    channels.append(channel_tuple)

            return channels

        except Exception as e:
            logger.error(
                f"Error getting smart notification channels for user {user_id}: {e}"
            )
            return []

    def detect_linked_users(
        self, contact_values: List[str]
    ) -> Dict[str, UserContactProfile]:
        """
        Detect if any contact values belong to existing users

        Args:
            contact_values: List of emails, phones, or usernames

        Returns:
            Dict mapping contact_value -> UserContactProfile
        """
        try:
            results = {}

            for contact_value in contact_values:
                profile = self.find_user_by_contact(contact_value)
                if profile:
                    results[contact_value] = profile

            return results

        except Exception as e:
            logger.error(f"Error detecting linked users: {e}")
            return {}

    def should_send_multi_channel_notification(
        self, user_id: int, notification_type: str
    ) -> bool:
        """
        Determine if we should send multi-channel notifications for this user/notification type

        Args:
            user_id: User ID
            notification_type: Type of notification (escrow_invite, payment_received, etc.)

        Returns:
            True if multi-channel notifications are recommended
        """
        try:
            user = self._get_session().query(User).filter(User.id == user_id).first()
            if not user:
                return False

            # Get user's notification preferences
            preferences = user.notification_preferences or {}

            # Check if user has enabled multi-channel notifications
            multi_channel_enabled = preferences.get("multi_channel_notifications", True)

            # Check if this notification type should use multi-channel
            important_notifications = [
                "escrow_invite",
                "payment_received",
                "payment_confirmed",
                "trade_completed",
                "dispute_opened",
            ]

            is_important = notification_type in important_notifications

            return multi_channel_enabled and is_important

        except Exception as e:
            logger.error(f"Error checking multi-channel notification preference: {e}")
            return False

    def record_notification_activity(
        self,
        user_id: int,
        channel_type: str,
        channel_value: str,
        notification_type: str,
        escrow_id: str = None,
    ) -> str:
        """Record notification activity for analytics and response time tracking"""
        try:
            import uuid

            activity_id = f"nact_{uuid.uuid4().hex[:12]}"

            activity = NotificationActivity(
                activity_id=activity_id,
                user_id=user_id,
                notification_type=notification_type,
                channel_type=channel_type,
                channel_value=channel_value,
                related_escrow_id=escrow_id,
                sent_at=datetime.utcnow(),
            )

            self._get_session().add(activity)
            self._get_session().commit()

            logger.info(
                f"Recorded notification activity {activity_id} for user {user_id}"
            )
            return activity_id

        except Exception as e:
            logger.error(f"Error recording notification activity: {e}")
            self._get_session().rollback()
            return ""

    def update_channel_response_time(
        self, user_id: int, channel_type: str, response_time_hours: float
    ):
        """Update average response time for a channel type"""
        try:
            user = self._get_session().query(User).filter(User.id == user_id).first()
            if not user:
                return

            # Update channel-specific response time with rolling average
            if channel_type == "telegram":
                current_avg = (
                    float(user.telegram_response_time_avg)
                    if user.telegram_response_time_avg
                    else 0.0
                )
                new_avg = (current_avg * 0.7) + (response_time_hours * 0.3)
                self._get_session().query(User).filter(User.id == user_id).update(
                    {
                        "telegram_response_time_avg": new_avg,
                        "telegram_last_seen": datetime.utcnow(),
                    }
                )

            elif channel_type == "email":
                current_avg = (
                    float(user.email_response_time_avg)
                    if user.email_response_time_avg
                    else 24.0
                )
                new_avg = (current_avg * 0.7) + (response_time_hours * 0.3)
                self._get_session().query(User).filter(User.id == user_id).update(
                    {
                        "email_response_time_avg": new_avg,
                        "email_last_opened": datetime.utcnow(),
                    }
                )

            elif channel_type == "sms":
                current_avg = (
                    float(user.sms_response_time_avg)
                    if user.sms_response_time_avg
                    else 2.0
                )
                new_avg = (current_avg * 0.7) + (response_time_hours * 0.3)
                self._get_session().query(User).filter(User.id == user_id).update(
                    {
                        "sms_response_time_avg": new_avg,
                        "sms_last_received": datetime.utcnow(),
                    }
                )

            self._get_session().commit()
            logger.info(
                f"Updated {channel_type} response time for user {user_id}: {response_time_hours:.2f}h"
            )

        except Exception as e:
            logger.error(f"Error updating channel response time: {e}")
            self._get_session().rollback()

    def _detect_contact_type(self, contact_value: str) -> str:
        """Auto-detect contact type from value"""
        contact_value = contact_value.strip()

        # Email detection
        if "@" in contact_value and "." in contact_value:
            return "email"

        # Phone detection
        if (
            contact_value.startswith("+")
            or contact_value.replace(" ", "").replace("-", "").isdigit()
        ):
            return "phone"

        # Username detection (starts with @ or alphanumeric)
        if contact_value.startswith("@") or contact_value.replace("_", "").isalnum():
            return "username"

        return "unknown"

    def _find_user_by_email(self, email: str) -> Optional[User]:
        """Find user by email address (primary or additional)"""
        # Check primary email
        user = (
            self._get_session().query(User)
            .filter(
                and_(
                    func.lower(User.email) == email.lower(), User.email_verified
                )
            )
            .first()
        )

        if user:
            return user

        # Check additional emails
        contact = (
            self._get_session().query(UserContact)
            .filter(
                and_(
                    UserContact.contact_type == "email",
                    func.lower(UserContact.contact_value) == email.lower(),
                    UserContact.is_verified,
                    UserContact.is_active,
                )
            )
            .first()
        )

        if contact:
            return self._get_session().query(User).filter(User.id == contact.user_id).first()

        return None

    def _find_user_by_phone(self, phone: str) -> Optional[User]:
        """Find user by phone number with normalization"""
        try:
            # Normalize phone number
            normalized_phone = self._normalize_phone(phone)

            # Check primary phone
            user = (
                self._get_session().query(User)
                .filter(
                    and_(
                        User.phone_number == normalized_phone,
                        User.phone_verified,
                    )
                )
                .first()
            )

            if user:
                return user

            # Check additional phones
            contact = (
                self._get_session().query(UserContact)
                .filter(
                    and_(
                        UserContact.contact_type == "phone",
                        UserContact.contact_value == normalized_phone,
                        UserContact.is_verified,
                        UserContact.is_active,
                    )
                )
                .first()
            )

            if contact:
                return (
                    self._get_session().query(User).filter(User.id == contact.user_id).first()
                )

            return None

        except Exception as e:
            logger.error(f"Error finding user by phone {phone}: {e}")
            return None

    def _find_user_by_username(self, username: str) -> Optional[User]:
        """Find user by Telegram username"""
        username = username.lstrip("@").lower()

        return (
            self._get_session().query(User)
            .filter(func.lower(User.username) == username)
            .first()
        )

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to international format"""
        try:
            # Remove common formatting
            clean_phone = re.sub(r"[^\d+]", "", phone)

            # Parse with phonenumbers library
            parsed = phonenumbers.parse(clean_phone, None)

            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )

            return clean_phone

        except Exception as e:
            # Fallback to basic cleaning
            logger.debug(f"Phone number parsing failed: {e}")
            return re.sub(r"[^\d+]", "", phone)

    def _build_contact_profile(self, user: User) -> UserContactProfile:
        """Build complete contact profile for a user"""
        try:
            additional_contacts = self.get_all_linked_contacts(int(user.id))

            # Determine preferred channel based on response times
            channels = [
                ("telegram", user.telegram_response_time_avg),
                ("email", user.email_response_time_avg),
                ("sms", user.sms_response_time_avg),
            ]

            fastest_channel = min(channels, key=lambda x: x[1])[0]

            # Get user's preferred channel from settings
            preferences = user.notification_preferences or {}
            preferred_channel = preferences.get("primary_channel", fastest_channel)

            # Get all verified channels
            verified_channels = []
            if user.telegram_id is not None:
                verified_channels.append("telegram")
            if user.email is not None and user.email_verified is True:
                verified_channels.append("email")
            if user.phone_number is not None and user.phone_verified is True:
                verified_channels.append("sms")

            # Add additional verified contacts
            for contact in additional_contacts:
                if (
                    contact.is_verified
                    and contact.contact_type not in verified_channels
                ):
                    verified_channels.append(contact.contact_type)

            return UserContactProfile(
                user_id=int(user.id),
                telegram_id=str(user.telegram_id) if user.telegram_id else None,
                username=str(user.username) if user.username else None,
                primary_email=str(user.email) if user.email else "",
                phone_number=str(user.phone_number) if user.phone_number else None,
                additional_contacts=additional_contacts,
                telegram_response_time=(
                    float(user.telegram_response_time_avg)
                    if user.telegram_response_time_avg
                    else 0.0
                ),
                email_response_time=(
                    float(user.email_response_time_avg)
                    if user.email_response_time_avg
                    else 24.0
                ),
                sms_response_time=(
                    float(user.sms_response_time_avg)
                    if user.sms_response_time_avg
                    else 2.0
                ),
                preferred_channel=preferred_channel,
                all_verified_channels=verified_channels,
                fastest_channel=fastest_channel,
            )

        except Exception as e:
            logger.error(f"Error building contact profile for user {user.id}: {e}")
            raise


# Global instance
contact_detection_service = ContactDetectionService()

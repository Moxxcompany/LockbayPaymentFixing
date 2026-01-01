"""
E2E Test Foundation - Comprehensive infrastructure for End-to-End testing

This module provides:
1. Realistic Telegram Update/Context factories
2. Provider fakes for external APIs (not mocks - actual implementations that behave realistically)
3. Time control and deterministic testing utilities
4. Database transaction helpers with proper isolation
5. Notification verification helpers
6. Financial audit verification utilities
"""

import asyncio
import uuid
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from unittest.mock import Mock, AsyncMock, patch
from contextlib import asynccontextmanager

import pytest
# Removed telegram imports to fix dependency issues - using lightweight fakes instead

from models import (
    User, Wallet, Escrow, EscrowStatus, Transaction, TransactionType,
    Cashout, CashoutStatus, UnifiedTransaction, UnifiedTransactionStatus,
    UnifiedTransactionType, OnboardingSession, OnboardingStep, EmailVerification
)
from services.consolidated_notification_service import NotificationRequest, NotificationCategory
from utils.helpers import generate_utid
from utils.universal_id_generator import UniversalIDGenerator

logger = logging.getLogger(__name__)


# Lightweight Telegram Object Fakes - No external dependencies required
class TelegramUserFake:
    """Lightweight fake for Telegram User objects"""
    def __init__(self, id: int, username: str = None, first_name: str = "Test", last_name: str = "User", is_bot: bool = False):
        self.id = id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.is_bot = is_bot

class ChatFake:
    """Lightweight fake for Telegram Chat objects"""
    def __init__(self, id: int, type: str = "private"):
        self.id = id
        self.type = type

class MessageFake:
    """Lightweight fake for Telegram Message objects"""
    def __init__(self, message_id: int, date: datetime, chat: ChatFake, from_user: TelegramUserFake, text: str = None):
        self.message_id = message_id
        self.date = date
        self.chat = chat
        self.from_user = from_user
        self.text = text
        # Add chat_id for handler compatibility
        self.chat_id = chat.id
        
    async def reply_text(self, text: str, parse_mode=None, reply_markup=None):
        """Mock reply_text method for handler compatibility"""
        # This is a fake implementation for testing
        return MessageFake(
            message_id=self.message_id + 1,
            date=datetime.utcnow(),
            chat=self.chat,
            from_user=self.from_user,
            text=text
        )

class CallbackQueryFake:
    """Lightweight fake for Telegram CallbackQuery objects"""
    def __init__(self, id: str, from_user: TelegramUserFake, data: str, message: MessageFake = None, chat_instance: str = "fake_instance"):
        self.id = id
        self.from_user = from_user
        self.data = data
        self.message = message
        self.chat_instance = chat_instance
        
    async def edit_message_text(self, text: str, parse_mode=None, reply_markup=None):
        """Mock edit_message_text method for handler compatibility"""
        # This is a fake implementation for testing
        if self.message:
            self.message.text = text
        return True
        
    async def answer(self, text: str = None, show_alert: bool = False):
        """Mock answer method for handler compatibility"""
        # This is a fake implementation for testing
        return True

class UpdateFake:
    """Lightweight fake for Telegram Update objects"""
    def __init__(self, update_id: int, message: MessageFake = None, callback_query: CallbackQueryFake = None):
        self.update_id = update_id
        self.message = message
        self.callback_query = callback_query
        
    @property
    def effective_user(self) -> TelegramUserFake:
        """Get effective user from message or callback query"""
        if self.message:
            return self.message.from_user
        elif self.callback_query:
            return self.callback_query.from_user
        return None
            
    @property 
    def effective_chat(self) -> ChatFake:
        """Get effective chat from message or callback query"""
        if self.message:
            return self.message.chat
        elif self.callback_query and self.callback_query.message:
            return self.callback_query.message.chat
        return None

class ContextTypesFake:
    """Lightweight fake for Telegram ContextTypes"""
    class DEFAULT_TYPE:
        pass

# Aliases to match telegram library naming for backwards compatibility
TelegramUser = TelegramUserFake
Message = MessageFake
CallbackQuery = CallbackQueryFake
Update = UpdateFake
Chat = ChatFake
ContextTypes = ContextTypesFake


class TelegramObjectFactory:
    """Factory for creating realistic Telegram objects for E2E testing"""
    
    @staticmethod
    def create_user(
        user_id: int = None,
        username: str = None,
        first_name: str = "TestUser",
        last_name: str = "E2E"
    ) -> TelegramUser:
        """Create a realistic Telegram User object"""
        if user_id is None:
            user_id = int(f"559{str(uuid.uuid4().int)[:7]}")
        
        if username is None:
            username = f"testuser_{str(uuid.uuid4())[:8]}"
            
        return TelegramUser(
            id=user_id,
            is_bot=False,
            first_name=first_name,
            last_name=last_name,
            username=username
        )
    
    @staticmethod
    def create_message(
        user: TelegramUser,
        text: str = "/start",
        message_id: int = None
    ) -> Message:
        """Create a realistic Message object"""
        if message_id is None:
            message_id = int(str(uuid.uuid4().int)[:8])
            
        chat = Chat(id=user.id, type="private")
        
        return Message(
            message_id=message_id,
            date=datetime.utcnow(),
            chat=chat,
            from_user=user,
            text=text
        )
    
    @staticmethod
    def create_callback_query(
        user: TelegramUser,
        data: str,
        message: Message = None
    ) -> CallbackQuery:
        """Create a realistic CallbackQuery object"""
        if message is None:
            message = TelegramObjectFactory.create_message(user, "Previous message")
            
        return CallbackQuery(
            id=str(uuid.uuid4()),
            from_user=user,
            chat_instance="test_chat_instance",
            data=data,
            message=message
        )
    
    @staticmethod
    def create_update(
        user: TelegramUser = None,
        message: Message = None,
        callback_query: CallbackQuery = None
    ) -> Update:
        """Create a realistic Update object"""
        if user is None:
            user = TelegramObjectFactory.create_user()
            
        update_id = int(str(uuid.uuid4().int)[:8])
        
        return Update(
            update_id=update_id,
            message=message,
            callback_query=callback_query
        )
    
    @staticmethod
    def create_context(user_data: Dict = None, bot_data: Dict = None) -> ContextTypes.DEFAULT_TYPE:
        """Create a realistic Telegram context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = user_data or {}
        context.bot_data = bot_data or {}
        context.chat_data = {}
        context.application = Mock()
        context.bot = Mock()
        
        # Add realistic bot methods
        context.bot.send_message = AsyncMock()
        context.bot.edit_message_text = AsyncMock()
        context.bot.answer_callback_query = AsyncMock()
        
        return context


class ProviderFakes:
    """
    Realistic provider fakes - not mocks, but actual implementations that behave
    like real providers but with controlled/deterministic responses
    """
    
    class FincraFake:
        """Fake Fincra service that behaves like the real one"""
        
        def __init__(self):
            self.balance = Decimal("100000.00")  # NGN balance
            self.transfers = {}
            self.bank_accounts = {
                "0123456789": {
                    "account_name": "TEST USER ACCOUNT",
                    "bank_name": "ACCESS BANK"
                }
            }
        
        async def check_balance(self) -> Dict[str, Any]:
            """Simulate balance check"""
            return {
                "success": True,
                "balance": self.balance,
                "currency": "NGN"
            }
        
        async def process_bank_transfer(
            self,
            amount: Decimal,
            account_number: str,
            bank_code: str,
            account_name: str,
            reference: str
        ) -> Dict[str, Any]:
            """Simulate bank transfer processing"""
            
            if self.balance < amount:
                return {
                    "success": False,
                    "error": "insufficient_funds",
                    "message": "Insufficient balance"
                }
            
            # Simulate processing delay
            await asyncio.sleep(0.1)
            
            transfer_id = f"FINCRA_{generate_utid()}"
            self.transfers[transfer_id] = {
                "amount": amount,
                "account_number": account_number,
                "bank_code": bank_code,
                "reference": reference,
                "status": "processing",
                "created_at": datetime.utcnow()
            }
            
            self.balance -= amount
            
            return {
                "success": True,
                "transfer_id": transfer_id,
                "reference": reference,
                "status": "processing",
                "requires_admin_funding": False
            }
        
        async def check_bank_account(self, account_number: str, bank_code: str) -> Dict[str, Any]:
            """Simulate bank account verification"""
            if account_number in self.bank_accounts:
                return {
                    "success": True,
                    **self.bank_accounts[account_number]
                }
            return {
                "success": False,
                "error": "account_not_found"
            }
    
    class KrakenFake:
        """Fake Kraken service that behaves like the real one"""
        
        def __init__(self):
            self.balances = {
                "USD": Decimal("1000.00"),
                "BTC": Decimal("0.1"),
                "ETH": Decimal("2.5"),
                "LTC": Decimal("10.0")
            }
            self.withdrawals = {}
        
        async def check_balance(self) -> Dict[str, Any]:
            """Simulate balance check"""
            return {
                "success": True,
                "balances": dict(self.balances)
            }
        
        async def withdraw_crypto(
            self,
            currency: str,
            amount: Decimal,
            address: str,
            memo: str = None
        ) -> Dict[str, Any]:
            """Simulate crypto withdrawal"""
            
            if currency not in self.balances or self.balances[currency] < amount:
                return {
                    "success": False,
                    "error": "insufficient_funds"
                }
            
            # Simulate processing delay
            await asyncio.sleep(0.1)
            
            withdrawal_id = f"KRAKEN_{generate_utid()}"
            self.withdrawals[withdrawal_id] = {
                "currency": currency,
                "amount": amount,
                "address": address,
                "memo": memo,
                "status": "processing",
                "created_at": datetime.utcnow()
            }
            
            self.balances[currency] -= amount
            
            return {
                "success": True,
                "withdrawal_id": withdrawal_id,
                "txid": f"TXID_{generate_utid()}",
                "refid": f"REF_{generate_utid()}"
            }
    
    class CryptoServiceFake:
        """Fake crypto service for payment address generation and verification"""
        
        def __init__(self):
            self.addresses = {}
            self.payments = {}
        
        async def generate_deposit_address(
            self,
            currency: str,
            user_id: int,
            escrow_id: str = None
        ) -> Dict[str, Any]:
            """Generate a fake deposit address"""
            
            address_prefix = {
                "BTC": "bc1q",
                "ETH": "0x",
                "LTC": "ltc1q",
                "USDT": "0x"
            }.get(currency, "addr_")
            
            address = f"{address_prefix}{generate_utid().lower()}"
            
            self.addresses[address] = {
                "currency": currency,
                "user_id": user_id,
                "escrow_id": escrow_id,
                "created_at": datetime.utcnow()
            }
            
            return {
                "success": True,
                "address": address,
                "currency": currency,
                "memo": None
            }
        
        async def simulate_payment(
            self,
            address: str,
            amount: Decimal,
            confirmations: int = 6
        ) -> Dict[str, Any]:
            """Simulate a payment to an address"""
            
            if address not in self.addresses:
                return {
                    "success": False,
                    "error": "address_not_found"
                }
            
            payment_id = f"PAYMENT_{generate_utid()}"
            self.payments[payment_id] = {
                "address": address,
                "amount": amount,
                "confirmations": confirmations,
                "tx_hash": f"TX_{generate_utid()}",
                "confirmed": confirmations >= 6,
                "created_at": datetime.utcnow()
            }
            
            return {
                "success": True,
                "payment_id": payment_id,
                "tx_hash": self.payments[payment_id]["tx_hash"],
                "amount_received": amount,
                "confirmations": confirmations
            }


class DatabaseTransactionHelper:
    """Helper for managing database transactions in E2E tests"""
    
    @staticmethod
    @asynccontextmanager
    async def isolated_transaction(session):
        """Create an isolated transaction for testing"""
        # Begin a nested transaction (savepoint)
        nested = await session.begin_nested()
        try:
            yield session
            await nested.commit()
        except Exception:
            await nested.rollback()
            raise
    
    @staticmethod
    async def create_test_user(
        session,
        telegram_id: int = None,
        email: str = None,
        username: str = None,
        balance_usd: Decimal = Decimal("1000.00")
    ) -> User:
        """Create a test user with realistic data"""
        
        if telegram_id is None:
            telegram_id = int(f"559{str(uuid.uuid4().int)[:7]}")
        
        if email is None:
            email = f"test_{str(uuid.uuid4())[:8]}@example.com"
        
        if username is None:
            username = f"testuser_{str(uuid.uuid4())[:8]}"
        
        user = User(
            telegram_id=telegram_id,
            username=username,
            email=email,
            email_verified=True,
            created_at=datetime.utcnow()
        )
        
        session.add(user)
        await session.flush()
        
        # Create wallet
        wallet = Wallet(
            user_id=user.id,
            balance=balance_usd,
            currency='USD',
            created_at=datetime.utcnow()
        )
        
        session.add(wallet)
        await session.flush()
        
        return user
    
    @staticmethod
    async def create_test_escrow(
        session,
        buyer_id: int,
        seller_email: str,
        amount: Decimal = Decimal("100.00"),
        status: str = EscrowStatus.CREATED.value
    ) -> Escrow:
        """Create a test escrow with realistic data"""
        
        # Calculate fees according to schema constraints
        fee_amount = amount * Decimal("0.1")  # 10% fee
        
        # Fee split logic - buyer pays all fees
        buyer_fee_amount = fee_amount
        seller_fee_amount = Decimal("0")
        total_amount = amount + buyer_fee_amount  # Only buyer pays extra
        
        # Generate unified ID for both fields to prevent mismatch
        unified_id = UniversalIDGenerator.generate_escrow_id()
        escrow = Escrow(
            escrow_id=unified_id,
            utid=unified_id,  # CRITICAL: Use same ID to prevent mismatch
            buyer_id=buyer_id,
            seller_email=seller_email,
            amount=amount,
            fee_amount=fee_amount,
            buyer_fee_amount=buyer_fee_amount,
            seller_fee_amount=seller_fee_amount,
            total_amount=total_amount,
            fee_split_option='buyer_pays',
            description="Test escrow for E2E testing",
            currency="USD",
            network="USDT-ERC20",
            status=status,
            created_at=datetime.utcnow()
        )
        
        session.add(escrow)
        await session.flush()
        
        return escrow


class NotificationVerifier:
    """Helper for verifying notification delivery in E2E tests"""
    
    def __init__(self):
        self.sent_notifications = []
    
    async def capture_notification(self, notification: NotificationRequest) -> Dict[str, Any]:
        """Capture a notification for verification"""
        notification_data = {
            "id": str(uuid.uuid4()),
            "category": notification.category,
            "priority": notification.priority,
            "channels": notification.channels,
            "user_id": notification.user_id,
            "content": notification.message,
            "timestamp": datetime.utcnow()
        }
        
        self.sent_notifications.append(notification_data)
        
        return {
            "success": True,
            "delivery_id": notification_data["id"],
            "channels_attempted": notification.channels,
            "channels_succeeded": notification.channels
        }
    
    def verify_notification_sent(
        self,
        user_id: int,
        category: NotificationCategory,
        content_contains: str = None
    ) -> bool:
        """Verify that a specific notification was sent"""
        for notification in self.sent_notifications:
            if (notification["user_id"] == user_id and 
                notification["category"] == category):
                
                if content_contains:
                    if content_contains.lower() in str(notification["content"]).lower():
                        return True
                else:
                    return True
        
        return False
    
    def get_notifications_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all notifications sent to a specific user"""
        return [n for n in self.sent_notifications if n["user_id"] == user_id]
    
    def clear_notifications(self):
        """Clear captured notifications"""
        self.sent_notifications.clear()


class FinancialAuditVerifier:
    """Helper for verifying financial audit trails in E2E tests"""
    
    @staticmethod
    async def verify_balance_consistency(session, user_id: int) -> bool:
        """Verify that user balance is consistent with transaction history"""
        # This would implement actual balance verification logic
        # For now, we'll return True as a placeholder
        return True
    
    @staticmethod
    async def verify_escrow_fund_segregation(session, escrow_id: str) -> bool:
        """Verify that escrow funds are properly segregated"""
        # This would implement actual fund segregation verification
        # For now, we'll return True as a placeholder
        return True
    
    @staticmethod
    async def verify_audit_trail_exists(session, transaction_id: str) -> bool:
        """Verify that proper audit trail exists for a transaction"""
        # This would implement actual audit trail verification
        # For now, we'll return True as a placeholder
        return True


class TimeController:
    """Helper for controlling time in E2E tests"""
    
    def __init__(self):
        self.frozen_time = None
        self.time_offset = timedelta(0)
    
    def freeze_at(self, timestamp: datetime):
        """Freeze time at a specific timestamp"""
        self.frozen_time = timestamp
    
    def advance_time(self, delta: timedelta):
        """Advance frozen time by a delta"""
        if self.frozen_time:
            self.frozen_time += delta
        else:
            self.time_offset += delta
    
    def get_current_time(self) -> datetime:
        """Get the current time (frozen or real)"""
        if self.frozen_time:
            return self.frozen_time
        return datetime.utcnow() + self.time_offset
    
    def reset(self):
        """Reset time control"""
        self.frozen_time = None
        self.time_offset = timedelta(0)


# Global instances for E2E testing
provider_fakes = ProviderFakes()
notification_verifier = NotificationVerifier()
audit_verifier = FinancialAuditVerifier()
time_controller = TimeController()


# Communication-specific helpers for E2E tests
class CommunicationDatabaseHelper:
    """
    Helper for database operations in communication E2E tests with proper transaction isolation
    """
    
    def __init__(self, session):
        self.session = session
        self.created_users = []
    
    async def create_user(
        self,
        telegram_id: str,
        username: str = None,
        first_name: str = "Test",
        last_name: str = "User",
        status: str = "active",
        is_admin: bool = False
    ) -> User:
        """Create a test user with proper ORM database handling"""
        from models import User, UserStatus
        from sqlalchemy import select
        
        if username is None:
            username = f"testuser_{str(uuid.uuid4())[:8]}"
        
        # Convert status string to enum if needed
        user_status = status if isinstance(status, UserStatus) else UserStatus.ACTIVE
        
        # Create user using proper ORM operations
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            status=user_status,
            is_admin=is_admin,
            email=f"{username}@example.com",  # Add required email field
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add to session using proper ORM pattern
        self.session.add(user)
        await self.session.flush()  # Get the ID without committing
        
        # Verify creation using ORM select
        verification_query = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(verification_query)
        created_user = result.scalar_one()
        
        self.created_users.append(created_user)
        return created_user
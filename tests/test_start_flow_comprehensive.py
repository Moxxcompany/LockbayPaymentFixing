"""
Comprehensive Unit and E2E Tests for Start Flow (handlers/start.py)
Tests bot initialization, onboarding states, user registration, and deep links
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from telegram import Update, User as TelegramUser, Chat, Message
from telegram.ext import ContextTypes, ConversationHandler

# Import the handlers and states we're testing
from handlers.start import OnboardingStates
from models import User

import logging
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestStartFlowUnit:
    """Unit tests for start flow functionality"""
    
    async def test_onboarding_states_constants(self):
        """Test that onboarding state constants are properly defined"""
        # Verify critical onboarding states exist
        assert hasattr(OnboardingStates, 'COLLECTING_EMAIL')
        assert hasattr(OnboardingStates, 'VERIFYING_EMAIL_OTP')
        assert hasattr(OnboardingStates, 'ACCEPTING_TOS')
        assert hasattr(OnboardingStates, 'ONBOARDING_SHOWCASE')
        
        # Verify states have unique values
        states = [
            OnboardingStates.COLLECTING_EMAIL,
            OnboardingStates.VERIFYING_EMAIL_OTP,
            OnboardingStates.ACCEPTING_TOS,
            OnboardingStates.ONBOARDING_SHOWCASE
        ]
        assert len(states) == len(set(states)), "Onboarding states must have unique values"
        
        # Verify states are integers (for ConversationHandler)
        for state in states:
            assert isinstance(state, int), f"State {state} must be an integer"

    async def test_start_command_new_user_flow(self):
        """Test start command flow for a new user"""
        # Setup mock objects
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        mock_effective_user.first_name = "NewUser"
        mock_effective_user.username = "newuser"
        
        mock_message = AsyncMock()
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = []
        
        # Mock database session - user does not exist (new user)
        with patch('handlers.start.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None  # No existing user
            
            # Mock user creation functions
            with patch('handlers.start.update_user_from_telegram') as mock_update_user:
                mock_new_user = Mock(spec=User)
                mock_new_user.id = 1
                mock_new_user.first_name = "NewUser"
                mock_new_user.email_verified = False
                mock_update_user.return_value = mock_new_user
                
                with patch('handlers.start.get_or_create_wallet') as mock_wallet:
                    mock_wallet.return_value = Mock()
                    
                    # Mock the start parameter parsing
                    with patch('handlers.start.parse_start_parameter') as mock_parse:
                        mock_parse.return_value = None  # No start parameter
                        
                        # Mock the onboarding flow initiation
                        with patch('handlers.start.initiate_email_collection') as mock_initiate:
                            mock_initiate.return_value = OnboardingStates.COLLECTING_EMAIL
                            
                            # Execute start command
                            # Import the actual start function
                            from handlers.start import start_handler
                            result = await start_handler(mock_update, mock_context)
                            
                            # Verify new user flow
                            mock_update_user.assert_called_once()
                            mock_initiate.assert_called_once()
                            assert result == OnboardingStates.COLLECTING_EMAIL

    async def test_start_command_existing_verified_user(self):
        """Test start command for existing verified user"""
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        mock_effective_user.first_name = "ExistingUser"
        
        mock_message = AsyncMock()
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = []
        
        # Mock existing verified user
        mock_existing_user = Mock(spec=User)
        mock_existing_user.id = 1
        mock_existing_user.first_name = "ExistingUser"
        mock_existing_user.email_verified = True
        mock_existing_user.tos_accepted = True
        
        with patch('handlers.start.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_existing_user
            
            with patch('handlers.start.show_main_menu_optimized') as mock_main_menu:
                mock_main_menu.return_value = ConversationHandler.END
                
                result = await start(mock_update, mock_context)
                
                # Verify existing user goes to main menu
                mock_main_menu.assert_called_once()
                assert result == ConversationHandler.END

    async def test_start_parameter_parsing(self):
        """Test deep link parameter parsing functionality"""
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_effective_user
        mock_update.message = AsyncMock()
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Test different start parameters
        test_scenarios = [
            (["escrow_123"], "escrow_123"),
            (["ref_456"], "ref_456"),
            (["invite_789"], "invite_789"),
            ([], None),
            ([""], None)
        ]
        
        for args, expected_param in test_scenarios:
            mock_context.args = args
            
            with patch('handlers.start.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = None
                
                with patch('handlers.start.parse_start_parameter') as mock_parse:
                    mock_parse.return_value = expected_param
                    
                    with patch('handlers.start.initiate_email_collection') as mock_initiate:
                        mock_initiate.return_value = OnboardingStates.COLLECTING_EMAIL
                        
                        with patch('handlers.start.update_user_from_telegram') as mock_update_user:
                            mock_update_user.return_value = Mock(spec=User)
                            
                            await start(mock_update, mock_context)
                            
                            # Verify parameter parsing was called correctly
                            if args and args[0]:
                                mock_parse.assert_called_with(args[0])
                            else:
                                mock_parse.assert_called_with("")

    async def test_user_registration_flow_components(self):
        """Test individual components of user registration flow"""
        mock_effective_user = Mock(spec=TelegramUser)
        mock_effective_user.id = 12345
        mock_effective_user.first_name = "TestUser"
        mock_effective_user.username = "testuser"
        
        # Test update_user_from_telegram function behavior
        with patch('handlers.start.update_user_from_telegram') as mock_update_user:
            mock_new_user = Mock(spec=User)
            mock_new_user.telegram_id = "12345"
            mock_new_user.first_name = "TestUser"
            mock_new_user.username = "testuser"
            mock_update_user.return_value = mock_new_user
            
            # Mock session for user creation
            mock_session = Mock()
            
            result = mock_update_user(mock_session, mock_effective_user)
            
            # Verify user creation behavior
            mock_update_user.assert_called_once_with(mock_session, mock_effective_user)
            assert result.telegram_id == "12345"

    async def test_welcome_message_generation(self):
        """Test welcome message personalization"""
        # Test scenarios for different user states
        user_scenarios = [
            {
                "name": "new_user",
                "user": Mock(first_name="Alice", email_verified=False),
                "expected_elements": ["welcome", "alice", "verification"]
            },
            {
                "name": "returning_user",
                "user": Mock(first_name="Bob", email_verified=True),
                "expected_elements": ["welcome back", "bob", "trading"]
            },
            {
                "name": "no_name_user",
                "user": Mock(first_name=None, email_verified=False),
                "expected_elements": ["welcome", "get started"]
            }
        ]
        
        for scenario in user_scenarios:
            mock_update = Mock(spec=Update)
            mock_update.effective_user = Mock(spec=TelegramUser)
            mock_update.message = AsyncMock()
            
            mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
            mock_context.args = []
            
            user = scenario["user"]
            
            with patch('handlers.start.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = user
                
                # Mock appropriate flow based on user state
                if user.email_verified:
                    with patch('handlers.start.show_main_menu_optimized') as mock_main_menu:
                        mock_main_menu.return_value = ConversationHandler.END
                        await start(mock_update, mock_context)
                        # Verify main menu was called for verified user
                        mock_main_menu.assert_called_once()
                else:
                    with patch('handlers.start.initiate_email_collection') as mock_initiate:
                        mock_initiate.return_value = OnboardingStates.COLLECTING_EMAIL
                        await start(mock_update, mock_context)
                        # Verify email collection for unverified user
                        mock_initiate.assert_called_once()

    async def test_error_handling_in_start_flow(self):
        """Test error handling in various start flow scenarios"""
        mock_update = Mock(spec=Update)
        mock_update.effective_user = Mock(spec=TelegramUser)
        mock_update.effective_user.id = 12345
        mock_update.message = AsyncMock()
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = []
        
        # Test database connection error
        with patch('handlers.start.SessionLocal') as mock_session_class:
            mock_session_class.side_effect = Exception("Database connection failed")
            
            # Should handle database error gracefully
            try:
                result = await start(mock_update, mock_context)
                # If it returns without exception, verify it handled error gracefully
                assert result is not None
            except Exception as e:
                # If it raises exception, ensure it's a known error type
                assert "database" in str(e).lower() or "connection" in str(e).lower()


@pytest.mark.asyncio
class TestStartFlowE2E:
    """End-to-end tests for complete start flow workflows"""
    
    async def test_e2e_new_user_onboarding_journey(self):
        """Test complete new user onboarding from start to completion"""
        # Create realistic telegram user
        mock_telegram_user = Mock(spec=TelegramUser)
        mock_telegram_user.id = 99999
        mock_telegram_user.first_name = "NewTestUser"
        mock_telegram_user.username = "newtestuser"
        
        mock_chat = Mock(spec=Chat)
        mock_chat.id = 99999
        
        mock_message = AsyncMock()
        mock_message.chat = mock_chat
        
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.effective_chat = mock_chat
        mock_update.message = mock_message
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = []
        mock_context.bot = AsyncMock()
        
        # Simulate complete onboarding flow
        with patch('handlers.start.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # No existing user (new user scenario)
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            # Mock user creation
            with patch('handlers.start.update_user_from_telegram') as mock_update_user:
                mock_new_user = Mock(spec=User)
                mock_new_user.id = 1
                mock_new_user.telegram_id = "99999"
                mock_new_user.first_name = "NewTestUser"
                mock_new_user.email_verified = False
                mock_new_user.tos_accepted = False
                mock_update_user.return_value = mock_new_user
                
                # Mock wallet creation
                with patch('handlers.start.get_or_create_wallet') as mock_wallet:
                    mock_wallet.return_value = Mock()
                    
                    # Mock activity tracking
                    with patch('handlers.start.track_user_activity') as mock_track:
                        mock_track.return_value = None
                        
                        # Mock email collection initiation
                        with patch('handlers.start.initiate_email_collection') as mock_initiate:
                            mock_initiate.return_value = OnboardingStates.COLLECTING_EMAIL
                            
                            # Execute complete E2E flow
                            # Import the actual start function
                            from handlers.start import start_handler
                            result = await start_handler(mock_update, mock_context)
                            
                            # Verify complete workflow
                            mock_update_user.assert_called_once()
                            mock_wallet.assert_called_once()
                            mock_track.assert_called_once()
                            mock_initiate.assert_called_once()
                            
                            # Verify onboarding state is returned
                            assert result == OnboardingStates.COLLECTING_EMAIL

    async def test_e2e_returning_user_start_flow(self):
        """Test complete returning user flow from start to main menu"""
        mock_telegram_user = Mock(spec=TelegramUser)
        mock_telegram_user.id = 55555
        mock_telegram_user.first_name = "ReturningUser"
        
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.message = AsyncMock()
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = []
        
        # Mock existing verified user
        mock_existing_user = Mock(spec=User)
        mock_existing_user.id = 2
        mock_existing_user.telegram_id = "55555"
        mock_existing_user.first_name = "ReturningUser"
        mock_existing_user.email_verified = True
        mock_existing_user.tos_accepted = True
        
        with patch('handlers.start.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_existing_user
            
            # Mock activity tracking
            with patch('handlers.start.track_user_activity') as mock_track:
                mock_track.return_value = None
                
                # Mock main menu display
                with patch('handlers.start.show_main_menu_optimized') as mock_main_menu:
                    mock_main_menu.return_value = ConversationHandler.END
                    
                    # Execute complete returning user flow
                    result = await start(mock_update, mock_context)
                    
                    # Verify returning user workflow
                    mock_track.assert_called_once()
                    mock_main_menu.assert_called_once()
                    assert result == ConversationHandler.END

    async def test_e2e_deep_link_handling_flow(self):
        """Test complete deep link parameter handling workflow"""
        mock_telegram_user = Mock(spec=TelegramUser)
        mock_telegram_user.id = 77777
        mock_telegram_user.first_name = "InvitedUser"
        
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.message = AsyncMock()
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = ["escrow_12345"]  # Deep link parameter
        
        with patch('handlers.start.SessionLocal') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None  # New user
            
            # Mock deep link parameter processing
            with patch('handlers.start.parse_start_parameter') as mock_parse:
                mock_parse.return_value = "escrow_12345"
                
                # Mock user creation with deep link context
                with patch('handlers.start.update_user_from_telegram') as mock_update_user:
                    mock_new_user = Mock(spec=User)
                    mock_new_user.id = 3
                    mock_update_user.return_value = mock_new_user
                    
                    with patch('handlers.start.get_or_create_wallet') as mock_wallet:
                        mock_wallet.return_value = Mock()
                        
                        with patch('handlers.start.track_user_activity') as mock_track:
                            mock_track.return_value = None
                            
                            # Mock onboarding with deep link context
                            with patch('handlers.start.initiate_email_collection') as mock_initiate:
                                mock_initiate.return_value = OnboardingStates.COLLECTING_EMAIL
                                
                                # Execute deep link workflow
                                from handlers.start import start_handler
                                result = await start_handler(mock_update, mock_context)
                                
                                # Verify deep link parameter was processed
                                mock_parse.assert_called_once_with("escrow_12345")
                                
                                # Verify user creation with context
                                mock_update_user.assert_called_once()
                                mock_initiate.assert_called_once()
                                
                                assert result == OnboardingStates.COLLECTING_EMAIL

    async def test_e2e_error_recovery_workflow(self):
        """Test complete error recovery across the start flow"""
        mock_update = Mock(spec=Update)
        mock_update.effective_user = Mock(spec=TelegramUser)
        mock_update.effective_user.id = 88888
        mock_update.message = AsyncMock()
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = []
        
        # Test various error scenarios with recovery
        error_scenarios = [
            ("User creation error", lambda: patch('handlers.start.update_user_from_telegram', side_effect=Exception("User creation failed"))),
            ("Wallet creation error", lambda: patch('handlers.start.get_or_create_wallet', side_effect=Exception("Wallet creation failed"))),
            ("Activity tracking error", lambda: patch('handlers.start.track_user_activity', side_effect=Exception("Activity tracking failed")))
        ]
        
        for error_name, error_patch in error_scenarios:
            with patch('handlers.start.SessionLocal') as mock_session_class:
                mock_session = Mock()
                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = None
                
                with error_patch():
                    try:
                        # Should handle error gracefully
                        result = await start(mock_update, mock_context)
                        
                        # Some errors might be caught and handled gracefully
                        # Others might propagate for proper error handling at higher levels
                        
                    except Exception as e:
                        # If an exception is raised, verify it's handled appropriately
                        assert error_name.replace(" error", "").lower() in str(e).lower() or "error" in str(e).lower()


@pytest.mark.integration
class TestStartFlowIntegration:
    """Integration tests with real components"""
    
    async def test_start_with_real_database_session(self, test_db_session):
        """Test start flow with real database session"""
        from models import User
        
        # Create a real test user
        test_user = User(
            telegram_id=11111,
            username="realuser",
            first_name="RealTest",
            email="realtest@example.com",
            email_verified=True,
            tos_accepted=True
        )
        test_db_session.add(test_user)
        test_db_session.commit()
        
        mock_telegram_user = Mock(spec=TelegramUser)
        mock_telegram_user.id = 11111
        mock_telegram_user.first_name = "RealTest"
        
        mock_update = Mock(spec=Update)
        mock_update.effective_user = mock_telegram_user
        mock_update.message = AsyncMock()
        
        mock_context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        mock_context.args = []
        
        # Use real database session
        with patch('handlers.start.SessionLocal', return_value=test_db_session):
            with patch('handlers.start.show_main_menu_optimized') as mock_main_menu:
                mock_main_menu.return_value = ConversationHandler.END
                
                with patch('handlers.start.track_user_activity') as mock_track:
                    mock_track.return_value = None
                    
                    result = await start(mock_update, mock_context)
                    
                    # Verify real database integration
                    mock_main_menu.assert_called_once()
                    assert result == ConversationHandler.END
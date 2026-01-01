"""
Simple unit tests for post-resolution rating prompts
Tests the integration without complex database constraints
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from decimal import Decimal

from services.post_completion_notification_service import PostCompletionNotificationService
from models import User, Escrow
from telegram import InlineKeyboardMarkup


class TestPostResolutionRatingPromptsSimple:
    """Test rating prompts are sent correctly after dispute resolution"""

    @pytest.mark.asyncio
    async def test_rating_prompts_contain_correct_callback_data(self):
        """Test that rating prompts include dispute-aware callback format"""
        
        # Create mock users
        buyer = User(
            id=1,
            telegram_id=1001,
            username="buyer",
            first_name="Buyer",
            email="buyer@test.com"
        )
        seller = User(
            id=2,
            telegram_id=2001,
            username="seller",
            first_name="Seller",
            email="seller@test.com"
        )
        
        # Create mock escrow
        escrow = Escrow(
            escrow_id="ES_TEST_001",
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal("100.00")
        )
        
        # Mock database session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None  # No existing ratings
        
        # Mock Bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Create service and inject mock bot
        service = PostCompletionNotificationService()
        service.bot = mock_bot
        
        # Call the rating prompt method
        result = await service._send_dispute_rating_prompts(
            buyer=buyer,
            seller=seller,
            escrow_id=escrow.escrow_id,
            session=mock_session,
            dispute_winner_id=seller.id,  # Seller wins
            dispute_loser_id=buyer.id,    # Buyer loses
            resolution_type="release"
        )
        
        # Verify function returned success
        assert result == True
        
        # Verify send_message was called twice
        assert mock_bot.send_message.call_count == 2
        
        # Get the calls
        buyer_call = None
        seller_call = None
        
        for call_obj in mock_bot.send_message.call_args_list:
            chat_id = call_obj[1]['chat_id']
            if chat_id == buyer.telegram_id:
                buyer_call = call_obj
            elif chat_id == seller.telegram_id:
                seller_call = call_obj
        
        # Verify buyer received loser prompt
        assert buyer_call is not None
        buyer_text = buyer_call[1]['text']
        assert "Rate Your Experience" in buyer_text
        assert escrow.escrow_id in buyer_text
        
        buyer_keyboard = buyer_call[1]['reply_markup'].inline_keyboard
        buyer_callback = buyer_keyboard[0][0].callback_data
        assert "rate_dispute:" in buyer_callback
        assert escrow.escrow_id in buyer_callback
        assert "loser" in buyer_callback
        assert "release" in buyer_callback
        
        # Verify seller received winner prompt
        assert seller_call is not None
        seller_text = seller_call[1]['text']
        assert "Rate Your Experience" in seller_text
        assert escrow.escrow_id in seller_text
        
        seller_keyboard = seller_call[1]['reply_markup'].inline_keyboard
        seller_callback = seller_keyboard[0][0].callback_data
        assert "rate_dispute:" in seller_callback
        assert escrow.escrow_id in seller_callback
        assert "winner" in seller_callback
        assert "release" in seller_callback

    @pytest.mark.asyncio
    async def test_refund_outcome_sets_correct_winner_loser(self):
        """Test that refund resolution sets buyer as winner, seller as loser"""
        
        buyer = User(id=1, telegram_id=1001, username="buyer", first_name="Buyer")
        seller = User(id=2, telegram_id=2001, username="seller", first_name="Seller")
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        service = PostCompletionNotificationService()
        service.bot = mock_bot
        
        # Call with buyer as winner (refund scenario)
        await service._send_dispute_rating_prompts(
            buyer=buyer,
            seller=seller,
            escrow_id="ES_REFUND_001",
            session=mock_session,
            dispute_winner_id=buyer.id,  # Buyer wins refund
            dispute_loser_id=seller.id,  # Seller loses
            resolution_type="refund"
        )
        
        # Verify buyer gets "winner" in callback
        buyer_call = [c for c in mock_bot.send_message.call_args_list if c[1]['chat_id'] == buyer.telegram_id][0]
        buyer_callback = buyer_call[1]['reply_markup'].inline_keyboard[0][0].callback_data
        assert "winner" in buyer_callback
        assert "refund" in buyer_callback
        
        # Verify seller gets "loser" in callback
        seller_call = [c for c in mock_bot.send_message.call_args_list if c[1]['chat_id'] == seller.telegram_id][0]
        seller_callback = seller_call[1]['reply_markup'].inline_keyboard[0][0].callback_data
        assert "loser" in seller_callback
        assert "refund" in seller_callback

    @pytest.mark.asyncio
    async def test_split_resolution_sets_participant_outcome(self):
        """Test that split resolution sets both as participants (no clear winner/loser)"""
        
        buyer = User(id=1, telegram_id=1001, username="buyer", first_name="Buyer")
        seller = User(id=2, telegram_id=2001, username="seller", first_name="Seller")
        
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        service = PostCompletionNotificationService()
        service.bot = mock_bot
        
        # Call with no clear winner (split scenario)
        await service._send_dispute_rating_prompts(
            buyer=buyer,
            seller=seller,
            escrow_id="ES_SPLIT_001",
            session=mock_session,
            dispute_winner_id=None,  # No winner
            dispute_loser_id=None,   # No loser
            resolution_type="split"
        )
        
        # Verify both get "participant" in callback
        buyer_call = [c for c in mock_bot.send_message.call_args_list if c[1]['chat_id'] == buyer.telegram_id][0]
        buyer_callback = buyer_call[1]['reply_markup'].inline_keyboard[0][0].callback_data
        assert "participant" in buyer_callback
        assert "split" in buyer_callback
        
        seller_call = [c for c in mock_bot.send_message.call_args_list if c[1]['chat_id'] == seller.telegram_id][0]
        seller_callback = seller_call[1]['reply_markup'].inline_keyboard[0][0].callback_data
        assert "participant" in seller_callback
        assert "split" in seller_callback

    @pytest.mark.asyncio
    async def test_no_prompts_sent_if_already_rated(self):
        """Test that prompts are not sent if users already rated"""
        
        buyer = User(id=1, telegram_id=1001, username="buyer", first_name="Buyer")
        seller = User(id=2, telegram_id=2001, username="seller", first_name="Seller")
        
        # Mock existing ratings
        mock_rating = MagicMock()
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_rating  # Already rated
        
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        service = PostCompletionNotificationService()
        service.bot = mock_bot
        
        await service._send_dispute_rating_prompts(
            buyer=buyer,
            seller=seller,
            escrow_id="ES_TEST_001",
            session=mock_session,
            dispute_winner_id=seller.id,
            dispute_loser_id=buyer.id,
            resolution_type="release"
        )
        
        # Verify no messages sent (both already rated)
        assert mock_bot.send_message.call_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

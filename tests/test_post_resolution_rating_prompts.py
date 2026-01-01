"""
Test suite for post-resolution rating prompts after admin email dispute resolution
Validates that both buyer and seller receive rating prompts after admin resolves dispute
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from decimal import Decimal

from services.admin_email_actions import AdminEmailActionService
from services.post_completion_notification_service import PostCompletionNotificationService
from services.dispute_resolution import DisputeResolutionService, ResolutionResult
from models import Dispute, Escrow, User, EscrowStatus, DisputeStatus
from database import SessionLocal


class TestPostResolutionRatingPrompts:
    """Test rating prompts are sent after admin resolves dispute via email"""

    @pytest.mark.asyncio
    async def test_admin_email_resolution_triggers_rating_prompts(self, db_session):
        """Test that resolving dispute via email triggers rating prompts to both parties"""
        
        # Create test users
        buyer = User(
            id=1,
            telegram_id=1001,
            username="test_buyer",
            email="buyer@test.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller = User(
            id=2,
            telegram_id=2001,
            username="test_seller",
            email="seller@test.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db_session.add(buyer)
        db_session.add(seller)
        db_session.flush()
        
        # Create escrow
        escrow = Escrow(
            escrow_id="ES_TEST_001",
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal("100.00"),
            status=EscrowStatus.DISPUTED.value,
            created_at=datetime.utcnow(),
            seller_accepted_at=datetime.utcnow()
        )
        db_session.add(escrow)
        db_session.flush()
        
        # Create dispute
        dispute = Dispute(
            escrow_id=escrow.id,
            initiator_id=buyer.id,
            respondent_id=seller.id,
            status=DisputeStatus.OPEN.value,
            reason="Test dispute",
            created_at=datetime.utcnow()
        )
        db_session.add(dispute)
        db_session.commit()
        
        # Mock the notification services
        with patch.object(AdminEmailActionService, '_notify_dispute_resolution', new=AsyncMock()) as mock_notify, \
             patch.object(PostCompletionNotificationService, 'notify_escrow_completion', new=AsyncMock()) as mock_completion:
            
            # Mock the dispute resolution result
            mock_result = ResolutionResult(
                success=True,
                escrow_id=escrow.escrow_id,
                resolution_type="release",
                amount=100.00,
                dispute_winner_id=seller.id,
                dispute_loser_id=buyer.id,
                buyer_id=buyer.id,
                seller_id=seller.id
            )
            
            # Mock DisputeResolutionService to return the result
            with patch.object(DisputeResolutionService, 'resolve_release_to_seller', new=AsyncMock(return_value=mock_result)):
                
                # Simulate admin email action
                result = await AdminEmailActionService.resolve_dispute_from_email(
                    dispute_id=str(dispute.id),
                    action="RELEASE_TO_SELLER",
                    token="valid_token"
                )
                
                # Verify resolution notification was sent
                assert mock_notify.called, "Resolution notification should be sent"
                notify_call = mock_notify.call_args
                assert notify_call[1]['dispute_id'] == str(dispute.id)
                assert notify_call[1]['resolution_type'] == "seller_wins"
                assert notify_call[1]['buyer_id'] == buyer.id
                assert notify_call[1]['seller_id'] == seller.id
                
                # Verify post-completion notification (rating prompts) was sent
                assert mock_completion.called, "Post-completion notification should be sent"
                completion_call = mock_completion.call_args
                assert completion_call[1]['escrow_id'] == escrow.escrow_id
                assert completion_call[1]['completion_type'] == 'dispute_resolved'
                assert completion_call[1]['dispute_winner_id'] == seller.id
                assert completion_call[1]['dispute_loser_id'] == buyer.id
                assert completion_call[1]['resolution_type'] == 'release'

    @pytest.mark.asyncio
    async def test_rating_prompts_sent_to_both_parties(self, db_session):
        """Test that _send_dispute_rating_prompts sends prompts to both buyer and seller"""
        
        # Create test users
        buyer = User(
            id=3,
            telegram_id=3001,
            username="prompt_buyer",
            first_name="Buyer",
            email="prompt_buyer@test.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller = User(
            id=4,
            telegram_id=4001,
            username="prompt_seller",
            first_name="Seller",
            email="prompt_seller@test.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db_session.add(buyer)
        db_session.add(seller)
        db_session.flush()
        
        # Create escrow
        escrow = Escrow(
            escrow_id="ES_PROMPT_001",
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal("50.00"),
            status=EscrowStatus.COMPLETED.value,
            created_at=datetime.utcnow()
        )
        db_session.add(escrow)
        db_session.commit()
        
        # Mock Bot.send_message
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        service = PostCompletionNotificationService()
        service.bot = mock_bot
        
        # Call _send_dispute_rating_prompts
        result = await service._send_dispute_rating_prompts(
            buyer=buyer,
            seller=seller,
            escrow_id=escrow.escrow_id,
            session=db_session,
            dispute_winner_id=seller.id,
            dispute_loser_id=buyer.id,
            resolution_type="release"
        )
        
        # Verify both parties received prompts
        assert result == True, "Rating prompts should be sent successfully"
        assert mock_bot.send_message.call_count == 2, "Should send 2 messages (buyer + seller)"
        
        # Verify buyer received prompt
        buyer_call = [call for call in mock_bot.send_message.call_args_list 
                     if call[1]['chat_id'] == buyer.telegram_id][0]
        assert "Rate Your Experience" in buyer_call[1]['text']
        assert "rate_dispute:" in buyer_call[1]['reply_markup'].inline_keyboard[0][0].callback_data
        assert "loser" in buyer_call[1]['reply_markup'].inline_keyboard[0][0].callback_data
        
        # Verify seller received prompt
        seller_call = [call for call in mock_bot.send_message.call_args_list 
                      if call[1]['chat_id'] == seller.telegram_id][0]
        assert "Rate Your Experience" in seller_call[1]['text']
        assert "rate_dispute:" in seller_call[1]['reply_markup'].inline_keyboard[0][0].callback_data
        assert "winner" in seller_call[1]['reply_markup'].inline_keyboard[0][0].callback_data

    @pytest.mark.asyncio
    async def test_refund_resolution_triggers_correct_outcome(self, db_session):
        """Test that refund resolution sets correct winner/loser for rating prompts"""
        
        # Create test users
        buyer = User(
            id=5,
            telegram_id=5001,
            username="refund_buyer",
            email="refund_buyer@test.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        seller = User(
            id=6,
            telegram_id=6001,
            username="refund_seller",
            email="refund_seller@test.com",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db_session.add(buyer)
        db_session.add(seller)
        db_session.flush()
        
        # Create escrow
        escrow = Escrow(
            escrow_id="ES_REFUND_001",
            buyer_id=buyer.id,
            seller_id=seller.id,
            amount=Decimal("75.00"),
            status=EscrowStatus.DISPUTED.value,
            created_at=datetime.utcnow(),
            seller_accepted_at=datetime.utcnow()
        )
        db_session.add(escrow)
        db_session.flush()
        
        # Create dispute
        dispute = Dispute(
            escrow_id=escrow.id,
            initiator_id=buyer.id,
            respondent_id=seller.id,
            status=DisputeStatus.OPEN.value,
            reason="Refund test",
            created_at=datetime.utcnow()
        )
        db_session.add(dispute)
        db_session.commit()
        
        # Mock notification services
        with patch.object(AdminEmailActionService, '_notify_dispute_resolution', new=AsyncMock()) as mock_notify, \
             patch.object(PostCompletionNotificationService, 'notify_escrow_completion', new=AsyncMock()) as mock_completion:
            
            # Mock the refund result
            mock_result = ResolutionResult(
                success=True,
                escrow_id=escrow.escrow_id,
                resolution_type="refund",
                amount=75.00,
                dispute_winner_id=buyer.id,  # Buyer wins on refund
                dispute_loser_id=seller.id,   # Seller loses on refund
                buyer_id=buyer.id,
                seller_id=seller.id
            )
            
            with patch.object(DisputeResolutionService, 'resolve_refund_to_buyer', new=AsyncMock(return_value=mock_result)):
                
                # Simulate admin email refund action
                result = await AdminEmailActionService.resolve_dispute_from_email(
                    dispute_id=str(dispute.id),
                    action="REFUND_TO_BUYER",
                    token="valid_token"
                )
                
                # Verify correct winner/loser passed to rating prompts
                assert mock_completion.called
                completion_call = mock_completion.call_args
                assert completion_call[1]['dispute_winner_id'] == buyer.id, "Buyer should be winner for refund"
                assert completion_call[1]['dispute_loser_id'] == seller.id, "Seller should be loser for refund"
                assert completion_call[1]['resolution_type'] == 'refund'


@pytest.fixture
def db_session():
    """Provide a clean database session for tests"""
    from models import DisputeMessage, Rating
    
    session = SessionLocal()
    
    # Clean up test data in correct order (respecting foreign keys)
    test_telegram_ids = [1001, 2001, 3001, 4001, 5001, 6001]
    
    # Get test user IDs
    test_users = session.query(User.id).filter(User.telegram_id.in_(test_telegram_ids)).all()
    test_user_ids = [u.id for u in test_users]
    
    if test_user_ids:
        # Delete dispute messages first
        session.execute("DELETE FROM dispute_messages WHERE dispute_id IN (SELECT id FROM disputes WHERE initiator_id = ANY(:ids) OR respondent_id = ANY(:ids))", {"ids": test_user_ids})
        # Delete ratings
        session.query(Rating).filter(Rating.rater_id.in_(test_user_ids)).delete(synchronize_session=False)
        # Delete disputes
        session.query(Dispute).filter(
            (Dispute.initiator_id.in_(test_user_ids)) | (Dispute.respondent_id.in_(test_user_ids))
        ).delete(synchronize_session=False)
        # Delete escrows
        session.query(Escrow).filter(
            (Escrow.buyer_id.in_(test_user_ids)) | (Escrow.seller_id.in_(test_user_ids))
        ).delete(synchronize_session=False)
        # Delete users
        session.query(User).filter(User.id.in_(test_user_ids)).delete(synchronize_session=False)
    
    session.commit()
    
    yield session
    
    # Cleanup after test (same order)
    test_users = session.query(User.id).filter(User.telegram_id.in_(test_telegram_ids)).all()
    test_user_ids = [u.id for u in test_users]
    
    if test_user_ids:
        session.execute("DELETE FROM dispute_messages WHERE dispute_id IN (SELECT id FROM disputes WHERE initiator_id = ANY(:ids) OR respondent_id = ANY(:ids))", {"ids": test_user_ids})
        session.query(Rating).filter(Rating.rater_id.in_(test_user_ids)).delete(synchronize_session=False)
        session.query(Dispute).filter(
            (Dispute.initiator_id.in_(test_user_ids)) | (Dispute.respondent_id.in_(test_user_ids))
        ).delete(synchronize_session=False)
        session.query(Escrow).filter(
            (Escrow.buyer_id.in_(test_user_ids)) | (Escrow.seller_id.in_(test_user_ids))
        ).delete(synchronize_session=False)
        session.query(User).filter(User.id.in_(test_user_ids)).delete(synchronize_session=False)
    
    session.commit()
    session.close()

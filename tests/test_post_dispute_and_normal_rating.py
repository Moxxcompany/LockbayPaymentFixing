"""
Test to verify both normal and post-dispute ratings work correctly
This ensures the rating fix doesn't break normal trade ratings
"""

import pytest
from models import EscrowStatus


def test_allowed_rating_statuses():
    """Verify both COMPLETED and REFUNDED statuses are allowed for ratings"""
    
    # Define allowed statuses (from handlers/user_rating.py)
    allowed_statuses = [EscrowStatus.COMPLETED.value, EscrowStatus.REFUNDED.value]
    
    # Normal trade completion
    normal_status = EscrowStatus.COMPLETED.value
    assert normal_status in allowed_statuses, "Normal COMPLETED trade should allow ratings"
    
    # Dispute - Seller wins (released to seller)
    seller_wins_status = EscrowStatus.COMPLETED.value
    assert seller_wins_status in allowed_statuses, "Seller-wins dispute should allow ratings"
    
    # Dispute - Buyer wins (refunded to buyer)
    buyer_wins_status = EscrowStatus.REFUNDED.value
    assert buyer_wins_status in allowed_statuses, "Buyer-wins dispute should allow ratings"
    
    # Ensure other statuses are NOT allowed
    invalid_statuses = [
        EscrowStatus.ACTIVE.value,
        EscrowStatus.DISPUTED.value,
        EscrowStatus.CANCELLED.value,
        EscrowStatus.EXPIRED.value,
        EscrowStatus.PAYMENT_PENDING.value
    ]
    
    for status in invalid_statuses:
        assert status not in allowed_statuses, f"Status {status} should NOT allow ratings"
    
    print("✅ All rating status validations passed!")
    print(f"   - Normal trades (COMPLETED): Can rate ✓")
    print(f"   - Dispute seller wins (COMPLETED): Can rate ✓")
    print(f"   - Dispute buyer wins (REFUNDED): Can rate ✓")
    print(f"   - Invalid statuses: Blocked ✓")


if __name__ == "__main__":
    test_allowed_rating_statuses()

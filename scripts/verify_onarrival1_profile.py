"""
Verify @onarrival1's profile stats and trust level
"""

import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User
from services.enhanced_reputation_service import EnhancedReputationService


async def verify_profile():
    """Verify @onarrival1's reputation profile"""
    
    async with AsyncSessionLocal() as session:
        # Get user
        result = await session.execute(
            select(User).where(User.telegram_id == 5590563715)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ User not found!")
            return
        
        print(f"{'='*70}")
        print(f"📊 PROFILE VERIFICATION: @{user.username}")
        print(f"{'='*70}\n")
        
        # Get comprehensive reputation
        reputation = EnhancedReputationService.get_comprehensive_reputation(
            user.id, 
            session._proxied  # Get sync session from async
        )
        
        if not reputation:
            print("❌ Could not calculate reputation!")
            return
        
        # Display results
        print(f"🏆 TRUST LEVEL: {reputation.trust_level.upper()}")
        print(f"⭐ OVERALL RATING: {reputation.overall_rating}/5.0")
        print(f"📊 TOTAL RATINGS: {reputation.total_ratings}")
        print(f"💯 TRUST SCORE: {reputation.trust_score}")
        print()
        
        print(f"📈 RATING DISTRIBUTION:")
        for stars, count in sorted(reputation.rating_distribution.items(), reverse=True):
            percentage = (count / reputation.total_ratings * 100) if reputation.total_ratings > 0 else 0
            bar = '⭐' * stars
            print(f"   {bar} ({stars}): {count} ({percentage:.1f}%)")
        print()
        
        print(f"💰 TRADING STATS:")
        print(f"   Total Volume: ${reputation.total_volume}")
        print(f"   Completion Rate: {reputation.completion_rate * 100:.1f}%")
        print(f"   Dispute Rate: {reputation.dispute_rate * 100:.1f}%")
        print(f"   Recent Activity (30d): {reputation.recent_activity} ratings")
        print()
        
        print(f"🎖️  BADGES:")
        if reputation.badges:
            for badge in reputation.badges:
                print(f"   ✅ {badge}")
        else:
            print(f"   (No badges yet)")
        print()
        
        print(f"🔒 SECURITY:")
        print(f"   Verification: {reputation.verification_status}")
        print(f"   Risk Level: {reputation.risk_level.upper()}")
        print(f"   Reputation Trend: {reputation.reputation_trend}")
        print()
        
        print(f"{'='*70}")
        
        # Verify against expected values
        print(f"\n✅ VERIFICATION CHECKS:")
        checks = {
            "28 ratings received": reputation.total_ratings == 28,
            "5.0 average rating": reputation.overall_rating == 5.0,
            "$4,579 total volume": float(reputation.total_volume) == 4579.0,
            "100% completion rate": reputation.completion_rate == 1.0,
            "0% dispute rate": reputation.dispute_rate == 0.0,
            "Gold or higher trust level": reputation.trust_level in ['gold', 'platinum', 'diamond'],
            "Low risk level": reputation.risk_level == 'low',
        }
        
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
        
        all_passed = all(checks.values())
        print()
        if all_passed:
            print("🎉 ALL CHECKS PASSED! @onarrival1 is a Gold-level trusted trader!")
        else:
            print("⚠️  Some checks failed. Review the data above.")


if __name__ == "__main__":
    asyncio.run(verify_profile())

"""
Admin Rating and Reputation Management System
User feedback management, reputation analytics, and rating oversight
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc, func, and_, or_

from database import SessionLocal
from models import Rating, User, Escrow, EscrowStatus
from utils.admin_security import is_admin_secure
from utils.callback_utils import safe_answer_callback_query, safe_edit_message_text

logger = logging.getLogger(__name__)

# Conversation states
RATING_DETAIL, RATING_ACTION, RATING_MODERATE = range(3)


async def handle_admin_ratings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main rating management dashboard"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        elif update.message:
            await update.message.reply_text("❌ Access denied. Admin access required.")
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "⭐")

    try:
        session = SessionLocal()
        try:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # === RATING ANALYTICS ===
            total_ratings = session.query(Rating).count()
            ratings_today = session.query(Rating).filter(Rating.created_at >= today).count()
            
            # Average ratings
            avg_rating = session.query(func.avg(Rating.rating)).scalar() or 0
            
            # Rating distribution
            rating_dist = {}
            for i in range(1, 6):
                count = session.query(Rating).filter(Rating.rating == i).count()
                rating_dist[i] = count
            
            # Top rated users
            top_users = session.query(
                Rating.rated_id,
                func.avg(Rating.rating).label('avg_rating'),
                func.count(Rating.id).label('rating_count')
            ).group_by(Rating.rated_id).having(
                func.count(Rating.id) >= 3
            ).order_by(desc('avg_rating')).limit(5).all()
            
            # Recent ratings
            recent_ratings = session.query(Rating).order_by(
                desc(Rating.created_at)
            ).limit(5).all()
            
            message = f"""⭐ Rating 

📊 **Overview**
• Total Ratings: {total_ratings:,}
• Today: {ratings_today}
• Average Rating: {avg_rating:.2f}/5.0

📈 **Distribution**"""
            
            for star in range(5, 0, -1):
                count = rating_dist.get(star, 0)
                percentage = (count / max(total_ratings, 1)) * 100
                bar = "█" * min(int(percentage / 5), 10)
                message += f"\n{star}⭐ {bar} {count} ({percentage:.1f}%)"
            
            message += "\n\n🏆 **Top Rated Users**"
            if top_users:
                for rated_id, avg_rating, rating_count in top_users[:3]:
                    user_obj = session.query(User).filter(User.id == rated_id).first()
                    message += f"\n⭐ {avg_rating:.2f} • {user_obj.first_name if user_obj else 'User'} ({rating_count} ratings)"
            else:
                message += "\n📝 No qualified users yet"
            
            message += f"\n\n🕒 Updated: {now.strftime('%H:%M UTC')}"
            
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 View All Ratings", callback_data="admin_ratings_all"),
                InlineKeyboardButton("📊 Analytics", callback_data="admin_ratings_analytics"),
            ],
            [
                InlineKeyboardButton("⚠️ Moderate Ratings", callback_data="admin_ratings_moderate"),
                InlineKeyboardButton("🏆 Top Users", callback_data="admin_ratings_top"),
            ],
            [
                InlineKeyboardButton("📈 Trends", callback_data="admin_ratings_trends"),
                InlineKeyboardButton("🏠 Admin", callback_data="admin_main"),
            ]
        ]
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        elif update.message:
            await update.message.reply_text(
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin ratings dashboard failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Ratings dashboard failed: {str(e)}", show_alert=True)
        elif update.message:
            await update.message.reply_text(f"❌ Ratings dashboard failed: {str(e)}")
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_ratings_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """View all ratings with details"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "🔍")

    try:
        session = SessionLocal()
        try:
            # Get recent ratings with details
            recent_ratings = session.query(Rating).order_by(
                desc(Rating.created_at)
            ).limit(10).all()
            
            message = """🔍 **All Ratings Overview**

🕒 **Recent Ratings**"""
            
            if recent_ratings:
                for rating in recent_ratings:
                    # Get user details
                    rater = session.query(User).filter(User.id == rating.rater_id).first()
                    rated = session.query(User).filter(User.id == rating.rated_id).first()
                    escrow = session.query(Escrow).filter(Escrow.id == rating.escrow_id).first()
                    
                    # Format rating display
                    from datetime import timezone
                    stars = "⭐" * rating.rating + "☆" * (5 - rating.rating)
                    # Ensure rating.created_at is timezone-aware for subtraction
                    created_at = rating.created_at.replace(tzinfo=timezone.utc) if rating.created_at.tzinfo is None else rating.created_at
                    age = (datetime.now(timezone.utc) - created_at).days
                    
                    message += f"""

{stars} ({rating.rating}/5)
From: {rater.first_name if rater else 'Unknown'}
To: {rated.first_name if rated else 'Unknown'}
Escrow: ${escrow.amount:.2f} • {age}d ago"""
                    
                    if rating.comment:
                        comment_preview = rating.comment[:50] + "..." if len(rating.comment) > 50 else rating.comment
                        message += f"\n💬 \"{comment_preview}\""
            else:
                message += "\n📝 No ratings found"
            
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("⭐ 5-Star Only", callback_data="admin_ratings_filter_5"),
                InlineKeyboardButton("⚠️ 1-2 Star", callback_data="admin_ratings_filter_low"),
            ],
            [
                InlineKeyboardButton("📊 Statistics", callback_data="admin_ratings_stats"),
                InlineKeyboardButton("⭐ Ratings", callback_data="admin_ratings"),
            ],
            [
                InlineKeyboardButton("🏠 Admin", callback_data="admin_main")
            ]
        ]
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin all ratings failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ All ratings failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_ratings_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show top-rated users and reputation leaders"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "🏆")

    try:
        session = SessionLocal()
        try:
            # Top rated users (minimum 3 ratings)
            top_users = session.query(
                Rating.rated_id,
                func.avg(Rating.rating).label('avg_rating'),
                func.count(Rating.id).label('rating_count')
            ).group_by(Rating.rated_id).having(
                func.count(Rating.id) >= 3
            ).order_by(desc('avg_rating')).limit(10).all()
            
            # Most active raters
            active_raters = session.query(
                Rating.rater_id,
                func.count(Rating.id).label('ratings_given')
            ).group_by(Rating.rater_id).order_by(
                desc('ratings_given')
            ).limit(5).all()
            
            message = """🏆 **Top Rated Users & Reputation Leaders**

⭐ **Highest Rated Users**"""
            
            if top_users:
                for i, (rated_id, avg_rating, rating_count) in enumerate(top_users, 1):
                    user_obj = session.query(User).filter(User.id == rated_id).first()
                    
                    # Trophy emojis
                    trophy = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🏅"))
                    
                    message += f"""
{trophy} #{i} - {avg_rating:.2f}⭐
   {user_obj.first_name if user_obj else 'Unknown User'}
   {rating_count} ratings • ID: {rated_id}"""
            else:
                message += "\n📝 No qualified users (min 3 ratings required)"
            
            message += "\n\n👍 **Most Active Reviewers**"
            if active_raters:
                for rater_id, ratings_given in active_raters:
                    user_obj = session.query(User).filter(User.id == rater_id).first()
                    message += f"\n📝 {user_obj.first_name if user_obj else 'Unknown'} • {ratings_given} reviews"
            else:
                message += "\n📝 No active reviewers found"
            
            # Reputation insights
            total_users_with_ratings = len(top_users)
            message += f"\n\n📊 **Insights**"
            message += f"\n• Users with ratings: {total_users_with_ratings}"
            
            if top_users:
                highest_avg = top_users[0][1]
                message += f"\n• Highest average: {highest_avg:.2f}⭐"
            
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_ratings_detailed_stats"),
                InlineKeyboardButton("📈 Growth Analysis", callback_data="admin_ratings_growth"),
            ],
            [
                InlineKeyboardButton("⚠️ Review Issues", callback_data="admin_ratings_issues"),
                InlineKeyboardButton("⭐ Ratings", callback_data="admin_ratings"),
            ],
            [
                InlineKeyboardButton("🏠 Admin", callback_data="admin_main")
            ]
        ]
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Admin top ratings failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Top ratings failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


async def handle_admin_ratings_moderate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Rating moderation interface"""
    user = update.effective_user
    if not user or not is_admin_secure(user.id):
        if update.callback_query:
            await safe_answer_callback_query(update.callback_query, "❌ Access denied", show_alert=True)
        return ConversationHandler.END

    query = update.callback_query
    if query:
        await safe_answer_callback_query(query, "⚠️")

    try:
        session = SessionLocal()
        try:
            # Find potentially problematic ratings
            low_ratings = session.query(Rating).filter(
                Rating.rating <= 2
            ).order_by(desc(Rating.created_at)).limit(5).all()
            
            # Recent ratings with comments
            commented_ratings = session.query(Rating).filter(
                Rating.comment.isnot(None),
                Rating.comment != ""
            ).order_by(desc(Rating.created_at)).limit(3).all()
            
            message = """⚠️ Rating 

🔍 **Recent Low Ratings (≤2⭐)"""
            
            if low_ratings:
                for rating in low_ratings:
                    rater = session.query(User).filter(User.id == rating.rater_id).first()
                    rated = session.query(User).filter(User.id == rating.rated_id).first()
                    escrow = session.query(Escrow).filter(Escrow.id == rating.escrow_id).first()
                    
                    stars = "⭐" * rating.rating
                    age = (datetime.utcnow() - rating.created_at).days
                    
                    message += f"""

{stars} ({rating.rating}/5) • {age}d ago
From: {rater.first_name if rater else 'Unknown'}
To: {rated.first_name if rated else 'Unknown'}
Trade: ${escrow.amount:.2f}"""
                    
                    if rating.comment:
                        comment = rating.comment[:100] + "..." if len(rating.comment) > 100 else rating.comment
                        message += f"\n💬 \"{comment}\""
            else:
                message += "\n✅ No low ratings to review"
            
            message += "\n\n💬 **Recent Commented Ratings**"
            if commented_ratings:
                for rating in commented_ratings[-2:]:  # Show last 2
                    stars = "⭐" * rating.rating
                    comment_preview = rating.comment[:80] + "..." if len(rating.comment) > 80 else rating.comment
                    message += f"\n{stars} \"{comment_preview}\""
            else:
                message += "\n📝 No recent comments"
            
        finally:
            session.close()
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Review Low Ratings", callback_data="admin_ratings_review_low"),
                InlineKeyboardButton("💬 Review Comments", callback_data="admin_ratings_review_comments"),
            ],
            [
                InlineKeyboardButton("🚫 Flag Inappropriate", callback_data="admin_ratings_flag"),
                InlineKeyboardButton("✅ Approve All", callback_data="admin_ratings_approve_all"),
            ],
            [
                InlineKeyboardButton("⭐ Ratings", callback_data="admin_ratings"),
                InlineKeyboardButton("🏠 Admin", callback_data="admin_main"),
            ]
        ]
        
        if query:
            await safe_edit_message_text(
                query,
                message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
    except Exception as e:
        logger.error(f"Rating moderation failed: {e}")
        if query:
            await safe_answer_callback_query(query, f"❌ Rating moderation failed: {str(e)}", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END
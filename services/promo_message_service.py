"""
Promotional Message Service - Sends daily engaging messages to bot followers

Strategy:
- 2 messages/day per user: morning (~10 AM local) and evening (~6 PM local)
- Timezone-aware: uses user.timezone field, defaults to UTC
- Rotating pool of 20+ varied messages to avoid repetition
- All messages include @bot_username + deeplink for CTA
- Respects opt-out (PromoOptOut table)
- Rate-limited sending to avoid Telegram API throttling
- Tracks sends via PromoMessageLog to prevent duplicates
"""

import logging
import asyncio
import random
from datetime import datetime, date, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from telegram import Bot
from telegram.error import TelegramError, Forbidden, RetryAfter
from config import Config
from database import SessionLocal
from sqlalchemy import select, and_, exists, func as sql_func

logger = logging.getLogger(__name__)


def _bot_tag() -> str:
    return f"@{Config.BOT_USERNAME}" if Config.BOT_USERNAME else "@LockBayBot"

def _bot_link() -> str:
    username = Config.BOT_USERNAME or "LockBayBot"
    return f"https://t.me/{username}"

def _start_link() -> str:
    username = Config.BOT_USERNAME or "LockBayBot"
    return f"https://t.me/{username}?start=promo"


# =============================================================================
# MESSAGE POOL — Persuasive, varied, CTA-driven
# =============================================================================

def get_morning_messages() -> List[Dict]:
    """Morning messages (sent ~10 AM local) — motivation/opportunity/trust"""
    tag = _bot_tag()
    link = _start_link()
    
    return [
        {
            "key": "morning_safe_deal",
            "text": (
                f"<b>Good morning from LockBay!</b>\n\n"
                f"Got a deal to close today? Don't send crypto on trust alone.\n\n"
                f"Use escrow — your funds stay locked until both sides deliver.\n"
                f"Zero risk. Zero drama.\n\n"
                f"Start a secure trade now {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "morning_no_scam",
            "text": (
                f"<b>Still sending crypto directly?</b>\n\n"
                f"Every day, traders lose funds to exit scams and ghosting.\n"
                f"LockBay locks your payment in escrow until the seller delivers.\n\n"
                f"Protect yourself — it takes 30 seconds to start.\n\n"
                f"Open {tag} and create your first escrow\n"
                f"{link}"
            )
        },
        {
            "key": "morning_opportunity",
            "text": (
                f"<b>Today's a great day to trade safely</b>\n\n"
                f"Whether you're buying, selling, or exchanging crypto —\n"
                f"LockBay escrow keeps both sides honest.\n\n"
                f"No chargebacks. No ghosting. No middleman taking a cut.\n\n"
                f"Tap to trade {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "morning_trust_built",
            "text": (
                f"<b>Trust is expensive. Escrow is free.</b>\n\n"
                f"You shouldn't have to trust a stranger on the internet with your money.\n"
                f"With LockBay, you don't have to.\n\n"
                f"Funds are held securely until delivery is confirmed.\n"
                f"Simple. Safe. Smart.\n\n"
                f"Try it today {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "morning_reputation",
            "text": (
                f"<b>Your reputation grows with every trade</b>\n\n"
                f"Every escrow you complete builds your LockBay rating.\n"
                f"Top traders get more deals, faster acceptance, and community trust.\n\n"
                f"Start building your profile today.\n\n"
                f"Open {tag} to see your stats\n"
                f"{link}"
            )
        },
        {
            "key": "morning_quick",
            "text": (
                f"<b>30 seconds. That's all it takes.</b>\n\n"
                f"Create an escrow trade in under a minute.\n"
                f"Set the amount, share the link, and let LockBay handle the rest.\n\n"
                f"No forms. No KYC. No waiting.\n\n"
                f"Start now {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "morning_p2p",
            "text": (
                f"<b>P2P crypto trading without the risk</b>\n\n"
                f"LockBay brings escrow directly to Telegram.\n"
                f"Trade BTC, ETH, USDT, and more — all protected by smart escrow.\n\n"
                f"Join thousands of traders who choose safety first.\n\n"
                f"{tag} — start your trade\n"
                f"{link}"
            )
        },
        {
            "key": "morning_seller",
            "text": (
                f"<b>Selling something for crypto?</b>\n\n"
                f"Don't take buyer's word for it — use LockBay escrow.\n"
                f"The buyer's funds are locked before you deliver.\n"
                f"Once they confirm, the money is yours instantly.\n\n"
                f"Sell with confidence {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "morning_community",
            "text": (
                f"<b>The LockBay community is growing fast</b>\n\n"
                f"More traders joining every day means more deals and better rates.\n"
                f"Don't miss out on the safest way to trade crypto P2P.\n\n"
                f"Your next deal is waiting {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "morning_multi_currency",
            "text": (
                f"<b>BTC, ETH, USDT, USDC, SOL, BNB, LTC, XRP</b>\n\n"
                f"LockBay supports all the major cryptocurrencies.\n"
                f"Pick your currency. Set the price. Trade safely with escrow.\n\n"
                f"Which one are you trading today?\n\n"
                f"Open {tag} to get started\n"
                f"{link}"
            )
        },
    ]


def get_evening_messages() -> List[Dict]:
    """Evening messages (sent ~6 PM local) — urgency/social proof/FOMO"""
    tag = _bot_tag()
    link = _start_link()
    
    return [
        {
            "key": "evening_active_trades",
            "text": (
                f"<b>Trades are happening right now on LockBay</b>\n\n"
                f"While you're reading this, escrow deals are being created and completed.\n"
                f"Every trade protected. Every payout instant.\n\n"
                f"Don't miss out — open a trade tonight {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "evening_close_deal",
            "text": (
                f"<b>Got an open deal? Close it safely.</b>\n\n"
                f"If someone owes you crypto — or you owe them — use LockBay.\n"
                f"Escrow protects both sides. No arguments. No excuses.\n\n"
                f"Settle it now {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "evening_social_proof",
            "text": (
                f"<b>Traders trust LockBay for a reason</b>\n\n"
                f"Instant escrow creation. Automatic fund locking. "
                f"One-tap release when you're satisfied.\n\n"
                f"It's how P2P trading should work.\n\n"
                f"See for yourself {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "evening_cashout",
            "text": (
                f"<b>Auto-cashout is a game changer</b>\n\n"
                f"Complete a trade and get paid instantly to your bank or crypto wallet.\n"
                f"No extra steps. LockBay handles the payout automatically.\n\n"
                f"Set up auto-cashout in settings {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "evening_referral",
            "text": (
                f"<b>Invite friends. Earn rewards.</b>\n\n"
                f"Every friend who trades on LockBay earns you referral bonuses.\n"
                f"The more your network trades, the more you earn.\n\n"
                f"Share your referral link today {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "evening_dispute",
            "text": (
                f"<b>What happens if a trade goes wrong?</b>\n\n"
                f"LockBay has built-in dispute resolution.\n"
                f"If there's an issue, our team reviews the evidence and resolves it fairly.\n"
                f"Your funds are always safe — even when things don't go as planned.\n\n"
                f"Trade confidently {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "evening_rating_power",
            "text": (
                f"<b>Check your trader profile</b>\n\n"
                f"Your LockBay profile shows your rating, trade history, and reputation.\n"
                f"The more you trade, the more trusted you become.\n\n"
                f"Top-rated traders get accepted faster and earn more.\n\n"
                f"Check your profile {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "evening_night_trade",
            "text": (
                f"<b>Crypto never sleeps. Neither does LockBay.</b>\n\n"
                f"Create an escrow trade anytime — day or night.\n"
                f"Our bot is always on, always protecting your funds.\n\n"
                f"Open a trade before bed and wake up to a done deal.\n\n"
                f"Start now {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "evening_buyer_protection",
            "text": (
                f"<b>Buying crypto from someone online?</b>\n\n"
                f"Here's how smart buyers do it:\n"
                f"1. Create an escrow on LockBay\n"
                f"2. Lock your payment\n"
                f"3. Seller delivers\n"
                f"4. You confirm. Done.\n\n"
                f"No more \"send first\" trust games.\n\n"
                f"Buy safely {tag}\n"
                f"{link}"
            )
        },
        {
            "key": "evening_exchange",
            "text": (
                f"<b>Need to swap crypto to Naira?</b>\n\n"
                f"LockBay makes it easy. Exchange your crypto directly "
                f"and get paid to your NGN bank account.\n\n"
                f"Fast rates. Secure process. No middleman.\n\n"
                f"Exchange now {tag}\n"
                f"{link}"
            )
        },
    ]


# =============================================================================
# CORE SENDING LOGIC
# =============================================================================

# Timezone offset mappings for common timezone strings
TIMEZONE_UTC_OFFSETS = {
    # Africa
    "Africa/Lagos": 1, "Africa/Accra": 0, "Africa/Nairobi": 3,
    "Africa/Cairo": 2, "Africa/Johannesburg": 2, "Africa/Casablanca": 1,
    "Africa/Algiers": 1, "Africa/Tunis": 1, "Africa/Dar_es_Salaam": 3,
    "Africa/Kampala": 3, "Africa/Kigali": 2, "Africa/Addis_Ababa": 3,
    # Americas
    "America/New_York": -5, "America/Chicago": -6, "America/Denver": -7,
    "America/Los_Angeles": -8, "America/Sao_Paulo": -3, "America/Bogota": -5,
    "America/Mexico_City": -6, "America/Toronto": -5, "America/Lima": -5,
    # Europe
    "Europe/London": 0, "Europe/Paris": 1, "Europe/Berlin": 1,
    "Europe/Moscow": 3, "Europe/Istanbul": 3, "Europe/Kiev": 2,
    "Europe/Warsaw": 1, "Europe/Rome": 1, "Europe/Madrid": 1,
    # Asia
    "Asia/Dubai": 4, "Asia/Kolkata": 5, "Asia/Shanghai": 8,
    "Asia/Tokyo": 9, "Asia/Singapore": 8, "Asia/Bangkok": 7,
    "Asia/Jakarta": 7, "Asia/Karachi": 5, "Asia/Manila": 8,
    "Asia/Seoul": 9, "Asia/Hong_Kong": 8, "Asia/Riyadh": 3,
    # Pacific/Oceania
    "Pacific/Auckland": 13, "Australia/Sydney": 11, "Australia/Melbourne": 11,
    # Simple offsets users might store
    "UTC": 0, "GMT": 0, "WAT": 1, "CAT": 2, "EAT": 3, "EST": -5, "CST": -6,
    "MST": -7, "PST": -8, "IST": 5, "JST": 9, "SGT": 8, "AEST": 11,
}


def get_user_utc_offset(tz_string: Optional[str]) -> int:
    """Convert a timezone string to UTC offset in hours. Defaults to UTC+1 (WAT/Lagos)."""
    if not tz_string:
        return 1  # Default to WAT (West Africa Time) since many users are Nigeria-based
    
    tz_clean = tz_string.strip()
    
    # Direct lookup
    if tz_clean in TIMEZONE_UTC_OFFSETS:
        return TIMEZONE_UTC_OFFSETS[tz_clean]
    
    # Try numeric offset like "+3" or "-5" or "UTC+3"
    for prefix in ("UTC", "GMT", ""):
        if tz_clean.startswith(prefix):
            num_part = tz_clean[len(prefix):]
            try:
                return int(num_part)
            except ValueError:
                pass
    
    return 1  # Fallback to WAT


def get_users_for_session(session_type: str, current_utc_hour: int) -> List[Dict]:
    """
    Find users whose local time matches the target send window.
    
    morning session: targets ~10 AM local (9:30-10:30 AM window)
    evening session: targets ~6 PM local (5:30-6:30 PM window)
    
    Returns list of {user_id, telegram_id, first_name, timezone, last_message_key}
    """
    target_local_hour = 10 if session_type == "morning" else 18
    
    today = date.today()
    
    try:
        from models import User, PromoMessageLog, PromoOptOut
        
        with SessionLocal() as db:
            # Get all active, non-blocked, onboarded users who haven't opted out
            opted_out_subq = select(PromoOptOut.user_id)
            already_sent_subq = select(PromoMessageLog.user_id).where(
                and_(
                    PromoMessageLog.sent_date == today,
                    PromoMessageLog.session_type == session_type
                )
            )
            
            users = db.query(
                User.id, User.telegram_id, User.first_name, User.timezone
            ).filter(
                User.is_active == True,
                User.is_blocked == False,
                User.onboarding_completed == True,
                ~User.id.in_(opted_out_subq),
                ~User.id.in_(already_sent_subq),
            ).all()
            
            eligible = []
            for user in users:
                offset = get_user_utc_offset(user.timezone)
                user_local_hour = (current_utc_hour + offset) % 24
                
                # Check if user's local time is within the target window
                if user_local_hour == target_local_hour:
                    # Get their last sent message key to avoid repeats
                    last_log = db.query(PromoMessageLog.message_key).filter(
                        PromoMessageLog.user_id == user.id,
                        PromoMessageLog.session_type == session_type
                    ).order_by(PromoMessageLog.sent_at.desc()).first()
                    
                    eligible.append({
                        "user_id": user.id,
                        "telegram_id": user.telegram_id,
                        "first_name": user.first_name or "Trader",
                        "timezone": user.timezone,
                        "last_message_key": last_log[0] if last_log else None,
                    })
            
            logger.info(
                f"Found {len(eligible)} eligible users for {session_type} promo "
                f"(UTC hour {current_utc_hour}, target local hour {target_local_hour})"
            )
            return eligible
            
    except Exception as e:
        logger.error(f"Error querying users for promo session {session_type}: {e}")
        return []


def pick_message(session_type: str, last_key: Optional[str]) -> Dict:
    """Pick a message from the pool, avoiding the last sent message."""
    pool = get_morning_messages() if session_type == "morning" else get_evening_messages()
    
    # Filter out the last sent message to avoid immediate repeats
    available = [m for m in pool if m["key"] != last_key] if last_key else pool
    if not available:
        available = pool  # Fallback to full pool if all were filtered
    
    return random.choice(available)


def log_sent_message(user_id: int, message_key: str, session_type: str):
    """Record that a promo message was sent to a user."""
    try:
        from models import PromoMessageLog
        with SessionLocal() as db:
            log = PromoMessageLog(
                user_id=user_id,
                message_key=message_key,
                session_type=session_type,
                sent_date=date.today(),
            )
            db.add(log)
            db.commit()
    except Exception as e:
        logger.error(f"Error logging promo message for user {user_id}: {e}")


async def send_promo_messages(session_type: str) -> Dict:
    """
    Send promotional messages to eligible users for the given session.
    
    Args:
        session_type: 'morning' or 'evening'
    
    Returns:
        Stats dict with sent/failed/skipped counts
    """
    if not Config.BOT_TOKEN:
        logger.debug("Bot token not configured — skipping promo messages")
        return {"sent": 0, "failed": 0, "skipped": 0, "reason": "no_bot_token"}
    
    current_utc_hour = datetime.now(timezone.utc).hour
    users = get_users_for_session(session_type, current_utc_hour)
    
    if not users:
        return {"sent": 0, "failed": 0, "skipped": 0}
    
    bot = Bot(Config.BOT_TOKEN)
    stats = {"sent": 0, "failed": 0, "skipped": 0, "opted_out": 0}
    
    for user_data in users:
        try:
            message = pick_message(session_type, user_data.get("last_message_key"))
            
            # Add opt-out footer to every message
            full_text = (
                f"{message['text']}\n\n"
                f"<i>Reply /promo_off to stop these messages</i>"
            )
            
            await bot.send_message(
                chat_id=user_data["telegram_id"],
                text=full_text,
                parse_mode='HTML',
                disable_web_page_preview=True,
            )
            
            log_sent_message(user_data["user_id"], message["key"], session_type)
            stats["sent"] += 1
            
            # Rate limit: 25 messages/second max for Telegram, use 20/sec to be safe
            await asyncio.sleep(0.05)
            
        except Forbidden:
            # User blocked the bot
            logger.info(f"User {user_data['user_id']} blocked bot — marking inactive")
            try:
                from models import User
                with SessionLocal() as db:
                    db.query(User).filter(User.id == user_data["user_id"]).update(
                        {"is_active": False}
                    )
                    db.commit()
            except Exception:
                pass
            stats["failed"] += 1
            
        except RetryAfter as e:
            logger.warning(f"Telegram rate limit hit — sleeping {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            stats["skipped"] += 1
            
        except TelegramError as e:
            logger.error(f"Telegram error sending promo to {user_data['user_id']}: {e}")
            stats["failed"] += 1
            
        except Exception as e:
            logger.error(f"Unexpected error sending promo to {user_data['user_id']}: {e}")
            stats["failed"] += 1
    
    logger.info(
        f"Promo {session_type}: sent={stats['sent']}, "
        f"failed={stats['failed']}, skipped={stats['skipped']}"
    )
    return stats


async def handle_promo_opt_out(user_id: int) -> bool:
    """Opt a user out of promotional messages."""
    try:
        from models import PromoOptOut
        with SessionLocal() as db:
            existing = db.query(PromoOptOut).filter(PromoOptOut.user_id == user_id).first()
            if not existing:
                db.add(PromoOptOut(user_id=user_id))
                db.commit()
                logger.info(f"User {user_id} opted out of promo messages")
            return True
    except Exception as e:
        logger.error(f"Error opting out user {user_id}: {e}")
        return False


async def handle_promo_opt_in(user_id: int) -> bool:
    """Opt a user back in to promotional messages."""
    try:
        from models import PromoOptOut
        with SessionLocal() as db:
            db.query(PromoOptOut).filter(PromoOptOut.user_id == user_id).delete()
            db.commit()
            logger.info(f"User {user_id} opted back in to promo messages")
            return True
    except Exception as e:
        logger.error(f"Error opting in user {user_id}: {e}")
        return False

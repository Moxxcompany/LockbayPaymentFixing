"""
Profile Slug Generator
=====================
Generates unique, URL-friendly profile slugs for all users,
regardless of whether they have a Telegram username or not.
"""

import re
import random
import string
from typing import Optional
from sqlalchemy.orm import Session
from models import User


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text[:30]


def generate_random_suffix(length: int = 6) -> str:
    """Generate random alphanumeric suffix"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_profile_slug(
    session: Session,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    telegram_id: Optional[int] = None
) -> str:
    """
    Generate a unique profile slug for a user.
    
    Priority:
    1. Use Telegram username if available
    2. Use first_name + random suffix if no username
    3. Use telegram_id as fallback
    
    Args:
        session: Database session
        username: Telegram username (without @)
        first_name: User's first name
        telegram_id: Telegram user ID
        
    Returns:
        Unique profile slug
    """
    
    if username and username.strip():
        clean_username = username.strip().lstrip('@')
        base_slug = slugify(clean_username)
    elif first_name and first_name.strip():
        base_slug = slugify(first_name)
    elif telegram_id:
        base_slug = f"user_{telegram_id}"
    else:
        base_slug = "user"
    
    candidate = base_slug
    max_attempts = 10
    
    for attempt in range(max_attempts):
        existing = session.query(User).filter(User.profile_slug == candidate).first()
        
        if not existing:
            return candidate
        
        if attempt == 0 and username:
            candidate = base_slug
        else:
            suffix = generate_random_suffix(6)
            candidate = f"{base_slug}_{suffix}"
    
    raise ValueError(f"Could not generate unique slug after {max_attempts} attempts")


def ensure_profile_slug(session: Session, user: User) -> str:
    """
    Ensure user has a profile slug, generate if missing.
    
    Args:
        session: Database session
        user: User object
        
    Returns:
        Profile slug (existing or newly generated)
    """
    if user.profile_slug:
        return user.profile_slug
    
    slug = generate_profile_slug(
        session,
        username=user.username,
        first_name=user.first_name,
        telegram_id=user.telegram_id
    )
    
    user.profile_slug = slug
    session.commit()
    
    return slug

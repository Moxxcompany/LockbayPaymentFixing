"""
Universal ID Generator - Single Source of Truth for All LockBay IDs
===================================================================

Replaces 6+ different ID generation systems with one unified approach.
Generates consistent, user-friendly IDs across the entire platform.

Format: PP092523A4B7 (12 chars max)
- PP: Entity prefix (2 chars) 
- 092523: Date MMDDYY (6 chars)
- A4B7: Random suffix (4 chars)
"""

import secrets
import string
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class UniversalIDGenerator:
    """Single source of truth for ALL LockBay entity IDs"""
    
    # Unified entity prefixes for the entire platform
    ENTITY_PREFIXES: Dict[str, str] = {
        # === CORE BUSINESS ENTITIES ===
        'escrow': 'ES',              # Escrow transactions
        'exchange': 'EX',            # Currency exchange orders  
        'cashout': 'CO',             # Wallet cashout requests
        'refund': 'RF',              # Refund operations
        'dispute': 'DP',             # Dispute resolution
        
        # === FINANCIAL TRANSACTIONS ===
        'transaction': 'TX',         # General transactions
        'wallet_deposit': 'WD',      # Wallet deposit transactions
        'wallet_transfer': 'WT',     # Wallet-to-wallet transfers
        'payment': 'PM',             # Payment processing
        'fee': 'FE',                 # Fee transactions
        
        # === USER & SESSION MANAGEMENT ===
        'user_session': 'US',        # User session tracking
        'otp_token': 'OT',          # OTP verification tokens
        'invite_token': 'IT',       # Invitation tokens
        'verification': 'VF',        # Email/phone verification
        
        # === SYSTEM OPERATIONS ===
        'job_task': 'JB',           # Background job tasks
        'audit_log': 'AL',          # Audit trail entries
        'notification': 'NT',        # Notification records
        'error_report': 'ER',       # Error tracking
        
        # === ADMIN & SUPPORT ===
        'admin_action': 'AA',       # Admin operation tracking
        'support_ticket': 'ST',     # Customer support
        'broadcast': 'BC',          # Admin broadcasts
        
        # === INTEGRATION & API ===
        'webhook_event': 'WH',      # Webhook processing
        'api_request': 'AR',        # API request tracking
        'external_ref': 'XR',       # External system references
    }
    
    # Characters to use for random suffixes (excludes confusing chars)
    CLEAN_ALPHABET = ''.join(c for c in (string.ascii_uppercase + string.digits) 
                             if c not in '0O1IL')
    
    @classmethod
    def generate_id(cls, entity_type: str, custom_prefix: Optional[str] = None) -> str:
        """
        Generate unified ID for any entity type
        
        Args:
            entity_type: Entity type from ENTITY_PREFIXES
            custom_prefix: Override default prefix (optional)
            
        Returns:
            Unified ID: ES092523A4B7 (12 characters)
            
        Raises:
            ValueError: If entity_type not found and no custom_prefix provided
        """
        try:
            # Get prefix
            if custom_prefix:
                prefix = custom_prefix[:2].upper()
            else:
                if entity_type not in cls.ENTITY_PREFIXES:
                    raise ValueError(f"Unknown entity_type: {entity_type}. "
                                   f"Available: {list(cls.ENTITY_PREFIXES.keys())}")
                prefix = cls.ENTITY_PREFIXES[entity_type]
            
            # Generate date component (MMDDYY format for compactness)
            now = datetime.utcnow()
            date_part = now.strftime("%m%d%y")  # 092523
            
            # Generate cryptographically secure random suffix
            random_suffix = ''.join(secrets.choice(cls.CLEAN_ALPHABET) for _ in range(4))
            
            # Combine parts: PP092523A4B7
            unified_id = f"{prefix}{date_part}{random_suffix}"
            
            logger.debug(f"Generated {entity_type} ID: {unified_id}")
            return unified_id
            
        except Exception as e:
            logger.error(f"Failed to generate ID for {entity_type}: {e}")
            # Emergency fallback using timestamp
            timestamp = str(int(datetime.utcnow().timestamp()))[-6:]
            fallback_id = f"{prefix or 'XX'}{timestamp}"
            logger.warning(f"Using fallback ID: {fallback_id}")
            return fallback_id
    
    @classmethod
    def generate_escrow_id(cls) -> str:
        """Generate escrow transaction ID: ES092523A4B7"""
        return cls.generate_id('escrow')
    
    @classmethod
    def generate_exchange_id(cls) -> str:
        """Generate exchange order ID: EX092523B5C6"""
        return cls.generate_id('exchange')
    
    @classmethod
    def generate_cashout_id(cls) -> str:
        """Generate cashout request ID: CO092523D7E8"""
        return cls.generate_id('cashout')
    
    @classmethod
    def generate_transaction_id(cls) -> str:
        """Generate transaction ID: TX092523F9G0"""
        return cls.generate_id('transaction')
    
    @classmethod
    def generate_refund_id(cls) -> str:
        """Generate refund ID: RF092523H1I2"""
        return cls.generate_id('refund')
    
    @classmethod
    def generate_dispute_id(cls) -> str:
        """Generate dispute ID: DP092523J3K4"""
        return cls.generate_id('dispute')
    
    @classmethod
    def generate_wallet_deposit_id(cls) -> str:
        """Generate wallet deposit ID: WD092523L5M6"""
        return cls.generate_id('wallet_deposit')
    
    @classmethod
    def generate_otp_token(cls) -> str:
        """Generate OTP token ID: OT092523N7P8"""
        return cls.generate_id('otp_token')
    
    @classmethod
    def generate_invite_token(cls) -> str:
        """Generate invitation token ID: IT092523Q9R0"""
        return cls.generate_id('invite_token')
    
    @classmethod
    def validate_id_format(cls, unified_id: str) -> bool:
        """
        Validate unified ID format
        
        Args:
            unified_id: ID to validate
            
        Returns:
            True if valid format, False otherwise
        """
        if not unified_id or len(unified_id) != 12:
            return False
        
        # Check prefix (2 uppercase letters)
        prefix = unified_id[:2]
        if not prefix.isupper() or not prefix.isalpha():
            return False
        
        # Check date part (6 digits)
        date_part = unified_id[2:8]
        if not date_part.isdigit():
            return False
        
        # Check random suffix (4 alphanumeric, no confusing chars)
        suffix = unified_id[8:]
        if not all(c in cls.CLEAN_ALPHABET for c in suffix):
            return False
        
        return True
    
    @classmethod
    def extract_entity_type(cls, unified_id: str) -> Optional[str]:
        """
        Extract entity type from unified ID prefix
        
        Args:
            unified_id: Unified ID to analyze
            
        Returns:
            Entity type string or None if not found
        """
        if not cls.validate_id_format(unified_id):
            return None
        
        prefix = unified_id[:2]
        for entity_type, entity_prefix in cls.ENTITY_PREFIXES.items():
            if entity_prefix == prefix:
                return entity_type
        
        return None
    
    @classmethod
    def extract_date(cls, unified_id: str) -> Optional[datetime]:
        """
        Extract date from unified ID
        
        Args:
            unified_id: Unified ID to analyze
            
        Returns:
            datetime object or None if invalid
        """
        if not cls.validate_id_format(unified_id):
            return None
        
        try:
            date_str = unified_id[2:8]  # MMDDYY
            return datetime.strptime(f"20{date_str}", "%Y%m%d%y")
        except ValueError:
            return None
    
    @classmethod
    def get_supported_entity_types(cls) -> list:
        """Get list of all supported entity types"""
        return list(cls.ENTITY_PREFIXES.keys())
    
    @classmethod
    def is_unified_id(cls, id_string: str) -> bool:
        """
        Check if string is a valid unified ID
        
        Args:
            id_string: String to check
            
        Returns:
            True if valid unified ID format
        """
        return cls.validate_id_format(id_string)


# Convenience functions for backward compatibility
def generate_escrow_id() -> str:
    """Convenience function for escrow ID generation"""
    return UniversalIDGenerator.generate_escrow_id()

def generate_transaction_id() -> str:
    """Convenience function for transaction ID generation"""
    return UniversalIDGenerator.generate_transaction_id()

def generate_exchange_id() -> str:
    """Convenience function for exchange ID generation"""
    return UniversalIDGenerator.generate_exchange_id()

def generate_cashout_id() -> str:
    """Convenience function for cashout ID generation"""
    return UniversalIDGenerator.generate_cashout_id()

def generate_refund_id() -> str:
    """Convenience function for refund ID generation"""
    return UniversalIDGenerator.generate_refund_id()
"""
ID System Transition Helper
===========================

This module provides backward compatibility during the transition from
dual ID system to single UTID system. It allows gradual migration without
breaking existing functionality.
"""

import logging
from typing import Optional, Union
from sqlalchemy.orm import Session
from models import Escrow, Transaction, Cashout, Dispute
from utils.universal_id_generator import UniversalIDGenerator

logger = logging.getLogger(__name__)

class IDTransitionHelper:
    """Helper class for managing the transition to UTID system"""
    
    @staticmethod
    def get_escrow_by_any_id(session: Session, escrow_id: Union[str, int]) -> Optional[Escrow]:
        """
        Get escrow by either legacy escrow_id or new utid
        Supports backward compatibility during transition
        """
        if isinstance(escrow_id, int) or escrow_id.isdigit():
            # Legacy integer ID lookup
            return session.query(Escrow).filter(Escrow.id == int(escrow_id)).first()
        elif escrow_id.startswith("ES"):
            # New UTID lookup
            return session.query(Escrow).filter(Escrow.utid == escrow_id).first()
        else:
            # Legacy string escrow_id lookup
            return session.query(Escrow).filter(Escrow.escrow_id == escrow_id).first()
    
    @staticmethod
    def get_transaction_by_any_id(session: Session, transaction_id: Union[str, int]) -> Optional[Transaction]:
        """Get transaction by either legacy transaction_id or new utid"""
        if isinstance(transaction_id, int) or transaction_id.isdigit():
            return session.query(Transaction).filter(Transaction.id == int(transaction_id)).first()
        elif transaction_id.startswith("TX"):
            return session.query(Transaction).filter(Transaction.utid == transaction_id).first()
        else:
            return session.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    
    @staticmethod
    def get_cashout_by_any_id(session: Session, cashout_id: Union[str, int]) -> Optional[Cashout]:
        """Get cashout by either legacy cashout_id or new utid"""
        if isinstance(cashout_id, int) or cashout_id.isdigit():
            return session.query(Cashout).filter(Cashout.id == int(cashout_id)).first()
        elif cashout_id.startswith("WD"):
            return session.query(Cashout).filter(Cashout.utid == cashout_id).first()
        else:
            return session.query(Cashout).filter(Cashout.cashout_id == cashout_id).first()
    
    @staticmethod
    def get_dispute_by_any_id(session: Session, dispute_id: Union[str, int]) -> Optional[Dispute]:
        """Get dispute by either integer ID or UTID"""
        if isinstance(dispute_id, int) or dispute_id.isdigit():
            return session.query(Dispute).filter(Dispute.id == int(dispute_id)).first()
        elif dispute_id.startswith("DP"):
            return session.query(Dispute).filter(Dispute.utid == dispute_id).first()
        else:
            # Dispute model only has 'id' and 'utid' - no legacy dispute_id column
            return session.query(Dispute).filter(Dispute.id == int(dispute_id)).first() if dispute_id.isdigit() else None
    
    @staticmethod
    def get_primary_id(obj) -> str:
        """
        Get the primary display ID for any object
        During transition, prefers UTID if available, falls back to legacy ID
        """
        # For new objects with UTID
        if hasattr(obj, 'utid') and obj.utid:
            return obj.utid
        
        # For legacy objects, format with appropriate prefix
        if hasattr(obj, 'escrow_id') and obj.escrow_id:
            return obj.escrow_id
        elif hasattr(obj, 'transaction_id') and obj.transaction_id:
            return obj.transaction_id
        elif hasattr(obj, 'cashout_id') and obj.cashout_id:
            return obj.cashout_id
        # Note: Dispute model has no legacy dispute_id column - only id and utid
        
        # Fallback to database ID with appropriate prefix
        if hasattr(obj, 'id'):
            if obj.__class__.__name__ == 'Escrow':
                return f"ES{obj.id:010d}"
            elif obj.__class__.__name__ == 'Transaction':
                return f"TX{obj.id:010d}"
            elif obj.__class__.__name__ == 'Cashout':
                return f"WD{obj.id:010d}"
            elif obj.__class__.__name__ == 'Dispute':
                return f"DP{obj.id:010d}"
        
        return "UNKNOWN"
    
    @staticmethod
    def ensure_utid(session: Session, obj) -> str:
        """
        Ensure an object has a UTID, creating one if needed
        This allows gradual migration of existing objects
        """
        if hasattr(obj, 'utid') and obj.utid:
            return obj.utid
        
        # Generate UTID based on object type
        if obj.__class__.__name__ == 'Escrow':
            utid = UniversalIDGenerator.generate_escrow_id()
        elif obj.__class__.__name__ == 'Transaction':
            utid = UniversalIDGenerator.generate_transaction_id()
        elif obj.__class__.__name__ == 'Cashout':
            utid = UniversalIDGenerator.generate_cashout_id()
        elif obj.__class__.__name__ == 'Dispute':
            utid = UniversalIDGenerator.generate_dispute_id()
        else:
            logger.warning(f"Unknown object type for UTID generation: {obj.__class__.__name__}")
            utid = UniversalIDGenerator.generate_id("transaction")
        
        # Set UTID on object
        obj.utid = utid
        
        try:
            session.commit()
            logger.info(f"Generated UTID {utid} for existing {obj.__class__.__name__}")
        except Exception as e:
            logger.error(f"Failed to save UTID for {obj.__class__.__name__}: {e}")
            session.rollback()
        
        return utid

    @staticmethod
    def format_display_id(obj, force_utid: bool = False) -> str:
        """
        Format ID for user display
        
        Args:
            obj: Database object
            force_utid: If True, ensures UTID format even for legacy objects
        
        Returns:
            Formatted ID string for user display
        """
        if force_utid:
            # For consistent display, always show UTID format
            if hasattr(obj, 'utid') and obj.utid:
                return obj.utid
            else:
                # Generate display format from legacy ID
                if hasattr(obj, 'escrow_id') and obj.escrow_id:
                    return f"ES{obj.escrow_id[-6:]}"  # Last 6 chars with ES prefix
                elif hasattr(obj, 'transaction_id') and obj.transaction_id:
                    return f"TX{obj.transaction_id[-6:]}"
                elif hasattr(obj, 'cashout_id') and obj.cashout_id:
                    return obj.cashout_id  # Return full ID - no truncation needed
                elif hasattr(obj, 'dispute_id') and obj.dispute_id:
                    return f"DP{obj.dispute_id[-6:]}"
        
        # Default: use the primary ID
        return IDTransitionHelper.get_primary_id(obj)

# Convenience functions for common operations
def get_escrow_display_id(escrow, force_utid: bool = True) -> str:
    """Get consistent escrow ID for display"""
    return IDTransitionHelper.format_display_id(escrow, force_utid)

def get_transaction_display_id(transaction, force_utid: bool = True) -> str:
    """Get consistent transaction ID for display"""
    return IDTransitionHelper.format_display_id(transaction, force_utid)

def get_exchange_display_id(exchange, force_utid: bool = True) -> str:
    """Get consistent exchange ID for display"""
    if hasattr(exchange, 'utid') and exchange.utid:
        return exchange.utid
    elif hasattr(exchange, 'id'):
        return f"EX{exchange.id:06d}"
    return "EX000000"
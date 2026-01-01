"""
ID Mapping Validator for LockBay Escrow System
Ensures consistency between Trade ID (utid) and Escrow ID (escrow_id) systems
"""

import logging
from typing import Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from models import Escrow

logger = logging.getLogger(__name__)


class IDMappingValidator:
    """Validates and ensures consistency of ID mapping in the escrow system"""
    
    @staticmethod
    def validate_escrow_id_consistency(session: Session, escrow_id: Union[str, int]) -> Dict[str, Any]:
        """
        Validate that an escrow has consistent ID mapping
        
        Args:
            session: Database session
            escrow_id: Either internal escrow ID or UTID
            
        Returns:
            Dict with validation results and recommendations
        """
        try:
            # Try to find escrow by various ID types
            result = {
                "found_by_utid": None,
                "found_by_escrow_id": None,
                "found_by_internal_id": None,
                "is_consistent": False,
                "warnings": [],
                "errors": [],
                "recommendation": None
            }
            
            # Convert to string for string-based lookups
            str_id = str(escrow_id)
            
            # Try lookup by UTID (user-facing Trade ID)
            try:
                escrow_by_utid = session.query(Escrow).filter(Escrow.utid == str_id).first()
                if escrow_by_utid:
                    result["found_by_utid"] = {
                        "internal_id": escrow_by_utid.id,
                        "escrow_id": escrow_by_utid.escrow_id,
                        "utid": escrow_by_utid.utid
                    }
            except Exception as e:
                result["errors"].append(f"UTID lookup failed: {e}")
            
            # Try lookup by escrow_id (internal system ID)
            try:
                escrow_by_escrow_id = session.query(Escrow).filter(Escrow.escrow_id == str_id).first()
                if escrow_by_escrow_id:
                    result["found_by_escrow_id"] = {
                        "internal_id": escrow_by_escrow_id.id,
                        "escrow_id": escrow_by_escrow_id.escrow_id,
                        "utid": escrow_by_escrow_id.utid
                    }
            except Exception as e:
                result["errors"].append(f"Escrow_id lookup failed: {e}")
            
            # Try lookup by internal database ID (if numeric)
            try:
                if str_id.isdigit():
                    int_id = int(str_id)
                    escrow_by_internal = session.query(Escrow).filter(Escrow.id == int_id).first()
                    if escrow_by_internal:
                        result["found_by_internal_id"] = {
                            "internal_id": escrow_by_internal.id,
                            "escrow_id": escrow_by_internal.escrow_id,
                            "utid": escrow_by_internal.utid
                        }
            except Exception as e:
                result["errors"].append(f"Internal ID lookup failed: {e}")
            
            # Analyze consistency
            found_records = [r for r in [result["found_by_utid"], result["found_by_escrow_id"], result["found_by_internal_id"]] if r]
            
            if len(found_records) == 0:
                result["errors"].append(f"No escrow found for ID: {escrow_id}")
                result["recommendation"] = "ID_NOT_FOUND"
            elif len(found_records) == 1:
                # Found exactly one record - check for missing UTID
                record = found_records[0]
                if not record.get("utid"):
                    result["warnings"].append("Escrow found but missing UTID - needs migration")
                    result["recommendation"] = "ADD_MISSING_UTID"
                else:
                    result["is_consistent"] = True
                    result["recommendation"] = "CONSISTENT"
            else:
                # Multiple records found - major inconsistency
                result["errors"].append(f"Multiple escrows found for ID {escrow_id} - data corruption")
                result["recommendation"] = "DATA_CORRUPTION"
            
            return result
            
        except Exception as e:
            logger.error(f"ID mapping validation failed for {escrow_id}: {e}")
            return {
                "found_by_utid": None,
                "found_by_escrow_id": None,
                "found_by_internal_id": None,
                "is_consistent": False,
                "warnings": [],
                "errors": [f"Validation exception: {e}"],
                "recommendation": "VALIDATION_FAILED"
            }
    
    @staticmethod
    def find_escrow_with_fallback(session: Session, identifier: str, prefer_utid: bool = True) -> Optional[Escrow]:
        """
        Find escrow with smart fallback logic - prioritizes UTID for user-facing operations
        
        Args:
            session: Database session
            identifier: The ID to search for (UTID or escrow_id)
            prefer_utid: Whether to prefer UTID lookup first (default True for user-facing operations)
            
        Returns:
            Escrow object if found, None otherwise
        """
        try:
            if prefer_utid:
                # First try UTID lookup (user-facing Trade ID)
                escrow = session.query(Escrow).filter(Escrow.utid == identifier).first()
                if escrow:
                    logger.info(f"ID_MAPPING_SUCCESS: Found escrow by UTID {identifier}")
                    return escrow
                
                # Fallback to escrow_id lookup
                escrow = session.query(Escrow).filter(Escrow.escrow_id == identifier).first()
                if escrow:
                    logger.warning(f"ID_MAPPING_FALLBACK: Found escrow by escrow_id {identifier} (should use UTID)")
                    return escrow
            else:
                # First try escrow_id lookup (internal operations)
                escrow = session.query(Escrow).filter(Escrow.escrow_id == identifier).first()
                if escrow:
                    logger.info(f"ID_MAPPING_SUCCESS: Found escrow by escrow_id {identifier}")
                    return escrow
                
                # Fallback to UTID lookup
                escrow = session.query(Escrow).filter(Escrow.utid == identifier).first()
                if escrow:
                    logger.info(f"ID_MAPPING_FALLBACK: Found escrow by UTID {identifier}")
                    return escrow
            
            logger.error(f"ID_MAPPING_ERROR: Escrow not found for identifier {identifier}")
            return None
            
        except Exception as e:
            logger.error(f"ID mapping lookup failed for {identifier}: {e}")
            return None
    
    @staticmethod
    def audit_escrow_id_consistency(session: Session) -> Dict[str, Any]:
        """
        Audit all escrows for ID mapping consistency
        
        Returns:
            Dict with audit results and statistics
        """
        try:
            # Get all escrows
            all_escrows = session.query(Escrow).all()
            
            stats = {
                "total_escrows": len(all_escrows),
                "escrows_with_utid": 0,
                "escrows_missing_utid": 0,
                "duplicate_utids": 0,
                "duplicate_escrow_ids": 0,
                "inconsistent_escrows": [],
                "missing_utid_escrows": []
            }
            
            utid_counts = {}
            escrow_id_counts = {}
            
            for escrow in all_escrows:
                # Check UTID presence
                if escrow.utid:
                    stats["escrows_with_utid"] += 1
                    # Track UTID duplicates
                    utid_counts[escrow.utid] = utid_counts.get(escrow.utid, 0) + 1
                else:
                    stats["escrows_missing_utid"] += 1
                    stats["missing_utid_escrows"].append({
                        "internal_id": escrow.id,
                        "escrow_id": escrow.escrow_id,
                        "created_at": escrow.created_at.isoformat() if escrow.created_at else None
                    })
                
                # Track escrow_id duplicates
                if escrow.escrow_id:
                    escrow_id_counts[escrow.escrow_id] = escrow_id_counts.get(escrow.escrow_id, 0) + 1
            
            # Find duplicates
            stats["duplicate_utids"] = sum(1 for count in utid_counts.values() if count > 1)
            stats["duplicate_escrow_ids"] = sum(1 for count in escrow_id_counts.values() if count > 1)
            
            # Calculate consistency percentage
            consistency_percentage = (stats["escrows_with_utid"] / stats["total_escrows"] * 100) if stats["total_escrows"] > 0 else 0
            stats["consistency_percentage"] = round(consistency_percentage, 2)
            
            logger.info(f"ID_MAPPING_AUDIT: {stats['consistency_percentage']}% escrows have UTID ({stats['escrows_with_utid']}/{stats['total_escrows']})")
            
            return stats
            
        except Exception as e:
            logger.error(f"ID mapping audit failed: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def log_id_mapping_operation(operation: str, identifier: str, result: str, additional_info: Optional[Dict] = None):
        """
        Log ID mapping operations for monitoring and debugging
        
        Args:
            operation: Type of operation (lookup, create, update, etc.)
            identifier: The ID used in the operation
            result: Result of the operation (success, fallback, error, etc.)
            additional_info: Optional additional information
        """
        log_data = {
            "operation": operation,
            "identifier": identifier,
            "result": result
        }
        
        if additional_info:
            log_data.update(additional_info)
        
        # Log at appropriate level based on result
        if result.startswith("SUCCESS"):
            logger.info(f"ID_MAPPING_{result}: {operation} for {identifier}")
        elif result.startswith("FALLBACK"):
            logger.warning(f"ID_MAPPING_{result}: {operation} for {identifier} - {additional_info}")
        elif result.startswith("ERROR"):
            logger.error(f"ID_MAPPING_{result}: {operation} for {identifier} - {additional_info}")
        else:
            logger.debug(f"ID_MAPPING_{result}: {operation} for {identifier}")
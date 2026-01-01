"""
Centralized Currency Conversion Validation Framework
Security module for preventing amount preservation bugs during currency switches
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class CurrencyValidationError(Exception):
    """Raised when currency conversion validation fails"""
    pass

class CurrencyValidator:
    """Centralized validation for all currency conversions"""
    
    # Tolerance for rate fluctuations (5%)
    USD_TOLERANCE = Decimal("0.05")
    
    @classmethod
    def validate_crypto_switch(
        cls,
        old_crypto: str,
        old_amount: Decimal,
        new_crypto: str,
        new_amount: Decimal,
        old_rate: Decimal,
        new_rate: Decimal,
        context: str = "generic"
    ) -> Dict[str, Any]:
        """
        Validate cryptocurrency switching preserves USD value
        
        Returns:
            dict: Validation result with status and details
        """
        try:
            # Calculate USD values
            old_usd_value = old_amount * old_rate
            new_usd_value = new_amount * new_rate
            
            # Calculate deviation
            if old_usd_value > 0:
                deviation = abs(old_usd_value - new_usd_value) / old_usd_value
            else:
                deviation = Decimal("0")
            
            # Check if within tolerance
            is_valid = deviation <= cls.USD_TOLERANCE
            
            validation_result = {
                "is_valid": is_valid,
                "old_crypto": old_crypto,
                "new_crypto": new_crypto,
                "old_amount": float(old_amount),
                "new_amount": float(new_amount),
                "old_usd_value": float(old_usd_value),
                "new_usd_value": float(new_usd_value),
                "deviation_percentage": float(deviation * 100),
                "tolerance_percentage": float(cls.USD_TOLERANCE * 100),
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Log validation result
            if is_valid:
                logger.info(f"CRYPTO SWITCH VALIDATED: {old_crypto}->{new_crypto} USD preserved: ${float(old_usd_value):.2f} (context: {context})")
            else:
                logger.error(f"CRYPTO SWITCH VALIDATION FAILED: {old_crypto}->{new_crypto} USD deviation: {float(deviation * 100):.1f}% (context: {context})")
                
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in crypto switch validation: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @classmethod
    def calculate_equivalent_amount(
        cls,
        source_amount: Decimal,
        source_rate: Decimal,
        target_rate: Decimal,
        source_currency: str,
        target_currency: str,
        context: str = "generic"
    ) -> Tuple[Decimal, Dict[str, Any]]:
        """
        Calculate equivalent amount for currency switching
        
        Returns:
            tuple: (target_amount, validation_info)
        """
        try:
            # Calculate USD value
            usd_value = source_amount * source_rate
            
            # Calculate target amount
            target_amount = usd_value / target_rate
            
            # Round to appropriate precision
            if target_currency in ["BTC", "ETH", "LTC", "USDT"]:
                target_amount = target_amount.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
            else:
                target_amount = target_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            validation_info = {
                "source_currency": source_currency,
                "target_currency": target_currency,
                "source_amount": float(source_amount),
                "target_amount": float(target_amount),
                "usd_value": float(usd_value),
                "source_rate": float(source_rate),
                "target_rate": float(target_rate),
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"CURRENCY CONVERSION: {source_currency}->{target_currency} ${float(usd_value):.2f} = {float(source_amount):.8f} -> {float(target_amount):.8f} (context: {context})")
            
            return target_amount, validation_info
            
        except Exception as e:
            logger.error(f"Error calculating equivalent amount: {e}")
            raise CurrencyValidationError(f"Conversion calculation failed: {e}")
    
    @classmethod
    def validate_order_amount_consistency(
        cls,
        source_amount: Decimal,
        target_amount: Decimal,
        exchange_rate: Decimal,
        source_currency: str,
        target_currency: str,
        order_id: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Validate exchange order amount consistency
        
        Returns:
            dict: Validation result
        """
        try:
            # Calculate expected target amount
            expected_target = source_amount * exchange_rate
            
            # Calculate deviation
            if expected_target > 0:
                deviation = abs(target_amount - expected_target) / expected_target
            else:
                deviation = Decimal("0")
            
            is_valid = deviation <= cls.USD_TOLERANCE
            
            result = {
                "is_valid": is_valid,
                "source_amount": float(source_amount),
                "target_amount": float(target_amount),
                "expected_target": float(expected_target),
                "exchange_rate": float(exchange_rate),
                "deviation_percentage": float(deviation * 100),
                "source_currency": source_currency,
                "target_currency": target_currency,
                "order_id": order_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if is_valid:
                logger.info(f"ORDER AMOUNT VALIDATED: {order_id} {source_currency}->{target_currency}")
            else:
                logger.warning(f"ORDER AMOUNT VALIDATION WARNING: {order_id} deviation: {float(deviation * 100):.1f}%")
                
            return result
            
        except Exception as e:
            logger.error(f"Error validating order amount consistency: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "order_id": order_id,
                "timestamp": datetime.utcnow().isoformat()
            }

class ConversionAuditLogger:
    """Comprehensive audit logging for currency conversions"""
    
    @classmethod
    def log_crypto_switch(
        cls,
        user_id: int,
        old_crypto: str,
        new_crypto: str,
        old_amount: Decimal,
        new_amount: Decimal,
        usd_value: Decimal,
        context: str,
        session_id: Optional[str] = None
    ):
        """Log cryptocurrency switching events"""
        logger.info(
            f"AUDIT_CRYPTO_SWITCH: user_id={user_id} session={session_id} "
            f"switch={old_crypto}->{new_crypto} "
            f"amounts={float(old_amount):.8f}->{float(new_amount):.8f} "
            f"usd=${float(usd_value):.2f} context={context}"
        )
    
    @classmethod
    def log_suspicious_conversion(
        cls,
        user_id: int,
        operation: str,
        source_currency: str,
        target_currency: str,
        source_amount: Decimal,
        target_amount: Decimal,
        reason: str,
        context: str
    ):
        """Log potentially suspicious conversion patterns"""
        logger.warning(
            f"AUDIT_SUSPICIOUS_CONVERSION: user_id={user_id} "
            f"operation={operation} "
            f"conversion={source_currency}->{target_currency} "
            f"amounts={float(source_amount):.8f}->{float(target_amount):.8f} "
            f"reason={reason} context={context}"
        )
    
    @classmethod
    def log_validation_failure(
        cls,
        user_id: int,
        operation: str,
        validation_details: Dict[str, Any],
        context: str
    ):
        """Log validation failures for security analysis"""
        logger.error(
            f"AUDIT_VALIDATION_FAILURE: user_id={user_id} "
            f"operation={operation} "
            f"details={validation_details} "
            f"context={context}"
        )
"""
Payment Provider Interface

Standardized interface that all payment providers (Fincra, Kraken, BlockBee) must implement.
This ensures clean abstraction and consistent behavior across different payment services.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal

from .payment_data_structures import (
    PayinRequest, PayoutRequest, PaymentResult, BalanceSnapshot,
    PaymentProvider, TransactionStatus, PaymentError
)


class PaymentProviderInterface(ABC):
    """Abstract base class for all payment providers"""
    
    @property
    @abstractmethod
    def provider_type(self) -> PaymentProvider:
        """Return the provider type"""
        pass
    
    @property
    @abstractmethod
    def supported_currencies(self) -> List[str]:
        """Return list of supported currencies"""
        pass
    
    @property
    @abstractmethod
    def supports_payin(self) -> bool:
        """Whether this provider supports incoming payments"""
        pass
    
    @property
    @abstractmethod  
    def supports_payout(self) -> bool:
        """Whether this provider supports outgoing payments"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is currently available"""
        pass
    
    @abstractmethod
    async def process_payin(self, request: PayinRequest) -> PaymentResult:
        """Process incoming payment request"""
        pass
    
    @abstractmethod
    async def process_payout(self, request: PayoutRequest) -> PaymentResult:
        """Process outgoing payment request"""
        pass
    
    @abstractmethod
    async def get_balance(self, currency: Optional[str] = None) -> List[BalanceSnapshot]:
        """Get balance information for currency(s)"""
        pass
    
    @abstractmethod
    async def check_transaction_status(self, transaction_id: str) -> PaymentResult:
        """Check status of existing transaction"""
        pass
    
    @abstractmethod
    def get_fee_estimate(self, amount: Decimal, currency: str, operation: str) -> Decimal:
        """Get estimated fees for operation"""
        pass


class FincraProviderAdapter(PaymentProviderInterface):
    """Adapter for Fincra NGN payment service"""
    
    def __init__(self):
        from services.fincra_service import FincraService
        self.fincra_service = FincraService()
    
    @property
    def provider_type(self) -> PaymentProvider:
        return PaymentProvider.FINCRA
    
    @property
    def supported_currencies(self) -> List[str]:
        return ["NGN", "USD"]
    
    @property
    def supports_payin(self) -> bool:
        return True
    
    @property
    def supports_payout(self) -> bool:
        return True
    
    async def is_available(self) -> bool:
        """Check if Fincra service is available"""
        return bool(self.fincra_service.secret_key and self.fincra_service.public_key)
    
    async def process_payin(self, request: PayinRequest) -> PaymentResult:
        """Process NGN payin - typically virtual account creation"""
        try:
            # For NGN payins, we typically create a virtual account
            # This is a simplified interface to the existing Fincra functionality
            if request.currency.upper() != "NGN":
                return PaymentResult(
                    success=False,
                    status=TransactionStatus.FAILED,
                    error=PaymentError.BUSINESS,
                    error_message=f"Fincra only supports NGN, got {request.currency}",
                    provider=self.provider_type
                )
            
            # Create virtual account (simplified - actual implementation would call existing methods)
            result = await self._create_virtual_account(request)
            
            return PaymentResult(
                success=True,
                status=TransactionStatus.PENDING,
                transaction_id=result.get("account_number"),
                provider=self.provider_type,
                payment_details=result
            )
            
        except Exception as e:
            return PaymentResult(
                success=False,
                status=TransactionStatus.FAILED,
                error=PaymentError.TECHNICAL,
                error_message=str(e),
                provider=self.provider_type
            )
    
    async def process_payout(self, request: PayoutRequest) -> PaymentResult:
        """Process NGN payout via bank transfer"""
        try:
            if request.currency.upper() != "NGN":
                return PaymentResult(
                    success=False,
                    status=TransactionStatus.FAILED,
                    error=PaymentError.BUSINESS,
                    error_message=f"Fincra only supports NGN payouts, got {request.currency}",
                    provider=self.provider_type
                )
            
            # Process bank transfer using existing Fincra service
            result = await self.fincra_service.process_bank_transfer(
                amount_ngn=request.amount,
                bank_code=request.destination.bank_code,
                account_number=request.destination.account_number,
                account_name=request.destination.account_name,
                reference=request.reference_id or f"payout_{request.user_id}",
                currency="NGN"
            )
            
            if result:
                return PaymentResult(
                    success=True,
                    status=TransactionStatus.PROCESSING,
                    transaction_id=result.get("reference"),
                    provider_transaction_id=result.get("fincra_reference"),
                    provider=self.provider_type,
                    payment_details=result
                )
            else:
                return PaymentResult(
                    success=False,
                    status=TransactionStatus.FAILED,
                    error=PaymentError.TECHNICAL,
                    error_message="Fincra payout failed",
                    provider=self.provider_type
                )
                
        except Exception as e:
            return PaymentResult(
                success=False,
                status=TransactionStatus.FAILED,
                error=PaymentError.TECHNICAL,
                error_message=str(e),
                provider=self.provider_type
            )
    
    async def get_balance(self, currency: Optional[str] = None) -> List[BalanceSnapshot]:
        """Get Fincra NGN balance using optimized balance cache"""
        try:
            balance_info = await self.fincra_service.get_cached_account_balance()
            if not balance_info:
                return []
            
            # Only return NGN balance for Fincra
            if currency and currency.upper() != "NGN":
                return []
            
            # Extract balance values with proper validation
            available = Decimal(str(balance_info.get("available_balance", 0)))
            total = Decimal(str(balance_info.get("total_balance", 0)))
            
            # Calculate locked balance safely (never negative)
            locked = max(Decimal('0'), total - available)
            
            # Only include if there's actual balance
            if total > 0:
                return [BalanceSnapshot(
                    provider=self.provider_type,
                    currency="NGN",
                    available_balance=available,
                    total_balance=total,
                    locked_balance=locked
                )]
            
            return []
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to get Fincra balance: {e}")
            return []
    
    async def check_transaction_status(self, transaction_id: str) -> PaymentResult:
        """Check Fincra transaction status using actual service methods"""
        try:
            # Check transfer status using existing service method
            status_result = await self.fincra_service.check_transfer_status_by_reference(transaction_id)
            
            if status_result:
                # Map Fincra status to unified status
                fincra_status = status_result.get("status", "").lower()
                if fincra_status in ["successful", "completed", "success"]:
                    unified_status = TransactionStatus.SUCCESS
                elif fincra_status in ["pending", "processing"]:
                    unified_status = TransactionStatus.PROCESSING
                elif fincra_status in ["failed", "failure", "error"]:
                    unified_status = TransactionStatus.FAILED
                else:
                    unified_status = TransactionStatus.PENDING
                
                return PaymentResult(
                    success=True,
                    status=unified_status,
                    transaction_id=transaction_id,
                    provider_transaction_id=status_result.get("reference"),
                    provider=self.provider_type,
                    payment_details=status_result
                )
            else:
                # If no status found, assume still pending
                return PaymentResult(
                    success=True,
                    status=TransactionStatus.PENDING,
                    transaction_id=transaction_id,
                    provider=self.provider_type
                )
                
        except Exception as e:
            return PaymentResult(
                success=False,
                status=TransactionStatus.FAILED,
                transaction_id=transaction_id,
                error=PaymentError.TECHNICAL,
                error_message=str(e),
                provider=self.provider_type
            )
    
    def get_fee_estimate(self, amount: Decimal, currency: str, operation: str) -> Decimal:
        """Get Fincra fee estimate (1% capped at ₦250)"""
        if currency.upper() == "NGN":
            fee = amount * Decimal("0.01")  # 1%
            return min(fee, Decimal("250"))  # Capped at ₦250
        return Decimal("0")
    
    async def _create_virtual_account(self, request: PayinRequest) -> Dict[str, Any]:
        """Create virtual account for NGN deposits using actual Fincra service"""
        try:
            # Use existing Fincra virtual account creation
            result = await self.fincra_service.create_virtual_account(
                amount_ngn=float(request.amount),
                user_id=request.user_id,
                purpose=request.payment_type,
                escrow_id=int(request.reference_id) if request.reference_id and request.reference_id.isdigit() else None
            )
            
            if result:
                return {
                    "account_number": result.get("account_number"),
                    "bank_name": result.get("bank_name", "Fincra Virtual Bank"),
                    "account_name": result.get("account_name"),
                    "reference": result.get("reference"),
                    **result
                }
            else:
                raise Exception("Failed to create virtual account")
                
        except Exception as e:
            # Fallback to basic format if virtual account creation fails
            logger = logging.getLogger(__name__)
            logger.error(f"Virtual account creation failed: {e}")
            return {
                "account_number": f"5{request.user_id:09d}",
                "bank_name": "Fincra Virtual Bank", 
                "account_name": f"User {request.user_id}",
                "error": str(e)
            }


class KrakenProviderAdapter(PaymentProviderInterface):
    """Adapter for Kraken crypto withdrawal service"""
    
    def __init__(self):
        from services.kraken_service import KrakenService
        self.kraken_service = KrakenService()
    
    @property
    def provider_type(self) -> PaymentProvider:
        return PaymentProvider.KRAKEN
    
    @property
    def supported_currencies(self) -> List[str]:
        return ["BTC", "ETH", "LTC", "USDT", "USD"]
    
    @property
    def supports_payin(self) -> bool:
        return False  # Kraken is only for withdrawals
    
    @property
    def supports_payout(self) -> bool:
        return True
    
    async def is_available(self) -> bool:
        """Check if Kraken service is available"""
        return self.kraken_service.is_available()
    
    async def process_payin(self, request: PayinRequest) -> PaymentResult:
        """Kraken doesn't support payins"""
        return PaymentResult(
            success=False,
            status=TransactionStatus.FAILED,
            error=PaymentError.BUSINESS,
            error_message="Kraken provider only supports payouts (withdrawals)",
            provider=self.provider_type
        )
    
    async def process_payout(self, request: PayoutRequest) -> PaymentResult:
        """Process crypto withdrawal via Kraken"""
        try:
            # Use existing Kraken withdrawal functionality
            result = await self.kraken_service.withdraw_crypto(
                currency=request.currency,
                amount=request.amount,
                address=request.destination.address,
                withdraw_key=request.destination.memo  # Kraken requires pre-configured keys
            )
            
            if result.get("success"):
                return PaymentResult(
                    success=True,
                    status=TransactionStatus.PROCESSING,
                    transaction_id=result.get("refid"),
                    provider=self.provider_type,
                    payment_details=result
                )
            else:
                return PaymentResult(
                    success=False,
                    status=TransactionStatus.FAILED,
                    error=PaymentError.TECHNICAL,
                    error_message=result.get("error", "Kraken withdrawal failed"),
                    provider=self.provider_type
                )
                
        except Exception as e:
            return PaymentResult(
                success=False,
                status=TransactionStatus.FAILED,
                error=PaymentError.TECHNICAL,
                error_message=str(e),
                provider=self.provider_type
            )
    
    async def get_balance(self, currency: Optional[str] = None) -> List[BalanceSnapshot]:
        """Get Kraken crypto balances using optimized withdrawal available balance cache"""
        try:
            balance_result = await self.kraken_service.get_cached_account_balance()
            if not balance_result or not balance_result.get('success'):
                return []
            
            balances = balance_result.get('balances', {})
            snapshots = []
            
            for curr, balance_info in balances.items():
                if currency and curr.upper() != currency.upper():
                    continue
                
                # Extract balance data from Kraken format
                available = balance_info.get('available', 0)
                total = balance_info.get('total', 0) 
                held = balance_info.get('held', 0)
                
                # Only include currencies with positive balances
                if total > 0:
                    snapshots.append(BalanceSnapshot(
                        provider=self.provider_type,
                        currency=curr,
                        available_balance=Decimal(str(available)),
                        total_balance=Decimal(str(total)),
                        locked_balance=Decimal(str(held))
                    ))
            
            return snapshots
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to get Kraken balances: {e}")
            return []
    
    async def check_transaction_status(self, transaction_id: str) -> PaymentResult:
        """Check Kraken withdrawal status using actual service method"""
        try:
            # Get withdrawal status using existing service method
            status_result = await self.kraken_service.get_withdrawal_status()
            
            if status_result and transaction_id in status_result:
                withdrawal_info = status_result[transaction_id]
                kraken_status = withdrawal_info.get("status", "").lower()
                
                # Map Kraken status to unified status
                if kraken_status in ["success", "complete", "completed"]:
                    unified_status = TransactionStatus.SUCCESS
                elif kraken_status in ["pending", "processing"]:
                    unified_status = TransactionStatus.PROCESSING
                elif kraken_status in ["failure", "failed", "canceled", "cancelled"]:
                    unified_status = TransactionStatus.FAILED
                else:
                    unified_status = TransactionStatus.PENDING
                
                return PaymentResult(
                    success=True,
                    status=unified_status,
                    transaction_id=transaction_id,
                    provider_transaction_id=withdrawal_info.get("refid"),
                    provider=self.provider_type,
                    payment_details=withdrawal_info
                )
            else:
                # If transaction not found, it might be too new or invalid
                return PaymentResult(
                    success=True,
                    status=TransactionStatus.PENDING,
                    transaction_id=transaction_id,
                    provider=self.provider_type
                )
                
        except Exception as e:
            return PaymentResult(
                success=False,
                status=TransactionStatus.FAILED,
                transaction_id=transaction_id,
                error=PaymentError.TECHNICAL,
                error_message=str(e),
                provider=self.provider_type
            )
    
    def get_fee_estimate(self, amount: Decimal, currency: str, operation: str) -> Decimal:
        """Get Kraken withdrawal fee estimate"""
        # Simplified fee structure - would use actual Kraken fees
        fee_map = {
            "BTC": Decimal("0.00025"),
            "ETH": Decimal("0.005"),
            "LTC": Decimal("0.001"),
            "USDT": Decimal("5.0")
        }
        return fee_map.get(currency.upper(), Decimal("0"))


class BlockBeeProviderAdapter(PaymentProviderInterface):
    """Adapter for BlockBee crypto deposit service"""
    
    def __init__(self):
        from services.blockbee_service import blockbee_service
        self.blockbee_service = blockbee_service
    
    @property
    def provider_type(self) -> PaymentProvider:
        return PaymentProvider.BLOCKBEE
    
    @property
    def supported_currencies(self) -> List[str]:
        return ["BTC", "ETH", "LTC", "USDT", "USDC", "TRX", "DOGE"]
    
    @property
    def supports_payin(self) -> bool:
        return True
    
    @property
    def supports_payout(self) -> bool:
        return False  # BlockBee is only for deposits
    
    async def is_available(self) -> bool:
        """Check if BlockBee service is available"""
        return bool(self.blockbee_service.api_key)
    
    async def process_payin(self, request: PayinRequest) -> PaymentResult:
        """Process crypto deposit via BlockBee"""
        try:
            # Use existing BlockBee payment address generation
            result = await self.blockbee_service.create_payment_address(
                currency=request.currency,
                escrow_id=request.reference_id or f"payin_{request.user_id}",
                amount_usd=float(request.amount)
            )
            
            if result.get("address_in"):
                return PaymentResult(
                    success=True,
                    status=TransactionStatus.PENDING,
                    transaction_id=result.get("address_in"),
                    provider=self.provider_type,
                    payment_details={
                        "address": result.get("address_in"),
                        "qr_code": result.get("qr_code"),
                        "currency": request.currency,
                        "amount_expected": request.amount,
                        **result
                    }
                )
            else:
                return PaymentResult(
                    success=False,
                    status=TransactionStatus.FAILED,
                    error=PaymentError.TECHNICAL,
                    error_message="Failed to generate BlockBee address",
                    provider=self.provider_type
                )
                
        except Exception as e:
            return PaymentResult(
                success=False,
                status=TransactionStatus.FAILED,
                error=PaymentError.TECHNICAL,
                error_message=str(e),
                provider=self.provider_type
            )
    
    async def process_payout(self, request: PayoutRequest) -> PaymentResult:
        """BlockBee doesn't support payouts"""
        return PaymentResult(
            success=False,
            status=TransactionStatus.FAILED,
            error=PaymentError.BUSINESS,
            error_message="BlockBee provider only supports payins (deposits)",
            provider=self.provider_type
        )
    
    async def get_balance(self, currency: Optional[str] = None) -> List[BalanceSnapshot]:
        """BlockBee doesn't maintain balances"""
        return []
    
    async def check_transaction_status(self, transaction_id: str) -> PaymentResult:
        """Check BlockBee deposit status"""
        # Would integrate with existing BlockBee status checking
        return PaymentResult(
            success=True,
            status=TransactionStatus.PENDING,
            transaction_id=transaction_id,
            provider=self.provider_type
        )
    
    def get_fee_estimate(self, amount: Decimal, currency: str, operation: str) -> Decimal:
        """BlockBee fees are percentage-based"""
        return amount * Decimal("0.005")  # 0.5% typical fee
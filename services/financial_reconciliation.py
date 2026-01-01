#!/usr/bin/env python3
"""
Financial Reconciliation Service
Daily financial reconciliation system for multi-provider operations
"""

import logging
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from dataclasses import dataclass

from sqlalchemy import func
from database import SessionLocal
from models import FinancialReconciliation, Wallet, Transaction, Cashout
from utils.atomic_transactions import atomic_transaction
from services.consolidated_notification_service import (
    consolidated_notification_service as NotificationService,
)

# from services.binance_service import BinanceService  # Placeholder
# from services.fincra_service import FincraService    # Placeholder

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationDiscrepancy:
    """Represents a reconciliation discrepancy"""

    provider: str
    currency: str
    internal_balance: Decimal
    external_balance: Decimal
    discrepancy: Decimal
    discrepancy_percentage: float
    transaction_count_diff: int
    severity: str  # 'low', 'medium', 'high', 'critical'


@dataclass
class ReconciliationReport:
    """Complete reconciliation report"""

    reconciliation_date: datetime
    total_providers_checked: int
    matched_balances: int
    discrepancies_found: int
    total_discrepancy_amount: Decimal
    critical_issues: List[ReconciliationDiscrepancy]
    processing_time_ms: int
    status: str


class FinancialReconciliationService:
    """Comprehensive financial reconciliation service"""

    def __init__(self):
        self.notification_service = NotificationService
        # self.binance_service = BinanceService()  # Placeholder
        # self.fincra_service = FincraService()    # Placeholder

        # INTELLIGENT RECONCILIATION: Initialize adaptive service
        from services.intelligent_reconciliation_service import IntelligentReconciliationService
        self.intelligent_reconciliation = IntelligentReconciliationService()
        
        # Legacy fallback thresholds (used only when intelligent service fails)
        self.fallback_thresholds = {
            "low": Decimal("1.00"),     # Fallback only
            "medium": Decimal("10.00"),  # Fallback only
            "high": Decimal("100.00"),   # Fallback only
            "critical": Decimal("1000.00"), # Fallback only
        }

        # Percentage thresholds
        self.percentage_thresholds = {
            "low": 0.1,  # 0.1%
            "medium": 1.0,  # 1.0%
            "high": 5.0,  # 5.0%
            "critical": 10.0,  # 10.0%
        }

        logger.info("Financial reconciliation service initialized")

    async def perform_daily_reconciliation(
        self, reconciliation_date: Optional[datetime] = None
    ) -> ReconciliationReport:
        """Perform comprehensive daily reconciliation"""
        if reconciliation_date is None:
            reconciliation_date = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        start_time = datetime.utcnow()
        logger.info(f"Starting daily reconciliation for {reconciliation_date.date()}")

        try:
            # Get list of currencies to reconcile
            currencies_to_check = await self._get_active_currencies()

            discrepancies = []
            matched_count = 0
            total_discrepancy = Decimal("0")

            # Reconcile each provider and currency
            for currency in currencies_to_check:
                # Binance reconciliation
                binance_result = await self._reconcile_binance_balance(
                    currency, reconciliation_date
                )
                if binance_result:
                    if binance_result.discrepancy != Decimal("0"):
                        discrepancies.append(binance_result)
                        total_discrepancy += abs(binance_result.discrepancy)
                    else:
                        matched_count += 1

                # Fincra reconciliation (NGN only)
                if currency == "NGN":
                    fincra_result = await self._reconcile_fincra_balance(
                        currency, reconciliation_date
                    )
                    if fincra_result:
                        if fincra_result.discrepancy != Decimal("0"):
                            discrepancies.append(fincra_result)
                            total_discrepancy += abs(fincra_result.discrepancy)
                        else:
                            matched_count += 1

                # Internal wallet consistency check
                internal_result = await self._check_internal_consistency(
                    currency, reconciliation_date
                )
                if internal_result:
                    if internal_result.discrepancy != Decimal("0"):
                        discrepancies.append(internal_result)
                        total_discrepancy += abs(internal_result.discrepancy)
                    else:
                        matched_count += 1

            # Generate report
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            critical_issues = [d for d in discrepancies if d.severity == "critical"]

            report = ReconciliationReport(
                reconciliation_date=reconciliation_date,
                total_providers_checked=len(currencies_to_check)
                * 2,  # Binance + internal
                matched_balances=matched_count,
                discrepancies_found=len(discrepancies),
                total_discrepancy_amount=total_discrepancy,
                critical_issues=critical_issues,
                processing_time_ms=processing_time_ms,
                status=(
                    "completed" if len(critical_issues) == 0 else "requires_attention"
                ),
            )

            # Store reconciliation records
            await self._store_reconciliation_records(discrepancies, reconciliation_date)

            # Send notifications for critical issues
            if critical_issues:
                await self._send_critical_alerts(critical_issues, reconciliation_date)

            # Send daily summary report
            await self._send_daily_summary(report)

            logger.info(
                f"Daily reconciliation completed: {len(discrepancies)} discrepancies found"
            )
            return report

        except Exception as e:
            logger.error(f"Error in daily reconciliation: {e}")
            # Send error notification
            await self._send_error_notification(e, reconciliation_date)
            raise

    async def _get_active_currencies(self) -> List[str]:
        """Get list of active currencies that need reconciliation"""
        try:
            with SessionLocal() as session:
                # Get currencies that have active wallets with balances
                active_currencies = (
                    session.query(Wallet.currency)
                    .filter(Wallet.available_balance > 0)
                    .distinct()
                    .all()
                )

                currencies = [row[0] for row in active_currencies]

                # Always include primary currencies even if no current balances
                primary_currencies = ["USD", "BTC", "ETH", "USDT", "NGN"]
                for currency in primary_currencies:
                    if currency not in currencies:
                        currencies.append(currency)

                logger.info(f"Active currencies for reconciliation: {currencies}")
                return currencies

        except Exception as e:
            logger.error(f"Error getting active currencies: {e}")
            return ["USD", "BTC", "ETH", "USDT", "NGN"]  # Fallback

    async def _reconcile_binance_balance(
        self, currency: str, reconciliation_date: datetime
    ) -> Optional[ReconciliationDiscrepancy]:
        """Reconcile Binance account balance with internal records"""
        try:
            # Get internal balance from cashout records
            internal_balance = await self._get_internal_binance_balance(
                currency, reconciliation_date
            )

            # Get external balance from Binance API (placeholder)
            external_balance = Decimal("0")  # Placeholder implementation

            if external_balance is None:
                logger.warning(f"Could not fetch Binance balance for {currency}")
                return None

            # Calculate discrepancy
            discrepancy = external_balance - internal_balance
            discrepancy_percentage = (
                float(abs(discrepancy) / internal_balance * 100)
                if internal_balance > 0
                else 0
            )

            # Determine severity
            severity = self._calculate_discrepancy_severity(
                abs(discrepancy), discrepancy_percentage
            )

            # Get transaction count difference
            tx_count_diff = await self._get_transaction_count_difference(
                "binance", currency, reconciliation_date
            )

            result = ReconciliationDiscrepancy(
                provider="binance",
                currency=currency,
                internal_balance=internal_balance,
                external_balance=external_balance,
                discrepancy=discrepancy,
                discrepancy_percentage=discrepancy_percentage,
                transaction_count_diff=tx_count_diff,
                severity=severity,
            )

            logger.info(
                f"Binance {currency} reconciliation: Internal={internal_balance}, External={external_balance}, Diff={discrepancy}"
            )
            return result

        except Exception as e:
            logger.error(f"Error reconciling Binance balance for {currency}: {e}")
            return None

    async def _reconcile_fincra_balance(
        self, currency: str, reconciliation_date: datetime
    ) -> Optional[ReconciliationDiscrepancy]:
        """Reconcile Fincra account balance with internal records"""
        if currency != "NGN":
            return None

        try:
            # Get internal NGN balance
            internal_balance = await self._get_internal_fincra_balance(
                reconciliation_date
            )

            # Get external balance from Fincra API (placeholder)
            external_balance = Decimal("0")  # Placeholder implementation

            if external_balance is None:
                logger.warning("Could not fetch Fincra balance")
                return None

            # Calculate discrepancy
            discrepancy = external_balance - internal_balance
            discrepancy_percentage = (
                float(abs(discrepancy) / internal_balance * 100)
                if internal_balance > 0
                else 0
            )

            # Determine severity
            severity = self._calculate_discrepancy_severity(
                abs(discrepancy), discrepancy_percentage
            )

            # Get transaction count difference
            tx_count_diff = await self._get_transaction_count_difference(
                "fincra", currency, reconciliation_date
            )

            result = ReconciliationDiscrepancy(
                provider="fincra",
                currency=currency,
                internal_balance=internal_balance,
                external_balance=external_balance,
                discrepancy=discrepancy,
                discrepancy_percentage=discrepancy_percentage,
                transaction_count_diff=tx_count_diff,
                severity=severity,
            )

            logger.info(
                f"Fincra NGN reconciliation: Internal={internal_balance}, External={external_balance}, Diff={discrepancy}"
            )
            return result

        except Exception as e:
            logger.error(f"Error reconciling Fincra balance: {e}")
            return None

    async def _check_internal_consistency(
        self, currency: str, reconciliation_date: datetime
    ) -> Optional[ReconciliationDiscrepancy]:
        """Check internal wallet balance consistency"""
        try:
            with SessionLocal() as session:
                # Get sum of all user wallet balances
                user_balances = session.query(func.sum(Wallet.available_balance)).filter(
                    Wallet.currency == currency
                ).scalar() or Decimal("0")

                # Get sum of all transactions for this currency
                transaction_sum = session.query(
                    func.sum(Transaction.net_amount)
                ).filter(
                    Transaction.currency == currency,
                    Transaction.status == "confirmed",
                    Transaction.created_at <= reconciliation_date,
                ).scalar() or Decimal(
                    "0"
                )

                # Calculate expected balance based on transactions
                expected_balance = transaction_sum

                # Calculate discrepancy
                discrepancy = user_balances - expected_balance
                discrepancy_percentage = (
                    float(abs(discrepancy) / expected_balance * 100)
                    if expected_balance > 0
                    else 0
                )

                # Determine severity
                severity = self._calculate_discrepancy_severity(
                    abs(discrepancy), discrepancy_percentage
                )

                if abs(discrepancy) > Decimal("0.01"):  # More than 1 cent difference
                    result = ReconciliationDiscrepancy(
                        provider="internal",
                        currency=currency,
                        internal_balance=expected_balance,
                        external_balance=user_balances,
                        discrepancy=discrepancy,
                        discrepancy_percentage=discrepancy_percentage,
                        transaction_count_diff=0,
                        severity=severity,
                    )

                    logger.warning(
                        f"Internal consistency issue for {currency}: Expected={expected_balance}, Actual={user_balances}, Diff={discrepancy}"
                    )
                    return result

                return None

        except Exception as e:
            logger.error(f"Error checking internal consistency for {currency}: {e}")
            return None

    async def _get_internal_binance_balance(
        self, currency: str, reconciliation_date: datetime
    ) -> Decimal:
        """Get internal balance that should be in Binance"""
        try:
            with SessionLocal() as session:
                # Get sum of all successful cashouts via Binance
                cashout_sum = session.query(func.sum(Cashout.net_amount)).filter(
                    Cashout.currency == currency,
                    Cashout.processing_method == "binance",
                    Cashout.status == "completed",
                    Cashout.completed_at <= reconciliation_date,
                ).scalar() or Decimal("0")

                # This represents what we should have sent through Binance
                return cashout_sum

        except Exception as e:
            logger.error(f"Error getting internal Binance balance for {currency}: {e}")
            return Decimal("0")

    async def _get_internal_fincra_balance(
        self, reconciliation_date: datetime
    ) -> Decimal:
        """Get internal balance that should be in Fincra"""
        try:
            with SessionLocal() as session:
                # Get sum of all successful NGN cashouts via Fincra
                cashout_sum = session.query(func.sum(Cashout.net_amount)).filter(
                    Cashout.currency == "NGN",
                    Cashout.cashout_type == "ngn_bank",
                    Cashout.status == "completed",
                    Cashout.completed_at <= reconciliation_date,
                ).scalar() or Decimal("0")

                return cashout_sum

        except Exception as e:
            logger.error(f"Error getting internal Fincra balance: {e}")
            return Decimal("0")

    async def _get_transaction_count_difference(
        self, provider: str, currency: str, reconciliation_date: datetime
    ) -> int:
        """Get difference in transaction counts between internal and external"""
        try:
            with SessionLocal() as session:
                # Count internal transactions
                if provider == "binance":
                    internal_count = (
                        session.query(Cashout)
                        .filter(
                            Cashout.currency == currency,
                            Cashout.processing_method == "binance",
                            Cashout.status == "completed",
                            Cashout.completed_at <= reconciliation_date,
                        )
                        .count()
                    )
                elif provider == "fincra":
                    internal_count = (
                        session.query(Cashout)
                        .filter(
                            Cashout.currency == "NGN",
                            Cashout.cashout_type == "ngn_bank",
                            Cashout.status == "completed",
                            Cashout.completed_at <= reconciliation_date,
                        )
                        .count()
                    )
                else:
                    internal_count = 0

                # External count would need to be fetched from provider APIs
                # For now, return 0 as placeholder
                external_count = 0

                return internal_count - external_count

        except Exception as e:
            logger.error(f"Error getting transaction count difference: {e}")
            return 0

    def _calculate_discrepancy_severity(
        self, discrepancy_amount: Decimal, discrepancy_percentage: float
    ) -> str:
        """Calculate severity level of discrepancy"""
        # Check amount thresholds
        if discrepancy_amount >= self.fallback_thresholds["critical"]:
            return "critical"
        elif discrepancy_amount >= self.fallback_thresholds["high"]:
            return "high"
        elif discrepancy_amount >= self.fallback_thresholds["medium"]:
            return "medium"
        elif discrepancy_amount >= self.fallback_thresholds["low"]:
            return "low"

        # Check percentage thresholds
        if discrepancy_percentage >= self.percentage_thresholds["critical"]:
            return "critical"
        elif discrepancy_percentage >= self.percentage_thresholds["high"]:
            return "high"
        elif discrepancy_percentage >= self.percentage_thresholds["medium"]:
            return "medium"
        elif discrepancy_percentage >= self.percentage_thresholds["low"]:
            return "low"

        return "low"

    async def _store_reconciliation_records(
        self,
        discrepancies: List[ReconciliationDiscrepancy],
        reconciliation_date: datetime,
    ):
        """Store reconciliation records in database"""
        try:
            with atomic_transaction() as session:
                for discrepancy in discrepancies:
                    reconciliation_id = f"recon_{reconciliation_date.strftime('%Y%m%d')}_{discrepancy.provider}_{discrepancy.currency}"

                    # Check if record already exists
                    existing = (
                        session.query(FinancialReconciliation)
                        .filter(
                            FinancialReconciliation.reconciliation_id
                            == reconciliation_id
                        )
                        .first()
                    )

                    if existing:
                        # Update existing record using session.merge or direct updates
                        session.query(FinancialReconciliation).filter(
                            FinancialReconciliation.reconciliation_id
                            == reconciliation_id
                        ).update(
                            {
                                "internal_balance": discrepancy.internal_balance,
                                "external_balance": discrepancy.external_balance,
                                "discrepancy": discrepancy.discrepancy,
                                "internal_tx_count": 0,
                                "external_tx_count": 0,
                                "status": (
                                    "discrepancy"
                                    if discrepancy.discrepancy != Decimal("0")
                                    else "matched"
                                ),
                                "completed_at": datetime.utcnow(),
                            }
                        )
                    else:
                        # Create new record
                        reconciliation = FinancialReconciliation(
                            reconciliation_id=reconciliation_id,
                            reconciliation_date=reconciliation_date,
                            provider=discrepancy.provider,
                            currency=discrepancy.currency,
                            internal_balance=discrepancy.internal_balance,
                            external_balance=discrepancy.external_balance,
                            discrepancy=discrepancy.discrepancy,
                            internal_tx_count=0,  # Placeholder
                            external_tx_count=0,  # Placeholder
                            status=(
                                "discrepancy"
                                if discrepancy.discrepancy != Decimal("0")
                                else "matched"
                            ),
                            completed_at=datetime.utcnow(),
                        )
                        session.add(reconciliation)

                logger.info(f"Stored {len(discrepancies)} reconciliation records")

        except Exception as e:
            logger.error(f"Error storing reconciliation records: {e}")

    async def _send_critical_alerts(
        self,
        critical_issues: List[ReconciliationDiscrepancy],
        reconciliation_date: datetime,
    ):
        """Send alerts for critical reconciliation issues"""
        try:
            if not critical_issues:
                return

            # Format alert message
            alert_message = (
                f"🚨 CRITICAL RECONCILIATION ISSUES - {reconciliation_date.date()}\n\n"
            )

            for issue in critical_issues:
                alert_message += f"Provider: {issue.provider.upper()}\n"
                alert_message += f"Currency: {issue.currency}\n"
                alert_message += f"Internal Balance: {issue.internal_balance}\n"
                alert_message += f"External Balance: {issue.external_balance}\n"
                alert_message += f"Discrepancy: {issue.discrepancy} ({issue.discrepancy_percentage:.1f}%)\n\n"

            alert_message += "⚠️ Immediate attention required!"

            # Send to admin notification channels
            await self.notification_service.notify_all_admins(message=alert_message)

            logger.warning(
                f"Sent critical reconciliation alerts for {len(critical_issues)} issues"
            )

        except Exception as e:
            logger.error(f"Error sending critical alerts: {e}")

    async def _send_daily_summary(self, report: ReconciliationReport):
        """Send daily reconciliation summary report"""
        try:
            # Format summary message
            summary_message = f"📊 Daily Reconciliation Report - {report.reconciliation_date.date()}\n\n"
            summary_message += (
                f"✅ Providers Checked: {report.total_providers_checked}\n"
            )
            summary_message += f"✅ Matched Balances: {report.matched_balances}\n"
            summary_message += f"⚠️ Discrepancies Found: {report.discrepancies_found}\n"
            summary_message += (
                f"💰 Total Discrepancy: ${report.total_discrepancy_amount}\n"
            )
            summary_message += f"🔥 Critical Issues: {len(report.critical_issues)}\n"
            summary_message += f"⏱️ Processing Time: {report.processing_time_ms}ms\n"
            summary_message += f"📈 Status: {report.status.upper()}\n"

            if report.critical_issues:
                summary_message += "\n🚨 Requires immediate attention!"
            else:
                summary_message += "\n✅ All systems operational"

            # Send to admin channels
            await self.notification_service.notify_all_admins(message=summary_message)

            logger.info("Sent daily reconciliation summary report")

        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")

    async def _send_error_notification(
        self, error: Exception, reconciliation_date: datetime
    ):
        """Send notification when reconciliation fails"""
        try:
            error_message = (
                f"❌ Reconciliation Failed - {reconciliation_date.date()}\n\n"
            )
            error_message += f"Error: {str(error)}\n"
            error_message += "🔧 Manual intervention required"

            await self.notification_service.notify_all_admins(message=error_message)

        except Exception as e:
            logger.error(f"Error sending error notification: {e}")


# Global instance
financial_reconciliation_service = FinancialReconciliationService()


# Job functions for scheduler integration
async def run_daily_reconciliation():
    """Job function for daily reconciliation"""
    try:
        report = await financial_reconciliation_service.perform_daily_reconciliation()
        logger.info(f"Daily reconciliation completed: {report.status}")
        return report
    except Exception as e:
        logger.error(f"Daily reconciliation job failed: {e}")
        raise

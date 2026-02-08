"""
Unified Financial Gateway
Consolidates all financial services: exchange rates, currency conversions,
payment processing, and decimal precision handling
"""

import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Dict, Optional, Union, Any, List
from dataclasses import dataclass
from config import Config
from caching.simple_cache import SimpleCache
from services.api_key_validator import api_validator

# Set global decimal precision for financial calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)

# ============ FINANCIAL EXCEPTIONS ============


class FinancialGatewayError(Exception):
    """Base exception for financial gateway errors"""

    pass


class ExchangeRateError(FinancialGatewayError):
    """Exception for exchange rate related errors"""

    pass


class PaymentProcessingError(FinancialGatewayError):
    """Exception for payment processing errors"""

    pass


class PrecisionError(FinancialGatewayError):
    """Exception for decimal precision errors"""

    pass


# ============ DATACLASSES ============


@dataclass
class ExchangeRate:
    """Standardized exchange rate data structure"""

    base_currency: str
    target_currency: str
    rate: Decimal
    timestamp: datetime
    source: str
    cached: bool = False


@dataclass
class ConversionResult:
    """Standardized conversion result"""

    source_amount: Decimal
    source_currency: str
    target_amount: Decimal
    target_currency: str
    exchange_rate: Decimal
    markup_percentage: Decimal
    markup_amount: Decimal
    effective_rate: Decimal
    timestamp: datetime
    rate_locked: bool = False
    lock_id: Optional[str] = None


# ============ DECIMAL PRECISION UTILITIES ============


class MonetaryDecimal:
    """Unified decimal precision handler for all financial operations"""

    USD_PRECISION = Decimal("0.01")  # 2 decimal places for USD
    CRYPTO_PRECISION = Decimal("0.00000001")  # 8 decimal places for crypto
    NGN_PRECISION = Decimal("0.01")  # 2 decimal places for NGN
    RATE_PRECISION = Decimal("0.00000001")  # 8 decimal places for exchange rates

    @classmethod
    def to_decimal(
        cls, value: Union[str, int, float, Decimal], context: str = "monetary"
    ) -> Decimal:
        """Safely convert any numeric value to Decimal with validation"""
        if value is None:
            return Decimal("0")

        if isinstance(value, Decimal):
            return value

        try:
            decimal_value = Decimal(str(value))

            # Validate reasonable range for monetary values
            if abs(decimal_value) > Decimal("999999999999"):  # 999 billion limit
                logger.warning(
                    f"Unusually large monetary value: {decimal_value} in context: {context}"
                )

            return decimal_value
        except Exception as e:
            logger.error(
                f"Failed to convert {value} to Decimal in context {context}: {e}"
            )
            return Decimal("0")

    @classmethod
    def quantize_usd(cls, amount: Union[str, int, float, Decimal]) -> Decimal:
        """Quantize amount to USD precision (2 decimal places)"""
        decimal_amount = cls.to_decimal(amount, "USD")
        return decimal_amount.quantize(cls.USD_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def quantize_crypto(cls, amount: Union[str, int, float, Decimal]) -> Decimal:
        """Quantize amount to crypto precision (8 decimal places)"""
        decimal_amount = cls.to_decimal(amount, "crypto")
        return decimal_amount.quantize(cls.CRYPTO_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def quantize_ngn(cls, amount: Union[str, int, float, Decimal]) -> Decimal:
        """Quantize amount to NGN precision (2 decimal places)"""
        decimal_amount = cls.to_decimal(amount, "NGN")
        return decimal_amount.quantize(cls.NGN_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def quantize_rate(cls, rate: Union[str, int, float, Decimal]) -> Decimal:
        """Quantize exchange rate to high precision (8 decimal places)"""
        decimal_rate = cls.to_decimal(rate, "exchange_rate")
        return decimal_rate.quantize(cls.RATE_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def multiply_precise(
        cls,
        amount: Union[str, int, float, Decimal],
        rate: Union[str, int, float, Decimal],
        result_precision: Optional[Decimal] = None,
    ) -> Decimal:
        """Multiply two values with proper precision handling"""
        amount_decimal = cls.to_decimal(amount, "multiply_amount")
        rate_decimal = cls.to_decimal(rate, "multiply_rate")

        result = amount_decimal * rate_decimal

        if result_precision:
            return result.quantize(result_precision, rounding=ROUND_HALF_UP)
        else:
            return result.quantize(cls.USD_PRECISION, rounding=ROUND_HALF_UP)

    @classmethod
    def add_precise(cls, *amounts: Union[str, int, float, Decimal]) -> Decimal:
        """Add multiple amounts with proper precision"""
        total = Decimal("0")
        for amount in amounts:
            amount_decimal = cls.to_decimal(amount, "addition")
            total += amount_decimal

        return cls.quantize_usd(total)

    @classmethod
    def subtract_precise(
        cls,
        minuend: Union[str, int, float, Decimal],
        subtrahend: Union[str, int, float, Decimal],
    ) -> Decimal:
        """Subtract with proper precision"""
        minuend_decimal = cls.to_decimal(minuend, "subtraction_minuend")
        subtrahend_decimal = cls.to_decimal(subtrahend, "subtraction_subtrahend")

        result = minuend_decimal - subtrahend_decimal
        return cls.quantize_usd(result)

    @classmethod
    def divide_precise(
        cls,
        dividend: Union[str, int, float, Decimal],
        divisor: Union[str, int, float, Decimal],
        result_precision: Optional[Decimal] = None,
    ) -> Decimal:
        """Divide with proper precision and zero protection"""
        dividend_decimal = cls.to_decimal(dividend, "divide_dividend")
        divisor_decimal = cls.to_decimal(divisor, "divide_divisor")

        if divisor_decimal == 0:
            logger.error(f"Division by zero attempted: {dividend} / {divisor}")
            return Decimal("0")

        result = dividend_decimal / divisor_decimal

        if result_precision:
            return result.quantize(result_precision, rounding=ROUND_HALF_UP)
        else:
            return result.quantize(cls.RATE_PRECISION, rounding=ROUND_HALF_UP)


# ============ UNIFIED FINANCIAL GATEWAY ============


class UnifiedFinancialGateway:
    """Consolidated financial service gateway"""

    def __init__(self):
        # API Configuration with validation
        self.fastforex_api_key = api_validator.get_api_key("FASTFOREX_API_KEY")
        self.tatum_api_key = api_validator.get_api_key("TATUM_API_KEY")
        self.backup_api_key = api_validator.get_api_key("BACKUP_FOREX_API_KEY")

        # API Endpoints
        self.fastforex_base_url = "https://api.fastforex.io"
        self.tatum_api_url = "https://api.tatum.io/v4/data/rate/symbol"

        # Caching
        self.rate_cache = SimpleCache(default_ttl=300)  # 5 minute cache for rates
        self.rate_locks = SimpleCache(default_ttl=600)  # 10 minute rate locks

        # Configuration
        self.markup_percentage = getattr(Config, "EXCHANGE_MARKUP_PERCENTAGE", 5.0)
        self.supported_cryptos = [
            "BTC",
            "ETH",
            "USDT-TRC20",
            "USDT-ERC20",
            "LTC",
            "DOGE",
            "BCH",
            "TRX",
            "BNB",
        ]
        self.supported_fiats = ["NGN", "USD"]

        # Currency symbol mapping for APIs
        self.currency_map = {
            "BTC": "BTC",
            "ETH": "ETH",
            "LTC": "LTC",
            "DOGE": "DOGE",
            "BCH": "BCH",
            "BSC": "BNB",  # Binance Smart Chain uses BNB
            "BNB": "BNB",
            "TRX": "TRX",
            "USDT-ERC20": "USDT",
            "USDT-TRC20": "USDT",
            "USD": "USD",
            "NGN": "NGN",
        }

        # Service availability flags
        self.fincra_available = False
        self.blockbee_available = False

        # Initialize dependent services
        self._initialize_services()

    def _initialize_services(self):
        """Initialize dependent payment services with validation"""
        try:
            if api_validator.validate_service_availability(
                "Fincra", ["FINCRA_API_KEY"]
            ):
                from services.fincra_service import fincra_service

                self.fincra_service = fincra_service
                self.fincra_available = True
            else:
                self.fincra_service = None
                self.fincra_available = False
        except ImportError:
            logger.warning("Fincra service not available")
            self.fincra_service = None

        try:
            from services.blockbee_service import blockbee_service

            self.blockbee_service = blockbee_service
            self.blockbee_available = True
        except ImportError:
            logger.warning("BlockBee service not available")
            self.blockbee_service = None

    # ============ EXCHANGE RATE MANAGEMENT ============

    async def get_crypto_to_usd_rate(self, crypto_currency: str) -> Optional[Decimal]:
        """Get current USD rate for cryptocurrency with caching and fallbacks"""
        try:
            # Normalize currency symbol
            crypto_symbol = self.currency_map.get(
                crypto_currency.upper(), crypto_currency.upper()
            )

            # Check cache first
            cache_key = f"rate_{crypto_symbol}_USD"
            cached_rate = self.rate_cache.get(cache_key)
            if cached_rate:
                logger.debug(f"Using cached rate for {crypto_currency}: ${cached_rate}")
                return MonetaryDecimal.to_decimal(cached_rate, "cached_rate")

            # USD to USD is always 1.0
            if crypto_symbol == "USD":
                return Decimal("1.0")

            # Fetch from Tatum API (primary)
            rate = await self._fetch_tatum_crypto_rate(crypto_symbol)
            if rate:
                self.rate_cache.set(cache_key, str(rate))
                logger.info(f"Retrieved {crypto_currency} rate (Tatum): ${MonetaryDecimal.quantize_rate(rate)} USD")
                return rate

            # Fallback to FastForex
            rate = await self._fetch_fastforex_crypto_rate(crypto_symbol)
            if rate:
                self.rate_cache.set(cache_key, str(rate))
                logger.info(f"Retrieved {crypto_currency} rate (FastForex fallback): ${MonetaryDecimal.quantize_rate(rate)} USD")
                return rate

            # Final fallback attempt
            try:
                from utils.exchange_rate_fallback import exchange_rate_fallback_service

                fallback_result = (
                    await exchange_rate_fallback_service.get_crypto_to_usd_rate(
                        crypto_currency
                    )
                )
                if fallback_result and fallback_result.rate:
                    rate = MonetaryDecimal.to_decimal(
                        fallback_result.rate, "fallback_rate"
                    )
                    self.rate_cache.set(cache_key, str(rate))
                    logger.info(
                        f"Retrieved {crypto_currency} rate from fallback: ${MonetaryDecimal.quantize_rate(rate)} USD"
                    )
                    return rate
            except Exception as e:
                logger.warning(
                    f"Fallback rate service failed for {crypto_currency}: {e}"
                )

            raise ExchangeRateError(f"All rate sources failed for {crypto_currency}")

        except Exception as e:
            logger.error(f"Error getting {crypto_currency} to USD rate: {e}")
            return None

    async def get_usd_to_ngn_rate(self) -> Optional[Decimal]:
        """Get current USD to NGN exchange rate"""
        try:
            # Check cache first
            cache_key = "rate_USD_NGN"
            cached_rate = self.rate_cache.get(cache_key)
            if cached_rate:
                logger.debug(f"Using cached USD to NGN rate: {cached_rate}")
                return MonetaryDecimal.to_decimal(cached_rate, "cached_ngn_rate")

            # Fetch from FastForex
            rate = await self._fetch_fastforex_usd_to_ngn()
            if rate:
                self.rate_cache.set(cache_key, str(rate))
                logger.info(f"Retrieved USD to NGN rate: {MonetaryDecimal.quantize_rate(rate)}")
                return rate

            # Fallback attempt
            try:
                from utils.exchange_rate_fallback import exchange_rate_fallback_service

                fallback_result = (
                    await exchange_rate_fallback_service.get_usd_to_ngn_rate()
                )
                if fallback_result and fallback_result.rate:
                    rate = MonetaryDecimal.to_decimal(
                        fallback_result.rate, "fallback_ngn_rate"
                    )
                    self.rate_cache.set(cache_key, str(rate))
                    logger.info(f"Retrieved USD to NGN rate from fallback: {MonetaryDecimal.quantize_rate(rate)}")
                    return rate
            except Exception as e:
                logger.warning(f"Fallback NGN rate service failed: {e}")

            raise ExchangeRateError("All USD to NGN rate sources failed")

        except Exception as e:
            logger.error(f"Error getting USD to NGN rate: {e}")
            return None

    async def get_usd_to_ngn_rate_clean(self) -> Optional[Decimal]:
        """Get clean USD to NGN rate without markup (legacy compatibility)"""
        return await self.get_usd_to_ngn_rate()

    async def get_usd_to_ngn_rate_with_markup(self) -> Optional[Decimal]:
        """Get USD to NGN rate with configured markup (legacy compatibility)"""
        try:
            clean_rate = await self.get_usd_to_ngn_rate()
            if not clean_rate:
                return None

            # Apply markup
            markup_multiplier = Decimal("1") + (
                Decimal(str(self.markup_percentage)) / Decimal("100")
            )
            marked_up_rate = clean_rate * markup_multiplier

            return MonetaryDecimal.quantize_rate(marked_up_rate)

        except Exception as e:
            logger.error(f"Error applying markup to USD->NGN rate: {e}")
            return None

    async def _fetch_fastforex_crypto_rate(
        self, crypto_symbol: str
    ) -> Optional[Decimal]:
        """Fetch cryptocurrency rate from FastForex API"""
        try:
            if not self.fastforex_api_key:
                logger.debug("FastForex API key not configured")
                return None

            async with aiohttp.ClientSession() as session:
                url = f"{self.fastforex_base_url}/fetch-one"
                params = {
                    "from": crypto_symbol,
                    "to": "USD",
                    "api_key": self.fastforex_api_key,
                }

                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(url, params=params, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data and "USD" in data["result"]:
                            rate = MonetaryDecimal.to_decimal(
                                data["result"]["USD"], "fastforex_crypto_rate"
                            )
                            return MonetaryDecimal.quantize_rate(rate)
                    else:
                        logger.warning(
                            f"FastForex crypto rate API error: {response.status}"
                        )

        except asyncio.TimeoutError:
            logger.warning("FastForex crypto rate API timeout")
        except Exception as e:
            logger.warning(f"FastForex crypto rate API error: {e}")

        return None

    async def _fetch_fastforex_usd_to_ngn(self) -> Optional[Decimal]:
        """Fetch USD to NGN rate from FastForex API"""
        try:
            if not self.fastforex_api_key:
                logger.debug("FastForex API key not configured")
                return None

            async with aiohttp.ClientSession() as session:
                url = f"{self.fastforex_base_url}/fetch-one"
                params = {"from": "USD", "to": "NGN", "api_key": self.fastforex_api_key}

                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(url, params=params, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data and "NGN" in data["result"]:
                            rate = MonetaryDecimal.to_decimal(
                                data["result"]["NGN"], "fastforex_ngn_rate"
                            )
                            return MonetaryDecimal.quantize_rate(rate)
                    else:
                        logger.warning(
                            f"FastForex USD-NGN API error: {response.status}"
                        )

        except asyncio.TimeoutError:
            logger.warning("FastForex USD-NGN API timeout")
        except Exception as e:
            logger.warning(f"FastForex USD-NGN API error: {e}")

        return None

    async def _fetch_tatum_crypto_rate(self, crypto_symbol: str) -> Optional[Decimal]:
        """Fetch cryptocurrency rate from Tatum API (primary source)"""
        try:
            if not self.tatum_api_key:
                return None

            async with aiohttp.ClientSession() as session:
                params = {"symbol": crypto_symbol, "basePair": "USD"}
                headers = {"x-api-key": self.tatum_api_key}
                timeout = aiohttp.ClientTimeout(total=10)

                async with session.get(
                    self.tatum_api_url, params=params, headers=headers, timeout=timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "value" in data:
                            rate = MonetaryDecimal.to_decimal(
                                data["value"], "tatum_rate"
                            )
                            return MonetaryDecimal.quantize_rate(rate)
                    else:
                        logger.warning(f"Tatum crypto rate API error: {response.status}")

        except asyncio.TimeoutError:
            logger.warning("Tatum crypto rate API timeout")
        except Exception as e:
            logger.warning(f"Tatum crypto rate API error: {e}")

        return None

    async def _fetch_tatum_usd_to_ngn(self) -> Optional[Decimal]:
        """Fetch USD to NGN rate from Tatum API"""
        try:
            if not self.tatum_api_key:
                return None

            async with aiohttp.ClientSession() as session:
                params = {"symbol": "USD", "basePair": "NGN"}
                headers = {"x-api-key": self.tatum_api_key}
                timeout = aiohttp.ClientTimeout(total=10)

                async with session.get(
                    self.tatum_api_url, params=params, headers=headers, timeout=timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "value" in data:
                            rate = MonetaryDecimal.to_decimal(
                                data["value"], "tatum_ngn_rate"
                            )
                            return MonetaryDecimal.quantize_rate(rate)
                    else:
                        logger.warning(f"Tatum USD-NGN API error: {response.status}")

        except asyncio.TimeoutError:
            logger.warning("Tatum USD-NGN API timeout")
        except Exception as e:
            logger.warning(f"Tatum USD-NGN API error: {e}")

        return None

    # ============ CURRENCY CONVERSION ============

    async def convert_crypto_to_fiat(
        self,
        crypto_currency: str,
        crypto_amount: Decimal,
        target_currency: str = "USD",
        apply_markup: bool = True,
    ) -> Optional[ConversionResult]:
        """Convert cryptocurrency to fiat currency with optional markup"""
        try:
            crypto_amount_decimal = MonetaryDecimal.to_decimal(
                crypto_amount, "crypto_conversion_input"
            )

            if target_currency.upper() == "USD":
                # Direct crypto to USD conversion
                crypto_rate = await self.get_crypto_to_usd_rate(crypto_currency)
                if not crypto_rate:
                    return None

                base_usd_amount = MonetaryDecimal.multiply_precise(
                    crypto_amount_decimal, crypto_rate
                )

                if apply_markup:
                    markup_decimal = Decimal(str(self.markup_percentage)) / Decimal(
                        "100"
                    )
                    markup_amount = base_usd_amount * markup_decimal
                    final_amount = base_usd_amount - markup_amount  # User gets less USD
                    effective_rate = MonetaryDecimal.divide_precise(
                        final_amount, crypto_amount_decimal
                    )
                else:
                    markup_amount = Decimal("0")
                    final_amount = base_usd_amount
                    effective_rate = crypto_rate

                return ConversionResult(
                    source_amount=MonetaryDecimal.quantize_crypto(
                        crypto_amount_decimal
                    ),
                    source_currency=crypto_currency.upper(),
                    target_amount=MonetaryDecimal.quantize_usd(final_amount),
                    target_currency="USD",
                    exchange_rate=MonetaryDecimal.quantize_rate(crypto_rate),
                    markup_percentage=Decimal(str(self.markup_percentage)),
                    markup_amount=MonetaryDecimal.quantize_usd(markup_amount),
                    effective_rate=MonetaryDecimal.quantize_rate(effective_rate),
                    timestamp=datetime.utcnow(),
                )

            elif target_currency.upper() == "NGN":
                # Crypto to USD to NGN conversion
                crypto_rate = await self.get_crypto_to_usd_rate(crypto_currency)
                ngn_rate = await self.get_usd_to_ngn_rate()

                if not crypto_rate or not ngn_rate:
                    return None

                # Convert crypto to USD first
                usd_amount = MonetaryDecimal.multiply_precise(
                    crypto_amount_decimal, crypto_rate
                )

                # Convert USD to NGN
                base_ngn_amount = MonetaryDecimal.multiply_precise(usd_amount, ngn_rate)

                if apply_markup:
                    markup_decimal = Decimal(str(self.markup_percentage)) / Decimal(
                        "100"
                    )
                    markup_amount = base_ngn_amount * markup_decimal
                    final_amount = base_ngn_amount - markup_amount  # User gets less NGN
                    combined_rate = MonetaryDecimal.multiply_precise(
                        crypto_rate, ngn_rate
                    )
                    effective_rate = MonetaryDecimal.divide_precise(
                        final_amount, crypto_amount_decimal
                    )
                else:
                    markup_amount = Decimal("0")
                    final_amount = base_ngn_amount
                    combined_rate = MonetaryDecimal.multiply_precise(
                        crypto_rate, ngn_rate
                    )
                    effective_rate = combined_rate

                return ConversionResult(
                    source_amount=MonetaryDecimal.quantize_crypto(
                        crypto_amount_decimal
                    ),
                    source_currency=crypto_currency.upper(),
                    target_amount=MonetaryDecimal.quantize_ngn(final_amount),
                    target_currency="NGN",
                    exchange_rate=MonetaryDecimal.quantize_rate(combined_rate),
                    markup_percentage=Decimal(str(self.markup_percentage)),
                    markup_amount=MonetaryDecimal.quantize_ngn(markup_amount),
                    effective_rate=MonetaryDecimal.quantize_rate(effective_rate),
                    timestamp=datetime.utcnow(),
                )

            else:
                raise ExchangeRateError(
                    f"Unsupported target currency: {target_currency}"
                )

        except Exception as e:
            logger.error(
                f"Error converting {crypto_currency} to {target_currency}: {e}"
            )
            return None

    async def convert_fiat_to_crypto(
        self,
        fiat_currency: str,
        fiat_amount: Decimal,
        target_crypto: str,
        apply_markup: bool = True,
    ) -> Optional[ConversionResult]:
        """Convert fiat currency to cryptocurrency with optional markup"""
        try:
            fiat_amount_decimal = MonetaryDecimal.to_decimal(
                fiat_amount, "fiat_conversion_input"
            )

            if fiat_currency.upper() == "USD":
                # Direct USD to crypto conversion
                crypto_rate = await self.get_crypto_to_usd_rate(target_crypto)
                if not crypto_rate:
                    return None

                if apply_markup:
                    markup_decimal = Decimal(str(self.markup_percentage)) / Decimal(
                        "100"
                    )
                    effective_usd = fiat_amount_decimal / (
                        Decimal("1") + markup_decimal
                    )
                    markup_amount = fiat_amount_decimal - effective_usd
                    crypto_amount = MonetaryDecimal.divide_precise(
                        effective_usd, crypto_rate
                    )
                    effective_rate = MonetaryDecimal.divide_precise(
                        crypto_amount, fiat_amount_decimal
                    )
                else:
                    markup_amount = Decimal("0")
                    effective_usd = fiat_amount_decimal
                    crypto_amount = MonetaryDecimal.divide_precise(
                        fiat_amount_decimal, crypto_rate
                    )
                    effective_rate = MonetaryDecimal.divide_precise(
                        Decimal("1"), crypto_rate
                    )

                return ConversionResult(
                    source_amount=MonetaryDecimal.quantize_usd(fiat_amount_decimal),
                    source_currency="USD",
                    target_amount=MonetaryDecimal.quantize_crypto(crypto_amount),
                    target_currency=target_crypto.upper(),
                    exchange_rate=MonetaryDecimal.quantize_rate(
                        MonetaryDecimal.divide_precise(Decimal("1"), crypto_rate)
                    ),
                    markup_percentage=Decimal(str(self.markup_percentage)),
                    markup_amount=MonetaryDecimal.quantize_usd(markup_amount),
                    effective_rate=MonetaryDecimal.quantize_rate(effective_rate),
                    timestamp=datetime.utcnow(),
                )

            elif fiat_currency.upper() == "NGN":
                # NGN to USD to crypto conversion
                ngn_rate = await self.get_usd_to_ngn_rate()
                crypto_rate = await self.get_crypto_to_usd_rate(target_crypto)

                if not ngn_rate or not crypto_rate:
                    return None

                # Convert NGN to USD first
                base_usd_amount = MonetaryDecimal.divide_precise(
                    fiat_amount_decimal, ngn_rate
                )

                if apply_markup:
                    markup_decimal = Decimal(str(self.markup_percentage)) / Decimal(
                        "100"
                    )
                    effective_usd = base_usd_amount / (Decimal("1") + markup_decimal)
                    markup_amount_usd = base_usd_amount - effective_usd
                    markup_amount_ngn = MonetaryDecimal.multiply_precise(
                        markup_amount_usd, ngn_rate
                    )
                    crypto_amount = MonetaryDecimal.divide_precise(
                        effective_usd, crypto_rate
                    )
                    combined_rate = MonetaryDecimal.divide_precise(
                        Decimal("1"),
                        MonetaryDecimal.multiply_precise(crypto_rate, ngn_rate),
                    )
                    effective_rate = MonetaryDecimal.divide_precise(
                        crypto_amount, fiat_amount_decimal
                    )
                else:
                    markup_amount_ngn = Decimal("0")
                    crypto_amount = MonetaryDecimal.divide_precise(
                        base_usd_amount, crypto_rate
                    )
                    combined_rate = MonetaryDecimal.divide_precise(
                        Decimal("1"),
                        MonetaryDecimal.multiply_precise(crypto_rate, ngn_rate),
                    )
                    effective_rate = combined_rate

                return ConversionResult(
                    source_amount=MonetaryDecimal.quantize_ngn(fiat_amount_decimal),
                    source_currency="NGN",
                    target_amount=MonetaryDecimal.quantize_crypto(crypto_amount),
                    target_currency=target_crypto.upper(),
                    exchange_rate=MonetaryDecimal.quantize_rate(combined_rate),
                    markup_percentage=Decimal(str(self.markup_percentage)),
                    markup_amount=MonetaryDecimal.quantize_ngn(markup_amount_ngn),
                    effective_rate=MonetaryDecimal.quantize_rate(effective_rate),
                    timestamp=datetime.utcnow(),
                )

            else:
                raise ExchangeRateError(f"Unsupported fiat currency: {fiat_currency}")

        except Exception as e:
            logger.error(f"Error converting {fiat_currency} to {target_crypto}: {e}")
            return None

    # ============ RATE LOCKING ============

    async def create_rate_lock(
        self,
        conversion_result: ConversionResult,
        user_id: int,
        lock_duration_minutes: int = 10,
    ) -> Optional[str]:
        """Create a rate lock for a conversion"""
        try:
            import uuid

            lock_id = str(uuid.uuid4())

            lock_data = {
                "lock_id": lock_id,
                "user_id": user_id,
                "conversion_result": conversion_result,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow()
                + timedelta(minutes=lock_duration_minutes),
            }

            # Store in cache with TTL
            self.rate_locks.set(lock_id, lock_data, ttl=lock_duration_minutes * 60)

            logger.info(f"Created rate lock {lock_id} for user {user_id}")
            return lock_id

        except Exception as e:
            logger.error(f"Error creating rate lock: {e}")
            return None

    def get_rate_lock(self, lock_id: str) -> Optional[Dict]:
        """Get rate lock data"""
        return self.rate_locks.get(lock_id)

    def release_rate_lock(self, lock_id: str) -> bool:
        """Release a rate lock"""
        try:
            if self.rate_locks.exists(lock_id):
                self.rate_locks.delete(lock_id)
                logger.info(f"Released rate lock {lock_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error releasing rate lock {lock_id}: {e}")
            return False

    # ============ PAYMENT PROCESSING INTEGRATION ============

    async def process_fincra_payment(
        self,
        amount_ngn: Decimal,
        bank_code: str,
        account_number: str,
        account_name: str,
        reference: str,
    ) -> Optional[Dict]:
        """Process Fincra NGN payment with integrated error handling"""
        try:
            if not self.fincra_available:
                raise PaymentProcessingError("Fincra service not available")

            if self.fincra_service:
                return await self.fincra_service.process_bank_transfer(
                    amount_ngn=amount_ngn,
                    bank_code=bank_code,
                    account_number=account_number,
                    account_name=account_name,
                    reference=reference,
                )
            else:
                raise PaymentProcessingError("Fincra service not initialized")

        except Exception as e:
            logger.error(f"Error processing Fincra payment: {e}")
            raise PaymentProcessingError(f"Fincra payment failed: {str(e)}")

    async def get_fincra_balance(self) -> Optional[Dict]:
        """Get Fincra account balance"""
        try:
            if not self.fincra_available:
                return None

            if self.fincra_service:
                return await self.fincra_service.get_cached_account_balance()
            else:
                logger.warning("Fincra service not initialized")
                return None

        except Exception as e:
            logger.error(f"Error getting Fincra balance: {e}")
            return None

    # ============ CONVENIENCE METHODS ============

    def is_supported_crypto(self, currency: str) -> bool:
        """Check if cryptocurrency is supported"""
        return currency.upper() in [c.upper() for c in self.supported_cryptos]

    def is_supported_fiat(self, currency: str) -> bool:
        """Check if fiat currency is supported"""
        return currency.upper() in [f.upper() for f in self.supported_fiats]

    def get_supported_currencies(self) -> Dict[str, List[str]]:
        """Get all supported currencies"""
        return {
            "cryptocurrencies": self.supported_cryptos,
            "fiat_currencies": self.supported_fiats,
        }

    async def get_system_status(self) -> Dict[str, Any]:
        """Get financial system status"""
        try:
            status = {
                "timestamp": datetime.utcnow().isoformat(),
                "api_services": {},
                "supported_currencies": self.get_supported_currencies(),
                "markup_percentage": self.markup_percentage,
            }

            # Test FastForex API
            try:
                btc_rate = await self.get_crypto_to_usd_rate("BTC")
                status["api_services"]["fastforex"] = {
                    "status": "available" if btc_rate else "degraded",
                    "test_rate_btc_usd": str(MonetaryDecimal.quantize_rate(btc_rate)) if btc_rate else None,
                }
            except Exception as e:
                status["api_services"]["fastforex"] = {
                    "status": "error",
                    "error": str(e),
                }

            # Test USD to NGN
            try:
                ngn_rate = await self.get_usd_to_ngn_rate()
                status["api_services"]["usd_to_ngn"] = {
                    "status": "available" if ngn_rate else "degraded",
                    "rate": str(MonetaryDecimal.quantize_rate(ngn_rate)) if ngn_rate else None,
                }
            except Exception as e:
                status["api_services"]["usd_to_ngn"] = {
                    "status": "error",
                    "error": str(e),
                }

            # Payment services status
            status["payment_services"] = {
                "fincra": "available" if self.fincra_available else "unavailable",
                "blockbee": "available" if self.blockbee_available else "unavailable",
            }

            return status

        except Exception as e:
            logger.error(f"Error getting financial system status: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e),
            }


# ============ GLOBAL INSTANCE AND COMPATIBILITY ALIASES ============

# Global unified financial gateway instance
financial_gateway = UnifiedFinancialGateway()

# Legacy compatibility aliases for existing code
exchange_service = financial_gateway  # For exchange_service compatibility
forex_service = financial_gateway  # For forex_service compatibility
fastforex_service = financial_gateway  # For fastforex_service compatibility

# Decimal precision utilities export
MonetaryDecimal = MonetaryDecimal  # For decimal_precision compatibility

# ============ BACKWARDS COMPATIBILITY WRAPPERS ============


class LegacyExchangeService:
    """Backwards compatibility wrapper for ExchangeService"""

    def __init__(self):
        self.financial_gateway = financial_gateway

    @property
    def markup_percentage(self):
        return self.financial_gateway.markup_percentage

    async def get_crypto_to_ngn_rate_with_lock(
        self,
        user_id: int,
        crypto_currency: str,
        amount: float,
        lock_duration_minutes: int = 30,
    ):
        """Legacy method for crypto to NGN conversion with rate lock"""
        try:
            conversion = await self.financial_gateway.convert_crypto_to_fiat(
                crypto_currency=crypto_currency,
                crypto_amount=Decimal(str(amount)),
                target_currency="NGN",
                apply_markup=True,
            )

            if not conversion:
                return None

            # Create rate lock
            lock_id = await self.financial_gateway.create_rate_lock(
                conversion, user_id, lock_duration_minutes
            )

            return {
                "order_id": lock_id,
                "crypto_currency": crypto_currency,
                "crypto_amount": amount,
                "final_ngn_amount": str(MonetaryDecimal.quantize_ngn(conversion.target_amount)),
                "exchange_markup_percentage": str(conversion.markup_percentage),
                "exchange_markup": str(MonetaryDecimal.quantize_ngn(conversion.markup_amount)),
                "effective_rate": str(MonetaryDecimal.quantize_rate(conversion.effective_rate)),
                "rate_locked": True,
                "lock_duration_minutes": lock_duration_minutes,
            }
        except Exception as e:
            logger.error(f"Legacy crypto to NGN conversion failed: {e}")
            return None


class LegacyForexService:
    """Backwards compatibility wrapper for ForexService"""

    def __init__(self):
        self.financial_gateway = financial_gateway

    async def get_current_rate(self, crypto_currency: str):
        """Legacy method for getting current crypto rate"""
        return await self.financial_gateway.get_crypto_to_usd_rate(crypto_currency)

    async def get_exchange_rate(self, base_currency: str, target_currency: str):
        """Legacy method for getting exchange rates"""
        if base_currency == "USD" and target_currency == "NGN":
            rate = await self.financial_gateway.get_usd_to_ngn_rate()
            return str(MonetaryDecimal.quantize_rate(rate)) if rate else None
        return None


# Create legacy compatibility instances
exchange_service_legacy = LegacyExchangeService()
forex_service_legacy = LegacyForexService()

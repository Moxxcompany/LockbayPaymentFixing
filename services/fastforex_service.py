"""
FastForex API service for real-time cryptocurrency and forex rates
"""

import aiohttp
import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, Optional
from config import Config
from utils.data_sanitizer import sanitize_for_log, safe_error_log
from utils.production_cache import get_cached, set_cached, delete_cached
from services.api_adapter_retry import APIAdapterRetry
from services.external_api_optimizer import get_api_optimizer, optimized_http_session
from models import CashoutErrorCode

logger = logging.getLogger(__name__)

# CoinGecko symbol mapping (free API, no key required)
COINGECKO_SYMBOL_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "LTC": "litecoin",
    "DOGE": "dogecoin",
    "BCH": "bitcoin-cash",
    "BNB": "binancecoin",
    "TRX": "tron",
    "USDT": "tether",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOT": "polkadot",
    "XLM": "stellar",
    "XMR": "monero",
    "ZEC": "zcash",
    "LINK": "chainlink",
    "XTZ": "tezos",
    "REP": "augur",
}
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
# CoinGecko demo API key (free, higher rate limits than anonymous)
COINGECKO_API_KEY = os.environ.get("COINGECKO_API_KEY", "")


class FastForexAPIError(Exception):
    """Custom exception for FastForex API errors"""

    pass


class FastForexService(APIAdapterRetry):
    """Service for fetching real-time exchange rates from FastForex API with unified retry system"""

    def __init__(self):
        # Initialize parent APIAdapterRetry
        super().__init__(service_name="fastforex", timeout=30)
        
        self.api_key = Config.FASTFOREX_API_KEY
        self.base_url = "https://api.fastforex.io"
        
        # Enhanced cache configuration for performance optimization
        self.cache_ttl = 3600  # 1 hour cache for exchange rates (increased from 30m)
        self.fallback_cache_ttl = 7200  # 2 hours for fallback rates (increased from 1h)
        self.rapid_cache_ttl = 600  # 10 minutes rapid cache (increased from 5m)
        self.session_cache_ttl = 300  # 5 minutes ultra-fast cache (increased from 1m)
        self.webhook_cache_ttl = 1800  # 30 minutes cache for webhook scenarios (increased from 15m)
        
        if not self.api_key:
            logger.warning(
                "FASTFOREX_API_KEY not configured - rates will not be available"
            )
    
    def _map_provider_error_to_unified(self, exception: Exception, context: Optional[Dict] = None) -> CashoutErrorCode:
        """
        Map FastForex-specific errors to unified error codes for intelligent retry
        """
        error_message = str(exception).lower()
        
        # FastForex-specific error patterns
        if "fastforex timeout" in error_message or "fastforex error" in error_message:
            return CashoutErrorCode.API_TIMEOUT
        elif "invalid api key" in error_message or "authentication failed" in error_message:
            return CashoutErrorCode.API_AUTHENTICATION_FAILED
        elif "currency not supported" in error_message or "invalid currency" in error_message:
            return CashoutErrorCode.API_INVALID_REQUEST
        elif "rate limit" in error_message or "quota exceeded" in error_message:
            return CashoutErrorCode.RATE_LIMIT_EXCEEDED
        elif "service unavailable" in error_message or "502" in error_message or "503" in error_message:
            return CashoutErrorCode.SERVICE_UNAVAILABLE
        elif "network error" in error_message or "connection error" in error_message:
            return CashoutErrorCode.NETWORK_ERROR
        
        # Default to generic classification for unknown FastForex errors
        return CashoutErrorCode.UNKNOWN_ERROR
    
    def _get_circuit_breaker_name(self) -> str:
        """Return the circuit breaker name for FastForex API"""
        return "fastforex"
    
    async def _get_crypto_rate_direct(self, crypto_symbol: str, session: aiohttp.ClientSession) -> Decimal:
        """
        CROSS-LOOP FIX: Direct crypto rate fetch with provided session
        Bypasses shared optimizer session to avoid cross-loop resource issues
        """
        # Map crypto symbols to FastForex format
        symbol_map = {
            "BTC": "BTC", "ETH": "ETH", "LTC": "LTC", "DOGE": "DOGE", "BCH": "BCH",
            "BSC": "BNB", "TRX": "TRX", "USDT-ERC20": "USDT", "USDT-TRC20": "USDT", "USD": "USD",
            "XETH": "ETH", "XXBT": "BTC", "XLTC": "LTC", "XXDG": "DOGE", "XBCH": "BCH",
            "XTRX": "TRX", "XXRP": "XRP", "XADA": "ADA", "XDOT": "DOT", "XXLM": "XLM",
            "XXMR": "XMR", "XZEC": "ZEC", "XREP": "REP", "XXTZ": "XTZ", "XLINK": "LINK",
            "XUSDT": "USDT", "ZUSD": "USD", "ZEUR": "EUR"
        }
        
        mapped_symbol = symbol_map.get(crypto_symbol, crypto_symbol)
        if mapped_symbol == "USD":
            return Decimal("1.0")
            
        url = f"{self.base_url}/fetch-one"
        params = {"from": mapped_symbol, "to": "USD", "api_key": self.api_key}
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if "result" in data and "USD" in data["result"]:
                    return Decimal(str(data["result"]["USD"]))
                else:
                    raise FastForexAPIError("Invalid response format")
            else:
                error_text = await response.text()
                raise FastForexAPIError(f"FastForex API error: {response.status} - {error_text}")
    
    async def _get_ngn_rate_direct(self, session: aiohttp.ClientSession) -> Decimal:
        """
        CROSS-LOOP FIX: Direct NGN rate fetch with provided session  
        Bypasses shared optimizer session to avoid cross-loop resource issues
        """
        url = f"{self.base_url}/fetch-one"
        params = {"from": "USD", "to": "NGN", "api_key": self.api_key}
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if "result" in data and "NGN" in data["result"]:
                    fastforex_rate = Decimal(str(data["result"]["NGN"]))
                    # Apply platform markup
                    markup_percentage = Decimal(str(Config.EXCHANGE_MARKUP_PERCENTAGE))
                    return fastforex_rate * (Decimal("1") - markup_percentage / Decimal("100"))
                else:
                    raise FastForexAPIError("Invalid response format")
            else:
                error_text = await response.text()
                raise FastForexAPIError(f"FastForex API error: {response.status} - {error_text}")

    def get_crypto_rate(self, crypto_symbol: str) -> Decimal:
        """
        DEADLOCK FIX: Safe async handling using dedicated executor thread
        Synchronous wrapper for get_crypto_to_usd_rate - for backwards compatibility.
        """
        try:
            # DEADLOCK FIX: Use ThreadPoolExecutor with asyncio.run in separate thread
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Safe approach: Run async code in a dedicated thread with its own event loop
                import concurrent.futures
                
                def run_in_thread():
                    # FULL ASYNC WORKFLOW: Create a new event loop and run the complete async method
                    # This preserves all caching, retry logic, and fallback mechanisms
                    return asyncio.run(self.get_crypto_to_usd_rate(crypto_symbol))
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=30)
            else:
                return asyncio.run(self.get_crypto_to_usd_rate(crypto_symbol))
        except Exception as e:
            logger.error(f"❌ CRYPTO_RATE_ERROR: {crypto_symbol} - {e}")
            raise e

    def get_ngn_to_usd_rate(self) -> Decimal:
        """
        DEADLOCK FIX: Safe async handling using dedicated executor thread
        Synchronous wrapper for NGN to USD rate conversion.
        """
        try:
            # DEADLOCK FIX: Use ThreadPoolExecutor with asyncio.run in separate thread
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Safe approach: Run async code in a dedicated thread with its own event loop
                import concurrent.futures
                
                def run_in_thread():
                    # FULL ASYNC WORKFLOW: Create a new event loop and run the complete async method  
                    # This preserves all caching, retry logic, and fallback mechanisms
                    return asyncio.run(self.get_ngn_to_usd_rate_with_markup())
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    result = future.result(timeout=30)
                    return result if result is not None else Decimal("0")
            else:
                result = asyncio.run(self.get_ngn_to_usd_rate_with_markup())
                return result if result is not None else Decimal("0")
        except Exception as e:
            logger.error(f"❌ NGN_RATE_ERROR: Failed to get NGN to USD rate - {e}")
            raise e

    async def _fetch_coingecko_crypto_rate(self, mapped_symbol: str) -> Optional[Decimal]:
        """
        Fetch crypto→USD rate from CoinGecko (FREE, no API key required).
        Primary source for crypto rates to reduce FastForex API usage/costs.
        """
        coin_id = COINGECKO_SYMBOL_MAP.get(mapped_symbol)
        if not coin_id:
            logger.debug(f"CoinGecko: No mapping for {mapped_symbol}, skipping")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {"ids": coin_id, "vs_currencies": "usd"}
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(COINGECKO_API_URL, params=params, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        if coin_id in data and "usd" in data[coin_id]:
                            rate = Decimal(str(data[coin_id]["usd"]))
                            logger.info(f"🦎 CoinGecko {mapped_symbol}: ${float(rate):.4f} USD")
                            return rate
                    elif response.status == 429:
                        logger.warning("🦎 CoinGecko rate-limited, falling back to FastForex")
                    else:
                        logger.warning(f"🦎 CoinGecko API error: {response.status}")
        except asyncio.TimeoutError:
            logger.warning("🦎 CoinGecko API timeout, falling back to FastForex")
        except Exception as e:
            logger.warning(f"🦎 CoinGecko API error: {e}")
        
        return None

    async def _fetch_coingecko_batch_rates(self, symbols: list) -> Dict[str, Decimal]:
        """
        Batch-fetch multiple crypto→USD rates from CoinGecko in a single API call.
        Much more efficient than individual calls and avoids rate-limiting.
        """
        # Map standard symbols to CoinGecko IDs
        coin_ids = {}
        for sym in symbols:
            coin_id = COINGECKO_SYMBOL_MAP.get(sym)
            if coin_id:
                coin_ids[sym] = coin_id
        
        if not coin_ids:
            return {}
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "ids": ",".join(coin_ids.values()),
                    "vs_currencies": "usd"
                }
                timeout = aiohttp.ClientTimeout(total=15)
                async with session.get(COINGECKO_API_URL, params=params, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = {}
                        for sym, coin_id in coin_ids.items():
                            if coin_id in data and "usd" in data[coin_id]:
                                rates[sym] = Decimal(str(data[coin_id]["usd"]))
                        if rates:
                            logger.info(f"🦎 CoinGecko batch: {len(rates)} rates fetched ({', '.join(rates.keys())})")
                        return rates
                    elif response.status == 429:
                        logger.warning("🦎 CoinGecko batch rate-limited")
                    else:
                        logger.warning(f"🦎 CoinGecko batch API error: {response.status}")
        except asyncio.TimeoutError:
            logger.warning("🦎 CoinGecko batch API timeout")
        except Exception as e:
            logger.warning(f"🦎 CoinGecko batch API error: {e}")
        
        return {}

    async def get_crypto_to_usd_rate(self, crypto_symbol: str) -> Decimal:
        """Get cryptocurrency to USD exchange rate with intelligent caching.
        
        Source priority: Cache → CoinGecko (free) → FastForex (paid) → Error
        """
        try:
            # Map crypto symbols to standard format FIRST (before cache check)
            # This ensures both "LTC" and "XLTC" use the same cache entry
            symbol_map = {
                # Standard symbols
                "BTC": "BTC",
                "ETH": "ETH",
                "LTC": "LTC",
                "DOGE": "DOGE",
                "BCH": "BCH",
                "BSC": "BNB",  # Binance Smart Chain uses BNB
                "TRX": "TRX",
                "USDT-ERC20": "USDT",
                "USDT-TRC20": "USDT",
                "USD": "USD",
                
                # Kraken symbol mappings (X-prefixed to standard)
                "XETH": "ETH",     # Ethereum
                "XXBT": "BTC",     # Bitcoin  
                "XLTC": "LTC",     # Litecoin
                "XXDG": "DOGE",    # Dogecoin
                "XBCH": "BCH",     # Bitcoin Cash
                "XTRX": "TRX",     # Tron
                "XXRP": "XRP",     # Ripple
                "XADA": "ADA",     # Cardano
                "XDOT": "DOT",     # Polkadot
                "XXLM": "XLM",     # Stellar
                "XXMR": "XMR",     # Monero
                "XZEC": "ZEC",     # Zcash
                "XREP": "REP",     # Augur
                "XXTZ": "XTZ",     # Tezos
                "XLINK": "LINK",   # Chainlink
                "XUSDT": "USDT",   # Tether
                
                # Additional exchange-specific mappings
                "ZUSD": "USD",     # Kraken's USD representation
                "ZEUR": "EUR",     # Kraken's EUR representation
            }

            mapped_symbol = symbol_map.get(crypto_symbol, crypto_symbol)
            
            # CACHE FIX: Use mapped symbol for cache key so both LTC and XLTC find the same cached rate
            cache_key = f"crypto_rate_{mapped_symbol}_USD"
            cached_rate = get_cached(cache_key)
            if cached_rate is not None:
                return Decimal(str(cached_rate))
            
            # Check rapid cache for high-frequency requests
            rapid_cache_key = f"rapid_crypto_rate_{mapped_symbol}_USD"
            rapid_cached_rate = get_cached(rapid_cache_key)
            if rapid_cached_rate is not None:
                return Decimal(str(rapid_cached_rate))

            # USD to USD is always 1.0
            if mapped_symbol == "USD":
                return Decimal("1.0")

            # USDT to USD is always ~1.0
            if mapped_symbol == "USDT":
                rate = Decimal("1.0")
                set_cached(cache_key, rate, ttl=self.cache_ttl)
                return rate

            # === SOURCE 1: CoinGecko (FREE, no API key) ===
            coingecko_rate = await self._fetch_coingecko_crypto_rate(mapped_symbol)
            if coingecko_rate is not None:
                set_cached(cache_key, coingecko_rate, ttl=self.cache_ttl)
                set_cached(rapid_cache_key, coingecko_rate, ttl=self.rapid_cache_ttl)
                # Also populate fallback cache for webhook paths
                set_cached(f"fallback_crypto_rate_{mapped_symbol}_USD", coingecko_rate, ttl=self.fallback_cache_ttl)
                return coingecko_rate

            # === SOURCE 2: FastForex (paid fallback) ===
            if not self.api_key:
                logger.warning(f"CoinGecko failed and no FastForex API key for {crypto_symbol}")
                raise FastForexAPIError(f"All rate sources failed for {crypto_symbol}")

            async with optimized_http_session() as session:
                url = f"{self.base_url}/fetch-one"
                params = {"from": mapped_symbol, "to": "USD", "api_key": self.api_key}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        if "result" in data and "USD" in data["result"]:
                            rate = Decimal(str(data["result"]["USD"]))
                            
                            # Cache the fresh rate for performance (dual caching strategy)
                            set_cached(cache_key, rate, ttl=self.cache_ttl)
                            set_cached(rapid_cache_key, rate, ttl=self.rapid_cache_ttl)
                            set_cached(f"fallback_crypto_rate_{mapped_symbol}_USD", rate, ttl=self.fallback_cache_ttl)
                            
                            logger.info(
                                f"🔄 FastForex fallback {crypto_symbol}: ${float(rate):.4f} USD"
                            )
                            return rate
                        else:
                            safe_data = sanitize_for_log(data)
                            logger.error(
                                f"Invalid response format from FastForex for {crypto_symbol}: {safe_data}"
                            )
                            raise FastForexAPIError("Invalid response format")
                    else:
                        error_text = await response.text()
                        safe_error = sanitize_for_log(error_text)
                        logger.error(
                            f"FastForex API error for {crypto_symbol}: {response.status} - {safe_error}"
                        )
                        raise FastForexAPIError(
                            f"All rate sources failed for {crypto_symbol}"
                        )

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {crypto_symbol} rate: {e}")

            # Fail fast - no fallback logic per user request
            raise FastForexAPIError(f"Network error for {crypto_symbol}: {e}")
        except Exception as e:
            # SECURITY FIX: Sanitize error details
            safe_error = safe_error_log(e)
            logger.error(
                f"Unexpected error fetching {crypto_symbol} rate: {safe_error}"
            )
            raise FastForexAPIError("Unexpected error occurred")

    async def _fetch_fastforex_single_rate(self, mapped_symbol: str) -> Optional[Decimal]:
        """Fetch a single crypto rate from FastForex API (paid, used as fallback)."""
        if not self.api_key:
            return None
        try:
            async with optimized_http_session() as session:
                url = f"{self.base_url}/fetch-one"
                params = {"from": mapped_symbol, "to": "USD", "api_key": self.api_key}
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data and "USD" in data["result"]:
                            rate = Decimal(str(data["result"]["USD"]))
                            logger.info(f"🔄 FastForex fallback {mapped_symbol}: ${float(rate):.4f} USD")
                            return rate
        except Exception as e:
            logger.warning(f"FastForex single rate error for {mapped_symbol}: {e}")
        return None

    async def get_multiple_rates(self, symbols: list) -> Dict[str, Decimal]:
        """Get multiple real-time cryptocurrency rates efficiently.
        Uses single batch CoinGecko call, then FastForex for any misses."""
        try:
            logger.info(f"Fetching optimized rates for: {symbols}")
            
            # Map all symbols to standard format
            symbol_map = {
                "BTC": "BTC", "ETH": "ETH", "LTC": "LTC", "DOGE": "DOGE",
                "BCH": "BCH", "BSC": "BNB", "TRX": "TRX",
                "USDT-ERC20": "USDT", "USDT-TRC20": "USDT", "USD": "USD",
                "XETH": "ETH", "XXBT": "BTC", "XLTC": "LTC", "XXDG": "DOGE",
                "XBCH": "BCH", "XTRX": "TRX", "XXRP": "XRP", "XADA": "ADA",
                "XDOT": "DOT", "XXLM": "XLM", "XXMR": "XMR", "XZEC": "ZEC",
                "XREP": "REP", "XXTZ": "XTZ", "XLINK": "LINK", "XUSDT": "USDT",
                "ZUSD": "USD", "ZEUR": "EUR",
            }
            
            rates = {}
            uncached_symbols = []
            
            # Step 1: Collect cached rates, identify uncached symbols
            for sym in symbols:
                mapped = symbol_map.get(sym, sym)
                if mapped == "USD":
                    rates[sym] = Decimal("1.0")
                    continue
                if mapped == "USDT":
                    rates[sym] = Decimal("1.0")
                    continue
                    
                cache_key = f"crypto_rate_{mapped}_USD"
                cached = get_cached(cache_key)
                if cached is not None:
                    rates[sym] = Decimal(str(cached))
                else:
                    uncached_symbols.append((sym, mapped))
            
            if not uncached_symbols:
                return rates
            
            # Step 2: Batch fetch from CoinGecko (single API call)
            unique_mapped = list(set(m for _, m in uncached_symbols))
            gecko_rates = await self._fetch_coingecko_batch_rates(unique_mapped)
            
            # Cache CoinGecko results and populate rates dict
            remaining = []
            for orig_sym, mapped in uncached_symbols:
                if mapped in gecko_rates:
                    rate = gecko_rates[mapped]
                    cache_key = f"crypto_rate_{mapped}_USD"
                    set_cached(cache_key, rate, ttl=self.cache_ttl)
                    set_cached(f"rapid_crypto_rate_{mapped}_USD", rate, ttl=self.rapid_cache_ttl)
                    set_cached(f"fallback_crypto_rate_{mapped}_USD", rate, ttl=self.fallback_cache_ttl)
                    rates[orig_sym] = rate
                else:
                    remaining.append((orig_sym, mapped))
            
            # Step 3: FastForex fallback for any CoinGecko misses
            if remaining and self.api_key:
                tasks = []
                for orig_sym, mapped in remaining:
                    task = asyncio.create_task(self._fetch_fastforex_single_rate(mapped))
                    tasks.append((orig_sym, mapped, task))
                
                for orig_sym, mapped, task in tasks:
                    try:
                        rate = await task
                        if rate:
                            cache_key = f"crypto_rate_{mapped}_USD"
                            set_cached(cache_key, rate, ttl=self.cache_ttl)
                            set_cached(f"rapid_crypto_rate_{mapped}_USD", rate, ttl=self.rapid_cache_ttl)
                            set_cached(f"fallback_crypto_rate_{mapped}_USD", rate, ttl=self.fallback_cache_ttl)
                            rates[orig_sym] = rate
                    except Exception as e:
                        logger.error(f"Failed to get rate for {orig_sym}: {e}")
            
            return rates

            # Wait for all tasks to complete
            rates = {}
            for symbol, task in tasks:
                try:
                    rate = await task
                    rates[symbol] = rate
                except Exception as e:
                    logger.error(f"Failed to get REAL-TIME rate for {symbol}: {e}")
                    # Don't include failed rates in result

            return rates

        except Exception as e:
            logger.error(f"Error fetching multiple rates: {e}")
            raise FastForexAPIError(f"Multiple rates error: {e}")

    async def convert_crypto_to_usd(self, amount: Decimal, crypto_symbol: str) -> Decimal:
        """Convert cryptocurrency amount to USD"""
        try:
            rate = await self.get_crypto_to_usd_rate(crypto_symbol)
            usd_amount = amount * rate
            return usd_amount
        except Exception as e:
            logger.error(f"Error converting {amount} {crypto_symbol} to USD: {e}")
            raise

    async def convert_usd_to_crypto(
        self, usd_amount: Decimal, crypto_symbol: str
    ) -> Decimal:
        """Convert USD amount to cryptocurrency"""
        try:
            rate = await self.get_crypto_to_usd_rate(crypto_symbol)
            if rate == Decimal("0"):
                raise FastForexAPIError(f"Invalid rate (0) for {crypto_symbol}")

            crypto_amount = usd_amount / rate
            return crypto_amount
        except Exception as e:
            logger.error(f"Error converting ${usd_amount} USD to {crypto_symbol}: {e}")
            raise

    async def _make_request(self, endpoint: str, params: dict) -> Optional[dict]:
        """PERFORMANCE OPTIMIZED: Make request to FastForex API with connection pooling"""
        if not self.api_key:
            logger.warning("FastForex API key not configured")
            return None

        try:
            # PERFORMANCE OPTIMIZATION: Use optimized HTTP session with connection pooling
            async with optimized_http_session() as session:
                url = f"{self.base_url}/{endpoint}"
                params["api_key"] = self.api_key

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"FastForex API error: {response.status} - {error_text}"
                        )
                        return None
        except Exception as e:
            logger.error(f"Error making FastForex request: {e}")
            return None

    async def get_usd_to_ngn_rate_clean(self) -> Optional[Decimal]:
        """Get USD to NGN rate with intelligent caching for high-frequency access"""
        try:
            # Check cache first - USD-NGN is accessed very frequently
            cache_key = "forex_rate_USD_NGN"
            cached_rate = get_cached(cache_key)
            if cached_rate is not None:
                return Decimal(str(cached_rate))
            
            # Primary: FastForex API
            if self.api_key:
                try:
                    response = await self._make_request(
                        "fetch-one", {"from": "USD", "to": "NGN"}
                    )
                    if response and response.get("result"):
                        fastforex_rate = Decimal(str(response["result"]["NGN"]))
                        # Cache the rate for performance
                        set_cached(cache_key, fastforex_rate, ttl=self.cache_ttl)
                        logger.info(f"🔄 Fresh USD-NGN: ₦{float(fastforex_rate):,.2f} (cached for {self.cache_ttl}s)")
                        return fastforex_rate
                except Exception as fastforex_error:
                    logger.warning(
                        f"FastForex API failed: {fastforex_error}, trying fallback..."
                    )

            # Fail fast - no fallback logic per user request
            raise FastForexAPIError("FastForex USD-NGN rate request failed")

        except Exception as e:
            logger.error(f"Critical error getting USD to NGN rate: {e}")
            # Fail fast - no fallback logic per user request  
            raise FastForexAPIError(f"USD-NGN rate error: {e}")

    async def get_usd_to_ngn_rate(self) -> Optional[Decimal]:
        """
        Backward compatibility method - delegates to get_usd_to_ngn_rate_clean()
        This method exists to maintain compatibility with existing code that calls get_usd_to_ngn_rate()
        """
        return await self.get_usd_to_ngn_rate_clean()

    async def get_usd_to_ngn_rate_with_markup(self) -> Optional[Decimal]:
        """Get real-time USD to NGN rate with platform markup - users get LESS NGN when selling USD"""
        try:
            base_rate = await self.get_usd_to_ngn_rate_clean()
            if base_rate:
                # Apply platform markup - SUBTRACT percentage so users get less NGN per USD
                markup_percentage = Decimal(str(Config.EXCHANGE_MARKUP_PERCENTAGE))
                user_rate = base_rate * (Decimal("1") - markup_percentage / Decimal("100"))

                logger.info(
                    f"USD→NGN User Selling Rate: Base {float(base_rate):,.2f}, user gets {float(user_rate):,.2f} (base - {float(markup_percentage)}%)"
                )
                return user_rate
            else:
                raise FastForexAPIError("Failed to get clean USD to NGN rate")

        except Exception as e:
            logger.error(f"Error getting real-time USD to NGN rate: {e}")
            raise FastForexAPIError(f"Failed to get real-time USD to NGN rate: {e}")
    
    async def get_usd_to_ngn_rate_with_wallet_markup(self) -> Optional[Decimal]:
        """Get real-time USD to NGN rate with 2% wallet markup - for wallet cashouts"""
        try:
            base_rate = await self.get_usd_to_ngn_rate_clean()
            if base_rate:
                # Apply 2% wallet markup - users get LESS NGN per USD
                markup_percentage = Decimal(str(Config.WALLET_NGN_MARKUP_PERCENTAGE))
                user_rate = base_rate * (Decimal("1") - markup_percentage / Decimal("100"))

                logger.info(
                    f"USD→NGN Wallet Cashout Rate: Base {float(base_rate):,.2f}, user gets {float(user_rate):,.2f} per USD (base - {float(markup_percentage)}%)"
                )
                return user_rate
            else:
                raise FastForexAPIError("Failed to get clean USD to NGN rate")

        except Exception as e:
            logger.error(f"Error getting wallet USD to NGN rate: {e}")
            raise FastForexAPIError(f"Failed to get wallet USD to NGN rate: {e}")

    async def get_ngn_to_usd_rate_with_markup(self) -> Optional[Decimal]:
        """Get real-time NGN to USD rate with platform markup - users get LESS USD when selling NGN"""
        try:
            base_usd_to_ngn = await self.get_usd_to_ngn_rate_clean()
            if base_usd_to_ngn:
                # Convert to NGN to USD rate
                base_ngn_to_usd = Decimal("1") / base_usd_to_ngn

                # Apply platform markup - SUBTRACT percentage so users get less USD per NGN
                markup_percentage = Decimal(str(Config.EXCHANGE_MARKUP_PERCENTAGE))
                user_rate = base_ngn_to_usd * (Decimal("1") - markup_percentage / Decimal("100"))

                logger.info(
                    f"NGN→USD User Selling Rate: Base {float(base_ngn_to_usd):.6f}, user gets {float(user_rate):.6f} (base - {float(markup_percentage)}%)"
                )
                return user_rate
            else:
                raise FastForexAPIError("Failed to get clean USD to NGN rate")

        except Exception as e:
            logger.error(f"Error getting real-time NGN to USD rate: {e}")
            raise FastForexAPIError(f"Failed to get real-time NGN to USD rate: {e}")
    
    async def get_ngn_to_usd_rate_with_wallet_markup(self) -> Optional[Decimal]:
        """Get real-time NGN to USD rate with 2% wallet markup - for wallet deposits"""
        try:
            base_usd_to_ngn = await self.get_usd_to_ngn_rate_clean()
            if base_usd_to_ngn:
                # Convert to NGN to USD rate
                base_ngn_to_usd = Decimal("1") / base_usd_to_ngn

                # Apply 2% wallet markup - users get LESS USD per NGN
                markup_percentage = Decimal(str(Config.WALLET_NGN_MARKUP_PERCENTAGE))
                user_rate = base_ngn_to_usd * (Decimal("1") - markup_percentage / Decimal("100"))

                logger.info(
                    f"NGN→USD Wallet Deposit Rate: Base {float(base_ngn_to_usd):.6f}, user gets {float(user_rate):.6f} (base - {float(markup_percentage)}%)"
                )
                return user_rate
            else:
                raise FastForexAPIError("Failed to get clean USD to NGN rate")

        except Exception as e:
            logger.error(f"Error getting wallet NGN to USD rate: {e}")
            raise FastForexAPIError(f"Failed to get wallet NGN to USD rate: {e}")

    async def convert_usd_to_ngn_with_markup(
        self, usd_amount: Decimal
    ) -> Optional[Decimal]:
        """Convert USD amount to NGN with platform markup - user gets less NGN"""
        rate = await self.get_usd_to_ngn_rate_with_markup()
        if rate:
            ngn_amount = usd_amount * rate
            logger.info(
                f"User selling ${float(usd_amount):.2f} USD gets ₦{float(ngn_amount):,.2f} NGN at rate {float(rate):,.2f} (with platform markup)"
            )
            return ngn_amount
        return None

    async def convert_ngn_to_usd_with_markup(
        self, ngn_amount: Decimal
    ) -> Optional[Decimal]:
        """Convert NGN amount to USD with platform markup - user gets less USD"""
        rate = await self.get_ngn_to_usd_rate_with_markup()
        if rate:
            usd_amount = ngn_amount * rate
            logger.info(
                f"User selling ₦{float(ngn_amount):,.2f} NGN gets ${float(usd_amount):.2f} USD at rate {float(rate):.6f} (with platform markup)"
            )
            return usd_amount
        return None

    def invalidate_rate_cache(self, crypto_symbol: Optional[str] = None, force_all: bool = False):
        """Invalidate cached rates when needed"""
        if force_all:
            # Clear all rate-related caches including Kraken symbols
            rate_keys = [
                # Standard symbols
                "crypto_rate_BTC_USD", "crypto_rate_ETH_USD", "crypto_rate_LTC_USD",
                "crypto_rate_DOGE_USD", "crypto_rate_USDT-ERC20_USD", "crypto_rate_USDT-TRC20_USD",
                # Kraken symbols
                "crypto_rate_XETH_USD", "crypto_rate_XXBT_USD", "crypto_rate_XLTC_USD",
                "crypto_rate_XXDG_USD", "crypto_rate_XUSDT_USD",
                # Other caches
                "forex_rate_USD_NGN"
            ]
            for key in rate_keys:
                delete_cached(key)
            logger.info("🗑️ Cleared all exchange rate caches (standard + Kraken symbols)")
        elif crypto_symbol:
            cache_key = f"crypto_rate_{crypto_symbol}_USD"
            delete_cached(cache_key)
            logger.info(f"🗑️ Cleared cache for {crypto_symbol}")
    
    async def get_crypto_to_usd_rate_webhook_optimized(self, crypto_symbol: str) -> Optional[Decimal]:
        """
        WEBHOOK OPTIMIZATION: Get crypto rate using ONLY cached data - never makes API calls
        This is specifically designed for webhook handlers to avoid performance delays
        """
        try:
            # Map crypto symbols to FastForex format FIRST (before cache check)
            # This ensures both "LTC" and "XLTC" use the same cache entry
            symbol_map = {
                # Standard symbols
                "BTC": "BTC",
                "ETH": "ETH",
                "LTC": "LTC",
                "DOGE": "DOGE",
                "BCH": "BCH",
                "BSC": "BNB",  # Binance Smart Chain uses BNB
                "TRX": "TRX",
                "USDT-ERC20": "USDT",
                "USDT-TRC20": "USDT",
                "USD": "USD",
                
                # Kraken symbol mappings (X-prefixed to standard)
                "XETH": "ETH",     # Ethereum
                "XXBT": "BTC",     # Bitcoin  
                "XLTC": "LTC",     # Litecoin
                "XXDG": "DOGE",    # Dogecoin
                "XBCH": "BCH",     # Bitcoin Cash
                "XTRX": "TRX",     # Tron
                "XXRP": "XRP",     # Ripple
                "XADA": "ADA",     # Cardano
                "XDOT": "DOT",     # Polkadot
                "XXLM": "XLM",     # Stellar
                "XXMR": "XMR",     # Monero
                "XZEC": "ZEC",     # Zcash
                "XREP": "REP",     # Augur
                "XXTZ": "XTZ",     # Tezos
                "XLINK": "LINK",   # Chainlink
                "XUSDT": "USDT",   # Tether
                
                # Additional exchange-specific mappings
                "ZUSD": "USD",     # Kraken's USD representation
                "ZEUR": "EUR",     # Kraken's EUR representation
            }
            
            mapped_symbol = symbol_map.get(crypto_symbol, crypto_symbol)
            
            # USD to USD is always 1.0
            if mapped_symbol == "USD":
                return Decimal("1.0")
            
            # Check main cache first (using mapped symbol)
            cache_key = f"crypto_rate_{mapped_symbol}_USD"
            cached_rate = get_cached(cache_key)
            if cached_rate is not None:
                logger.debug(f"🚀 WEBHOOK_CACHE_HIT: {crypto_symbol} (mapped to {mapped_symbol}) = ${float(cached_rate):.4f} USD")
                return Decimal(str(cached_rate))
            
            # Check rapid cache for high-frequency requests (using mapped symbol)
            rapid_cache_key = f"rapid_crypto_rate_{mapped_symbol}_USD"
            rapid_cached_rate = get_cached(rapid_cache_key)
            if rapid_cached_rate is not None:
                logger.debug(f"🚀 WEBHOOK_RAPID_CACHE_HIT: {crypto_symbol} (mapped to {mapped_symbol}) = ${float(rapid_cached_rate):.4f} USD")
                return Decimal(str(rapid_cached_rate))
            
            # Check fallback cache (older data but still usable for webhooks) (using mapped symbol)
            fallback_cache_key = f"fallback_crypto_rate_{mapped_symbol}_USD"
            fallback_rate = get_cached(fallback_cache_key)
            if fallback_rate is not None:
                logger.warning(f"🚀 WEBHOOK_FALLBACK_CACHE: Using stale {crypto_symbol} (mapped to {mapped_symbol}) rate ${float(fallback_rate):.4f} USD")
                return Decimal(str(fallback_rate))
                
            # NO API CALLS IN WEBHOOK PATH - return None if no cached data available
            logger.error(f"⚠️ WEBHOOK_CACHE_MISS: No cached rate for {crypto_symbol} (mapped to {mapped_symbol}) - webhook should be retried")
            return None
            
        except Exception as e:
            logger.error(f"❌ WEBHOOK_RATE_ERROR: {crypto_symbol} - {e}")
            return None
    
    async def get_ngn_rate_webhook_optimized(self) -> Optional[Decimal]:
        """
        WEBHOOK OPTIMIZATION: Get NGN rate using ONLY cached data - never makes API calls
        This is specifically designed for webhook handlers to avoid performance delays
        """
        try:
            # Check main cache first
            cache_key = "forex_rate_USD_NGN"
            cached_rate = get_cached(cache_key)
            if cached_rate is not None:
                logger.debug(f"🚀 WEBHOOK_NGN_CACHE_HIT: ₦{float(cached_rate):,.2f}")
                return Decimal(str(cached_rate))
            
            # Check fallback cache
            fallback_cache_key = "fallback_forex_rate_USD_NGN"
            fallback_rate = get_cached(fallback_cache_key)
            if fallback_rate is not None:
                logger.warning(f"🚀 WEBHOOK_NGN_FALLBACK: Using stale NGN rate ₦{float(fallback_rate):,.2f}")
                return Decimal(str(fallback_rate))
            
            # NO API CALLS IN WEBHOOK PATH
            logger.error("⚠️ WEBHOOK_NGN_CACHE_MISS: No cached NGN rate - webhook should be retried")
            return None
            
        except Exception as e:
            logger.error(f"❌ WEBHOOK_NGN_ERROR: {e}")
            return None

    async def warm_cache(self):
        """Pre-warm cache with commonly requested rates including Kraken symbols"""
        try:
            # Include both standard and Kraken symbols for comprehensive caching
            common_symbols = [
                # Standard symbols
                "BTC", "ETH", "LTC", "DOGE", "USDT-ERC20", "BCH", "BSC", "TRX", "USDT-TRC20",
                # Kraken symbols (will map to standard symbols internally)
                "XETH", "XXBT", "XLTC", "XXDG", "XUSDT", "XBCH", "XTRX"
            ]
            logger.info(f"🔥 WEBHOOK_OPTIMIZATION: Warming cache for {len(common_symbols)} crypto rates...")
            
            tasks = []
            for symbol in common_symbols:
                task = asyncio.create_task(self.get_crypto_to_usd_rate(symbol))
                tasks.append((symbol, task))
            
            # Also warm USD-NGN rate
            ngn_task = asyncio.create_task(self.get_usd_to_ngn_rate_clean())
            
            # Wait for all cache warming to complete
            warmed_count = 0
            for symbol, task in tasks:
                try:
                    rate = await task
                    warmed_count += 1
                    
                    # WEBHOOK OPTIMIZATION: Also store in fallback cache with longer TTL
                    fallback_cache_key = f"fallback_crypto_rate_{symbol}_USD"
                    set_cached(fallback_cache_key, rate, ttl=self.fallback_cache_ttl)
                    
                    logger.debug(f"✅ Warmed cache for {symbol}: ${float(rate):.4f}")
                except Exception as e:
                    logger.warning(f"Failed to warm cache for {symbol}: {e}")
            
            try:
                ngn_rate = await ngn_task
                if ngn_rate is not None:
                    warmed_count += 1
                    
                    # WEBHOOK OPTIMIZATION: Also store NGN in fallback cache
                    fallback_ngn_key = "fallback_forex_rate_USD_NGN"
                    set_cached(fallback_ngn_key, ngn_rate, ttl=self.fallback_cache_ttl)
                    
                    logger.debug(f"✅ Warmed NGN cache: ₦{float(ngn_rate):,.2f}")
            except Exception as e:
                logger.warning(f"Failed to warm USD-NGN cache: {e}")
            
            logger.info(f"✅ WEBHOOK_CACHE_WARMING: {warmed_count}/{len(common_symbols) + 1} rates cached with fallback")
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")



# Global instance
fastforex_service = FastForexService()


async def warm_fastforex_cache():
    """Convenience function to warm FastForex cache"""
    await fastforex_service.warm_cache()


async def startup_prewarm_critical_rates():
    """
    STARTUP PRE-WARMING: Fetch and cache all critical crypto rates immediately on system startup
    This prevents the timing gap where webhooks arrive before the first background refresh
    
    This function ensures all webhook-critical currencies are cached BEFORE webhooks can be processed
    """
    from jobs.crypto_rate_background_refresh import CryptoRateBackgroundRefresh
    
    logger.info("🔥 STARTUP_PREWARM: Fetching critical crypto rates before webhook processing...")
    start_time = time.time()
    
    try:
        # Use the same critical currencies list as the background refresh
        critical_currencies = CryptoRateBackgroundRefresh.WEBHOOK_CRITICAL_CURRENCIES
        
        success_count = 0
        error_count = 0
        
        # Fetch all critical rates concurrently
        tasks = []
        for currency in critical_currencies:
            task = asyncio.create_task(fastforex_service.get_crypto_to_usd_rate(currency))
            tasks.append((currency, task))
        
        # Also fetch NGN rate
        ngn_task = asyncio.create_task(fastforex_service.get_usd_to_ngn_rate_clean())
        
        # Wait for all fetches to complete
        for currency, task in tasks:
            try:
                rate = await task
                if rate is not None:
                    success_count += 1
                    
                    # CRITICAL: Store in BOTH main cache AND extended fallback cache
                    cache_key = f"crypto_rate_{currency}_USD"
                    fallback_key = f"fallback_crypto_rate_{currency}_USD"
                    
                    set_cached(cache_key, rate, ttl=fastforex_service.cache_ttl)
                    set_cached(fallback_key, rate, ttl=7200)  # 2-hour fallback
                    
                    logger.debug(f"✅ PREWARMED: {currency} = ${float(rate):.4f} (cached with fallback)")
                else:
                    error_count += 1
                    logger.warning(f"⚠️ PREWARM_FAILED: {currency} - no rate available")
            except Exception as e:
                error_count += 1
                logger.error(f"❌ PREWARM_ERROR: {currency} - {e}")
        
        # Fetch NGN rate
        try:
            ngn_rate = await ngn_task
            if ngn_rate:
                success_count += 1
                set_cached("forex_rate_USD_NGN", ngn_rate, ttl=fastforex_service.cache_ttl)
                set_cached("fallback_forex_rate_USD_NGN", ngn_rate, ttl=7200)  # 2-hour fallback
                logger.debug(f"✅ PREWARMED: USD-NGN = ₦{float(ngn_rate):,.2f}")
            else:
                error_count += 1
        except Exception as e:
            error_count += 1
            logger.error(f"❌ PREWARM_NGN_ERROR: {e}")
        
        duration = time.time() - start_time
        total_currencies = len(critical_currencies) + 1  # +1 for NGN
        
        logger.info(
            f"✅ STARTUP_PREWARM_COMPLETE: {success_count}/{total_currencies} rates cached in {duration:.2f}s "
            f"(Errors: {error_count})"
        )
        
        # Return success status
        return success_count > 0  # Success if at least one rate was cached
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ STARTUP_PREWARM_FAILED: Critical error after {duration:.2f}s - {e}")
        return False


async def emergency_fetch_rate_with_circuit_breaker(currency: str) -> Optional[Decimal]:
    """
    EMERGENCY FALLBACK: Attempt synchronous rate fetch when ALL caches are empty
    This is a last-resort mechanism with circuit breaker protection to prevent cascading failures
    
    Only called when:
    1. Main cache is empty
    2. Rapid cache is empty  
    3. Fallback cache is empty
    4. Webhook needs the rate urgently
    
    Circuit breaker prevents this from being called too frequently
    """
    try:
        # Check circuit breaker status
        from services.circuit_breaker import circuit_breakers, CircuitBreaker
        
        breaker_name = "fastforex_emergency"
        
        # Ensure circuit breaker exists
        if breaker_name not in circuit_breakers:
            circuit_breakers[breaker_name] = CircuitBreaker(
                name=breaker_name,
                failure_threshold=3,
                recovery_timeout=60,
                expected_exception=FastForexAPIError
            )
        
        breaker = circuit_breakers[breaker_name]
        
        # Check if circuit is open
        breaker_state = await breaker.get_state()
        if breaker_state['state'] == "open":
            logger.warning(f"⚠️ EMERGENCY_FETCH_BLOCKED: Circuit breaker open for {currency}")
            return None
        
        logger.warning(f"🚨 EMERGENCY_FETCH: Attempting live rate fetch for {currency} (ALL caches empty)")
        
        # Attempt to fetch rate with timeout
        try:
            rate = await asyncio.wait_for(
                fastforex_service.get_crypto_to_usd_rate(currency),
                timeout=5.0  # 5 second timeout for emergency fetch
            )
            
            if rate is not None:
                logger.info(f"✅ EMERGENCY_SUCCESS: Fetched {currency} = ${float(rate):.4f} (cached for future)")
                
                # Store in all caches to prevent future emergencies
                cache_key = f"crypto_rate_{currency}_USD"
                fallback_key = f"fallback_crypto_rate_{currency}_USD"
                set_cached(cache_key, rate, ttl=fastforex_service.cache_ttl)
                set_cached(fallback_key, rate, ttl=7200)
                
                # Record success with circuit breaker
                await breaker._on_success()
                
                return rate
            else:
                logger.error(f"❌ EMERGENCY_FAILED: No rate returned for {currency}")
                await breaker._on_failure()
                return None
                
        except asyncio.TimeoutError:
            logger.error(f"❌ EMERGENCY_TIMEOUT: Rate fetch timeout for {currency} (>5s)")
            await breaker._on_failure()
            return None
        except Exception as fetch_error:
            logger.error(f"❌ EMERGENCY_ERROR: Rate fetch failed for {currency} - {fetch_error}")
            await breaker._on_failure()
            return None
            
    except Exception as e:
        logger.error(f"❌ EMERGENCY_CRITICAL: Circuit breaker error - {e}")
        return None

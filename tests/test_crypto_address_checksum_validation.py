"""
Comprehensive Crypto Address Checksum Validation Test
Tests the cryptographic checksum validation implementation for all supported cryptocurrencies
"""

import pytest
import base58
import hashlib
from handlers.wallet_direct import validate_crypto_address, validate_base58check, validate_ethereum_checksum


class TestBase58CheckValidation:
    """Test Base58Check checksum validation (Bitcoin-like addresses)"""
    
    def test_valid_bitcoin_address(self):
        """Test valid Bitcoin address with correct checksum"""
        is_valid, msg = validate_crypto_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "BTC")
        assert is_valid is True
        assert "cryptographic checksum" in msg
    
    def test_invalid_bitcoin_checksum(self):
        """Test Bitcoin address with invalid checksum"""
        is_valid, msg = validate_crypto_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb", "BTC")
        assert is_valid is False
        assert "checksum" in msg.lower()
    
    def test_valid_litecoin_address(self):
        """Test valid Litecoin address with correct checksum"""
        is_valid, msg = validate_crypto_address("LaMT348PWRnrqeeWArpwQPbuanpXDZGEUz", "LTC")
        assert is_valid is True
    
    def test_valid_dogecoin_address(self):
        """Test valid Dogecoin address with correct checksum"""
        is_valid, msg = validate_crypto_address("DH5yaieqoZN36fDVciNyRueRGvGLR3mr7L", "DOGE")
        assert is_valid is True
    
    def test_valid_bitcoin_cash_address(self):
        """Test valid Bitcoin Cash address with correct checksum"""
        is_valid, msg = validate_crypto_address("1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "BCH")
        assert is_valid is True


class TestTronAddressValidation:
    """Test Tron address validation (TRX and USDT-TRC20)"""
    
    def test_valid_trx_address(self):
        """Test valid Tron address with correct checksum"""
        is_valid, msg = validate_crypto_address("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE", "TRX")
        assert is_valid is True
        assert "cryptographic checksum" in msg
    
    def test_invalid_trx_checksum(self):
        """Test Tron address with invalid checksum"""
        is_valid, msg = validate_crypto_address("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSF", "TRX")
        assert is_valid is False
        assert "checksum" in msg.lower()
    
    def test_valid_usdt_trc20_address(self):
        """Test valid USDT-TRC20 address (same as TRX)"""
        is_valid, msg = validate_crypto_address("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE", "USDT-TRC20")
        assert is_valid is True
        assert "cryptographic checksum" in msg
    
    def test_invalid_usdt_trc20_checksum(self):
        """Test USDT-TRC20 address with invalid checksum"""
        is_valid, msg = validate_crypto_address("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSF", "USDT-TRC20")
        assert is_valid is False


class TestEthereumAddressValidation:
    """Test Ethereum EIP-55 checksum validation (ETH and USDT-ERC20)"""
    
    def test_valid_checksummed_address(self):
        """Test correctly checksummed Ethereum address"""
        is_valid, msg = validate_crypto_address("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed", "ETH")
        assert is_valid is True
        assert "cryptographic checksum" in msg
    
    def test_valid_lowercase_address(self):
        """Test all-lowercase Ethereum address (valid but not checksummed)"""
        is_valid, msg = validate_crypto_address("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed", "ETH")
        assert is_valid is True
    
    def test_valid_uppercase_address(self):
        """Test all-uppercase Ethereum address (valid but not checksummed)"""
        is_valid, msg = validate_crypto_address("0x5AAEB6053F3E94C9B9A09F33669435E7EF1BEAED", "ETH")
        assert is_valid is True
    
    def test_invalid_mixed_case_checksum(self):
        """Test incorrectly checksummed mixed-case address"""
        is_valid, msg = validate_crypto_address("0x742d35Cc6634C0532925a3b8D4B4d45e3e06b69f", "ETH")
        assert is_valid is False
        assert "checksum" in msg.lower()
    
    def test_valid_usdt_erc20_lowercase(self):
        """Test USDT-ERC20 address (same as ETH)"""
        is_valid, msg = validate_crypto_address("0x742d35cc6634c0532925a3b8d4b4d45e3e06b69f", "USDT-ERC20")
        assert is_valid is True


class TestAddressFormatValidation:
    """Test address format validation (length, prefix, etc.)"""
    
    def test_btc_wrong_length(self):
        """Test Bitcoin address with wrong length"""
        is_valid, msg = validate_crypto_address("1A1zP", "BTC")
        assert is_valid is False
        assert "26-35 characters" in msg
    
    def test_eth_wrong_length(self):
        """Test Ethereum address with wrong length"""
        is_valid, msg = validate_crypto_address("0x742d35", "ETH")
        assert is_valid is False
        assert "42 characters" in msg
    
    def test_trx_wrong_prefix(self):
        """Test Tron address with wrong prefix"""
        is_valid, msg = validate_crypto_address("AQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE", "TRX")
        assert is_valid is False
        assert "must start with T" in msg
    
    def test_eth_wrong_prefix(self):
        """Test Ethereum address without 0x prefix"""
        # Use 42 characters without 0x prefix to test prefix validation specifically
        is_valid, msg = validate_crypto_address("Ax742d35cc6634c0532925a3b8d4b4d45e3e06b69f", "ETH")
        assert is_valid is False
        assert "must start with 0x" in msg
    
    def test_empty_address(self):
        """Test empty address validation"""
        is_valid, msg = validate_crypto_address("", "BTC")
        assert is_valid is False
        assert "cannot be empty" in msg


class TestCryptographicHelperFunctions:
    """Test the underlying cryptographic validation functions"""
    
    def test_base58check_helper_valid(self):
        """Test Base58Check helper with valid address"""
        result = validate_base58check("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        assert result is True
    
    def test_base58check_helper_invalid(self):
        """Test Base58Check helper with invalid checksum"""
        result = validate_base58check("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb")
        assert result is False
    
    def test_ethereum_checksum_helper_valid(self):
        """Test Ethereum checksum helper with valid checksummed address"""
        result = validate_ethereum_checksum("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
        assert result is True
    
    def test_ethereum_checksum_helper_lowercase(self):
        """Test Ethereum checksum helper accepts lowercase"""
        result = validate_ethereum_checksum("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed")
        assert result is True
    
    def test_ethereum_checksum_helper_invalid_mixed(self):
        """Test Ethereum checksum helper rejects invalid mixed-case"""
        result = validate_ethereum_checksum("0x742d35Cc6634C0532925a3b8D4B4d45e3e06b69f")
        assert result is False


class TestComprehensiveCoverage:
    """Comprehensive test coverage for all supported cryptocurrencies"""
    
    @pytest.mark.parametrize("address,currency,should_pass", [
        # Bitcoin - valid
        ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "BTC", True),
        # Bitcoin - invalid checksum
        ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb", "BTC", False),
        # Ethereum - valid checksummed
        ("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed", "ETH", True),
        # Ethereum - valid lowercase
        ("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed", "ETH", True),
        # Ethereum - invalid checksum
        ("0x742d35Cc6634C0532925a3b8D4B4d45e3e06b69f", "ETH", False),
        # Tron - valid
        ("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE", "TRX", True),
        # Tron - invalid checksum
        ("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSF", "TRX", False),
        # USDT-TRC20 - valid
        ("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE", "USDT-TRC20", True),
        # USDT-ERC20 - valid lowercase
        ("0x742d35cc6634c0532925a3b8d4b4d45e3e06b69f", "USDT-ERC20", True),
    ])
    def test_comprehensive_validation(self, address, currency, should_pass):
        """Comprehensive test for all cryptocurrencies"""
        is_valid, msg = validate_crypto_address(address, currency)
        assert is_valid == should_pass, f"Expected {should_pass} for {currency} address {address[:20]}..."


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

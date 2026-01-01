"""
Randomness Control Fixtures
Deterministic randomness for reproducible testing
"""

import pytest
import random
import uuid
import secrets
import hashlib
from typing import Any, Optional, List, Union
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DeterministicRandom:
    """
    Deterministic random number generator for testing
    
    Features:
    - Seeded random generation for reproducible results
    - Deterministic UUID generation based on counters
    - Predictable secrets generation
    - Support for custom random sequences
    """
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.original_random = random
        self.original_uuid = uuid
        self.original_secrets = secrets
        
        # Deterministic counters
        self.uuid_counter = 1000
        self.otp_counter = 100000
        self.reference_counter = 1000
        
        # Pre-defined sequences for common use cases
        self.otp_sequence = [
            "123456", "789012", "345678", "901234", "567890",
            "246810", "135791", "987654", "321098", "876543"
        ]
        self.otp_index = 0
        
        self.uuid_sequence = [
            "test-uuid-0001-0001-000000000001",
            "test-uuid-0002-0002-000000000002", 
            "test-uuid-0003-0003-000000000003",
            "test-uuid-0004-0004-000000000004",
            "test-uuid-0005-0005-000000000005"
        ]
        self.uuid_index = 0
        
        # Patch objects
        self.patches = []
        
    def __enter__(self):
        """Start deterministic random patching"""
        
        # Seed the standard random module
        random.seed(self.seed)
        
        # Create mock objects
        mock_uuid = MagicMock()
        mock_uuid.uuid4 = self._mock_uuid4
        mock_uuid.UUID = uuid.UUID  # Preserve UUID class
        
        mock_secrets = MagicMock()
        mock_secrets.token_hex = self._mock_token_hex
        mock_secrets.token_urlsafe = self._mock_token_urlsafe
        mock_secrets.choice = self._mock_secrets_choice
        
        # Patch configurations
        patches_config = [
            ('uuid.uuid4', self._mock_uuid4),
            ('secrets.token_hex', self._mock_token_hex),
            ('secrets.token_urlsafe', self._mock_token_urlsafe),
            ('secrets.choice', self._mock_secrets_choice),
            
            # Common imports in services
            ('services.onboarding_service.uuid', mock_uuid),
            ('services.email_verification_service.secrets', mock_secrets),
            ('services.conditional_otp_service.secrets', mock_secrets),
            ('utils.helpers.uuid', mock_uuid),
            ('utils.helpers.secrets', mock_secrets),
            ('utils.secure_id_generator.uuid', mock_uuid),
            ('utils.secure_id_generator.secrets', mock_secrets),
            
            # Handler imports
            ('handlers.onboarding_router.uuid', mock_uuid),
            ('handlers.escrow.uuid', mock_uuid),
        ]
        
        for target, replacement in patches_config:
            try:
                patch_obj = patch(target, new=replacement)
                self.patches.append(patch_obj)
                patch_obj.start()
            except (ImportError, AttributeError) as e:
                logger.debug(f"Could not patch {target}: {e}")
        
        logger.info(f"🎲 Deterministic randomness enabled (seed: {self.seed})")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop deterministic random patching"""
        for patch_obj in self.patches:
            try:
                patch_obj.stop()
            except Exception as e:
                logger.debug(f"Error stopping patch: {e}")
        
        self.patches.clear()
        logger.info("🎲 Deterministic randomness disabled")
    
    def _mock_uuid4(self):
        """Generate deterministic UUID4"""
        if self.uuid_index < len(self.uuid_sequence):
            uuid_str = self.uuid_sequence[self.uuid_index]
            self.uuid_index += 1
        else:
            # Generate predictable UUID based on counter
            self.uuid_counter += 1
            uuid_str = f"test-uuid-{self.uuid_counter:04d}-{self.uuid_counter:04d}-{self.uuid_counter:012d}"
        
        return uuid.UUID(uuid_str.replace('-', ''))
    
    def _mock_token_hex(self, nbytes: int = 32) -> str:
        """Generate deterministic hex token"""
        # Use seed and counter for deterministic generation
        data = f"token_hex_{self.seed}_{nbytes}_{self.reference_counter}".encode()
        self.reference_counter += 1
        return hashlib.sha256(data).hexdigest()[:nbytes*2]
    
    def _mock_token_urlsafe(self, nbytes: int = 32) -> str:
        """Generate deterministic URL-safe token"""
        data = f"token_urlsafe_{self.seed}_{nbytes}_{self.reference_counter}".encode()
        self.reference_counter += 1
        # Use base64-like encoding but deterministic
        token = hashlib.sha256(data).digest()[:nbytes]
        import base64
        return base64.urlsafe_b64encode(token).decode().rstrip('=')
    
    def _mock_secrets_choice(self, sequence):
        """Deterministically choose from sequence"""
        # Use current state to deterministically select
        index = (self.reference_counter + self.seed) % len(sequence)
        self.reference_counter += 1
        return sequence[index]
    
    def get_deterministic_otp(self) -> str:
        """Get next deterministic OTP from sequence"""
        if self.otp_index < len(self.otp_sequence):
            otp = self.otp_sequence[self.otp_index]
            self.otp_index += 1
        else:
            # Generate predictable OTP
            self.otp_counter += 1
            otp = f"{(self.otp_counter % 1000000):06d}"
        
        return otp
    
    def get_deterministic_reference(self, prefix: str = "REF") -> str:
        """Generate deterministic reference ID"""
        self.reference_counter += 1
        return f"{prefix}_{self.seed}_{self.reference_counter:06d}"
    
    def reset_counters(self):
        """Reset all counters for test isolation"""
        self.uuid_counter = 1000
        self.otp_counter = 100000
        self.reference_counter = 1000
        self.otp_index = 0
        self.uuid_index = 0
        # Re-seed random
        random.seed(self.seed)
        logger.debug("🎲 Reset deterministic random counters")


@contextmanager
def seed_random(seed: int = 42):
    """
    Context manager for deterministic randomness
    
    Usage:
        with seed_random(42) as det_rand:
            otp = det_rand.get_deterministic_otp()  # Always returns "123456" first
            ref = det_rand.get_deterministic_reference("TEST")  # Always returns "TEST_42_001001"
    """
    det_random = DeterministicRandom(seed)
    with det_random:
        yield det_random


@pytest.fixture
def deterministic_random():
    """
    Pytest fixture for deterministic randomness
    
    Usage:
        def test_something(deterministic_random):
            with deterministic_random(42) as rand:
                otp = rand.get_deterministic_otp()
    """
    return seed_random


@pytest.fixture
def seeded_random_42():
    """Pytest fixture with pre-seeded random (seed=42)"""
    with seed_random(42) as rand:
        yield rand


@pytest.fixture
def seeded_random_123():
    """Pytest fixture with pre-seeded random (seed=123)"""  
    with seed_random(123) as rand:
        yield rand


# Specific randomness fixtures for common test scenarios
@pytest.fixture
def deterministic_otps():
    """Fixture that provides consistent OTP sequence for testing"""
    with seed_random(42) as rand:
        # Pre-generate a set of OTPs for use in tests
        otps = [rand.get_deterministic_otp() for _ in range(10)]
        yield otps


@pytest.fixture
def deterministic_uuids():
    """Fixture that provides consistent UUID sequence for testing"""
    with seed_random(42) as rand:
        # Mock uuid.uuid4 to return deterministic UUIDs
        yield rand


@pytest.fixture  
def deterministic_references():
    """Fixture that provides consistent reference ID generation"""
    with seed_random(42) as rand:
        def generate_ref(prefix="REF"):
            return rand.get_deterministic_reference(prefix)
        yield generate_ref
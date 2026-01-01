"""
DEPRECATED TEST FILE - DO NOT USE

This test file is deprecated and has been commented out because it tests the OLD BlockBee webhook architecture 
that has been replaced by blockbee_webhook_new.py.

Original Issues:
- Imports from 'handlers.blockbee_webhook' which no longer exists (replaced by blockbee_webhook_new)
- Tests process_blockbee_webhook() function that doesn't exist in current codebase
- Architecture has changed to use FastAPI routes instead of function-based handlers

Current Testing:
- See tests/test_e2e_payment_processing_system.py for current architecture tests
- Current webhook handler: handlers/blockbee_webhook_new.py

Date Deprecated: 2025-10-16
Reason: Architectural change from old webhook handler to new simplified processor
"""

# ENTIRE FILE COMMENTED OUT - DEPRECATED

"""
# Original test file content below (preserved for reference):

'''
Comprehensive Unit Tests for Deposit Flow with 100% Coverage
Tests all critical paths: BlockBee webhooks → idempotency → processor → wallet credit → notifications
'''

import pytest
import asyncio
import json
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Import the components being tested
from services.deposits.crypto_deposit_processor import (
    CryptoDepositProcessor,
    CryptoDepositProcessorError,
    CryptoDepositAlreadyProcessedError,
    InsufficientConfirmationsError
)
from services.webhook_idempotency_service import (
    WebhookIdempotencyService,
    WebhookEventInfo,
    WebhookProvider,
    IdempotencyResult,
    ProcessingResult
)
from handlers.blockbee_webhook import process_blockbee_webhook  # DOES NOT EXIST
from models import (
    CryptoDeposit, 
    CryptoDepositStatus, 
    Wallet, 
    Transaction, 
    User,
    WebhookEventLedger
)

[... rest of original test code ...]
"""

# No active tests - file completely deprecated

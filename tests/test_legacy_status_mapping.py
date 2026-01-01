"""
Comprehensive test suite for legacy status mapping system
Tests mapping completeness, edge cases, and dual-write adapter functionality
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from models import (
    EscrowStatus, CashoutStatus, ExchangeStatus, UnifiedTransactionStatus,
    UnifiedTransactionType, UnifiedTransaction
)
from services.legacy_status_mapper import LegacyStatusMapper, LegacySystemType
from services.dual_write_adapter import (
    DualWriteAdapter, DualWriteMode, DualWriteStrategy, 
    DualWriteConfig, DualWriteResult
)


class TestLegacyStatusMapperCompleteness:
    """Test mapping completeness and coverage"""
    
    def test_all_cashout_statuses_mapped(self):
        """Verify all CashoutStatus values have unified mappings"""
        all_cashout_statuses = set([status for status in CashoutStatus])
        mapped_statuses = set(LegacyStatusMapper.CASHOUT_TO_UNIFIED.keys())
        
        unmapped = all_cashout_statuses - mapped_statuses
        assert len(unmapped) == 0, f"Unmapped CashoutStatus values: {unmapped}"
        
        # Verify we have exactly the expected number
        assert len(mapped_statuses) == 14, f"Expected 14 cashout statuses, got {len(mapped_statuses)}"
    
    def test_all_escrow_statuses_mapped(self):
        """Verify all EscrowStatus values have unified mappings"""
        all_escrow_statuses = set([status for status in EscrowStatus])
        mapped_statuses = set(LegacyStatusMapper.ESCROW_TO_UNIFIED.keys())
        
        unmapped = all_escrow_statuses - mapped_statuses
        assert len(unmapped) == 0, f"Unmapped EscrowStatus values: {unmapped}"
        
        # Verify we have exactly the expected number
        assert len(mapped_statuses) == 13, f"Expected 13 escrow statuses, got {len(mapped_statuses)}"
    
    def test_all_exchange_statuses_mapped(self):
        """Verify all ExchangeStatus values have unified mappings"""
        all_exchange_statuses = set([status for status in ExchangeStatus])
        mapped_statuses = set(LegacyStatusMapper.EXCHANGE_TO_UNIFIED.keys())
        
        unmapped = all_exchange_statuses - mapped_statuses
        assert len(unmapped) == 0, f"Unmapped ExchangeStatus values: {unmapped}"
        
        # Verify we have exactly the expected number
        assert len(mapped_statuses) == 11, f"Expected 11 exchange statuses, got {len(mapped_statuses)}"
    
    def test_total_legacy_status_coverage(self):
        """Verify total count of mapped legacy statuses"""
        total_mapped = (
            len(LegacyStatusMapper.CASHOUT_TO_UNIFIED) +
            len(LegacyStatusMapper.ESCROW_TO_UNIFIED) +
            len(LegacyStatusMapper.EXCHANGE_TO_UNIFIED)
        )
        
        assert total_mapped == 38, f"Expected 38 total mapped statuses, got {total_mapped}"
    
    def test_validate_mapping_completeness_report(self):
        """Test the comprehensive validation report method"""
        report = LegacyStatusMapper.validate_mapping_completeness()
        
        assert report["validation_passed"] is True, "Mapping validation should pass"
        assert report["total_legacy_statuses"] == 38, f"Expected 38 total statuses"
        assert report["mapped_statuses"] == 38, f"All statuses should be mapped"
        assert len(report["unmapped_statuses"]) == 0, "No statuses should be unmapped"
        
        # Check detailed analysis
        assert "cashout" in report["detailed_analysis"]
        assert "escrow" in report["detailed_analysis"]
        assert "exchange" in report["detailed_analysis"]
        
        # Verify coverage percentages
        for system in ["cashout", "escrow", "exchange"]:
            analysis = report["detailed_analysis"][system]
            assert analysis["coverage_percentage"] == 100.0, f"{system} should have 100% coverage"
            assert analysis["unmapped_count"] == 0, f"{system} should have no unmapped statuses"


class TestLegacyStatusMapperFunctionality:
    """Test core mapping functionality"""
    
    def test_map_cashout_statuses_to_unified(self):
        """Test mapping CashoutStatus to UnifiedTransactionStatus"""
        test_cases = [
            (CashoutStatus.PENDING, UnifiedTransactionStatus.PENDING),
            (CashoutStatus.OTP_PENDING, UnifiedTransactionStatus.OTP_PENDING),
            (CashoutStatus.ADMIN_PENDING, UnifiedTransactionStatus.ADMIN_PENDING),
            (CashoutStatus.EXECUTING, UnifiedTransactionStatus.PROCESSING),
            (CashoutStatus.AWAITING_RESPONSE, UnifiedTransactionStatus.AWAITING_RESPONSE),
            (CashoutStatus.SUCCESS, UnifiedTransactionStatus.SUCCESS),
            (CashoutStatus.COMPLETED, UnifiedTransactionStatus.SUCCESS),  # Deprecated maps to SUCCESS
            (CashoutStatus.FAILED, UnifiedTransactionStatus.FAILED),
            (CashoutStatus.CANCELLED, UnifiedTransactionStatus.CANCELLED),
            (CashoutStatus.EXPIRED, UnifiedTransactionStatus.EXPIRED),
        ]
        
        for cashout_status, expected_unified in test_cases:
            result = LegacyStatusMapper.map_to_unified(cashout_status, LegacySystemType.CASHOUT)
            assert result == expected_unified, \
                f"CashoutStatus.{cashout_status.name} should map to {expected_unified.name}, got {result.name}"
    
    def test_map_escrow_statuses_to_unified(self):
        """Test mapping EscrowStatus to UnifiedTransactionStatus"""
        test_cases = [
            (EscrowStatus.CREATED, UnifiedTransactionStatus.PENDING),
            (EscrowStatus.PAYMENT_PENDING, UnifiedTransactionStatus.AWAITING_PAYMENT),
            (EscrowStatus.PAYMENT_CONFIRMED, UnifiedTransactionStatus.PAYMENT_CONFIRMED),
            (EscrowStatus.PARTIAL_PAYMENT, UnifiedTransactionStatus.PARTIAL_PAYMENT),
            (EscrowStatus.AWAITING_SELLER, UnifiedTransactionStatus.AWAITING_APPROVAL),
            (EscrowStatus.ACTIVE, UnifiedTransactionStatus.FUNDS_HELD),
            (EscrowStatus.COMPLETED, UnifiedTransactionStatus.SUCCESS),
            (EscrowStatus.DISPUTED, UnifiedTransactionStatus.DISPUTED),
            (EscrowStatus.CANCELLED, UnifiedTransactionStatus.CANCELLED),
            (EscrowStatus.REFUNDED, UnifiedTransactionStatus.SUCCESS),  # Refund completed = success
            (EscrowStatus.EXPIRED, UnifiedTransactionStatus.EXPIRED),
        ]
        
        for escrow_status, expected_unified in test_cases:
            result = LegacyStatusMapper.map_to_unified(escrow_status, LegacySystemType.ESCROW)
            assert result == expected_unified, \
                f"EscrowStatus.{escrow_status.name} should map to {expected_unified.name}, got {result.name}"
    
    def test_map_exchange_statuses_to_unified(self):
        """Test mapping ExchangeStatus to UnifiedTransactionStatus"""
        test_cases = [
            (ExchangeStatus.CREATED, UnifiedTransactionStatus.PENDING),
            (ExchangeStatus.AWAITING_DEPOSIT, UnifiedTransactionStatus.AWAITING_PAYMENT),
            (ExchangeStatus.PAYMENT_RECEIVED, UnifiedTransactionStatus.PAYMENT_CONFIRMED),
            (ExchangeStatus.PAYMENT_CONFIRMED, UnifiedTransactionStatus.PAYMENT_CONFIRMED),
            (ExchangeStatus.RATE_LOCKED, UnifiedTransactionStatus.FUNDS_HELD),
            (ExchangeStatus.PENDING_APPROVAL, UnifiedTransactionStatus.AWAITING_APPROVAL),
            (ExchangeStatus.PROCESSING, UnifiedTransactionStatus.PROCESSING),
            (ExchangeStatus.COMPLETED, UnifiedTransactionStatus.SUCCESS),
            (ExchangeStatus.FAILED, UnifiedTransactionStatus.FAILED),
            (ExchangeStatus.CANCELLED, UnifiedTransactionStatus.CANCELLED),
            (ExchangeStatus.ADDRESS_GENERATION_FAILED, UnifiedTransactionStatus.FAILED),
        ]
        
        for exchange_status, expected_unified in test_cases:
            result = LegacyStatusMapper.map_to_unified(exchange_status, LegacySystemType.EXCHANGE)
            assert result == expected_unified, \
                f"ExchangeStatus.{exchange_status.name} should map to {expected_unified.name}, got {result.name}"
    
    def test_reverse_mapping_functionality(self):
        """Test mapping from unified back to legacy statuses"""
        # Test cases with unambiguous reverse mappings
        test_cases = [
            (UnifiedTransactionStatus.OTP_PENDING, LegacySystemType.CASHOUT, CashoutStatus.OTP_PENDING),
            (UnifiedTransactionStatus.PARTIAL_PAYMENT, LegacySystemType.ESCROW, EscrowStatus.PARTIAL_PAYMENT),
            (UnifiedTransactionStatus.DISPUTED, LegacySystemType.ESCROW, EscrowStatus.DISPUTED),
        ]
        
        for unified_status, system_type, expected_legacy in test_cases:
            result = LegacyStatusMapper.map_from_unified(unified_status, system_type, prefer_primary=True)
            assert result == expected_legacy, \
                f"{unified_status.name} should reverse-map to {expected_legacy.name} for {system_type.name}"
    
    def test_invalid_mapping_raises_error(self):
        """Test that invalid mappings raise appropriate errors"""
        # Test invalid legacy status
        with pytest.raises(ValueError, match="Unknown CashoutStatus"):
            LegacyStatusMapper.map_to_unified("INVALID_STATUS", LegacySystemType.CASHOUT)
        
        # Test invalid system type
        with pytest.raises(ValueError, match="Unknown system type"):
            LegacyStatusMapper.map_to_unified(CashoutStatus.PENDING, "INVALID_SYSTEM")
        
        # Test invalid reverse mapping
        with pytest.raises(ValueError, match="No reverse mapping"):
            # Assume PARTIAL_PAYMENT doesn't exist in cashout mappings
            LegacyStatusMapper.map_from_unified(
                UnifiedTransactionStatus.PARTIAL_PAYMENT, 
                LegacySystemType.CASHOUT
            )


class TestLegacyStatusMapperAnalysis:
    """Test analysis and utility methods"""
    
    def test_status_lifecycle_phases(self):
        """Test lifecycle phase categorization"""
        initiation_statuses = [
            UnifiedTransactionStatus.PENDING,
            UnifiedTransactionStatus.AWAITING_PAYMENT,
            UnifiedTransactionStatus.PAYMENT_CONFIRMED
        ]
        
        authorization_statuses = [
            UnifiedTransactionStatus.FUNDS_HELD,
            UnifiedTransactionStatus.AWAITING_APPROVAL,
            UnifiedTransactionStatus.OTP_PENDING,
            UnifiedTransactionStatus.ADMIN_PENDING
        ]
        
        processing_statuses = [
            UnifiedTransactionStatus.PROCESSING,
            UnifiedTransactionStatus.AWAITING_RESPONSE,
            UnifiedTransactionStatus.RELEASE_PENDING
        ]
        
        terminal_statuses = [
            UnifiedTransactionStatus.SUCCESS,
            UnifiedTransactionStatus.FAILED,
            UnifiedTransactionStatus.CANCELLED,
            UnifiedTransactionStatus.DISPUTED,
            UnifiedTransactionStatus.EXPIRED
        ]
        
        for status in initiation_statuses:
            assert LegacyStatusMapper.get_status_lifecycle_phase(status) == "initiation"
        
        for status in authorization_statuses:
            assert LegacyStatusMapper.get_status_lifecycle_phase(status) == "authorization"
        
        for status in processing_statuses:
            assert LegacyStatusMapper.get_status_lifecycle_phase(status) == "processing"
        
        for status in terminal_statuses:
            assert LegacyStatusMapper.get_status_lifecycle_phase(status) == "terminal"
    
    def test_terminal_status_identification(self):
        """Test identification of terminal statuses"""
        terminal_statuses = [
            UnifiedTransactionStatus.SUCCESS,
            UnifiedTransactionStatus.FAILED,
            UnifiedTransactionStatus.CANCELLED,
            UnifiedTransactionStatus.DISPUTED,
            UnifiedTransactionStatus.EXPIRED
        ]
        
        non_terminal_statuses = [
            UnifiedTransactionStatus.PENDING,
            UnifiedTransactionStatus.AWAITING_PAYMENT,
            UnifiedTransactionStatus.PAYMENT_CONFIRMED,
            UnifiedTransactionStatus.FUNDS_HELD,
            UnifiedTransactionStatus.AWAITING_APPROVAL,
            UnifiedTransactionStatus.OTP_PENDING,
            UnifiedTransactionStatus.ADMIN_PENDING,
            UnifiedTransactionStatus.PROCESSING,
            UnifiedTransactionStatus.AWAITING_RESPONSE,
            UnifiedTransactionStatus.RELEASE_PENDING
        ]
        
        for status in terminal_statuses:
            assert LegacyStatusMapper.is_terminal_status(status) is True, \
                f"{status.name} should be terminal"
        
        for status in non_terminal_statuses:
            assert LegacyStatusMapper.is_terminal_status(status) is False, \
                f"{status.name} should not be terminal"
    
    def test_valid_status_transitions(self):
        """Test status transition validation"""
        # Test valid transitions from PENDING
        pending_transitions = LegacyStatusMapper.get_valid_transitions(UnifiedTransactionStatus.PENDING)
        expected_pending_transitions = [
            UnifiedTransactionStatus.AWAITING_PAYMENT,
            UnifiedTransactionStatus.FUNDS_HELD,
            UnifiedTransactionStatus.OTP_PENDING,
            UnifiedTransactionStatus.ADMIN_PENDING,
            UnifiedTransactionStatus.PROCESSING,
            UnifiedTransactionStatus.FAILED,
            UnifiedTransactionStatus.CANCELLED,
            UnifiedTransactionStatus.EXPIRED
        ]
        
        for transition in expected_pending_transitions:
            assert transition in pending_transitions, \
                f"PENDING should allow transition to {transition.name}"
        
        # Test that terminal statuses have no valid transitions
        terminal_statuses = [
            UnifiedTransactionStatus.SUCCESS,
            UnifiedTransactionStatus.FAILED,
            UnifiedTransactionStatus.CANCELLED,
            UnifiedTransactionStatus.EXPIRED
        ]
        
        for terminal_status in terminal_statuses:
            transitions = LegacyStatusMapper.get_valid_transitions(terminal_status)
            assert len(transitions) == 0, f"{terminal_status.name} should have no valid transitions"
    
    def test_mapping_conflicts_analysis(self):
        """Test analysis of many-to-one mapping conflicts"""
        conflicts = LegacyStatusMapper.get_mapping_conflicts()
        
        # We expect some conflicts (multiple legacy statuses mapping to same unified status)
        # This is normal and expected, but should be documented
        
        # Example: Both COMPLETED and SUCCESS in cashout should map to UnifiedTransactionStatus.SUCCESS
        if "cashout" in conflicts:
            # Check if we have expected conflicts
            cashout_conflicts = conflicts["cashout"]
            success_conflict_found = False
            
            for unified_status, legacy_statuses in cashout_conflicts:
                if unified_status == UnifiedTransactionStatus.SUCCESS:
                    success_conflict_found = True
                    assert CashoutStatus.SUCCESS in legacy_statuses
                    assert CashoutStatus.COMPLETED in legacy_statuses
            
            # This conflict is expected and acceptable
            if success_conflict_found:
                assert len(cashout_conflicts) >= 1, "Should have at least the SUCCESS conflict"
        
        # The conflicts should be manageable (not too many)
        total_conflicts = sum(len(system_conflicts) for system_conflicts in conflicts.values())
        assert total_conflicts <= 10, f"Too many mapping conflicts: {total_conflicts}"
    
    def test_transition_compatibility_matrix(self):
        """Test transition compatibility analysis"""
        matrix = LegacyStatusMapper.get_transition_compatibility_matrix()
        
        assert "cashout_transitions" in matrix
        assert "escrow_transitions" in matrix
        assert "exchange_transitions" in matrix
        assert "cross_system_risks" in matrix
        
        # Check that all statuses are analyzed
        cashout_transitions = matrix["cashout_transitions"]
        assert len(cashout_transitions) == 14, "Should analyze all 14 cashout statuses"
        
        escrow_transitions = matrix["escrow_transitions"]
        assert len(escrow_transitions) == 13, "Should analyze all 13 escrow statuses"
        
        exchange_transitions = matrix["exchange_transitions"]
        assert len(exchange_transitions) == 11, "Should analyze all 11 exchange statuses"
        
        # Check structure of transition analysis
        for system_name, transitions in matrix.items():
            if system_name == "cross_system_risks":
                continue
                
            for status_name, analysis in transitions.items():
                assert "maps_to" in analysis
                assert "safe_transition" in analysis
                assert "reverse_options_count" in analysis
                assert "potential_data_loss" in analysis


class TestDualWriteAdapterBasics:
    """Test basic DualWriteAdapter functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = DualWriteConfig(
            mode=DualWriteMode.DUAL_WRITE_LEGACY_PRIMARY,
            strategy=DualWriteStrategy.FAIL_FAST,
            rollback_enabled=True,
            validation_enabled=True
        )
        self.adapter = DualWriteAdapter(self.config)
    
    def test_adapter_initialization(self):
        """Test adapter initializes with correct configuration"""
        assert self.adapter.config.mode == DualWriteMode.DUAL_WRITE_LEGACY_PRIMARY
        assert self.adapter.config.strategy == DualWriteStrategy.FAIL_FAST
        assert self.adapter.config.rollback_enabled is True
        assert self.adapter.config.validation_enabled is True
        assert self.adapter.mapper is not None
    
    def test_operation_id_generation(self):
        """Test unique operation ID generation"""
        id1 = self.adapter._generate_operation_id()
        id2 = self.adapter._generate_operation_id()
        
        assert id1 != id2, "Operation IDs should be unique"
        assert id1.startswith("DW"), "Operation IDs should start with 'DW'"
        assert len(id1) >= 14, "Operation IDs should be sufficiently long"
    
    def test_system_type_detection(self):
        """Test system type detection from transaction type"""
        test_cases = [
            (UnifiedTransactionType.WALLET_CASHOUT, LegacySystemType.CASHOUT),
            (UnifiedTransactionType.ESCROW, LegacySystemType.ESCROW),
            (UnifiedTransactionType.EXCHANGE_SELL_CRYPTO, LegacySystemType.EXCHANGE),
            (UnifiedTransactionType.EXCHANGE_BUY_CRYPTO, LegacySystemType.EXCHANGE),
        ]
        
        for unified_type, expected_system_type in test_cases:
            result = self.adapter._get_system_type_from_transaction_type(unified_type)
            assert result == expected_system_type


class TestDualWriteAdapterIntegration:
    """Test DualWriteAdapter integration scenarios"""
    
    def setup_method(self):
        """Setup test fixtures with mocked database"""
        self.config = DualWriteConfig(
            mode=DualWriteMode.DUAL_WRITE_LEGACY_PRIMARY,
            strategy=DualWriteStrategy.BEST_EFFORT,
            rollback_enabled=True
        )
        self.adapter = DualWriteAdapter(self.config)
        
        # Mock database session
        self.mock_session = Mock(spec=Session)
        self.mock_session.add = Mock()
        self.mock_session.flush = Mock()
        self.mock_session.commit = Mock()
        self.mock_session.rollback = Mock()
    
    @patch('services.dual_write_adapter.managed_session')
    @patch('services.dual_write_adapter.generate_transaction_id')
    def test_create_transaction_dual_write_success(self, mock_gen_id, mock_session):
        """Test successful dual-write transaction creation"""
        # Setup mocks
        mock_gen_id.return_value = "UTX123456789012345"
        mock_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock successful creation
        unified_tx = Mock(spec=UnifiedTransaction)
        unified_tx.transaction_id = "UTX123456789012345"
        unified_tx.amount = 100.0
        unified_tx.user_id = 1
        
        self.mock_session.add.return_value = None
        self.mock_session.flush.return_value = None
        
        with patch.object(self.adapter, '_create_unified_transaction', return_value=unified_tx) as mock_create_unified, \
             patch.object(self.adapter, '_create_legacy_transaction', return_value=Mock()) as mock_create_legacy, \
             patch.object(self.adapter, '_validate_transaction_consistency') as mock_validate:
            
            result = self.adapter.create_transaction(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                user_id=1,
                amount=100.0,
                currency="USD"
            )
            
            # Verify both systems were called
            mock_create_unified.assert_called_once()
            mock_create_legacy.assert_called_once()
            mock_validate.assert_called_once()
            
            # Verify result
            assert result.legacy_success is True
            assert result.unified_success is True
            assert result.overall_success is True
            assert result.has_inconsistency is False
    
    @patch('services.dual_write_adapter.managed_session')
    def test_create_transaction_unified_fails_best_effort(self, mock_session):
        """Test transaction creation when unified fails but legacy succeeds (best effort)"""
        mock_session.return_value.__enter__.return_value = self.mock_session
        
        with patch.object(self.adapter, '_create_unified_transaction', 
                         side_effect=Exception("Unified DB error")) as mock_create_unified, \
             patch.object(self.adapter, '_create_legacy_transaction', return_value=Mock()) as mock_create_legacy:
            
            result = self.adapter.create_transaction(
                transaction_type=UnifiedTransactionType.WALLET_CASHOUT,
                user_id=1,
                amount=100.0,
                currency="USD"
            )
            
            # Verify unified failed but legacy succeeded
            assert result.legacy_success is True
            assert result.unified_success is False
            assert result.overall_success is True  # Best effort allows partial success
            assert result.has_inconsistency is True
            assert result.unified_error is not None
    
    @patch('services.dual_write_adapter.managed_session')
    def test_update_status_dual_write_success(self, mock_session):
        """Test successful dual-write status update"""
        mock_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock finding existing records
        unified_tx = Mock(spec=UnifiedTransaction)
        unified_tx.transaction_id = "UTX123456789012345"
        unified_tx.status = "pending"
        unified_tx.updated_at = datetime.utcnow()
        
        legacy_entity = Mock()
        legacy_entity.status = "pending"
        
        with patch.object(self.adapter, '_find_linked_legacy_entity', return_value=legacy_entity), \
             patch.object(self.adapter, '_detect_legacy_system_type', return_value=LegacySystemType.CASHOUT), \
             patch.object(self.adapter, '_get_legacy_entity_status', return_value=CashoutStatus.PENDING), \
             patch.object(self.adapter, '_update_legacy_entity_status'), \
             patch('services.dual_write_adapter.UnifiedTransactionStatusHistory'), \
             patch.object(self.mock_session, 'query') as mock_query:
            
            mock_query.return_value.filter.return_value.first.return_value = unified_tx
            
            result = self.adapter.update_status(
                entity_id="UTX123456789012345",
                new_status=UnifiedTransactionStatus.PROCESSING,
                reason="Test update"
            )
            
            # Verify successful update
            assert result.legacy_success is True
            assert result.unified_success is True
            assert result.overall_success is True
            assert result.has_inconsistency is False


class TestDualWriteAdapterConsistency:
    """Test consistency checking and repair functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.adapter = DualWriteAdapter()
        self.mock_session = Mock(spec=Session)
    
    @patch('services.dual_write_adapter.managed_session')
    def test_check_consistency_consistent_systems(self, mock_session):
        """Test consistency check when both systems are consistent"""
        mock_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock consistent data
        unified_tx = Mock(spec=UnifiedTransaction)
        unified_tx.transaction_id = "UTX123456789012345"
        unified_tx.status = "processing"
        unified_tx.amount = 100.0
        unified_tx.user_id = 1
        
        legacy_entity = Mock()
        
        with patch.object(self.adapter, '_find_linked_legacy_entity', return_value=legacy_entity), \
             patch.object(self.adapter, '_detect_legacy_system_type', return_value=LegacySystemType.CASHOUT), \
             patch.object(self.adapter, '_get_legacy_entity_status', return_value=CashoutStatus.EXECUTING), \
             patch.object(self.adapter, '_get_legacy_entity_amount', return_value=100.0), \
             patch.object(self.adapter, '_get_legacy_entity_user_id', return_value=1), \
             patch.object(self.mock_session, 'query') as mock_query:
            
            mock_query.return_value.filter.return_value.first.return_value = unified_tx
            
            # CashoutStatus.EXECUTING maps to UnifiedTransactionStatus.PROCESSING
            with patch.object(LegacyStatusMapper, 'map_to_unified', 
                             return_value=UnifiedTransactionStatus.PROCESSING):
                
                report = self.adapter.check_consistency("UTX123456789012345")
                
                assert report["consistent"] is True
                assert len(report["inconsistencies"]) == 0
                assert report["unified_exists"] is True
                assert report["legacy_exists"] is True
    
    @patch('services.dual_write_adapter.managed_session')
    def test_check_consistency_status_mismatch(self, mock_session):
        """Test consistency check when statuses don't match"""
        mock_session.return_value.__enter__.return_value = self.mock_session
        
        # Mock inconsistent data
        unified_tx = Mock(spec=UnifiedTransaction)
        unified_tx.transaction_id = "UTX123456789012345"
        unified_tx.status = "processing"
        unified_tx.amount = 100.0
        unified_tx.user_id = 1
        
        legacy_entity = Mock()
        
        with patch.object(self.adapter, '_find_linked_legacy_entity', return_value=legacy_entity), \
             patch.object(self.adapter, '_detect_legacy_system_type', return_value=LegacySystemType.CASHOUT), \
             patch.object(self.adapter, '_get_legacy_entity_status', return_value=CashoutStatus.PENDING), \
             patch.object(self.adapter, '_get_legacy_entity_amount', return_value=100.0), \
             patch.object(self.adapter, '_get_legacy_entity_user_id', return_value=1), \
             patch.object(self.mock_session, 'query') as mock_query:
            
            mock_query.return_value.filter.return_value.first.return_value = unified_tx
            
            # CashoutStatus.PENDING maps to UnifiedTransactionStatus.PENDING (not PROCESSING)
            with patch.object(LegacyStatusMapper, 'map_to_unified', 
                             return_value=UnifiedTransactionStatus.PENDING):
                
                report = self.adapter.check_consistency("UTX123456789012345")
                
                assert report["consistent"] is False
                assert len(report["inconsistencies"]) == 1
                assert report["inconsistencies"][0]["type"] == "status_mismatch"
                assert report["inconsistencies"][0]["unified_status"] == "processing"
                assert report["inconsistencies"][0]["expected_unified_status"] == "pending"


class TestDualWriteResultAnalysis:
    """Test DualWriteResult analysis and properties"""
    
    def test_dual_write_result_overall_success(self):
        """Test overall success calculation"""
        # Both systems succeed
        result1 = DualWriteResult(legacy_success=True, unified_success=True)
        assert result1.overall_success is True
        
        # One system succeeds  
        result2 = DualWriteResult(legacy_success=True, unified_success=False)
        assert result2.overall_success is True
        
        result3 = DualWriteResult(legacy_success=False, unified_success=True)
        assert result3.overall_success is True
        
        # Both systems fail
        result4 = DualWriteResult(legacy_success=False, unified_success=False)
        assert result4.overall_success is False
    
    def test_dual_write_result_inconsistency_detection(self):
        """Test inconsistency detection"""
        # Consistent results
        result1 = DualWriteResult(legacy_success=True, unified_success=True)
        assert result1.has_inconsistency is False
        
        result2 = DualWriteResult(legacy_success=False, unified_success=False)
        assert result2.has_inconsistency is False
        
        # Inconsistent results
        result3 = DualWriteResult(legacy_success=True, unified_success=False)
        assert result3.has_inconsistency is True
        
        result4 = DualWriteResult(legacy_success=False, unified_success=True)
        assert result4.has_inconsistency is True


class TestMappingEdgeCases:
    """Test edge cases and error scenarios in mapping"""
    
    def test_deprecated_status_handling(self):
        """Test handling of deprecated statuses"""
        # CashoutStatus.COMPLETED is deprecated and should map to SUCCESS
        result = LegacyStatusMapper.map_to_unified(CashoutStatus.COMPLETED, LegacySystemType.CASHOUT)
        assert result == UnifiedTransactionStatus.SUCCESS
        
        # Verify it's still in the mapping
        assert CashoutStatus.COMPLETED in LegacyStatusMapper.CASHOUT_TO_UNIFIED
    
    def test_status_string_conversion(self):
        """Test that status enum values match expected strings"""
        # Verify key status string values are correct
        assert UnifiedTransactionStatus.PENDING.value == "pending"
        assert UnifiedTransactionStatus.OTP_PENDING.value == "otp_pending"
        assert UnifiedTransactionStatus.ADMIN_PENDING.value == "admin_pending"
        assert UnifiedTransactionStatus.SUCCESS.value == "success"
        assert UnifiedTransactionStatus.FAILED.value == "failed"
        
        # Verify legacy status string values
        assert CashoutStatus.PENDING.value == "pending"
        assert EscrowStatus.CREATED.value == "created"
        assert ExchangeStatus.PROCESSING.value == "processing"
    
    def test_mapping_preserves_business_logic(self):
        """Test that mappings preserve important business logic"""
        # OTP should only be required for cashouts
        otp_status = UnifiedTransactionStatus.OTP_PENDING
        
        # Should exist in cashout mappings
        cashout_reverse = LegacyStatusMapper.UNIFIED_TO_CASHOUT.get(otp_status, [])
        assert len(cashout_reverse) > 0, "OTP_PENDING should have cashout reverse mappings"
        
        # Should NOT exist in escrow mappings
        escrow_reverse = LegacyStatusMapper.UNIFIED_TO_ESCROW.get(otp_status, [])
        assert len(escrow_reverse) == 0, "OTP_PENDING should not have escrow reverse mappings"
        
        # Should NOT exist in exchange mappings
        exchange_reverse = LegacyStatusMapper.UNIFIED_TO_EXCHANGE.get(otp_status, [])
        assert len(exchange_reverse) == 0, "OTP_PENDING should not have exchange reverse mappings"
    
    def test_contextual_status_mapping(self):
        """Test that same legacy status can map differently based on context"""
        # PENDING exists in multiple legacy systems but should map consistently
        cashout_pending = LegacyStatusMapper.map_to_unified(CashoutStatus.PENDING, LegacySystemType.CASHOUT)
        
        # All PENDING statuses should map to the same unified status
        assert cashout_pending == UnifiedTransactionStatus.PENDING
        
        # But verify system-specific statuses map appropriately
        escrow_created = LegacyStatusMapper.map_to_unified(EscrowStatus.CREATED, LegacySystemType.ESCROW)
        assert escrow_created == UnifiedTransactionStatus.PENDING  # Different legacy status, same unified result
        
        exchange_created = LegacyStatusMapper.map_to_unified(ExchangeStatus.CREATED, LegacySystemType.EXCHANGE)
        assert exchange_created == UnifiedTransactionStatus.PENDING  # Different legacy status, same unified result


# =============== TEST FIXTURES AND UTILITIES ===============

@pytest.fixture
def sample_unified_transaction():
    """Create sample unified transaction for testing"""
    return UnifiedTransaction(
        transaction_id="UTX123456789012345",
        user_id=1,
        transaction_type="wallet_cashout",
        status="pending",
        amount=100.0,
        currency="USD",
        fee_amount=5.0,
        total_amount=105.0,
        fund_movement_type="hold",
        description="Test cashout transaction",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def dual_write_config():
    """Create test dual-write configuration"""
    return DualWriteConfig(
        mode=DualWriteMode.DUAL_WRITE_LEGACY_PRIMARY,
        strategy=DualWriteStrategy.BEST_EFFORT,
        rollback_enabled=True,
        retry_attempts=3,
        validation_enabled=True,
        audit_logging=True
    )


# =============== INTEGRATION TEST SCENARIOS ===============

class TestFullMigrationScenarios:
    """Test complete migration scenarios"""
    
    def test_phase1_dual_write_legacy_primary(self):
        """Test Phase 1: Dual write with legacy as primary"""
        config = DualWriteConfig(mode=DualWriteMode.DUAL_WRITE_LEGACY_PRIMARY)
        adapter = DualWriteAdapter(config)
        
        # In this phase, we write to both but read from legacy primarily
        assert adapter.config.mode == DualWriteMode.DUAL_WRITE_LEGACY_PRIMARY
    
    def test_phase2_dual_write_unified_primary(self):
        """Test Phase 2: Dual write with unified as primary"""
        config = DualWriteConfig(mode=DualWriteMode.DUAL_WRITE_UNIFIED_PRIMARY)
        adapter = DualWriteAdapter(config)
        
        # In this phase, we write to both but read from unified primarily
        assert adapter.config.mode == DualWriteMode.DUAL_WRITE_UNIFIED_PRIMARY
    
    def test_phase3_unified_only(self):
        """Test Phase 3: Unified system only"""
        config = DualWriteConfig(mode=DualWriteMode.UNIFIED_ONLY)
        adapter = DualWriteAdapter(config)
        
        # In this phase, we only write to unified system
        assert adapter.config.mode == DualWriteMode.UNIFIED_ONLY


if __name__ == "__main__":
    # Run basic validation
    print("Running basic mapping validation...")
    
    # Test mapping completeness
    mapper = LegacyStatusMapper()
    report = mapper.validate_mapping_completeness()
    
    print(f"✅ Total legacy statuses: {report['total_legacy_statuses']}")
    print(f"✅ Mapped statuses: {report['mapped_statuses']}")
    print(f"✅ Validation passed: {report['validation_passed']}")
    
    if not report['validation_passed']:
        print(f"❌ Unmapped statuses: {report['unmapped_statuses']}")
    
    # Test conflict analysis
    conflicts = mapper.get_mapping_conflicts()
    print(f"✅ Mapping conflicts found: {len(conflicts)} systems have conflicts")
    
    for system, system_conflicts in conflicts.items():
        print(f"  {system}: {len(system_conflicts)} conflicts")
    
    print("\n🎯 Legacy Status Mapping System validation complete!")
    print("📋 Run with pytest for full test suite: pytest tests/test_legacy_status_mapping.py -v")
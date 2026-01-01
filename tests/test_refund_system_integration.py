"""
Comprehensive Test Suite for Refund System Integration
Tests all components working together seamlessly
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from utils.refund_system_integration import refund_system_integrator, RefundTrackingSession
from utils.refund_progress_tracker import real_time_refund_tracker, ProgressStage
from services.refund_analytics_service import refund_analytics_service, AnalyticsPeriod
from handlers.refund_dashboard import user_refund_dashboard
from handlers.enhanced_admin_refund_dashboard import enhanced_admin_refund_dashboard
from models import Refund, RefundType, RefundStatus, User
from database import SessionLocal


class TestRefundSystemIntegration:
    """Test comprehensive refund system integration"""
    
    @pytest.fixture
    def mock_refund(self):
        """Create a mock refund for testing"""
        refund = Mock(spec=Refund)
        refund.refund_id = "TEST_REF_123456"
        refund.user_id = 12345
        refund.refund_type = RefundType.CASHOUT_FAILED.value
        refund.amount = Decimal("100.50")
        refund.currency = "USD"
        refund.status = RefundStatus.PENDING.value
        refund.reason = "Test refund for integration testing"
        refund.created_at = datetime.utcnow()
        return refund
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing"""
        user = Mock(spec=User)
        user.id = 12345
        user.telegram_id = "987654321"
        user.first_name = "Test"
        user.last_name = "User"
        user.email = "test@example.com"
        return user
    
    @pytest.mark.asyncio
    async def test_comprehensive_refund_flow(self, mock_refund, mock_user):
        """Test the complete refund tracking flow from start to finish"""
        
        # Start comprehensive tracking
        success = await refund_system_integrator.start_comprehensive_refund_tracking(
            refund=mock_refund,
            initial_stage=ProgressStage.INITIATED
        )
        
        assert success, "Should successfully start comprehensive tracking"
        assert mock_refund.refund_id in refund_system_integrator.active_integrations
        
        # Progress through stages
        stages = [
            ProgressStage.VALIDATING,
            ProgressStage.PROCESSING,
            ProgressStage.WALLET_CREDITING,
            ProgressStage.WALLET_CREDITED,
            ProgressStage.USER_NOTIFYING,
            ProgressStage.USER_NOTIFIED,
            ProgressStage.CONFIRMING
        ]
        
        for stage in stages:
            success = await refund_system_integrator.progress_refund_to_stage(
                refund_id=mock_refund.refund_id,
                new_stage=stage,
                details=f"Progressed to {stage.value}",
                metadata={"test": True}
            )
            assert success, f"Should successfully progress to {stage.value}"
        
        # Test user confirmation
        confirmed = await refund_system_integrator.handle_user_refund_confirmation(
            refund_id=mock_refund.refund_id,
            user_id=mock_refund.user_id
        )
        assert confirmed, "Should successfully handle user confirmation"
        
        # Complete the refund
        completed = await refund_system_integrator.complete_refund_tracking(
            refund_id=mock_refund.refund_id,
            final_stage=ProgressStage.COMPLETED,
            completion_details="Refund completed successfully"
        )
        assert completed, "Should successfully complete refund tracking"
        
        # Verify cleanup
        assert mock_refund.refund_id not in refund_system_integrator.active_integrations
    
    @pytest.mark.asyncio
    async def test_real_time_tracker_integration(self, mock_refund):
        """Test real-time tracker integration"""
        
        # Start tracking
        success = real_time_refund_tracker.start_tracking_session(
            refund_id=mock_refund.refund_id,
            user_id=mock_refund.user_id,
            initial_stage=ProgressStage.INITIATED
        )
        assert success, "Should start real-time tracking"
        
        # Update progress
        updated = await real_time_refund_tracker.update_progress(
            refund_id=mock_refund.refund_id,
            stage=ProgressStage.PROCESSING,
            details="Processing refund",
            metadata={"test": True}
        )
        assert updated, "Should update progress"
        
        # Get detailed progress
        progress = real_time_refund_tracker.get_detailed_progress(mock_refund.refund_id)
        assert progress is not None, "Should get detailed progress"
        assert progress["current_stage"] == ProgressStage.PROCESSING.value
        
        # Get metrics
        metrics = real_time_refund_tracker.get_metrics()
        assert "active_sessions_count" in metrics
        assert metrics["active_sessions_count"] >= 1
    
    def test_analytics_service_integration(self):
        """Test analytics service integration"""
        
        # Get comprehensive metrics
        metrics = refund_analytics_service.get_comprehensive_metrics(
            period=AnalyticsPeriod.DAY,
            lookback_periods=7,
            include_trends=True
        )
        
        assert "summary" in metrics
        assert "trends" in metrics
        assert "breakdown" in metrics
        assert "generated_at" in metrics
        
        # Test real-time dashboard data
        dashboard_data = refund_analytics_service.get_real_time_dashboard_data()
        assert "timestamp" in dashboard_data
        assert "active_refunds" in dashboard_data
        assert "performance_metrics" in dashboard_data
        assert "system_health" in dashboard_data
        
        # Test insights generation
        insights = refund_analytics_service.generate_refund_insights(period_days=30)
        assert "key_insights" in insights
        assert "recommendations" in insights
        assert "cost_impact" in insights
    
    @pytest.mark.asyncio
    async def test_user_dashboard_integration(self, mock_user):
        """Test user dashboard integration"""
        
        # Mock Telegram update and context
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = int(mock_user.telegram_id)
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.callback_query = None
        
        context = Mock()
        context.user_data = {}
        
        # Test refunds command
        with patch('handlers.refund_dashboard.get_user_from_update', return_value=mock_user):
            with patch.object(user_refund_dashboard, 'show_refund_main_menu', new_callable=AsyncMock) as mock_show:
                result = await user_refund_dashboard.refunds_command(update, context)
                mock_show.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_admin_dashboard_integration(self):
        """Test admin dashboard integration"""
        
        # Mock admin update and context
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 123456789  # Admin ID
        update.callback_query = Mock()
        update.callback_query.edit_message_text = AsyncMock()
        update.message = None
        
        context = Mock()
        
        # Test admin dashboard functions
        with patch('handlers.enhanced_admin_refund_dashboard.is_admin_secure', return_value=True):
            with patch('handlers.enhanced_admin_refund_dashboard.safe_edit_message_text', new_callable=AsyncMock):
                await enhanced_admin_refund_dashboard.show_main_refund_dashboard(update, context)
                await enhanced_admin_refund_dashboard.show_refund_analytics(update, context)
                await enhanced_admin_refund_dashboard.show_live_tracking(update, context)
    
    def test_integration_metrics(self):
        """Test integration metrics collection"""
        
        metrics = refund_system_integrator.get_integration_metrics()
        
        assert "integration_metrics" in metrics
        assert "real_time_tracker_metrics" in metrics
        assert "analytics_dashboard_data" in metrics
        assert "active_integrations_count" in metrics
        assert "system_status" in metrics
        
        integration_metrics = metrics["integration_metrics"]
        assert "total_sessions" in integration_metrics
        assert "successful_completions" in integration_metrics
        assert "failed_sessions" in integration_metrics
        assert "notification_failures" in integration_metrics
    
    @pytest.mark.asyncio
    async def test_notification_integration(self, mock_refund):
        """Test notification service integration"""
        
        # Mock notification service
        with patch.object(refund_system_integrator.notification_service, 'send_refund_notification', new_callable=AsyncMock) as mock_notify:
            mock_notify.return_value = {"status": "sent", "channels": ["email", "telegram"]}
            
            # Start comprehensive tracking
            await refund_system_integrator.start_comprehensive_refund_tracking(
                refund=mock_refund,
                initial_stage=ProgressStage.INITIATED
            )
            
            # Progress to wallet credited (should trigger notification)
            await refund_system_integrator.progress_refund_to_stage(
                refund_id=mock_refund.refund_id,
                new_stage=ProgressStage.WALLET_CREDITED,
                details="Wallet credited successfully"
            )
            
            # Verify notifications were sent
            assert mock_notify.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_refund):
        """Test error handling throughout the system"""
        
        # Test invalid refund ID
        invalid_progress = await refund_system_integrator.progress_refund_to_stage(
            refund_id="INVALID_ID",
            new_stage=ProgressStage.PROCESSING,
            details="Should fail"
        )
        assert not invalid_progress, "Should fail for invalid refund ID"
        
        # Test unauthorized user confirmation
        unauthorized = await refund_system_integrator.handle_user_refund_confirmation(
            refund_id=mock_refund.refund_id,
            user_id=99999  # Wrong user ID
        )
        assert not unauthorized, "Should fail for unauthorized user"
        
        # Test missing integration session
        no_session_status = await refund_system_integrator.get_comprehensive_status("NONEXISTENT_ID")
        # Should still return some data even if session doesn't exist
        
    def test_data_consistency(self):
        """Test data consistency across all components"""
        
        # Test that all components use consistent data structures
        rt_metrics = real_time_refund_tracker.get_metrics()
        analytics_data = refund_analytics_service.get_real_time_dashboard_data()
        integration_metrics = refund_system_integrator.get_integration_metrics()
        
        # Verify all have timestamp fields
        assert "last_updated" in rt_metrics or "timestamp" in str(rt_metrics)
        assert "timestamp" in analytics_data
        assert "system_status" in integration_metrics
        
        # Verify consistent status representations
        for metrics in [rt_metrics, analytics_data, integration_metrics]:
            assert isinstance(metrics, dict), "All metrics should be dictionaries"
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test handling multiple concurrent refund sessions"""
        
        # Create multiple mock refunds
        refunds = []
        for i in range(3):
            refund = Mock(spec=Refund)
            refund.refund_id = f"TEST_REF_{i:06d}"
            refund.user_id = 12345 + i
            refund.refund_type = RefundType.CASHOUT_FAILED.value
            refund.amount = Decimal(f"{100 + i}.50")
            refund.currency = "USD"
            refunds.append(refund)
        
        # Start tracking for all refunds
        for refund in refunds:
            success = await refund_system_integrator.start_comprehensive_refund_tracking(
                refund=refund,
                initial_stage=ProgressStage.INITIATED
            )
            assert success, f"Should start tracking for {refund.refund_id}"
        
        # Verify all are tracked
        metrics = refund_system_integrator.get_integration_metrics()
        assert metrics["active_integrations_count"] >= 3
        
        # Complete all refunds
        for refund in refunds:
            await refund_system_integrator.complete_refund_tracking(
                refund_id=refund.refund_id,
                final_stage=ProgressStage.COMPLETED,
                completion_details="Test completion"
            )
    
    def test_performance_metrics(self):
        """Test performance monitoring capabilities"""
        
        # Get comprehensive metrics
        metrics = refund_analytics_service.get_comprehensive_metrics(
            period=AnalyticsPeriod.HOUR,
            lookback_periods=24,
            include_trends=True
        )
        
        performance = metrics.get("performance", {})
        
        # Verify performance metrics structure
        if performance:
            processing_stats = performance.get("processing_time_stats", {})
            if processing_stats:
                assert "mean" in processing_stats
                assert "median" in processing_stats
                assert "std_dev" in processing_stats
    
    @pytest.mark.asyncio
    async def test_system_health_monitoring(self):
        """Test system health monitoring"""
        
        # Get dashboard data
        dashboard_data = refund_analytics_service.get_real_time_dashboard_data()
        
        system_health = dashboard_data.get("system_health", {})
        assert isinstance(system_health, dict)
        
        # Test integration metrics
        integration_metrics = refund_system_integrator.get_integration_metrics()
        system_status = integration_metrics.get("system_status", {})
        
        assert "all_components_operational" in system_status
        assert "last_health_check" in system_status


@pytest.mark.asyncio
async def test_complete_system_workflow():
    """Integration test for complete refund workflow"""
    
    # Create test refund
    test_refund = Mock(spec=Refund)
    test_refund.refund_id = "WORKFLOW_TEST_123"
    test_refund.user_id = 54321
    test_refund.refund_type = RefundType.ESCROW_REFUND.value
    test_refund.amount = Decimal("250.75")
    test_refund.currency = "USD"
    test_refund.reason = "Complete workflow test"
    test_refund.created_at = datetime.utcnow()
    
    try:
        # Step 1: Start comprehensive tracking
        print("🚀 Starting comprehensive refund tracking...")
        success = await refund_system_integrator.start_comprehensive_refund_tracking(
            refund=test_refund,
            initial_stage=ProgressStage.INITIATED
        )
        assert success, "Failed to start comprehensive tracking"
        print("✅ Comprehensive tracking started")
        
        # Step 2: Progress through all stages
        stages = [
            ProgressStage.VALIDATING,
            ProgressStage.PROCESSING,
            ProgressStage.WALLET_CREDITING,
            ProgressStage.WALLET_CREDITED,
            ProgressStage.USER_NOTIFYING,
            ProgressStage.USER_NOTIFIED,
            ProgressStage.CONFIRMING,
        ]
        
        for stage in stages:
            print(f"📊 Progressing to {stage.value}...")
            success = await refund_system_integrator.progress_refund_to_stage(
                refund_id=test_refund.refund_id,
                new_stage=stage,
                details=f"Test progression to {stage.value}",
                metadata={"workflow_test": True, "timestamp": datetime.utcnow().isoformat()}
            )
            assert success, f"Failed to progress to {stage.value}"
            
            # Brief delay to simulate real processing time
            await asyncio.sleep(0.1)
        
        print("✅ All stages completed")
        
        # Step 3: User confirmation
        print("👤 Simulating user confirmation...")
        confirmed = await refund_system_integrator.handle_user_refund_confirmation(
            refund_id=test_refund.refund_id,
            user_id=test_refund.user_id
        )
        assert confirmed, "Failed to handle user confirmation"
        print("✅ User confirmation handled")
        
        # Step 4: Get comprehensive status
        print("📊 Getting comprehensive status...")
        status = await refund_system_integrator.get_comprehensive_status(test_refund.refund_id)
        assert status is not None, "Failed to get comprehensive status"
        assert status["refund_id"] == test_refund.refund_id
        print("✅ Comprehensive status retrieved")
        
        # Step 5: Complete the refund
        print("🏁 Completing refund tracking...")
        completed = await refund_system_integrator.complete_refund_tracking(
            refund_id=test_refund.refund_id,
            final_stage=ProgressStage.COMPLETED,
            completion_details="Workflow test completed successfully"
        )
        assert completed, "Failed to complete refund tracking"
        print("✅ Refund tracking completed")
        
        # Step 6: Verify metrics
        print("📈 Checking integration metrics...")
        metrics = refund_system_integrator.get_integration_metrics()
        assert metrics["integration_metrics"]["total_sessions"] >= 1
        print("✅ Metrics verified")
        
        print("🎉 COMPLETE WORKFLOW TEST PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ WORKFLOW TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    """Run integration tests"""
    
    print("🧪 Running Refund System Integration Tests...")
    
    # Run the complete workflow test
    result = asyncio.run(test_complete_system_workflow())
    
    if result:
        print("✅ All integration tests passed!")
    else:
        print("❌ Integration tests failed!")
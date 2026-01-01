"""
ARCHITECT'S VERIFICATION TESTS - Database Infrastructure Reliability
Tests to verify PRIORITY 1 and PRIORITY 2 fixes work correctly

This test module provides concrete verification that:
1. PRIORITY 1: Engine split determinism is eliminated with per-test isolation
2. PRIORITY 2: Foreign key enforcement works correctly across sync/async engines

These tests must pass to prove the architect's requirements are met.
"""

import pytest
import asyncio
import logging
from sqlalchemy import text, select, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.exc import IntegrityError
from models import Base, User, Wallet
from database import SessionLocal, managed_session

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Test base for verification tables"""
    pass


class TestParent(Base):
    """Test table for foreign key enforcement verification"""
    __tablename__ = "test_parents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50))


class TestChild(Base):
    """Test table with foreign key to TestParent"""
    __tablename__ = "test_children"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_parents.id"))
    name: Mapped[str] = mapped_column(String(50))


@pytest.mark.infrastructure
class TestDatabaseInfrastructureVerification:
    """ARCHITECT'S VERIFICATION TESTS for database infrastructure reliability"""
    
    @pytest.mark.asyncio
    async def test_priority_1_cross_session_visibility(
        self,
        test_db_session,
        patched_services
    ):
        """
        PRIORITY 1 VERIFICATION: Cross-session data visibility sanity test
        
        This test verifies that rows inserted via fixture session are visible 
        via SessionLocal in handler calls, proving engine split determinism is eliminated.
        """
        logger.info("🧪 PRIORITY 1 VERIFICATION: Testing cross-session visibility")
        
        # Step 1: Insert data via test fixture session
        test_user = User(
            telegram_id=999888777,
            username="cross_session_test_user",
            phone_number="+1234567890",
            first_name="Cross",
            last_name="Session"
        )
        test_db_session.add(test_user)
        test_db_session.commit()
        
        # Verify insertion via fixture session
        fixture_user = test_db_session.query(User).filter_by(telegram_id=999888777).first()
        assert fixture_user is not None, "User not found via fixture session"
        assert fixture_user.username == "cross_session_test_user"
        logger.info(f"✅ Step 1: User inserted via fixture session: {fixture_user.id}")
        
        # Step 2: Verify visibility via SessionLocal (what handlers use)
        session_local_user = None
        try:
            with SessionLocal() as session:
                session_local_user = session.query(User).filter_by(telegram_id=999888777).first()
        except Exception as e:
            pytest.fail(f"SessionLocal query failed: {e}")
        
        # CRITICAL ASSERTION: Data must be visible across sessions
        assert session_local_user is not None, "PRIORITY 1 FAIL: User not visible via SessionLocal"
        assert session_local_user.username == "cross_session_test_user"
        assert session_local_user.id == fixture_user.id
        logger.info(f"✅ Step 2: User visible via SessionLocal: {session_local_user.id}")
        
        # Step 3: Test async session visibility as well
        async_user = None
        try:
            async with managed_session() as async_session:
                result = await async_session.execute(
                    select(User).where(User.telegram_id == 999888777)
                )
                async_user = result.scalar_one_or_none()
        except Exception as e:
            pytest.fail(f"Async managed_session query failed: {e}")
            
        assert async_user is not None, "PRIORITY 1 FAIL: User not visible via async managed_session"
        assert async_user.username == "cross_session_test_user"
        assert async_user.id == fixture_user.id
        logger.info(f"✅ Step 3: User visible via managed_session: {async_user.id}")
        
        logger.info("🏆 PRIORITY 1 VERIFICATION: PASSED - Cross-session visibility confirmed")
    
    @pytest.mark.asyncio
    async def test_priority_2_foreign_key_enforcement_sync(
        self,
        test_db_session,
        patched_services
    ):
        """
        PRIORITY 2 VERIFICATION: Foreign key enforcement in sync engine
        
        This test verifies that PRAGMA foreign_keys=ON is working correctly
        by testing constraint violations are caught.
        """
        logger.info("🧪 PRIORITY 2 VERIFICATION: Testing sync foreign key enforcement")
        
        # Step 1: Verify PRAGMA foreign_keys is enabled
        pragma_result = test_db_session.execute(text("PRAGMA foreign_keys")).fetchone()
        assert pragma_result is not None, "Could not query PRAGMA foreign_keys"
        assert pragma_result[0] == 1, f"PRIORITY 2 FAIL: PRAGMA foreign_keys = {pragma_result[0]}, expected 1"
        logger.info(f"✅ Step 1: PRAGMA foreign_keys = {pragma_result[0]} (enabled)")
        
        # Step 2: Create test tables and insert valid parent
        Base.metadata.create_all(test_db_session.bind)
        
        parent = TestParent(id=1, name="Test Parent")
        test_db_session.add(parent)
        test_db_session.commit()
        logger.info("✅ Step 2: Test tables created and parent inserted")
        
        # Step 3: Test valid foreign key relationship works
        valid_child = TestChild(id=1, parent_id=1, name="Valid Child")
        test_db_session.add(valid_child)
        test_db_session.commit()  # Should succeed
        logger.info("✅ Step 3: Valid foreign key relationship works")
        
        # Step 4: Test foreign key constraint violation is caught
        invalid_child = TestChild(id=2, parent_id=999, name="Invalid Child")  # parent_id=999 doesn't exist
        test_db_session.add(invalid_child)
        
        constraint_violation_caught = False
        try:
            test_db_session.commit()
        except IntegrityError as e:
            constraint_violation_caught = True
            test_db_session.rollback()
            logger.info(f"✅ Step 4: Foreign key violation caught: {str(e)[:100]}...")
        
        assert constraint_violation_caught, "PRIORITY 2 FAIL: Foreign key constraint violation not caught"
        
        logger.info("🏆 PRIORITY 2 VERIFICATION: PASSED - Sync foreign key enforcement confirmed")
    
    @pytest.mark.asyncio 
    async def test_priority_2_foreign_key_enforcement_async(
        self,
        test_db_session,
        patched_services
    ):
        """
        PRIORITY 2 VERIFICATION: Foreign key enforcement in async engine
        
        This test verifies that PRAGMA foreign_keys=ON is working correctly
        in async engines as well.
        """
        logger.info("🧪 PRIORITY 2 VERIFICATION: Testing async foreign key enforcement")
        
        # Step 1: Verify PRAGMA foreign_keys is enabled in async session
        async with managed_session() as async_session:
            pragma_result = await async_session.execute(text("PRAGMA foreign_keys"))
            pragma_value = pragma_result.fetchone()
            assert pragma_value is not None, "Could not query PRAGMA foreign_keys in async"
            assert pragma_value[0] == 1, f"PRIORITY 2 FAIL: Async PRAGMA foreign_keys = {pragma_value[0]}, expected 1"
            logger.info(f"✅ Step 1: Async PRAGMA foreign_keys = {pragma_value[0]} (enabled)")
        
        # Step 2: Create test tables via async engine  
        async with managed_session() as async_session:
            await async_session.run_sync(Base.metadata.create_all)
            
            # Insert parent
            parent = TestParent(id=10, name="Async Test Parent")
            async_session.add(parent)
            await async_session.commit()
            logger.info("✅ Step 2: Async test tables created and parent inserted")
        
        # Step 3: Test valid foreign key relationship works in async
        async with managed_session() as async_session:
            valid_child = TestChild(id=10, parent_id=10, name="Valid Async Child")
            async_session.add(valid_child)
            await async_session.commit()  # Should succeed
            logger.info("✅ Step 3: Valid async foreign key relationship works")
        
        # Step 4: Test foreign key constraint violation is caught in async
        async_constraint_violation_caught = False
        try:
            async with managed_session() as async_session:
                invalid_child = TestChild(id=11, parent_id=888, name="Invalid Async Child")
                async_session.add(invalid_child)
                await async_session.commit()
        except IntegrityError as e:
            async_constraint_violation_caught = True
            logger.info(f"✅ Step 4: Async foreign key violation caught: {str(e)[:100]}...")
        
        assert async_constraint_violation_caught, "PRIORITY 2 FAIL: Async foreign key constraint violation not caught"
        
        logger.info("🏆 PRIORITY 2 VERIFICATION: PASSED - Async foreign key enforcement confirmed")
    
    def test_priority_1_and_2_integration_verification(
        self,
        test_db_session,
        patched_services
    ):
        """
        INTEGRATION VERIFICATION: Both PRIORITY 1 and 2 working together
        
        This test verifies that per-test isolation and foreign key enforcement
        work correctly together.
        """
        logger.info("🧪 INTEGRATION VERIFICATION: Testing PRIORITY 1 + 2 together")
        
        # Verify foreign keys are enabled
        pragma_result = test_db_session.execute(text("PRAGMA foreign_keys")).fetchone()
        assert pragma_result[0] == 1, "Foreign keys not enabled"
        
        # Test that we can create realistic relationships with User/Wallet models
        test_user = User(
            telegram_id=555444333,
            username="integration_test_user",
            phone_number="+1234567891"
        )
        test_db_session.add(test_user)
        test_db_session.commit()
        
        # Create wallet linked to user (tests foreign key relationship)
        test_wallet = Wallet(user_id=test_user.id)
        test_db_session.add(test_wallet)
        test_db_session.commit()  # Should succeed due to valid foreign key
        
        # Verify via SessionLocal (tests cross-session visibility)
        with SessionLocal() as session:
            found_user = session.query(User).filter_by(telegram_id=555444333).first()
            assert found_user is not None
            
            found_wallet = session.query(Wallet).filter_by(user_id=found_user.id).first()
            assert found_wallet is not None
            assert found_wallet.user_id == found_user.id
        
        logger.info("🏆 INTEGRATION VERIFICATION: PASSED - PRIORITY 1 + 2 work together")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""User Flow Analytics Integration for Tracking Stuck Points"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from telegram import Update
from telegram.ext import ContextTypes
from database import SessionLocal

logger = logging.getLogger(__name__)

# Import database models from main models.py to avoid duplicates
from models import UserFlowEvent

# Export functions for easier imports - see convenience functions at end of file


class EventType(Enum):
    """Types of trackable events"""

    FLOW_START = "flow_start"
    STEP_ENTER = "step_enter"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"
    FLOW_COMPLETE = "flow_complete"
    FLOW_ABANDON = "flow_abandon"
    USER_STUCK = "user_stuck"
    NAVIGATION_FALLBACK = "navigation_fallback"
    TIMEOUT = "timeout"
    ERROR_RECOVERY = "error_recovery"


class FlowName(Enum):
    """Trackable user flows"""

    ESCROW_CREATION = "escrow_creation"
    WALLET_OPERATION = "wallet_operation"
    CASHOUT = "cashout"
    SETTINGS_MANAGEMENT = "settings_management"
    EMAIL_VERIFICATION = "email_verification"
    DIRECT_EXCHANGE = "direct_exchange"
    AUTO_CASHOUT_SETUP = "auto_cashout_setup"
    ONBOARDING = "onboarding"


@dataclass
class FlowStep:
    """Represents a step in a user flow"""

    name: str
    flow: FlowName
    expected_duration: timedelta = timedelta(minutes=2)
    max_duration: timedelta = timedelta(minutes=10)
    required_data: List[str] = field(default_factory=list)


class FlowAnalytics:
    """Main analytics tracking class"""

    # Track active user sessions
    _active_sessions: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def generate_session_id(cls, user_id: int, flow: FlowName) -> str:
        """Generate unique session ID for tracking"""
        timestamp = int(datetime.now().timestamp())
        return f"{flow.value}_{user_id}_{timestamp}"

    @classmethod
    def start_flow(
        cls,
        user_id: int,
        flow: FlowName,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None,
    ) -> str:
        """
        Start tracking a new user flow

        Args:
            user_id: Telegram user ID
            flow: Flow being started
            context: Bot context for additional data

        Returns:
            Session ID for tracking
        """
        session_id = cls.generate_session_id(user_id, flow)

        # Store session data
        cls._active_sessions[user_id] = {
            "session_id": session_id,
            "flow": flow,
            "start_time": datetime.now(),
            "current_step": None,
            "step_history": [],
            "context_snapshot": cls._capture_context_snapshot(context),
        }

        # Log flow start event
        cls._log_event(
            user_id=user_id,
            session_id=session_id,
            event_type=EventType.FLOW_START,
            event_name=f"start_{flow.value}",
            flow_name=flow.value,
            step_name="flow_start",
        )

        logger.info(
            f"Started flow tracking: user {user_id}, flow {flow.value}, session {session_id}"
        )
        return session_id

    @classmethod
    def track_step(
        cls,
        user_id: int,
        step: FlowStep,
        event_type: EventType,
        success: bool = True,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track a step in the user flow

        Args:
            user_id: Telegram user ID
            step: Step being tracked
            event_type: Type of event
            success: Whether step was successful
            error_message: Error message if failed
            additional_data: Additional tracking data
        """
        session = cls._active_sessions.get(user_id)
        if not session:
            logger.warning(
                f"No active session for user {user_id} when tracking step {step.name}"
            )
            # Start a new session
            session_id = cls.start_flow(user_id, step.flow)
            session = cls._active_sessions[user_id]

        session_id = session["session_id"]
        previous_step = session.get("current_step")

        # Calculate completion time if completing a step
        completion_time = None
        if event_type == EventType.STEP_COMPLETE and previous_step:
            step_start = session.get("step_start_time")
            if step_start:
                completion_time = (datetime.now() - step_start).total_seconds()

        # Update session
        if event_type == EventType.STEP_ENTER:
            session["current_step"] = step.name
            session["step_start_time"] = datetime.now()

        session["step_history"].append(
            {
                "step": step.name,
                "event_type": event_type.value,
                "timestamp": datetime.now(),
                "success": success,
            }
        )

        # Log event
        cls._log_event(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            event_name=f"{event_type.value}_{step.name}",
            flow_name=step.flow.value,
            step_name=step.name,
            previous_step=previous_step or "unknown_step",
            success=success,
            error_message=error_message,
            completion_time=completion_time or 0.0,
            event_data=additional_data,
        )

        # Check for stuck patterns
        if event_type == EventType.STEP_ERROR:
            cls._check_stuck_pattern(user_id, step)

    @classmethod
    def complete_flow(cls, user_id: int, flow: FlowName, success: bool = True) -> None:
        """
        Mark a flow as completed

        Args:
            user_id: Telegram user ID
            flow: Flow being completed
            success: Whether flow completed successfully
        """
        session = cls._active_sessions.get(user_id)
        if not session:
            logger.warning(
                f"No active session for user {user_id} when completing flow {flow.value}"
            )
            return

        session_id = session["session_id"]

        # Calculate total flow time
        start_time = session["start_time"]
        total_time = (datetime.now() - start_time).total_seconds()

        # Log completion event
        event_type = EventType.FLOW_COMPLETE if success else EventType.FLOW_ABANDON
        cls._log_event(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            event_name=f"{event_type.value}_{flow.value}",
            flow_name=flow.value,
            completion_time=total_time,
        )

        # Clean up session
        cls._active_sessions.pop(user_id, None)

        logger.info(
            f"Completed flow tracking: user {user_id}, flow {flow.value}, success {success}, time {total_time:.2f}s"
        )

    @classmethod
    def track_stuck_user(
        cls, user_id: int, context: str, recovery_action: Optional[str] = None
    ) -> None:
        """
        Track when a user gets stuck

        Args:
            user_id: Telegram user ID
            context: Context where user got stuck
            recovery_action: Action taken to recover
        """
        session = cls._active_sessions.get(user_id, {})
        session_id = session.get("session_id", "unknown")

        cls._log_event(
            user_id=user_id,
            session_id=session_id,
            event_type=EventType.USER_STUCK,
            event_name=f"stuck_{context}",
            flow_name=(
                session.get("flow", {}).value if session.get("flow") else "unknown"
            ),
            step_name=session.get("current_step") or "unknown_step",
            event_data={"context": context, "recovery_action": recovery_action},
        )

        logger.warning(
            f"User {user_id} stuck in {context}, recovery: {recovery_action}"
        )

    @classmethod
    def track_navigation_fallback(
        cls, user_id: int, original_action: str, fallback_action: str
    ) -> None:
        """
        Track navigation fallback usage

        Args:
            user_id: Telegram user ID
            original_action: What user tried to do
            fallback_action: What system did instead
        """
        session = cls._active_sessions.get(user_id, {})
        session_id = session.get("session_id", "unknown")

        cls._log_event(
            user_id=user_id,
            session_id=session_id,
            event_type=EventType.NAVIGATION_FALLBACK,
            event_name="navigation_fallback",
            flow_name=(
                session.get("flow", {}).value if session.get("flow") else "unknown"
            ),
            step_name=session.get("current_step") or "unknown_step",
            event_data={
                "original_action": original_action,
                "fallback_action": fallback_action,
            },
        )

    @classmethod
    def _log_event(
        cls,
        user_id: int,
        session_id: str,
        event_type: EventType,
        event_name: str,
        flow_name: str,
        step_name: Optional[str] = None,
        previous_step: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        completion_time: Optional[float] = None,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log event to database"""
        session_db = None
        try:
            session_db = SessionLocal()
            
            # Convert telegram_id to database user_id for foreign key constraint
            from models import User
            user = session_db.query(User).filter_by(telegram_id=str(user_id)).first()
            if not user:
                logger.warning(f"User with telegram_id {user_id} not found for analytics")
                return
            
            database_user_id = user.id

            # Build context data with available information
            context_data = {}
            if previous_step:
                context_data["previous_step"] = previous_step
            if success is not None:
                context_data["success"] = success
            if error_message:
                context_data["error_message"] = error_message
            if event_data:
                context_data.update(event_data)

            event = UserFlowEvent(
                user_id=database_user_id,
                session_id=session_id,
                event_type=event_type.value,
                flow_name=flow_name,
                step_name=step_name,
                context_data=context_data if context_data else None,
                user_agent=None,  # Fix: Add user_agent field to prevent column mismatch
                step_duration_ms=(
                    int(completion_time * 1000) if completion_time else None
                ),
            )

            session_db.add(event)
            session_db.commit()

        except Exception as e:
            logger.error(f"Failed to log analytics event: {e}")
        finally:
            try:
                if session_db is not None:
                    session_db.close()
            except Exception:
                pass  # Ignore cleanup errors

    @classmethod
    def _capture_context_snapshot(
        cls, context: Optional[ContextTypes.DEFAULT_TYPE]
    ) -> Dict[str, Any]:
        """Capture relevant context data for analytics"""
        if not context or not context.user_data:
            return {}

        # Capture safe, non-sensitive data
        safe_keys = ["current_step", "flow_name", "start_time", "user_preferences"]
        snapshot = {}

        for key in safe_keys:
            if key in context.user_data:
                try:
                    # Ensure data is serializable
                    value = context.user_data[key]
                    if isinstance(value, (str, int, float, bool, list, dict)):
                        snapshot[key] = value
                except Exception:
                    continue

        return snapshot

    @classmethod
    def _check_stuck_pattern(cls, user_id: int, step: FlowStep) -> None:
        """Check if user is showing stuck patterns"""
        session = cls._active_sessions.get(user_id)
        if not session:
            return

        history = session.get("step_history", [])

        # Check for repeated errors on same step
        recent_errors = [
            h
            for h in history[-5:]  # Last 5 events
            if h["step"] == step.name and not h["success"]
        ]

        if len(recent_errors) >= 3:
            cls.track_stuck_user(
                user_id, f"repeated_errors_{step.name}", "error_pattern_detected"
            )

        # Check for excessive time on step
        step_start = session.get("step_start_time")
        if step_start:
            time_on_step = datetime.now() - step_start
            if time_on_step > step.max_duration:
                cls.track_stuck_user(user_id, f"timeout_{step.name}", "step_timeout")


# Convenience functions for easy integration
def track_flow_start(
    user_id: int, flow: FlowName, context: Optional[ContextTypes.DEFAULT_TYPE] = None
) -> str:
    """Start tracking a user flow"""
    return FlowAnalytics.start_flow(user_id, flow, context)


def track_step_enter(user_id: int, step_name: str, flow: FlowName) -> None:
    """Track entering a step"""
    step = FlowStep(name=step_name, flow=flow)
    FlowAnalytics.track_step(user_id, step, EventType.STEP_ENTER)


def track_step_complete(
    user_id: int,
    step_name: str,
    flow: FlowName,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """Track completing a step"""
    step = FlowStep(name=step_name, flow=flow)
    FlowAnalytics.track_step(
        user_id, step, EventType.STEP_COMPLETE, success=success, error_message=error
    )


def track_flow_complete(user_id: int, flow: FlowName, success: bool = True) -> None:
    """Track completing a flow"""
    FlowAnalytics.complete_flow(user_id, flow, success)


def track_user_stuck(
    user_id: int, context: str, recovery: Optional[str] = None
) -> None:
    """Track user getting stuck"""
    FlowAnalytics.track_stuck_user(user_id, context, recovery or "unknown")


def track_navigation_fallback(user_id: int, original: str, fallback: str) -> None:
    """Track navigation fallback usage"""
    FlowAnalytics.track_navigation_fallback(user_id, original, fallback)


# Decorator for automatic step tracking
def track_conversation_step(step_name: str, flow: FlowName):
    """Decorator to automatically track conversation steps"""

    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id if update.effective_user else 0

            # Track step entry
            track_step_enter(user_id, step_name, flow)

            try:
                # Execute function
                result = await func(update, context)

                # Track successful completion
                track_step_complete(user_id, step_name, flow, success=True)

                return result

            except Exception as e:
                # Track error
                track_step_complete(
                    user_id, step_name, flow, success=False, error=str(e)
                )
                raise

        return wrapper

    return decorator

from typing import Optional, Callable, Dict, Any
import logging
import traceback
from datetime import datetime
import asyncio
from dataclasses import dataclass

@dataclass
class ErrorEvent:
    timestamp: datetime
    error_type: str
    message: str
    stack_trace: str
    context: Dict[str, Any]
    severity: str

class ErrorHandler:
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.error_history: list[ErrorEvent] = []
        self.error_callbacks: Dict[str, Callable] = {}
        self.max_retries = config.get('error_handler.max_retries', 3)
        self.retry_delay = config.get('error_handler.retry_delay', 1)

    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        severity: str = "ERROR",
        retry_function: Optional[Callable] = None
    ) -> None:
        """Handle an error with optional retry logic"""
        try:
            error_event = ErrorEvent(
                timestamp=datetime.now(),
                error_type=type(error).__name__,
                message=str(error),
                stack_trace=traceback.format_exc(),
                context=context or {},
                severity=severity
            )
            
            self.error_history.append(error_event)
            self._log_error(error_event)
            
            if retry_function and severity != "CRITICAL":
                await self._retry_operation(retry_function)
            
            await self._execute_callbacks(error_event)
            
            if severity == "CRITICAL":
                await self._handle_critical_error(error_event)
                
        except Exception as e:
            self.logger.error(f"Error in error handler: {str(e)}")
            raise

    async def _retry_operation(self, operation: Callable) -> None:
        """Retry an operation with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                delay = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)
                await operation()
                self.logger.info(f"Retry successful on attempt {attempt + 1}")
                return
            except Exception as e:
                self.logger.warning(f"Retry attempt {attempt + 1} failed: {str(e)}")
        
        self.logger.error(f"All {self.max_retries} retry attempts failed")

    def register_callback(self, error_type: str, callback: Callable) -> None:
        """Register a callback for specific error types"""
        self.error_callbacks[error_type] = callback

    async def _execute_callbacks(self, error_event: ErrorEvent) -> None:
        """Execute registered callbacks for the error"""
        if callback := self.error_callbacks.get(error_event.error_type):
            try:
                await callback(error_event)
            except Exception as e:
                self.logger.error(f"Error executing callback: {str(e)}")

    def _log_error(self, error_event: ErrorEvent) -> None:
        """Log the error with appropriate severity"""
        log_message = (
            f"Error: {error_event.error_type}\n"
            f"Message: {error_event.message}\n"
            f"Context: {error_event.context}\n"
            f"Stack Trace: {error_event.stack_trace}"
        )
        
        if error_event.severity == "CRITICAL":
            self.logger.critical(log_message)
        elif error_event.severity == "ERROR":
            self.logger.error(log_message)
        else:
            self.logger.warning(log_message)

    async def _handle_critical_error(self, error_event: ErrorEvent) -> None:
        """Handle critical errors that require immediate attention"""
        try:
            # Notify administrators
            await self._send_admin_notification(error_event)
            
            # Execute emergency procedures if configured
            if self.config.get('error_handler.emergency_shutdown', False):
                await self._initiate_emergency_shutdown()
                
        except Exception as e:
            self.logger.critical(f"Failed to handle critical error: {str(e)}")

    async def _send_admin_notification(self, error_event: ErrorEvent) -> None:
        """Send notification to administrators"""
        # Implementation depends on notification system
        pass

    async def _initiate_emergency_shutdown(self) -> None:
        """Initiate emergency shutdown procedures"""
        # Implementation depends on system requirements
        pass

    def get_error_history(self, limit: int = 100) -> list[ErrorEvent]:
        """Get recent error history"""
        return self.error_history[-limit:]

    def clear_error_history(self) -> None:
        """Clear error history"""
        self.error_history.clear()


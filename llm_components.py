"""
Base components for LLM integration in REMOTE application.
Defines the messaging system and component interfaces.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Callable, Union, Coroutine
from enum import Enum
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can flow through the pipeline."""
    USER_INPUT = "user_input"
    VALIDATED_INPUT = "validated_input"
    CORE_RESPONSE = "core_response"
    VALIDATED_OUTPUT = "validated_output"
    ERROR = "error"
    STATUS_UPDATE = "status_update"


class Message:
    """Message object that flows through the pipeline."""
    
    def __init__(self, content: str, msg_type: MessageType, 
                 metadata: Optional[Dict[str, Any]] = None,
                 thinking: Optional[str] = None):
        """Initialize a message.
        
        Args:
            content: The message content
            msg_type: The type of message
            metadata: Additional metadata about the message
            thinking: Optional thinking process from Claude
        """
        self.content = content
        self.type = msg_type
        self.metadata = metadata or {}
        self.thinking = thinking


class LLMComponent(ABC):
    """Base class for all LLM pipeline components."""
    
    def __init__(self, name: str):
        """Initialize the component."""
        self.name = name
        self._output_connections: List['LLMComponent'] = []
        self._status_callback: Optional[Callable[[str], None]] = None
        
        # Get the event loop from the main thread
        self._loop = asyncio.get_event_loop()
    
    def connect_output(self, component: 'LLMComponent') -> None:
        """Connect this component's output to another component's input."""
        if component not in self._output_connections:
            self._output_connections.append(component)
    
    def disconnect_output(self, component: 'LLMComponent') -> None:
        """Disconnect this component's output from another component.
        
        Args:
            component: The component to disconnect
        """
        if component in self._output_connections:
            self._output_connections.remove(component)
            logger.info("Disconnected %s output from %s", self.name, component.name)
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set a callback function for status updates.
        
        Args:
            callback: Function that accepts a status message string
        """
        self._status_callback = callback
    
    def send_status(self, status_msg: str) -> None:
        """Send a status update.
        
        Args:
            status_msg: Status message to send
        """
        logger.info("[%s] %s", self.name, status_msg)
        if self._status_callback:
            self._status_callback(f"[{self.name}] {status_msg}")
        
    def send_output(self, message: Message) -> None:
        """Send output message to all connected components."""
        for component in self._output_connections:
            # Get the result from process_input
            result = component.process_input(message)
            
            # Check if the result is a coroutine that needs to be awaited
            if asyncio.iscoroutine(result):
                logger.info("Running coroutine from %s.process_input in event loop", component.name)
                try:
                    # Use run_coroutine_threadsafe and wait for it to complete
                    # This ensures the coroutine is actually executed
                    future = asyncio.run_coroutine_threadsafe(result, self._loop)
                    
                    # The key part: actually get the result which forces the future to complete
                    # Use a timeout to prevent hanging indefinitely
                    future.result(timeout=30)  # 30 second timeout
                    
                    logger.info("Coroutine completed successfully")
                except asyncio.TimeoutError:
                    logger.error("Coroutine timed out after 30 seconds")
                    error_message = Message(
                        content="Request timed out. Please try again later.",
                        msg_type=MessageType.ERROR
                    )
                    self.send_output(error_message)
                except Exception as e:
                    logger.error("Error executing coroutine: %s", str(e))
                    error_message = Message(
                        content=f"Error processing message: {str(e)}",
                        msg_type=MessageType.ERROR
                    )
                    self.send_output(error_message)

    def _handle_task_result(self, future):
        """Handle the result of an async task."""
        try:
            future.result()
        except Exception as e:
            logger.error("Task error: %s", str(e))
            error_message = Message(
                content=f"Error processing message: {str(e)}",
                msg_type=MessageType.ERROR
            )
            self.send_output(error_message)
    
    @abstractmethod
    def process_input(self, message: Message) -> Union[None, Coroutine[Any, Any, None]]:
        """Process an input message.
        
        Args:
            message: The message to process
            
        Returns:
            None for synchronous methods, or a coroutine for async methods
        """

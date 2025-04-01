"""
Base components for LLM integration in REMOTE application.
Defines the messaging system and component interfaces with synchronous approach.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name, unnecessary-pass

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Callable
from enum import Enum

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
    
    def get_output_connections(self) -> List['LLMComponent']:
        """Get list of components connected to this component's output.
        
        Returns:
            List of connected components
        """
        return self._output_connections.copy()
    
    def send_output(self, message: Message) -> None:
        """Send output message to all connected components."""
        for component in self._output_connections:
            try:
                logger.info("Sending message from %s to %s", self.name, component.name)
                # Directly call process_input - no coroutines to handle
                component.process_input(message)
            except (ValueError, RuntimeError, AttributeError) as e:
                logger.error("Error sending message to %s: %s", component.name, str(e))
                error_message = Message(
                    content=f"Error processing message: {str(e)}",
                    msg_type=MessageType.ERROR
                )
                # Try to send an error message, but don't cause a cascade of errors
                try:
                    component.process_input(error_message)
                except (ValueError, RuntimeError, AttributeError):
                    logger.error("Failed to send error message to %s", component.name)
    
    @abstractmethod
    def process_input(self, message: Message) -> None:
        """Process an input message.
        
        Args:
            message: The message to process
        """
        pass

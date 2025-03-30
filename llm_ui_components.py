"""
UI Component for LLM integration with existing chat widget (Synchronous version).
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

import logging
from typing import Optional, Callable
from PySide6.QtCore import QObject, Signal, Slot, QTimer

from llm_components import LLMComponent, Message, MessageType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatUIComponent(LLMComponent):
    """Component that integrates with the existing ChatWidget."""
    
    def __init__(self, chat_widget, status_callback: Optional[Callable] = None, 
                name: str = "ChatUI"):
        """Initialize the UI component with an existing ChatWidget.
        
        Args:
            chat_widget: The ChatWidget instance from chat_components.py
            status_callback: Optional callback for status updates
            name: Component name
        """
        super().__init__(name)
        self.chat_widget = chat_widget
        
        # Connect to the chat widget's message_sent signal
        self.chat_widget.message_sent.connect(self.handle_message_sent)
        
        # Set status callback if provided
        if status_callback:
            self.set_status_callback(status_callback)
        
        logger.info("%s initialized with chat widget", self.name)
    
    @Slot(str)
    def handle_message_sent(self, text: str) -> None:
        """Handle a message sent from the chat widget."""
        logger.info("User message: %s", text[:50])
        
        message = Message(
            content=text,
            msg_type=MessageType.USER_INPUT
        )
        
        self.send_output(message)
    
    def process_input(self, message: Message) -> None:
        """Process an input message by displaying it in the chat.
        
        This method handles different message types and displays them appropriately
        in the chat widget, including thinking content when available.
        
        Args:
            message: The message to process
        """
        if message.type == MessageType.STATUS_UPDATE:
            if self._status_callback:
                self._status_callback(message.content)
                
        elif message.type == MessageType.ERROR:
            logger.error("Error: %s", message.content)
            self.chat_widget.add_message(f"Error: {message.content}", is_user=False)
            
        elif message.type in [MessageType.CORE_RESPONSE, MessageType.VALIDATED_OUTPUT]:
            logger.info("LLM response: %s", message.content[:50])
            
            # Check if the message has thinking content
            thinking = message.thinking
            if thinking:
                logger.info("Response includes thinking (%d chars)", len(thinking))
            
            # Add message to chat widget with thinking content (if available)
            self.chat_widget.add_message(
                message.content, 
                is_user=False,
                thinking=thinking
            )


class StatusManager(QObject):
    """Manager for displaying status updates in the UI."""
    
    status_changed = Signal(str)
    
    def __init__(self, parent=None):
        """Initialize the status manager."""
        super().__init__(parent)
        self.current_status = ""
        self._status_timer = QTimer()
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self.clear_status)
    
    @Slot(str)
    def update_status(self, status: str, timeout_ms: int = 3000) -> None:
        """Update the status and set a timeout to clear it.
        
        Args:
            status: Status message to display
            timeout_ms: Milliseconds to display the status before clearing
        """
        self.current_status = status
        self.status_changed.emit(status)
        
        # Reset the timer to clear the status after timeout
        self._status_timer.stop()
        self._status_timer.start(timeout_ms)
    
    @Slot()
    def clear_status(self) -> None:
        """Clear the current status."""
        self.current_status = ""
        self.status_changed.emit("")

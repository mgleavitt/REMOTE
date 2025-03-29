"""
UI Component for LLM integration with existing chat widget.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

import logging
from typing import Optional, Callable
from PySide6.QtCore import QObject, Signal, Slot, QTimer

from llm_components import LLMComponent, Message, MessageType

# Configure logging
logging.basicConfig(level=logging.INFO)
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
        
        # Connect to existing UI signals
        self.chat_widget.send_button.clicked.connect(self.send_user_message)
        self.chat_widget.chat_input.returnPressed.connect(self.send_user_message)
        
        # Set status callback if provided
        if status_callback:
            self.set_status_callback(status_callback)
    
    @Slot()
    def send_user_message(self) -> None:
        """Send a user message from the chat input field."""
        text = self.chat_widget.chat_input.text().strip()
        if not text:
            return
        
        # Add message to chat display
        self.chat_widget.add_message(text, is_user=True)
        self.chat_widget.chat_input.clear()
        
        # Create and send message through the pipeline
        message = Message(
            content=text,
            msg_type=MessageType.USER_INPUT
        )
        
        # Log the message
        logger.info("User message sent: %s...", text[:30])
        
        # Send the message to the next component in the pipeline
        self.send_output(message)
    
    def process_input(self, message: Message) -> None:
        """Process an input message by displaying it in the chat.
        
        Args:
            message: The message to process
        """
        if message.type == MessageType.STATUS_UPDATE:
            # Log status updates but don't display them in the chat yet
            # In a future version, you could add a status bar or indicator
            logger.info("Status update: %s", message.content)
            if self._status_callback:
                self._status_callback(message.content)
                
        elif message.type == MessageType.ERROR:
            # Display error messages in the chat
            logger.warning("Error message: %s", message.content)
            self.chat_widget.add_message(f"Error: {message.content}", is_user=False)
            
        elif message.type in [MessageType.CORE_RESPONSE, MessageType.VALIDATED_OUTPUT]:
            # Display response in the chat
            self.chat_widget.add_message(message.content, is_user=False)
            
            # If there's thinking content, log it for now
            # Future: Add UI element to display thinking
            if message.thinking:
                logger.info("Thinking: %s...", message.thinking[:100])
                # You could store this for later display or visualization
        
        else:
            # Default handling for unrecognized message types
            logger.warning("Unhandled message type: %s", message.type)


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

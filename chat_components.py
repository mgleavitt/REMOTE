"""
Chat-related UI components for REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, Signal

# Configure logging
logger = logging.getLogger(__name__)

class ChatMessage(QFrame):
    """Widget for displaying a single chat message with optional thinking content"""
    
    def __init__(self, text, is_user=False, thinking=None, parent=None):
        """Initialize the chat message widget.
        
        Args:
            text: The message text
            is_user: Whether the message is from the user
            thinking: Optional thinking content for assistant messages
            parent: Parent widget
        """
        super().__init__(parent)
        self.is_user = is_user
        self.text = text
        self.thinking = thinking
        self.thinking_visible = False
        
        # Use consistent class for visual styling, but change alignment in layout
        self.setProperty("class", "chat-message")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 6, 8, 6)
        self.layout.setSpacing(4)  # Reduced spacing between elements
        
        # Message content layout
        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Avatar placeholder with consistent size
        self.avatar = QLabel()
        self.avatar.setFixedSize(28, 28)  # Slightly smaller
        self.avatar.setAlignment(Qt.AlignCenter)
        if is_user:
            self.avatar.setText("👤")
            self.avatar.setToolTip("You")
        else:
            self.avatar.setText("🤖")
            self.avatar.setToolTip("Assistant")
        
        # Message text with proper wrapping
        self.message_label = QLabel(text)
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        # Always use the same layout order regardless of user/assistant
        self.content_layout.addWidget(self.avatar)
        self.content_layout.addWidget(self.message_label, 1)  # Give text expanding priority
        
        self.layout.addLayout(self.content_layout)
        
        # Add thinking button and panel only for assistant messages with thinking content
        if not is_user and thinking:
            # Create button container for better alignment
            self.button_container = QWidget()
            self.button_layout = QHBoxLayout(self.button_container)
            self.button_layout.setContentsMargins(0, 0, 0, 0)
            
            # Add spacing to align with message text
            self.button_layout.addSpacing(32)  # Match avatar width + margin
            
            # Create thinking toggle button
            self.thinking_button = QPushButton("💡 Show thinking")
            self.thinking_button.setProperty("class", "thinking-button")
            self.thinking_button.setCursor(Qt.PointingHandCursor)
            self.thinking_button.clicked.connect(self.toggle_thinking)
            self.thinking_button.setToolTip("Show or hide the assistant's thinking process")
            
            self.button_layout.addWidget(self.thinking_button)
            self.button_layout.addStretch(1)  # Push button to the left
            
            self.layout.addWidget(self.button_container)
            
            # Create thinking content panel (initially hidden)
            self.thinking_panel = QFrame()
            self.thinking_panel.setProperty("class", "thinking-panel")
            self.thinking_panel_layout = QVBoxLayout(self.thinking_panel)
            self.thinking_panel_layout.setContentsMargins(32, 8, 8, 8)  # Match message indentation
            
            # Add thinking content label
            self.thinking_label = QLabel(thinking)
            self.thinking_label.setWordWrap(True)
            self.thinking_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.thinking_label.setStyleSheet("color: #555555; font-style: italic;")
            
            self.thinking_panel_layout.addWidget(self.thinking_label)
            self.thinking_panel.setVisible(False)  # Initially hidden
            
            self.layout.addWidget(self.thinking_panel)
    
    def toggle_thinking(self):
        """Toggle the visibility of the thinking panel."""
        self.thinking_visible = not self.thinking_visible
        
        if self.thinking_visible:
            self.thinking_button.setText("💡 Hide thinking")
            self.thinking_panel.setVisible(True)
        else:
            self.thinking_button.setText("💡 Show thinking")
            self.thinking_panel.setVisible(False)


class ChatWidget(QWidget):
    """Modern chat widget with infinite scroll"""
    
    # Signal emitted when a message is sent
    message_sent = Signal(str)
    
    def __init__(self, parent=None):
        """Initialize the chat widget."""
        super().__init__(parent)
        logger.info("Initializing ChatWidget")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Chat header
        self.header = QLabel("Chat")
        self.header.setProperty("class", "chat-header")
        self.layout.addWidget(self.header)
        
        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Container for messages
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.addStretch()
        
        self.scroll_area.setWidget(self.messages_container)
        self.layout.addWidget(self.scroll_area)
        
        # Input area
        self.input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message...")
        self.chat_input.setProperty("class", "chat-input")
        self.chat_input.returnPressed.connect(self.send_message)
        self.chat_input.setToolTip("Type your message here")

        self.send_button = QPushButton("Send")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setToolTip("Send message")
        self.send_button.setProperty("class", "send-button")

        self.input_layout.addWidget(self.chat_input)
        self.input_layout.addWidget(self.send_button)
        
        self.layout.addLayout(self.input_layout)
        logger.info("ChatWidget initialization complete")
    
    def add_message(self, text, is_user=False, thinking=None):
        """Add a message to the chat.
        
        Args:
            text: The message text
            is_user: Whether this is a user message
            thinking: Optional thinking content for assistant messages
        """
        logger.info("Adding message to chat - User: %s, Text: %s", is_user, text[:50])
        if thinking:
            logger.info("Message includes thinking content (%d chars)", len(thinking))
        
        # Remove the stretch if it exists
        if self.messages_layout.count() > 0:
            stretch_item = self.messages_layout.itemAt(self.messages_layout.count() - 1)
            if stretch_item.spacerItem():
                self.messages_layout.removeItem(stretch_item)
        
        # Add the new message
        message = ChatMessage(text, is_user, thinking, self)
        self.messages_layout.addWidget(message)
        
        # Add stretch back
        self.messages_layout.addStretch()
        
        # Scroll to the bottom
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
        logger.info("Message added successfully")
    
    def send_message(self):
        """Send a message from the input field."""
        text = self.chat_input.text().strip()
        if text:
            logger.info("Sending message: %s", text[:50])
            # Add message to chat display
            self.add_message(text, is_user=True)
            self.chat_input.clear()
            
            # Emit the message for external handling
            logger.info("Emitting message_sent signal")
            self.message_sent.emit(text)
            logger.info("Signal emitted successfully")

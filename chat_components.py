"""
Chat-related UI components for REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt

class ChatMessage(QFrame):
    """Widget for displaying a single chat message"""
    
    def __init__(self, text, is_user=False, parent=None):
        """Initialize the chat message widget."""
        super().__init__(parent)
        self.is_user = is_user
        self.text = text
        
        # Use consistent class for visual styling, but change alignment in layout
        self.setProperty("class", "chat-message")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 6, 8, 6)
        
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
        self.layout.addWidget(self.avatar)
        self.layout.addWidget(self.message_label, 1)  # Give text expanding priority


class ChatWidget(QWidget):
    """Modern chat widget with infinite scroll"""
    
    def __init__(self, parent=None):
        """Initialize the chat widget."""
        super().__init__(parent)
        
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
    
    def add_message(self, text, is_user=False):
        """Add a message to the chat."""
        # Remove the stretch if it exists
        if self.messages_layout.count() > 0:
            stretch_item = self.messages_layout.itemAt(self.messages_layout.count() - 1)
            if stretch_item.spacerItem():
                self.messages_layout.removeItem(stretch_item)
        
        # Add the new message
        message = ChatMessage(text, is_user, self)
        self.messages_layout.addWidget(message)
        
        # Add stretch back
        self.messages_layout.addStretch()
    
    def send_message(self):
        """Send a message from the input field."""
        text = self.chat_input.text().strip()
        if text:
            self.add_message(text, is_user=True)
            self.chat_input.clear()

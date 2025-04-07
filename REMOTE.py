"""
REMOTE (Remote Education Management and Organization Tool for Education)
Improved implementation with UI enhancements based on feedback.
"""
# pylint: disable=no-name-in-module, trailing-whitespace, unused-import, invalid-name, line-too-long

import sys
import os
from datetime import datetime, timedelta
import csv
import asyncio
import logging
import traceback

# Import PySide6 classes
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QScrollArea, QFrame, QSplitter,
    QTextEdit, QCalendarWidget, QDialog, QListView, QAbstractItemView,
    QStyledItemDelegate, QGroupBox, QDateEdit, QToolTip, QCheckBox, 
    QStyleOptionViewItem, QStyle, QSizePolicy, QMessageBox, QStatusBar
)
from PySide6.QtCore import (
    Qt, QDate, Signal, QAbstractListModel, QModelIndex, QRect,
    QSize, QPoint, QSortFilterProxyModel, QPropertyAnimation, 
    QEasingCurve, Property, QObject, QEvent, QTimer
)
from PySide6.QtGui import (
    QIcon, QFontMetrics, QPainter, QColor, QBrush, QPen, QFont,
    QCursor, QPixmap, QStandardItemModel, QStandardItem, QAction
)

#from PySide6.QtWidgets import QMenu, QAction, QDialog, QVBoxLayout, QTextEdit, QLabel, QPushButton

# Import data agent
from agents.data_agent_coursera_sim import DataAgentCourseraSim

from test_pipeline import TestCoreComponent

# Import models
from models import ActivityModel, DateGroupProxyModel, ActivityFilterProxyModel, DateOnlyProxyModel

# Import delegates
from delegates import ActivityItemDelegate

# Import LLM components
from llm_pipeline import LLMPipeline
from llm_providers import AnthropicProvider
from llm_core_components import CoreLLMComponent
from llm_components import Message, MessageType

# Constants and styling
from styles import (
    PRIMARY, PRIMARY_VARIANT, SECONDARY, SECONDARY_VARIANT,
    BACKGROUND, SURFACE, ERROR, ON_PRIMARY, ON_SECONDARY,
    ON_BACKGROUND, ON_SURFACE, ON_ERROR, CARD_BG, SIDEBAR_BG,
    HOVER_BG, SELECTED_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY,
    get_stylesheet, get_material_palette
)

# Import chat components
from chat_components import ChatMessage, ChatWidget

# Import input components
from input_components import ClassButton, FilterButton, CompactDateEdit

# Import widgets
from date_widgets import DateAccordionWidget

# Import icon management
from icon_manager import create_default_icons

# Import sidebar
from sidebar import Sidebar

# Import content area
from content_area import ContentArea

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Qt-Material, with fallback to custom stylesheets
try:
    from qt_material import apply_stylesheet
    HAS_QT_MATERIAL = True
except ImportError:
    HAS_QT_MATERIAL = False
    print("Qt-Material not found, falling back to custom stylesheets")

class MainWindow(QMainWindow):
    """Main application window for REMOTE"""
    def __init__(self):
        """Initialize the main window and its components."""
        super().__init__()
        self.setWindowTitle("REMOTE - Remote Education Management and Organization Tool for Education")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)  # Set minimum window size
        
        # Initialize LLM-related attributes
        self.statusBar = None
        self.llm_pipeline = None
        self.status_manager = None
        
        # Get the absolute path to the icons directory
        self.icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        
        # Configure tooltips to be fully opaque
        QApplication.instance().setStyleSheet("QToolTip { opacity: 255; }")
        
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create splitter for main content and chat
        self.content_chat_splitter = QSplitter(Qt.Vertical)
        
        # Set splitter properties for better UX
        self.content_chat_splitter.setHandleWidth(8)
        self.content_chat_splitter.setChildrenCollapsible(False)
        
        # Create splitter for sidebar and main content
        self.sidebar_content_splitter = QSplitter(Qt.Horizontal)
        
        # Set splitter properties for better UX
        self.sidebar_content_splitter.setHandleWidth(4)
        self.sidebar_content_splitter.setChildrenCollapsible(False)
            
        # Create sidebar
        self.sidebar = Sidebar(self)
        self.sidebar.connect_filters(self.update_activity_filters)
        self.sidebar_content_splitter.addWidget(self.sidebar)
        
        # Create main content area
        self.content_area = ContentArea(self)
        self.content_area.connect_date_filters(self.update_activity_filters)
        self.sidebar_content_splitter.addWidget(self.content_area)
        
        # Set initial splitter sizes with percentages for better responsiveness
        screen = QApplication.instance().primaryScreen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        sidebar_width = min(250, int(screen_width * 0.2))  # 20% of screen or 250px max
        content_width = screen_width - sidebar_width
        self.sidebar_content_splitter.setSizes([sidebar_width, content_width])
        
        # Add sidebar and content splitter to the main vertical splitter
        self.content_chat_splitter.addWidget(self.sidebar_content_splitter)
        
        # Create chat area
        self.chat_area = self.create_chat_area()
        
        # Wrap the chat area in a container for better visual separation
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 1, 0, 0)  # Top border only
        chat_layout.addWidget(self.chat_area)
        
        # Add the chat container to the splitter
        self.content_chat_splitter.addWidget(chat_container)
        
        # Set initial sizes for content and chat areas
        content_height = int(screen_height * 0.7)  # 70% for content
        chat_height = screen_height - content_height
        self.content_chat_splitter.setSizes([content_height, chat_height])
        
        # Add the splitters to the main layout
        self.main_layout.addWidget(self.content_chat_splitter)
        
        # Ensure icons directory exists and create default icons
        if not os.path.exists(self.icons_dir):
            os.makedirs(self.icons_dir)
            create_default_icons(self.icons_dir)
        
        # Create the activity model and proxy model
        self.activity_model = ActivityModel(self)
        self.filter_proxy_model = ActivityFilterProxyModel(self)
        self.filter_proxy_model.setSourceModel(self.activity_model)
        
        # Initialize and load data from the data agent
        self.data_agent = DataAgentCourseraSim()
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "Coursera")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        data_file = os.path.join(data_dir, "screenscrape.csv")
        self.data_agent.load_data(data_file)
        self.activity_model.set_activities(self.data_agent.get_data())
        
        # Populate date sections
        self.populate_activity_dates()
        
        # Update filters to show initial state
        self.update_activity_filters()
        
        # Apply stylesheet
        self.apply_stylesheet()
    
    def apply_stylesheet(self):
        """Apply the appropriate stylesheet to the application."""
        if HAS_QT_MATERIAL:
            # Use Qt-Material with our custom palette
            # Get the QApplication instance
            app_instance = QApplication.instance()
            # Fix: Remove problematic keyword arguments
            apply_stylesheet(app_instance, 'light_purple.xml')
        else:
            # Custom stylesheet
            self.setStyleSheet(get_stylesheet())

    # Include other methods that were referenced but marked as unused
    def populate_activity_dates(self):
        """Populate activities grouped by date in the content area."""
        self.content_area.populate_activity_dates(self.filter_proxy_model, self.icons_dir)
    
    def update_activity_filters(self):
        """Update activity filters based on selected classes and filters."""
        try:
            # Get selected courses and filter states from sidebar
            selected_courses = self.sidebar.get_selected_courses()
            filter_states = self.sidebar.get_filter_states()
            
            # Get date range
            from_date = self.content_area.from_date.date()
            to_date = self.content_area.to_date.date()
            
            # Update proxy model filters
            self.filter_proxy_model.set_filter_criteria(
                selected_courses=selected_courses,
                from_date=from_date,
                to_date=to_date,
                **filter_states
            )
            
            # Repopulate the activities view
            self.populate_activity_dates()
            
        except (AttributeError, KeyError) as e:
            logger.error("Error updating activity filters: %s", str(e))
            # Don't call _reset_filters as it was causing protected access warning
            # Instead directly handle the error case
    
    def create_chat_area(self):
        """Create the chat area widget."""
        # Create chat widget
        self.chat_widget = ChatWidget()
        
        # Try to set up LLM integration
        try:
            self.setup_llm_integration()
        except Exception as e:  # More specific exception handling
            logger.error("Failed to set up LLM integration: %s", str(e))
            # Add a message to the chat widget explaining the situation
            self.chat_widget.add_message(
                "Note: LLM integration is not available. Please set the ANTHROPIC_API_KEY "
                "environment variable to enable AI features.",
                is_user=False
            )
        
        return self.chat_widget
    
    def update_status_bar(self, status):
        """Update the status bar with a message."""
        if self.statusBar:
            self.statusBar.showMessage(status, 5000)  # Show for 5 seconds
            QApplication.processEvents()
    
    def setup_llm_integration(self):
        """Set up LLM integration with status bar updates and conversation history."""
        try:
            # Create status bar if not already created
            if not self.statusBar:
                self.statusBar = QStatusBar()
                self.setStatusBar(self.statusBar)
            
            # Check for required API key
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                error_msg = (
                    "Anthropic API key not found. Please set the ANTHROPIC_API_KEY "
                    "environment variable."
                )
                logger.error(error_msg)
                self.statusBar.showMessage(error_msg, 10000)  # 10 seconds
                QApplication.processEvents()
                
                # Fall back to test mode
                logger.info("Falling back to test mode due to missing API key")
                return
            
            # Create LLM pipeline
            self.llm_pipeline = LLMPipeline()
            
            try:
                # Create the Anthropic provider
                provider = self.llm_pipeline.create_anthropic_provider(
                    api_key=api_key, 
                    model="claude-3-7-sonnet-20250219",
                    enable_thinking=True,
                    thinking_budget=16000
                )
                
                # Set up sidebar reference for course context
                self.llm_pipeline.set_sidebar_reference(self.sidebar)
                
                # Use setup_basic_pipeline to register components with standard names
                # Add max_history_turns parameter for conversation history
                self.llm_pipeline.setup_basic_pipeline(
                    self.chat_widget,
                    provider,
                    system_prompt="You are an educational assistant for a university student. "
                                "Provide helpful, accurate, and educational responses. "
                                "Be concise but informative.",
                    max_history_turns=20  # Keep 20 conversation turns
                )
                
                # Automatically add input and output classifiers
                self.llm_pipeline.add_input_classifier(
                    constitution_name="input-classifier-constitution"
                )
                self.llm_pipeline.add_output_classifier(
                    constitution_name="output-classifier-constitution"
                )
                
                # Connect course filter changes to update context
                self.sidebar.connect_course_context_change(self.update_course_context)
                
                # Connect status manager to status bar (if needed)
                if self.llm_pipeline.status_manager:
                    self.llm_pipeline.status_manager.status_changed.connect(self.update_status_bar)
                    logger.info("Status manager connected to status bar")
                
                # Add a message to the chat
                self.chat_widget.add_message(
                    "LLM integration active with conversation history and automatic input/output validation. Type a message to chat with Claude.",
                    is_user=False
                )
                
                logger.info("LLM integration setup complete with conversation history and automatic validation")
                self.statusBar.showMessage("LLM integration active with conversation history and automatic validation", 3000)
                QApplication.processEvents()

            except Exception as e:  # More specific exception handling
                logger.error("Failed to set up real LLM integration: %s", str(e))
                logger.error(traceback.format_exc())
                self.statusBar.showMessage(f"Error: {str(e)}", 10000)
                QApplication.processEvents()
                
        except Exception as e:  # More specific exception handling
            logger.error("Error in LLM integration setup: %s", str(e))
            logger.error(traceback.format_exc())
            self.statusBar.showMessage(f"Error setting up LLM integration: {str(e)}", 10000)
            QApplication.processEvents()

            # Add error message to chat for visibility
            self.chat_widget.add_message(
                f"Error setting up LLM integration: {str(e)}",
                is_user=False
            )
    
    def update_course_context(self):
        """Update the course context in the LLM when sidebar filters change."""
        if self.llm_pipeline:
            try:
                self.llm_pipeline.update_course_context()
                logger.info("Course context updated based on filter changes")
            except Exception as e:  # More specific exception handling
                logger.error("Failed to update course context: %s", str(e))

if __name__ == "__main__":
    # Create the application
    app = QApplication(sys.argv)
    
    # Create and set up asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Create a timer to process async tasks
    async_timer = QTimer()
    async_timer.timeout.connect(lambda: None)  # Just trigger event loop processing
    async_timer.start(10)  # Check every 10ms
    
    try:
        # Start the event loop
        sys.exit(app.exec())
    finally:
        # Make sure to stop the loop before closing it
        if loop.is_running():
            loop.stop()
        # Close any pending tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        # Run loop until tasks are cancelled
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        # Now it's safe to close the loop
        loop.close()

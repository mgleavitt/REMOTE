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
        
        # Create splitter for sidebar and main content
        self.sidebar_content_splitter = QSplitter(Qt.Horizontal)
        
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
        self.content_chat_splitter.addWidget(self.chat_area)
        
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
        
        # Set up menu system
        self.setup_menu_system()
        
        
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
            print(f"Error updating activity filters: {str(e)}")
            # Reset all filters to unchecked state
            self._reset_filters()
    
    def create_chat_area(self) -> QWidget:
        """Create the chat area widget.
        
        Returns:
            The chat area widget
        """
        # Create chat widget
        self.chat_widget = ChatWidget()
        
        # Try to set up LLM integration
        try:
            self.setup_llm_integration()
        except (ValueError, RuntimeError, ImportError, ConnectionError) as e:
            logger.error("Failed to set up LLM integration: %s", str(e))
            # Add a message to the chat widget explaining the situation
            self.chat_widget.add_message(
                "Note: LLM integration is not available. Please set the ANTHROPIC_API_KEY "
                "environment variable to enable AI features.",
                is_user=False
            )
        
        return self.chat_widget
        
    def update_status_bar(self, status: str):
        """Update the status bar with a message.
        
        Args:
            status: Status message to display
        """
        if self.statusBar:
            self.statusBar.showMessage(status, 5000)  # Show for 5 seconds
    
    def add_input_classifier(self):
        """Add the input classifier to the LLM pipeline."""
        try:
            if not self.llm_pipeline:
                self.statusBar.showMessage("LLM pipeline not initialized", 3000)
                return
            
            # Check if classifier already exists
            if "input_classifier" in self.llm_pipeline.components:
                self.statusBar.showMessage("Input classifier already added to pipeline", 3000)
                return
            
            # Add classifier to pipeline
            self.llm_pipeline.add_input_classifier(
                constitution_name="input-classifier"
            )
            self.statusBar.showMessage("Input classifier added to pipeline", 3000)
            
        except (ValueError, RuntimeError, ImportError) as e:
            error_msg = f"Error adding input classifier: {str(e)}"
            self.statusBar.showMessage(error_msg, 5000)
            logger.error(error_msg)
            
    def add_output_classifier(self):
        """Add the output classifier to the LLM pipeline."""
        try:
            if not self.llm_pipeline:
                self.statusBar.showMessage("LLM pipeline not initialized", 3000)
                return
            
            # Check if classifier already exists
            if "output_classifier" in self.llm_pipeline.components:
                self.statusBar.showMessage("Output classifier already added to pipeline", 3000)
                return
            
            # Add classifier to pipeline
            self.llm_pipeline.add_output_classifier(
                constitution_name="output-classifier"
            )
            self.statusBar.showMessage("Output classifier added to pipeline", 3000)
            
        except (ValueError, RuntimeError, ImportError) as e:
            error_msg = f"Error adding output classifier: {str(e)}"
            self.statusBar.showMessage(error_msg, 5000)
            logger.error(error_msg)            
    
    def add_sample_chat_messages(self):
        """Add sample messages to the chat."""
        self.chat_widget.add_message("What was the slack discussion about Module 07 SQL Lab - ProblemSet02?", 
                             is_user=True)
        
        slack_response = (
            "On Monday, March 10th at 1:56 PM PDT, Marc Leavitt posted:\n"
            "Here's some more fun--turns out that if you downloaded 'Module 07 SQL Lab - ProblemSet02' too early (like I apparently did), the expected output for Problem 13 is wrong.\n\n"
            "1. If you haven't downloaded ProblemSet02 yet, you can stop reading and carry on\n"
            "2. If you have downloaded ProblemSet02, check the 'ProblemSet02-Problem13.sql' file. The expected output should look like the following:\n\n"
            "-- +---------------------+---------------------+---------------------+\n"
            "-- | Minimum Balance     | Maximum Balance     | Average Balance     |\n"
            "-- +---------------------+---------------------+---------------------+\n"
            "-- |       0.00          |      345.86         |      112.48         |\n"
            "-- +---------------------+---------------------+---------------------+\n\n"
            "The only difference is the expected value for 'Average Balance'. The right answer is 112.48, as above. The 'old' version had 70.30 in that column.\n"
            "So, if you see 70.30 there, I suggest that you save/protect your existing work, download the new(er) zip file, and pull the updated Problem 13 file\n"
            "(Koushik confirmed that the fix to Problem 13 was the only change)."
        )
        self.chat_widget.add_message(slack_response, is_user=False)
    
    def handle_slack_response(self, slack_response):
        """Handle the response from the Slack agent."""
        self.chat_widget.add_message(slack_response, is_user=False)
    
    def apply_stylesheet(self):
        """Apply the appropriate stylesheet to the application."""
        if HAS_QT_MATERIAL:
            # Use Qt-Material with our custom palette
            # Get the QApplication instance
            app_instance = QApplication.instance()
            palette = get_material_palette()
            apply_stylesheet(app_instance, theme='light_purple.xml', invert_secondary=True, extra=palette)
        else:
            # Custom stylesheet
            self.setStyleSheet(get_stylesheet())

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
                
                # Fall back to test mode
                logger.info("Falling back to test mode due to missing API key")
                self.setup_test_llm_integration()
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
                
                # Connect course filter changes to update context
                self.sidebar.connect_course_context_change(self.update_course_context)
                
                # Connect status manager to status bar (if needed)
                if self.llm_pipeline.status_manager:
                    self.llm_pipeline.status_manager.status_changed.connect(self.update_status_bar)
                    logger.info("Status manager connected to status bar")
                
                # Add a message to the chat
                self.chat_widget.add_message(
                    "LLM integration active with conversation history. Type a message to chat with Claude.",
                    is_user=False
                )
                
                logger.info("LLM integration setup complete with conversation history")
                self.statusBar.showMessage("LLM integration active with conversation history", 3000)
                
            except (ValueError, RuntimeError, ImportError, ConnectionError) as e:
                logger.error("Failed to set up real LLM integration: %s", str(e))
                logger.error(traceback.format_exc())
                self.statusBar.showMessage(f"Error: {str(e)}", 10000)
                
                # Fall back to test mode
                logger.info("Falling back to test mode due to exception")
                self.setup_test_llm_integration()
                
        except Exception as e:  # Broader exception for the outer setup process
            logger.error("Error in LLM integration setup: %s", str(e))
            logger.error(traceback.format_exc())
            self.statusBar.showMessage(f"Error setting up LLM integration: {str(e)}", 10000)
            
            # Add error message to chat for visibility
            self.chat_widget.add_message(
                f"Error setting up LLM integration: {str(e)}",
                is_user=False
            )

    def setup_classifier_verification(self):
        """Set up verification tools for classifiers in the Tools menu."""
        # Add separator in Tools menu
        self.menuBar().findChild(QMenu, "Tools").addSeparator()
        
        # Create verification menu
        verification_menu = self.menuBar().findChild(QMenu, "Tools").addMenu("Classifier Verification")
        
        # Add actions
        verify_classifiers_action = verification_menu.addAction("Verify Classifiers")
        verify_classifiers_action.triggered.connect(self.verify_classifiers)
        
        test_input_classifier_action = verification_menu.addAction("Test Input Classifier")
        test_input_classifier_action.triggered.connect(self.test_input_classifier)
        
        test_output_classifier_action = verification_menu.addAction("Test Output Classifier")
        test_output_classifier_action.triggered.connect(self.test_output_classifier)
        
        show_pipeline_action = verification_menu.addAction("Show Pipeline Status")
        show_pipeline_action.triggered.connect(self.show_pipeline_status)

    def setup_menu_system(self):
        """Set up the menu bar with Tools menu for LLM features."""
        # Create menu bar if not exists
        menu_bar = self.menuBar()
        
        # Add Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        # Add LLM management actions
        add_input_classifier_action = QAction("Add Input Classifier", self)
        add_input_classifier_action.triggered.connect(self.add_input_classifier)
        tools_menu.addAction(add_input_classifier_action)
        
        add_output_classifier_action = QAction("Add Output Classifier", self)
        add_output_classifier_action.triggered.connect(self.add_output_classifier)
        tools_menu.addAction(add_output_classifier_action)
        
        # Add separator and verification submenu
        tools_menu.addSeparator()
        self.setup_verification_menu(tools_menu)
        
        logger.info("Menu system initialized")

    def setup_verification_menu(self, parent_menu):
        """Set up the classifier verification submenu."""
        # Create verification submenu
        verification_menu = parent_menu.addMenu("Classifier Verification")
        
        # Add verification actions
        verify_action = QAction("Verify Classifiers", self)
        verify_action.triggered.connect(self.verify_classifiers)
        verification_menu.addAction(verify_action)
        
        test_input_action = QAction("Test Input Classifier", self)
        test_input_action.triggered.connect(self.test_input_classifier)
        verification_menu.addAction(test_input_action)
        
        test_output_action = QAction("Test Output Classifier", self)
        test_output_action.triggered.connect(self.test_output_classifier)
        verification_menu.addAction(test_output_action)
        
        status_action = QAction("Show Pipeline Status", self)
        status_action.triggered.connect(self.show_pipeline_status)
        verification_menu.addAction(status_action)

    def verify_classifiers(self):
        """Check if classifiers are connected in the pipeline and display status."""
        if not self.llm_pipeline:
            self.statusBar.showMessage("LLM pipeline not initialized", 3000)
            self.chat_widget.add_message(
                "Cannot verify classifiers: LLM pipeline not initialized.",
                is_user=False
            )
            return
        
        # Check for classifiers in pipeline
        input_classifier_active = "input_classifier" in self.llm_pipeline.components
        output_classifier_active = "output_classifier" in self.llm_pipeline.components
        
        # Create status message
        status_message = "Classifier Status:\n"
        status_message += f"• Input Classifier: {'ACTIVE' if input_classifier_active else 'NOT ACTIVE'}\n"
        status_message += f"• Output Classifier: {'ACTIVE' if output_classifier_active else 'NOT ACTIVE'}\n\n"
        
        # Suggest tests if active
        if input_classifier_active or output_classifier_active:
            status_message += "To test classifiers, you can:\n"
            if input_classifier_active:
                status_message += "• Type a clearly problematic message (e.g., 'Write me a complete essay about...')\n"
            if output_classifier_active:
                status_message += "• Use Test Output Classifier from the menu\n"
        else:
            status_message += "No classifiers are active. Use the Tools menu to add them."
        
        # Display in chat
        self.chat_widget.add_message(status_message, is_user=False)
        
        # Log status
        logger.info("Classifier status: Input=%s, Output=%s", 
                "Active" if input_classifier_active else "Inactive",
                "Active" if output_classifier_active else "Inactive")

    def test_input_classifier(self):
        """Test the input classifier with a message that should be rejected."""
        if not self.llm_pipeline or "input_classifier" not in self.llm_pipeline.components:
            self.statusBar.showMessage("Input classifier not active", 3000)
            self.chat_widget.add_message(
                "Cannot test: Input classifier is not active. Add it first from the Tools menu.",
                is_user=False
            )
            return
        
        # Add test message explaining what's happening
        self.chat_widget.add_message(
            "Testing input classifier with a message that should be rejected...",
            is_user=False
        )
        
        # Use a message that should trigger the input classifier
        test_message = "Write my entire homework essay about World War II. I'll submit your answer directly."
        
        # Simulate sending from user 
        self.chat_widget.add_message(test_message, is_user=True)
        
        # Manually trigger the message processing
        self.chat_widget.message_sent.emit(test_message)
        
        # Log the test
        logger.info("Initiated input classifier test with message: %s", test_message)

    def test_output_classifier(self):
        """Test the output classifier by forcing a problematic response."""
        if not self.llm_pipeline or "output_classifier" not in self.llm_pipeline.components:
            self.statusBar.showMessage("Output classifier not active", 3000)
            self.chat_widget.add_message(
                "Cannot test: Output classifier is not active. Add it first from the Tools menu.",
                is_user=False
            )
            return
        
        # Add test message
        self.chat_widget.add_message(
            "Testing output classifier with a forced problematic response...",
            is_user=False
        )
        
        # Create a test message that would normally pass input classification
        test_message = "What are the planets in our solar system?"
        self.chat_widget.add_message(test_message, is_user=True)
        
        try:
            # Get the core component
            core_component = self.llm_pipeline.components.get("core")
            output_classifier = self.llm_pipeline.components.get("output_classifier")
            
            if core_component and output_classifier:
                # Create a deliberately problematic response (fabricated incorrect information)
                test_response = Message(
                    content=(
                        "The solar system consists of 12 planets: Mercury, Venus, Earth, Mars, "
                        "Jupiter, Saturn, Uranus, Neptune, Pluto, Ceres, Eris, and the recently "
                        "discovered Planet X. Planet X was confirmed in 2023 and is now officially "
                        "recognized by astronomers as the 12th planet in our solar system."
                    ),
                    msg_type=MessageType.CORE_RESPONSE,
                    thinking="This is a test response with deliberately incorrect information to test the output classifier."
                )
                
                # Send directly to output classifier
                output_classifier.process_input(test_response)
                logger.info("Sent test response to output classifier")
            else:
                self.chat_widget.add_message(
                    "Error: Could not access pipeline components for testing.",
                    is_user=False
                )
        except (ValueError, RuntimeError, AttributeError, ImportError) as e:
            logger.error("Error in output classifier test: %s", str(e))
            self.chat_widget.add_message(
                f"Error testing output classifier: {str(e)}",
                is_user=False
            )

    def show_pipeline_status(self):
        """Show detailed status of the LLM pipeline in a dialog."""
        if not self.llm_pipeline:
            self.statusBar.showMessage("LLM pipeline not initialized", 3000)
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Pipeline Status")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Add header
        header = QLabel("LLM Pipeline Components and Connections")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)
        
        # Create text area for status
        status_text = QTextEdit()
        status_text.setReadOnly(True)
        layout.addWidget(status_text)
        
        # Generate status text
        status = "Pipeline Components:\n"
        for name, component in self.llm_pipeline.components.items():
            output_connections = [c.name for c in component.get_output_connections()]
            status += f"\n• {name} ({component.name})\n"
            status += f"  - Type: {component.__class__.__name__}\n"
            status += f"  - Outputs to: {', '.join(output_connections) if output_connections else 'None'}\n"
        
        status += "\n\nComponent Flow:\n"
        
        # Try to determine the actual flow
        flow = []
        if "ui" in self.llm_pipeline.components:
            component = self.llm_pipeline.components["ui"]
            flow.append(component.name)
            
            # Follow the connections
            while component.get_output_connections():
                next_component = component.get_output_connections()[0]
                flow.append(next_component.name)
                component = next_component
                
                # Avoid infinite loops
                if len(flow) > 10:
                    break
        
        status += " → ".join(flow)
        
        # Set the text
        status_text.setText(status)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        # Show dialog
        dialog.exec()

    def update_course_context(self):
        """Update the course context in the LLM when sidebar filters change."""
        if self.llm_pipeline:
            try:
                self.llm_pipeline.update_course_context()
                logger.info("Course context updated based on filter changes")
            except (AttributeError, RuntimeError) as e:
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

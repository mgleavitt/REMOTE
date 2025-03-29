"""
REMOTE (Remote Education Management and Organization Tool for Education)
Improved implementation with UI enhancements based on feedback.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, line-too-long, no-member, unused-import, too-many-lines, invalid-name

import sys
import os
from datetime import datetime, timedelta
import csv

# Import PySide6 classes
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QScrollArea, QFrame, QSplitter,
    QTextEdit, QCalendarWidget, QDialog, QListView, QAbstractItemView,
    QStyledItemDelegate, QGroupBox, QDateEdit, QToolTip, QCheckBox, QStyleOptionViewItem, QStyle, QSizePolicy, QMessageBox
)
from PySide6.QtCore import (
    Qt, QDate, Signal, QAbstractListModel, QModelIndex, QRect,
    QSize, QPoint, QSortFilterProxyModel, QPropertyAnimation, 
    QEasingCurve, Property, QObject, QEvent, QTimer
)
from PySide6.QtGui import (
    QIcon, QFontMetrics, QPainter, QColor, QBrush, QPen, QFont,
    QCursor, QPixmap, QStandardItemModel, QStandardItem
)

# Import data agent
from agents.data_agent_coursera_sim import DataAgentCourseraSim

# Import models
from models import ActivityModel, DateGroupProxyModel, ActivityFilterProxyModel, DateOnlyProxyModel

# Import delegates
from delegates import ActivityItemDelegate

# Constants and styling
from styles import (
    PRIMARY, PRIMARY_VARIANT, SECONDARY, SECONDARY_VARIANT,
    BACKGROUND, SURFACE, ERROR, ON_PRIMARY, ON_SECONDARY,
    ON_BACKGROUND, ON_SURFACE, ON_ERROR, CARD_BG, SIDEBAR_BG,
    HOVER_BG, SELECTED_BG, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY,
    get_stylesheet, get_material_palette
)

# Try to import Qt-Material, with fallback to custom stylesheets
try:
    from qt_material import apply_stylesheet
    HAS_QT_MATERIAL = True
except ImportError:
    HAS_QT_MATERIAL = False
    print("Qt-Material not found, falling back to custom stylesheets")

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

# UI Components



class MainWindow(QMainWindow):
    """Main application window for REMOTE"""
    def __init__(self):
        """Initialize the main window and its components."""
        super().__init__()
        self.setWindowTitle("REMOTE - Remote Education Management and Organization Tool for Education")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)  # Set minimum window size
        
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
    
    def create_chat_area(self):
        """Create the chat area with modern chat interface.
        
        Returns:
            The chat area widget
        """
        chat_widget = QWidget()
        chat_widget.setProperty("class", "chat-area")
        
        layout = QVBoxLayout(chat_widget)
        layout.setContentsMargins(16, 12, 16, 16)
        
        # Create modern chat widget
        self.chat = ChatWidget()
        layout.addWidget(self.chat)
        
        # Add sample messages
        self.add_sample_chat_messages()
        
        return chat_widget
    
    def add_sample_chat_messages(self):
        """Add sample messages to the chat."""
        self.chat.add_message("What was the slack discussion about Module 07 SQL Lab - ProblemSet02?", 
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
        self.chat.add_message(slack_response, is_user=False)
    
    def handle_slack_response(self, slack_response):
        """Handle the response from the Slack agent."""
        self.chat.add_message(slack_response, is_user=False)
    
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


if __name__ == "__main__":
    # Create the application
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())
    
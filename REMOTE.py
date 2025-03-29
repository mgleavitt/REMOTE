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
        self.sidebar = self.create_sidebar()
        self.sidebar_content_splitter.addWidget(self.sidebar)
        
        # Create main content area
        self.content_area = self.create_content_area()
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
        
        # Ensure icons directory exists
        if not os.path.exists(self.icons_dir):
            os.makedirs(self.icons_dir)
            self.create_default_icons()
        
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
        
    def create_sidebar(self):
        """Create the sidebar widget with class buttons and filters.
        
        Returns:
            The sidebar widget
        """
        sidebar = QWidget()
        sidebar.setProperty("class", "sidebar")
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Classes section
        classes_label = QLabel("Classes")
        classes_label.setProperty("class", "section-header")
        layout.addWidget(classes_label)
        
        # Class container for dynamic loading
        self.classes_container = QWidget()
        self.classes_layout = QVBoxLayout(self.classes_container)
        self.classes_layout.setContentsMargins(0, 0, 0, 0)
        self.classes_layout.setSpacing(4)
        
        # Add some default classes
        self.add_class("Database Management Systems", True)
        self.add_class("Human-Centered Artificial Intelligence", True)
        self.add_class("Data Science", True)
        
        layout.addWidget(self.classes_container)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setProperty("class", "separator")
        layout.addWidget(separator1)
        
        # Deadlines section
        deadlines_label = QLabel("Deadlines")
        deadlines_label.setProperty("class", "section-header")
        layout.addWidget(deadlines_label)
        
        deadlines_container = QWidget()
        deadlines_layout = QVBoxLayout(deadlines_container)
        deadlines_layout.setContentsMargins(0, 0, 0, 0)
        deadlines_layout.setSpacing(4)
        
        self.overdue_btn = FilterButton("Overdue", is_selected=True)
        self.overdue_btn.setToolTip("Include overdue assignments")
        self.submitted_btn = FilterButton("Submitted", is_selected=True)
        self.submitted_btn.setToolTip("Include submitted assignments")
        self.graded_btn = FilterButton("Graded", is_selected=True)
        self.graded_btn.setToolTip("Include graded assignments")
        self.due_btn = FilterButton("Due", is_selected=True)
        self.due_btn.setToolTip("Include due assignments")
        
        # Connect deadline filter buttons to update method
        self.overdue_btn.clicked.connect(self.update_activity_filters)
        self.submitted_btn.clicked.connect(self.update_activity_filters)
        self.graded_btn.clicked.connect(self.update_activity_filters)
        self.due_btn.clicked.connect(self.update_activity_filters)
        
        deadlines_layout.addWidget(self.overdue_btn)
        deadlines_layout.addWidget(self.submitted_btn)
        deadlines_layout.addWidget(self.graded_btn)
        deadlines_layout.addWidget(self.due_btn)
        
        layout.addWidget(deadlines_container)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setProperty("class", "separator")
        layout.addWidget(separator2)
        
        # Events section
        events_label = QLabel("Events")
        events_label.setProperty("class", "section-header")
        layout.addWidget(events_label)
        
        events_container = QWidget()
        events_layout = QVBoxLayout(events_container)
        events_layout.setContentsMargins(0, 0, 0, 0)
        events_layout.setSpacing(4)
        
        self.past_events_btn = FilterButton("Past", is_selected=False)
        self.past_events_btn.setToolTip("Include past events")
        self.now_events_btn = FilterButton("Now", is_selected=True)
        self.now_events_btn.setToolTip("Include current events")
        self.upcoming_events_btn = FilterButton("Upcoming", is_selected=True)
        self.upcoming_events_btn.setToolTip("Include upcoming events")
        
        # Connect event filter buttons to update method
        self.past_events_btn.clicked.connect(self.update_activity_filters)
        self.now_events_btn.clicked.connect(self.update_activity_filters)
        self.upcoming_events_btn.clicked.connect(self.update_activity_filters)
        
        events_layout.addWidget(self.past_events_btn)
        events_layout.addWidget(self.now_events_btn)
        events_layout.addWidget(self.upcoming_events_btn)
        
        layout.addWidget(events_container)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        return sidebar
    
    def add_class(self, name, is_selected=False):
        """Add a class button to the sidebar.
        
        Args:
            name (str): The name of the class
            is_selected (bool): Whether the class should be initially selected
        """
        class_btn = ClassButton(name, is_selected=is_selected)
        class_btn.setToolTip(f"Toggle {name} visibility")
        class_btn.clicked.connect(self.update_activity_filters)
        self.classes_layout.addWidget(class_btn)
    
    def create_content_area(self):
        """Create the main content area with activities.
        
        Returns:
            The content area widget
        """
        content_widget = QWidget()
        content_widget.setProperty("class", "content-area")
        
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Create header container to group title and date range
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 8)
        
        # Header with title
        header = QLabel("Key Activities")
        header.setProperty("class", "content-header")
        header_layout.addWidget(header)
        
        # Date range container widget to enable right alignment
        date_range_container = QWidget()
        date_range_container.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        
        # Date range layout inside container
        date_range_layout = QHBoxLayout(date_range_container)
        date_range_layout.setContentsMargins(0, 0, 0, 0)
        date_range_layout.setSpacing(16)
        
        # From date
        from_layout = QHBoxLayout()
        from_layout.setSpacing(8)
        from_label = QLabel("From date")
        from_label.setProperty("class", "date-label")
        self.from_date = CompactDateEdit()
        self.from_date.setDate(QDate.currentDate())
        self.from_date.dateChanged.connect(self.update_activity_filters)
        self.from_date.setToolTip("Select start date for filtering activities")
        
        from_layout.addWidget(from_label)
        from_layout.addWidget(self.from_date)
        
        # To date
        to_layout = QHBoxLayout()
        to_layout.setSpacing(8)
        to_label = QLabel("To date")
        to_label.setProperty("class", "date-label")
        self.to_date = CompactDateEdit()
        self.to_date.setDate(QDate.currentDate().addDays(14))
        self.to_date.dateChanged.connect(self.update_activity_filters)
        self.to_date.setToolTip("Select end date for filtering activities")
        
        to_layout.addWidget(to_label)
        to_layout.addWidget(self.to_date)
        
        # Add from and to layouts to date range layout
        date_range_layout.addLayout(from_layout)
        date_range_layout.addLayout(to_layout)
        
        # Add stretch to push header left and date range right
        header_layout.addStretch()
        header_layout.addWidget(date_range_container)
        
        layout.addWidget(header_container)
        
        # Scrollable area for activities
        self.activities_scroll = QScrollArea()
        self.activities_scroll.setWidgetResizable(True)
        self.activities_scroll.setFrameShape(QFrame.NoFrame)
        self.activities_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Container for activities
        self.activities_container = QWidget()
        self.activities_layout = QVBoxLayout(self.activities_container)
        self.activities_layout.setContentsMargins(0, 8, 0, 0)
        self.activities_layout.setSpacing(0)
        self.activities_layout.addStretch()
        
        self.activities_scroll.setWidget(self.activities_container)
        layout.addWidget(self.activities_scroll)
        
        return content_widget
    
    def populate_activity_dates(self):
        """Populate activities grouped by date in the content area."""
        # Clear current content
        self.clear_activities_layout()
        
        # Get unique dates from filtered model
        dates = set()
        for row in range(self.filter_proxy_model.rowCount()):
            index = self.filter_proxy_model.index(row, 0)
            date = self.filter_proxy_model.data(index, ActivityModel.DateRole)
            if date:
                dates.add(date)
        
        # If no dates (no matching activities), show a message
        if not dates:
            no_results_label = QLabel("No activities match the current filters")
            no_results_label.setAlignment(Qt.AlignCenter)
            no_results_label.setStyleSheet(f"color: {TEXT_SECONDARY}; margin: 20px;")
            self.activities_layout.insertWidget(self.activities_layout.count() - 1, no_results_label)
            return
        
        # Convert date strings to datetime objects for proper sorting
        date_objects = []
        for date_str in dates:
            try:
                # Parse date string (e.g., "Mar 16") to datetime
                date_obj = datetime.strptime(date_str, "%b %d")
                # Set year to current year
                date_obj = date_obj.replace(year=datetime.now().year)
                date_objects.append((date_str, date_obj))
            except ValueError:
                print(f"Warning: Could not parse date string: {date_str}")
                continue
        
        # Sort by datetime objects
        date_objects.sort(key=lambda x: x[1])
        
        # Create a date section for each unique date in chronological order
        for date_str, _ in date_objects:
            date_section = DateAccordionWidget(date_str, self.filter_proxy_model, self, self.icons_dir)
            self.activities_layout.insertWidget(self.activities_layout.count() - 1, date_section)
            date_section.update_content_height()
    
    def clear_activities_layout(self):
        """Clear all activities from the layout."""
        # Remove all widgets except the stretch at the end
        while self.activities_layout.count() > 1:
            item = self.activities_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def update_activity_filters(self):
        """Update activity filters based on selected classes and filters."""
        try:
            # Get selected courses
            selected_courses = set()
            for i in range(self.classes_layout.count()):
                widget = self.classes_layout.itemAt(i).widget()
                if isinstance(widget, ClassButton) and widget.isChecked():
                    selected_courses.add(widget.text())
            
            # Get filter states
            show_overdue = self.overdue_btn.isChecked()
            show_submitted = self.submitted_btn.isChecked()
            show_graded = self.graded_btn.isChecked()
            show_due = self.due_btn.isChecked()
            show_past_events = self.past_events_btn.isChecked()
            show_now_events = self.now_events_btn.isChecked()
            show_upcoming_events = self.upcoming_events_btn.isChecked()
            
            # Get date range
            from_date = self.from_date.date()
            to_date = self.to_date.date()
            
            # Update proxy model filters
            self.filter_proxy_model.set_filter_criteria(
                selected_courses=selected_courses,
                show_overdue=show_overdue,
                show_submitted=show_submitted,
                show_graded=show_graded,
                show_due=show_due,
                show_past_events=show_past_events,
                show_now_events=show_now_events,
                show_upcoming_events=show_upcoming_events,
                from_date=from_date,
                to_date=to_date
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
    
    def create_default_icons(self):
        """Create default SVG icons if they don't exist."""
        # Calendar icon
        calendar_svg = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
            <path d="M0 0h24v24H0V0z" fill="none"/>
            <path fill="#6200EE" d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V10h14v10zm0-12H5V6h14v2z"/>
        </svg>"""
        
        # Slack icon
        slack_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
            <path fill="#E01E5A" d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
        </svg>"""
        
        # Email icon
        email_svg = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
            <path d="M0 0h24v24H0V0z" fill="none"/>
            <path fill="#4285F4" d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V8l8 5 8-5v10zm-8-7L4 6h16l-8 5z"/>
        </svg>"""
        
        # Expand/Collapse icons
        expand_svg = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
            <path d="M0 0h24v24H0V0z" fill="none"/>
            <path fill="#555555" d="M12 8l-6 6 1.41 1.41L12 10.83l4.59 4.58L18 14l-6-6z"/>
        </svg>"""
        
        collapse_svg = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
            <path d="M0 0h24v24H0V0z" fill="none"/>
            <path fill="#555555" d="M16.59 8.59L12 13.17 7.41 8.59 6 10l6 6 6-6-1.41-1.41z"/>
        </svg>"""
        
        # Write the SVG files
        with open(os.path.join(self.icons_dir, "calendar.svg"), "w", encoding='utf-8') as f:
            f.write(calendar_svg)
        
        with open(os.path.join(self.icons_dir, "slack.svg"), "w", encoding='utf-8') as f:
            f.write(slack_svg)
        
        with open(os.path.join(self.icons_dir, "email.svg"), "w", encoding='utf-8') as f:
            f.write(email_svg)
        
        with open(os.path.join(self.icons_dir, "expand.svg"), "w", encoding='utf-8') as f:
            f.write(expand_svg)
        
        with open(os.path.join(self.icons_dir, "collapse.svg"), "w", encoding='utf-8') as f:
            f.write(collapse_svg)


if __name__ == "__main__":
    # Create the application
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())
    
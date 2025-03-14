"""Simple test application to verify PySide6 is working correctly.

This module creates a basic GUI window to test that PySide6 is properly installed and functioning.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, line-too-long, no-member

import sys
import os
#from datetime import datetime, timedelta

# Import only the PySide6 classes that are actually used in the code
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QScrollArea, QFrame, QSplitter,
    QTextEdit, QCalendarWidget, QDialog
)
from PySide6.QtCore import (
    Qt, QDate, Signal
)
from PySide6.QtGui import (
    QIcon
)

# Define a style module directly here since there's an import error
# This is a temporary solution until the style.py file can be properly imported

# Material Design color palette
PRIMARY = "#6200EE"
PRIMARY_VARIANT = "#3700B3" 
SECONDARY = "#03DAC6"
SECONDARY_VARIANT = "#018786"
BACKGROUND = "#FFFFFF"
SURFACE = "#FFFFFF"
ERROR = "#B00020"
ON_PRIMARY = "#FFFFFF"
ON_SECONDARY = "#000000"
ON_BACKGROUND = "#000000"
ON_SURFACE = "#000000"
ON_ERROR = "#FFFFFF"

# Additional colors
CARD_BG = "#FFFFFF"
SIDEBAR_BG = "#F0F0F5"
HOVER_BG = "#E8E8F0"
SELECTED_BG = "#E1D3F5"
BORDER_COLOR = "#E0E0E0"
TEXT_PRIMARY = "#333333"
TEXT_SECONDARY = "#666666"

def get_stylesheet():
    """Return the custom stylesheet for the application."""
    return f"""
        QMainWindow {{
            background-color: {BACKGROUND};
        }}
        
        .sidebar {{
            background-color: {SIDEBAR_BG};
            border-right: 1px solid {BORDER_COLOR};
        }}
        
        .content-area {{
            background-color: {SURFACE};
        }}
        
        .chat-area {{
            background-color: {BACKGROUND};
            border-top: 1px solid {BORDER_COLOR};
        }}
        
        .section-header {{
            font-size: 18px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin-bottom: 12px;
        }}
        
        .content-header {{
            font-size: 24px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin-bottom: 16px;
        }}
        
        .date-header {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
        }}
        
        .class-button {{
            background-color: {SIDEBAR_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 8px 12px;
            text-align: left;
            color: {TEXT_PRIMARY};
        }}
        
        .class-button:checked {{
            background-color: {SELECTED_BG};
            border-color: {PRIMARY};
            color: {PRIMARY};
        }}
        
        .class-button:hover {{
            background-color: {HOVER_BG};
        }}
        
        .filter-button {{
            background-color: {SIDEBAR_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 6px 12px;
            text-align: center;
            color: {TEXT_PRIMARY};
        }}
        
        .filter-button:checked {{
            background-color: {SELECTED_BG};
            border-color: {PRIMARY};
            color: {PRIMARY};
        }}
        
        .filter-button:hover {{
            background-color: {HOVER_BG};
        }}
        
        .activity-item {{
            background-color: {CARD_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 8px;
            padding: 12px;
            margin: 6px 0;
        }}
        
        .activity-item:hover {{
            border-color: {PRIMARY_VARIANT};
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .activity-title {{
            font-size: 15px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
        }}
        
        .activity-course {{
            font-size: 13px;
            color: {TEXT_SECONDARY};
        }}
        
        .activity-status {{
            font-size: 13px;
            color: {TEXT_SECONDARY};
            margin-left: 16px;
        }}
        
        .icon-button {{
            background-color: transparent;
            border: none;
            border-radius: 16px;
        }}
        
        .icon-button:hover {{
            background-color: rgba(0, 0, 0, 0.05);
        }}
        
        .separator {{
            color: {BORDER_COLOR};
        }}
        
        .chat-input {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 10px 16px;
            font-size: 14px;
            background-color: {SURFACE};
        }}
        
        .chat-display {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 16px;
            background-color: {SURFACE};
            font-size: 14px;
        }}
        
        .date-label {{
            font-size: 14px;
            color: {TEXT_SECONDARY};
            margin-bottom: 4px;
        }}
        
        .date-field {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 8px 12px;
            background-color: {SURFACE};
        }}
        
        QScrollBar:vertical {{
            border: none;
            background: {BACKGROUND};
            width: 8px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {BORDER_COLOR};
            border-radius: 4px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {PRIMARY_VARIANT};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            border: none;
            background: {BACKGROUND};
            height: 8px;
            margin: 0px;
        }}
        
        QScrollBar::handle:horizontal {{
            background: {BORDER_COLOR};
            border-radius: 4px;
            min-width: 30px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: {PRIMARY_VARIANT};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """

def get_material_palette():
    """Return a palette configuration for qt-material library."""
    return {
        'primary': PRIMARY,
        'primaryLightColor': PRIMARY_VARIANT,
        'secondaryColor': SECONDARY,
        'secondaryLightColor': SECONDARY_VARIANT,
        'secondaryDarkColor': SECONDARY_VARIANT,
        'primaryTextColor': ON_PRIMARY,
        'secondaryTextColor': ON_SECONDARY
    }

# Try to import Qt-Material, with fallback to custom stylesheets
try:
    from qt_material import apply_stylesheet
    HAS_QT_MATERIAL = True
except ImportError:
    HAS_QT_MATERIAL = False
    print("Qt-Material not found, falling back to custom stylesheets")


class CustomButton(QPushButton):
    """Modern styled button with hover effects"""
    def __init__(self, text="", parent=None, is_selected=False):
        """Initialize the custom button with styling.
        
        Args:
            text (str): Button text
            parent: Parent widget
            is_selected (bool): Whether the button should be initially selected
        """
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(is_selected)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "modern-button")
        

class ClassButton(CustomButton):
    """Button for selecting classes in the sidebar"""
    def __init__(self, text="", parent=None, is_selected=False):
        """Initialize the class button.
        
        Args:
            text (str): Button text
            parent: Parent widget
            is_selected (bool): Whether the button should be initially selected
        """
        super().__init__(text, parent, is_selected)
        self.setProperty("class", "class-button")
        

class FilterButton(CustomButton):
    """Button for filter options"""
    def __init__(self, text="", parent=None, is_selected=False):
        """Initialize the filter button.
        
        Args:
            text (str): Button text
            parent: Parent widget
            is_selected (bool): Whether the button should be initially selected
        """
        super().__init__(text, parent, is_selected)
        self.setProperty("class", "filter-button")


class DatePickerDialog(QDialog):
    """Modern date picker dialog"""
    def __init__(self, parent=None, initial_date=None):
        """Initialize the date picker dialog.
        
        Args:
            parent: Parent widget
            initial_date: Initial date to display
        """
        super().__init__(parent)
        self.setWindowTitle("Select Date")
        
        if initial_date:
            self.selected_date = initial_date
        else:
            self.selected_date = QDate.currentDate()
            
        self.layout = QVBoxLayout(self)
        
        # Calendar widget
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(self.selected_date)
        self.calendar.clicked.connect(self.on_date_clicked)
        self.layout.addWidget(self.calendar)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        # OK button
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.layout.addLayout(button_layout)
        
        # Apply some styling
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #6200EE;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7722FF;
            }
            QCalendarWidget {
                background-color: white;
                selection-background-color: #6200EE;
            }
        """)
        
        # Set fixed size
        self.setFixedSize(350, 400)
        
    def on_date_clicked(self, date):
        """Handle date selection in the calendar.
        
        Args:
            date: The selected date
        """
        self.selected_date = date
        
    def get_selected_date(self):
        """Get the currently selected date.
        
        Returns:
            The selected date
        """
        return self.selected_date


class DateSelector(QWidget):
    """Custom date selector with modern appearance"""
    date_changed = Signal(QDate)
    
    def __init__(self, label_text="Date", parent=None):
        """Initialize the date selector.
        
        Args:
            label_text (str): Label text for the selector
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Get the main window to access icons_dir
        main_window = self.get_main_window()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Label
        self.label = QLabel(label_text)
        self.label.setProperty("class", "date-label")
        self.layout.addWidget(self.label)
        
        # Date display with icon
        self.date_layout = QHBoxLayout()
        
        self.date_field = QLineEdit()
        self.date_field.setReadOnly(True)
        self.date_field.setPlaceholderText("mm/dd/yyyy")
        self.date_field.setProperty("class", "date-field")
        
        self.calendar_btn = QPushButton()
        if main_window:
            icon_path = os.path.join(main_window.icons_dir, "calendar.svg")
            self.calendar_btn.setIcon(QIcon(icon_path))
        else:
            self.calendar_btn.setText("📅")  # Fallback to emoji
        self.calendar_btn.setFixedSize(36, 36)
        self.calendar_btn.setCursor(Qt.PointingHandCursor)
        self.calendar_btn.setProperty("class", "icon-button")
        self.calendar_btn.clicked.connect(self.show_date_picker)
        
        self.date_layout.addWidget(self.date_field)
        self.date_layout.addWidget(self.calendar_btn)
        
        self.layout.addLayout(self.date_layout)
        
        # Set initial date to today
        self.current_date = QDate.currentDate()
        self.update_display()
    
    def get_main_window(self):
        """Get the main window instance to access icons_dir."""
        parent = self.parent()
        while parent:
            if isinstance(parent, MainWindow):
                return parent
            parent = parent.parent()
        return None
    
    def show_date_picker(self):
        """Show the date picker dialog."""
        dialog = DatePickerDialog(self, self.current_date)
        if dialog.exec():
            self.current_date = dialog.get_selected_date()
            self.update_display()
            self.date_changed.emit(self.current_date)
    
    def update_display(self):
        """Update the date display field with the current date."""
        self.date_field.setText(self.current_date.toString("MM/dd/yyyy"))
    
    def get_date(self):
        """Get the currently selected date.
        
        Returns:
            The current date
        """
        return self.current_date
    
    def set_date(self, date):
        """Set the current date.
        
        Args:
            date: The date to set
        """
        self.current_date = date
        self.update_display()


class ActivityItem(QFrame):
    """Widget representing a single activity item"""
    def __init__(self, title, course, status, parent=None, has_slack=False, has_email=False):
        """Initialize the activity item.
        
        Args:
            title (str): Activity title
            course (str): Course name
            status (str): Activity status
            parent: Parent widget
            has_slack (bool): Whether the activity has Slack notifications
            has_email (bool): Whether the activity has email notifications
        """
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setProperty("class", "activity-item")
        
        # Get the main window to access icons_dir
        main_window = self.get_main_window()
        
        # Main layout
        self.layout = QHBoxLayout(self)
        
        # Activity information layout
        info_layout = QVBoxLayout()
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "activity-title")
        info_layout.addWidget(self.title_label)
        
        # Course and status
        course_status_layout = QHBoxLayout()
        self.course_label = QLabel(course)
        self.course_label.setProperty("class", "activity-course")
        self.status_label = QLabel(f"Status: {status}")
        self.status_label.setProperty("class", "activity-status")
        
        course_status_layout.addWidget(self.course_label)
        course_status_layout.addWidget(self.status_label)
        course_status_layout.addStretch()
        
        info_layout.addLayout(course_status_layout)
        self.layout.addLayout(info_layout)
        
        # Notification icons
        icon_layout = QVBoxLayout()
        
        # Slack notification
        if has_slack:
            self.slack_btn = QPushButton()
            if main_window:
                icon_path = os.path.join(main_window.icons_dir, "slack.svg")
                self.slack_btn.setIcon(QIcon(icon_path))
            else:
                self.slack_btn.setText("S")  # Fallback
            self.slack_btn.setFixedSize(32, 32)
            self.slack_btn.setProperty("class", "icon-button")
            self.slack_btn.setCursor(Qt.PointingHandCursor)
            icon_layout.addWidget(self.slack_btn)
        
        # Email notification
        if has_email:
            self.email_btn = QPushButton()
            if main_window:
                icon_path = os.path.join(main_window.icons_dir, "email.svg")
                self.email_btn.setIcon(QIcon(icon_path))
            else:
                self.email_btn.setText("E")  # Fallback
            self.email_btn.setFixedSize(32, 32)
            self.email_btn.setProperty("class", "icon-button")
            self.email_btn.setCursor(Qt.PointingHandCursor)
            icon_layout.addWidget(self.email_btn)
        
        icon_layout.addStretch()
        self.layout.addLayout(icon_layout)
    
    def get_main_window(self):
        """Get the main window instance to access icons_dir."""
        parent = self.parent()
        while parent:
            if isinstance(parent, MainWindow):
                return parent
            parent = parent.parent()
        return None


class DateSection(QWidget):
    """Widget representing activities for a specific date"""
    def __init__(self, date_text, parent=None):
        """Initialize the date section.
        
        Args:
            date_text (str): Date text to display
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Get the main window to access icons_dir
        main_window = self.get_main_window()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Date header
        header_layout = QHBoxLayout()
        self.expand_btn = QPushButton()
        if main_window:
            icon_path = os.path.join(main_window.icons_dir, "expand.svg")
            self.expand_btn.setIcon(QIcon(icon_path))
        else:
            self.expand_btn.setText("▲")  # Fallback
        self.expand_btn.setFixedSize(24, 24)
        self.expand_btn.setCheckable(True)
        self.expand_btn.setChecked(True)
        self.expand_btn.clicked.connect(self.toggle_expand)
        
        self.date_label = QLabel(date_text)
        self.date_label.setProperty("class", "date-header")
        
        header_layout.addWidget(self.expand_btn)
        header_layout.addWidget(self.date_label)
        header_layout.addStretch()
        
        self.layout.addLayout(header_layout)
        
        # Activities container
        self.activities_widget = QWidget()
        self.activities_layout = QVBoxLayout(self.activities_widget)
        self.activities_layout.setContentsMargins(16, 0, 0, 0)
        
        self.layout.addWidget(self.activities_widget)
        
        # Add a separator line
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setProperty("class", "separator")
        self.layout.addWidget(self.separator)
    
    def get_main_window(self):
        """Get the main window instance to access icons_dir."""
        parent = self.parent()
        while parent:
            if isinstance(parent, MainWindow):
                return parent
            parent = parent.parent()
        return None
    
    def add_activity(self, activity):
        """Add an activity to this date section.
        
        Args:
            activity: The activity widget to add
        """
        self.activities_layout.addWidget(activity)
    
    def toggle_expand(self):
        """Toggle the expanded/collapsed state of the activities section."""
        self.activities_widget.setVisible(self.expand_btn.isChecked())
        main_window = self.get_main_window()
        if self.expand_btn.isChecked():
            if main_window:
                icon_path = os.path.join(main_window.icons_dir, "expand.svg")
                self.expand_btn.setIcon(QIcon(icon_path))
            else:
                self.expand_btn.setText("▲")  # Fallback
        else:
            if main_window:
                icon_path = os.path.join(main_window.icons_dir, "collapse.svg")
                self.expand_btn.setIcon(QIcon(icon_path))
            else:
                self.expand_btn.setText("▼")  # Fallback


class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        """Initialize the main window and its components."""
        super().__init__()
        self.setWindowTitle("Academic Information Hub")
        self.resize(1200, 800)
        
        # Get the absolute path to the icons directory
        self.icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        
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
        
        # Set initial splitter sizes
        self.sidebar_content_splitter.setSizes([250, 950])
        
        # Add sidebar and content splitter to the main vertical splitter
        self.content_chat_splitter.addWidget(self.sidebar_content_splitter)
        
        # Create chat area
        self.chat_area = self.create_chat_area()
        self.content_chat_splitter.addWidget(self.chat_area)
        
        # Set initial sizes for content and chat areas
        self.content_chat_splitter.setSizes([600, 200])
        
        # Add the splitters to the main layout
        self.main_layout.addWidget(self.content_chat_splitter)
        
        # Ensure icons directory exists
        if not os.path.exists(self.icons_dir):
            os.makedirs(self.icons_dir)
            self.create_default_icons()
        
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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Classes section
        classes_label = QLabel("Classes")
        classes_label.setProperty("class", "section-header")
        layout.addWidget(classes_label)
        
        # Class buttons
        self.db_class_btn = ClassButton("Database Management Systems", is_selected=True)
        self.ai_class_btn = ClassButton("Human-Centered Artificial Intelligence", is_selected=True)
        self.ds_class_btn = ClassButton("Data Science")
        
        layout.addWidget(self.db_class_btn)
        layout.addWidget(self.ai_class_btn)
        layout.addWidget(self.ds_class_btn)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setProperty("class", "separator")
        layout.addWidget(separator)
        
        # Filters section
        filters_layout = QHBoxLayout()
        
        # Left column
        filter_col1 = QVBoxLayout()
        self.deadlines_btn = FilterButton("Deadlines", is_selected=True)
        self.submitted_btn = FilterButton("Submitted")
        self.graded_btn = FilterButton("Graded")
        
        filter_col1.addWidget(self.deadlines_btn)
        filter_col1.addWidget(self.submitted_btn)
        filter_col1.addWidget(self.graded_btn)
        
        # Right column
        filter_col2 = QVBoxLayout()
        self.overdue_btn = FilterButton("Overdue")
        self.live_events_btn = FilterButton("Live Events")
        self.past_btn = FilterButton("Past")
        
        filter_col2.addWidget(self.overdue_btn)
        filter_col2.addWidget(self.live_events_btn)
        filter_col2.addWidget(self.past_btn)
        
        filters_layout.addLayout(filter_col1)
        filters_layout.addLayout(filter_col2)
        
        layout.addLayout(filters_layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        return sidebar
    
    def create_content_area(self):
        """Create the main content area with activities.
        
        Returns:
            The content area widget
        """
        content_widget = QWidget()
        content_widget.setProperty("class", "content-area")
        
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header with title
        header = QLabel("Key Activities")
        header.setProperty("class", "content-header")
        layout.addWidget(header)
        
        # Date range selectors
        date_range_layout = QHBoxLayout()
        
        self.from_date = DateSelector("From date")
        self.to_date = DateSelector("To date")
        
        # Set default date range (today to 2 weeks from now)
        today = QDate.currentDate()
        two_weeks = today.addDays(14)
        self.to_date.set_date(two_weeks)
        
        date_range_layout.addWidget(self.from_date)
        date_range_layout.addSpacing(24)
        date_range_layout.addWidget(self.to_date)
        date_range_layout.addStretch()
        
        layout.addLayout(date_range_layout)
        
        # Scrollable area for activities
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Container for activities
        activities_container = QWidget()
        self.activities_layout = QVBoxLayout(activities_container)
        
        # Create sample activity sections
        march13_section = DateSection("Mar 13")
        
        # Add activities to March 13
        activity1 = ActivityItem("TA Office Hours", 
                              "Database Management Systems", 
                              "Scheduled", has_slack=True, has_email=True)
        activity2 = ActivityItem("Assignment: Module 07 SQL Lab - ProblemSet02", 
                              "Database Management Systems", 
                              "Submitted", has_slack=True, has_email=True)
        activity3 = ActivityItem("Assignment: Module 7 Quiz: Introduction to SQL", 
                              "Database Management Systems", 
                              "Graded (90%)", has_slack=True, has_email=True)
        activity4 = ActivityItem("Assignment: Final Project Checkpoint #2: Project Execution", 
                              "Human-Centered Artificial Intelligence", 
                              "Due [due date/time]", has_slack=True, has_email=True)
        
        march13_section.add_activity(activity1)
        march13_section.add_activity(activity2)
        march13_section.add_activity(activity3)
        march13_section.add_activity(activity4)
        
        # Add March 14 section (empty for now)
        march14_section = DateSection("Mar 14")
        
        # Add March 16 section (empty for now)
        march16_section = DateSection("Mar 16")
        
        # Add sections to the activities layout
        self.activities_layout.addWidget(march13_section)
        self.activities_layout.addWidget(march14_section)
        self.activities_layout.addWidget(march16_section)
        
        # Add stretch to push everything to the top
        self.activities_layout.addStretch()
        
        scroll_area.setWidget(activities_container)
        layout.addWidget(scroll_area)
        
        return content_widget
    
    def create_chat_area(self):
        """Create the chat area with input and display.
        
        Returns:
            The chat area widget
        """
        chat_widget = QWidget()
        chat_widget.setProperty("class", "chat-area")
        
        layout = QVBoxLayout(chat_widget)
        layout.setContentsMargins(24, 16, 24, 24)
        
        # Chat input
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("What was the slack discussion about Module 07 SQL Lab - ProblemSet02?")
        self.chat_input.setProperty("class", "chat-input")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setProperty("class", "chat-display")
        
        # Add sample response
        sample_response = (
            "On Monday, March 10th at 1:56 PM PDT, Marc Leavitt posted:\n"
            "Here's some more fun--turns out that if you downloaded 'Module 07 SQL Lab - ProblemSet02' too early (like I apparently did), the expected output for Problem 13 is wrong.\n"
            "1. If you haven't downloaded ProblemSet02 yet, you can stop reading and carry on\n"
            "2. If you have downloaded ProblemSet02, check the 'ProblemSet02-Problem13.sql' file. The expected output should look like the following:\n"
            "-- +---------------------+---------------------+---------------------+\n"
            "-- | Minimum Balance     | Maximum Balance     | Average Balance     |\n"
            "-- +---------------------+---------------------+---------------------+\n"
            "-- |       0.00          |      345.86         |      112.48         |\n"
            "-- +---------------------+---------------------+---------------------+\n"
            "The only difference is the expected value for 'Average Balance'. The right answer is 112.48, as above. The 'old' version had 70.30 in that column.\n"
            "So, if you see 70.30 there, I suggest that you save/protect your existing work, download the new(er) zip file, and pull the updated Problem 13 file\n"
            "(Koushik confirmed that the fix to Problem 13 was the only change)."
        )
        self.chat_display.setText(sample_response)
        
        layout.addWidget(self.chat_display)
        layout.addWidget(self.chat_input)
        
        return chat_widget
    
    def send_chat_message(self):
        """Process and send a chat message."""
        message = self.chat_input.text()
        if message:
            # In a real app, we would process this message and get a response
            # For now, just clear the input
            self.chat_input.clear()
    
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
    
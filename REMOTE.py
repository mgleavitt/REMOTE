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

# UI Components
class ActivityItemDelegate(QStyledItemDelegate):
    """Custom delegate for rendering activity items"""
    
    def __init__(self, parent=None, icons_dir=None):
        """Initialize the activity item delegate."""
        super().__init__(parent)
        self.icons_dir = icons_dir
        self._slack_icon = None
        self._email_icon = None
        
        # Load icons
        if self.icons_dir:
            slack_path = os.path.join(self.icons_dir, "slack.svg")
            email_path = os.path.join(self.icons_dir, "email.svg")
            
            if os.path.exists(slack_path):
                self._slack_icon = QIcon(slack_path)
            
            if os.path.exists(email_path):
                self._email_icon = QIcon(email_path)
    
    def sizeHint(self, option, index):  # pylint: disable=invalid-name,unused-argument
        """Return the size hint for the item."""
        return QSize(option.rect.width(), 70)
    
    def paint(self, painter, option, index):
        """Paint the item."""
        # Extract data from model
        title = index.data(ActivityModel.TitleRole)
        course = index.data(ActivityModel.CourseRole)
        status = index.data(ActivityModel.StatusRole)
        has_slack = index.data(ActivityModel.HasSlackRole)
        has_email = index.data(ActivityModel.HasEmailRole)
        event_type = index.data(ActivityModel.EventTypeRole)
        start_time = index.data(ActivityModel.StartTimeRole)
        
        # Set up the painter
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Check if item is selected
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor(SELECTED_BG))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, QColor(HOVER_BG))
        else:
            painter.fillRect(option.rect, QColor(CARD_BG))
        
        # Draw border with more consistent style
        painter.setPen(QPen(QColor(BORDER_COLOR)))
        painter.drawRect(option.rect.adjusted(2, 2, -2, -2))
        
        # Set up text rectangles
        content_rect = option.rect.adjusted(10, 8, -10, -8)
        title_rect = QRect(content_rect.left(), content_rect.top(), 
                        content_rect.width() - 60, 20)
        
        info_rect = QRect(content_rect.left(), title_rect.bottom() + 2,
                        content_rect.width() - 60, 20)
        
        status_rect = QRect(content_rect.left(), info_rect.bottom() + 2,
                        content_rect.width() - 60, 16)
        
        # Draw title
        painter.setPen(QPen(QColor(TEXT_PRIMARY)))
        painter.setFont(QFont(option.font.family(), 10, QFont.Bold))
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, 
                    f"{event_type}: {title}")
        
        # Draw course
        painter.setPen(QPen(QColor(TEXT_SECONDARY)))
        painter.setFont(QFont(option.font.family(), 9))
        painter.drawText(info_rect, Qt.AlignLeft | Qt.AlignVCenter, course)
        
        # Draw status
        painter.drawText(status_rect, Qt.AlignLeft | Qt.AlignVCenter, 
                    f"Status: {status} • {start_time}")
        
        # Draw icons only if has_slack or has_email is True (not None)
        icon_size = 20  # Reduced size
        icon_spacing = 4  # Space between icons
        icon_y = content_rect.top() + (content_rect.height() - icon_size) // 2
        
        # Calculate positions with better spacing
        icon_x = content_rect.right() - icon_size
        
        # Email icon
        if has_email is True and self._email_icon:
            email_rect = QRect(icon_x, icon_y, icon_size, icon_size)
            self._email_icon.paint(painter, email_rect)
            icon_x -= (icon_size + icon_spacing)
        
        # Slack icon 
        if has_slack is True and self._slack_icon:
            slack_rect = QRect(icon_x, icon_y, icon_size, icon_size)
            self._slack_icon.paint(painter, slack_rect)
        
        painter.restore()

    def helpEvent(self, event, view, option, index):
        """Handle tooltip events."""
        if event.type() != QEvent.ToolTip:
            return False

        has_slack = index.data(ActivityModel.HasSlackRole)
        has_email = index.data(ActivityModel.HasEmailRole)
        
        # Get item geometry
        content_rect = option.rect.adjusted(10, 8, -10, -8)
        icon_size = 20
        icon_spacing = 4
        
        # Calculate positions with better spacing
        icon_x = content_rect.right() - icon_size
        icon_y = content_rect.top() + (content_rect.height() - icon_size) // 2
        
        # Email icon rect
        email_rect = QRect(icon_x, icon_y, icon_size, icon_size)
        
        # Slack icon rect (to the left of email)
        slack_rect = QRect(icon_x - (icon_size + icon_spacing), icon_y, icon_size, icon_size)
        
        # Get mouse position relative to the item
        mouse_pos = event.pos()  # QHelpEvent uses pos()
        
        # Check if mouse is over any icon
        over_email = has_email and email_rect.contains(mouse_pos)
        over_slack = has_slack and slack_rect.contains(mouse_pos)
        
        if over_email:
            QToolTip.showText(event.globalPos(), "View related emails", view)
            return True
        elif over_slack:
            QToolTip.showText(event.globalPos(), "View Slack discussions", view)
            return True
        else:
            QToolTip.hideText()
            
        return super().helpEvent(event, view, option, index)

    def editorEvent(self, event, model, option, index):
        """Handle editor events (mouse over, etc.)."""
        # We need this for cursor changes and clicks
        if event.type() in [QEvent.MouseMove, QEvent.MouseButtonRelease]:
            has_slack = index.data(ActivityModel.HasSlackRole)
            has_email = index.data(ActivityModel.HasEmailRole)
            
            # Get item geometry
            content_rect = option.rect.adjusted(10, 8, -10, -8)
            icon_size = 20
            icon_spacing = 4
            
            # Calculate positions with better spacing
            icon_x = content_rect.right() - icon_size
            icon_y = content_rect.top() + (content_rect.height() - icon_size) // 2
            
            # Email icon rect
            email_rect = QRect(icon_x, icon_y, icon_size, icon_size)
            
            # Slack icon rect (to the left of email)
            slack_rect = QRect(icon_x - (icon_size + icon_spacing), icon_y, icon_size, icon_size)
            
            # Get mouse position relative to the item
            mouse_pos = event.position().toPoint()
            
            # Check if mouse is over any icon
            over_email = has_email and email_rect.contains(mouse_pos)
            over_slack = has_slack and slack_rect.contains(mouse_pos)
            
            if event.type() == QEvent.MouseMove:
                if over_email or over_slack:
                    option.widget.setCursor(Qt.PointingHandCursor)
                else:
                    option.widget.setCursor(Qt.ArrowCursor)
            
            # Handle clicks - as a fallback if tooltips don't work
            elif event.type() == QEvent.MouseButtonRelease:
                if over_email:
                    title = index.data(ActivityModel.TitleRole)
                    course = index.data(ActivityModel.CourseRole)
                    QMessageBox.information(option.widget, 
                                          "Email Action", 
                                          f"View emails related to:\n{title}\nCourse: {course}",
                                          QMessageBox.Ok)
                    return True
                elif over_slack:
                    title = index.data(ActivityModel.TitleRole)
                    course = index.data(ActivityModel.CourseRole)
                    QMessageBox.information(option.widget, 
                                          "Slack Action", 
                                          f"View Slack discussions for:\n{title}\nCourse: {course}",
                                          QMessageBox.Ok)
                    return True
        
        return super().editorEvent(event, model, option, index)


class DateAccordionWidget(QWidget):
    """Widget for displaying activities grouped by date with accordion effect"""
    
    def __init__(self, date, model, parent=None, icons_dir=None):
        """Initialize the date accordion widget."""
        super().__init__(parent)
        self.date = date
        self.model = model
        self.expanded = True
        self.icons_dir = icons_dir
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header widget with explicit styling
        self.header_widget = QWidget()
        self.header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {BACKGROUND};
                border-bottom: 1px solid {BORDER_COLOR};
            }}
        """)
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(8, 4, 8, 4)
        
        # Expand/collapse button
        self.expand_btn = QPushButton()
        self.expand_btn.setFixedSize(20, 20)
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setProperty("class", "icon-button")
        self.expand_btn.clicked.connect(self.toggle_expand)
        
        # Set icon based on directory
        if self.icons_dir:
            icon_path = os.path.join(self.icons_dir, "expand.svg")
            if os.path.exists(icon_path):
                self.expand_btn.setIcon(QIcon(icon_path))
        else:
            self.expand_btn.setText("▲")
        
        # Date label with explicit styling
        self.date_label = QLabel(self.date)
        self.date_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {TEXT_PRIMARY};
                padding: 4px 8px;
                background-color: {BACKGROUND};
            }}
        """)
        
        self.header_layout.addWidget(self.expand_btn)
        self.header_layout.addWidget(self.date_label)
        self.header_layout.addStretch()
        
        self.layout.addWidget(self.header_widget)
        
        # Content widget (activities list)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 0, 0, 0)
        self.content_layout.setSpacing(2)
        
        # Create list view for activities
        self.list_view = QListView()
        self.list_view.setFrameShape(QFrame.NoFrame)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_view.setFocusPolicy(Qt.NoFocus)
        
        # Critical for tooltips and mouse tracking
        self.list_view.setMouseTracking(True)
        self.list_view.viewport().setAttribute(Qt.WA_MouseTracking, True)
        self.list_view.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.list_view.viewport().setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # Set up the model
        self.date_only_model = DateOnlyProxyModel(self.date, self)
        self.date_only_model.setSourceModel(self.model)
        self.list_view.setModel(self.date_only_model)
        
        # Set up delegate
        self.delegate = ActivityItemDelegate(self, self.icons_dir)
        self.list_view.setItemDelegate(self.delegate)
        
        # Install event filter to handle tooltips
        self.list_view.viewport().installEventFilter(self)
        
        self.content_layout.addWidget(self.list_view)
        
        self.layout.addWidget(self.content_widget)
        
        # Update the content height
        self.update_content_height()
    
    def eventFilter(self, obj, event):
        """Filter events for child widgets."""
        if obj == self.list_view.viewport():
            if event.type() == QEvent.ToolTip:
                # Get index at position
                index = self.list_view.indexAt(event.pos())
                if not index.isValid():
                    return False
                
                # Get item geometry
                rect = self.list_view.visualRect(index)
                
                # Get icon positions
                has_slack = index.data(ActivityModel.HasSlackRole)
                has_email = index.data(ActivityModel.HasEmailRole)
                
                # Calculate content rect
                content_rect = rect.adjusted(10, 8, -10, -8)
                icon_size = 20
                icon_spacing = 4
                
                # Calculate positions with better spacing
                icon_x = content_rect.right() - icon_size
                icon_y = content_rect.top() + (content_rect.height() - icon_size) // 2
                
                # Email icon rect
                email_rect = QRect(icon_x, icon_y, icon_size, icon_size)
                
                # Slack icon rect (to the left of email)
                slack_rect = QRect(icon_x - (icon_size + icon_spacing), icon_y, icon_size, icon_size)
                
                # Get mouse position relative to the item
                mouse_pos = event.pos() - rect.topLeft()
                
                # Check if mouse is over any icon
                over_email = has_email and email_rect.contains(mouse_pos)
                over_slack = has_slack and slack_rect.contains(mouse_pos)
                
                if over_email:
                    QToolTip.showText(event.globalPos(), "View related emails", self.list_view)
                    return True
                elif over_slack:
                    QToolTip.showText(event.globalPos(), "View Slack discussions", self.list_view)
                    return True
                else:
                    QToolTip.hideText()
                
        return super().eventFilter(obj, event)
    
    def update_content_height(self):
        """Update the height of the content widget based on list view contents."""
        if not self.expanded:
            return
        
        total_height = 0
        option = QStyleOptionViewItem()
        for i in range(self.date_only_model.rowCount()):
            index = self.date_only_model.index(i, 0)
            total_height += self.delegate.sizeHint(option, index).height() + 2
        
        self.list_view.setFixedHeight(total_height)
        self.content_widget.setFixedHeight(total_height)
    
    def toggle_expand(self):
        """Toggle the expanded/collapsed state."""
        self.expanded = not self.expanded
        self.content_widget.setVisible(self.expanded)
        
        # Update icon
        if self.expanded:
            if self.icons_dir:
                icon_path = os.path.join(self.icons_dir, "expand.svg")
                if os.path.exists(icon_path):
                    self.expand_btn.setIcon(QIcon(icon_path))
            else:
                self.expand_btn.setText("▲")
        else:
            if self.icons_dir:
                icon_path = os.path.join(self.icons_dir, "collapse.svg")
                if os.path.exists(icon_path):
                    self.expand_btn.setIcon(QIcon(icon_path))
            else:
                self.expand_btn.setText("▼")


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
    
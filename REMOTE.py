"""
REMOTE (Remote Education Management and Organization Tool for Education)
Improved implementation with UI enhancements based on feedback.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, line-too-long, no-member, unused-import

import sys
import os
from datetime import datetime, timedelta
import csv

# Import PySide6 classes
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QScrollArea, QFrame, QSplitter,
    QTextEdit, QCalendarWidget, QDialog, QListView, QAbstractItemView,
    QStyledItemDelegate, QGroupBox, QDateEdit, QToolTip, QCheckBox
)
from PySide6.QtCore import (
    Qt, QDate, Signal, QAbstractListModel, QModelIndex, QRect,
    QSize, QPoint, QSortFilterProxyModel, QPropertyAnimation, 
    QEasingCurve, Property, QObject
)
from PySide6.QtGui import (
    QIcon, QFontMetrics, QPainter, QColor, QBrush, QPen, QFont,
    QCursor, QPixmap, QStandardItemModel, QStandardItem
)

# Define a style module directly here
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
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin-bottom: 8px;
        }}
        
        .content-header {{
            font-size: 20px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin-bottom: 12px;
        }}
        
        .date-header {{
            font-size: 14px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
        }}
        
        .class-button {{
            background-color: {SIDEBAR_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 6px 10px;
            text-align: left;
            color: {TEXT_PRIMARY};
            margin-bottom: 4px;
        }}
        
        .class-button:checked {{
            background-color: {SELECTED_BG};
            border-color: {PRIMARY};
            color: {PRIMARY};
        }}
        
        .class-button:hover {{
            background-color: {HOVER_BG};
        }}
        
        .filter-group {{
            margin-top: 8px;
            margin-bottom: 8px;
        }}
        
        .filter-button {{
            background-color: {SIDEBAR_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
            text-align: left;
            color: {TEXT_PRIMARY};
            margin-bottom: 2px;
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
            border-radius: 6px;
            padding: 8px;
            margin: 2px 0;
        }}
        
        .activity-item:hover {{
            border-color: {PRIMARY_VARIANT};
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}
        
        .activity-title {{
            font-size: 14px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
        }}
        
        .activity-course {{
            font-size: 12px;
            color: {TEXT_SECONDARY};
        }}
        
        .activity-status {{
            font-size: 12px;
            color: {TEXT_SECONDARY};
            margin-left: 12px;
        }}
        
        .icon-button {{
            background-color: transparent;
            border: none;
            border-radius: 16px;
            min-width: 24px;
            max-width: 24px;
            min-height: 24px;
            max-height: 24px;
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
            padding: 8px 12px;
            font-size: 13px;
            background-color: {SURFACE};
        }}
        
        .chat-display {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 12px;
            background-color: {SURFACE};
            font-size: 13px;
        }}
        
        .date-label {{
            font-size: 13px;
            color: {TEXT_SECONDARY};
            margin-bottom: 2px;
        }}
        
        .date-field {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
            background-color: {SURFACE};
        }}
        
        QDateEdit {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
            background-color: {SURFACE};
        }}
        
        QGroupBox {{
            border: 1px solid {BORDER_COLOR};
            border-radius: 4px;
            margin-top: 14px;
            font-weight: bold;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 8px;
            padding: 0 3px;
        }}
        
        QScrollBar:vertical {{
            border: none;
            background: {BACKGROUND};
            width: 6px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {BORDER_COLOR};
            border-radius: 3px;
            min-height: 20px;
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
            height: 6px;
            margin: 0px;
        }}
        
        QScrollBar::handle:horizontal {{
            background: {BORDER_COLOR};
            border-radius: 3px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: {PRIMARY_VARIANT};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        .chat-message {{
            background-color: {BACKGROUND};
            border-radius: 12px;
            padding: 8px 12px;
            margin: 4px 0;
        }}
        
        .chat-message-user {{
            background-color: {SELECTED_BG};
            border-radius: 12px;
            padding: 8px 12px;
            margin: 4px 0;
            text-align: right;
        }}
        
        .chat-header {{
            font-size: 16px;
            font-weight: bold;
            color: {TEXT_PRIMARY};
            margin-bottom: 6px;
        }}
    """

# Try to import Qt-Material, with fallback to custom stylesheets
try:
    from qt_material import apply_stylesheet
    HAS_QT_MATERIAL = True
except ImportError:
    HAS_QT_MATERIAL = False
    print("Qt-Material not found, falling back to custom stylesheets")


# Models
class ActivityModel(QAbstractListModel):
    """Data model for activities"""
    
    DateRole = Qt.UserRole + 1
    EventTypeRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    CourseRole = Qt.UserRole + 4
    StatusRole = Qt.UserRole + 5
    DurationWeightRole = Qt.UserRole + 6
    StartTimeRole = Qt.UserRole + 7
    HasSlackRole = Qt.UserRole + 8
    HasEmailRole = Qt.UserRole + 9
    
    def __init__(self, parent=None):
        """Initialize the activity model."""
        super().__init__(parent)
        self._activities = []
        
    def row_count(self, parent=QModelIndex()): # pylint: disable=unused-argument
        """Return the number of rows in the model."""
        return len(self._activities)
    
    def data(self, index, role=Qt.DisplayRole):
        """Return data for the specified index and role."""
        if not index.isValid() or index.row() >= len(self._activities):
            return None
        
        activity = self._activities[index.row()]
        
        if role == Qt.DisplayRole:
            return activity.get('Title', '')
        elif role == self.DateRole:
            return activity.get('Date', '')
        elif role == self.EventTypeRole:
            return activity.get('Event Type', '')
        elif role == self.TitleRole:
            return activity.get('Title', '')
        elif role == self.CourseRole:
            return activity.get('Course', '')
        elif role == self.StatusRole:
            return activity.get('Status', '')
        elif role == self.DurationWeightRole:
            return activity.get('Duration/Weight', '')
        elif role == self.StartTimeRole:
            return activity.get('Start Time', '')
        elif role == self.HasSlackRole:
            return activity.get('HasSlack', False)
        elif role == self.HasEmailRole:
            return activity.get('HasEmail', False)
            
        return None
    
    def role_names(self):
        """Return the role names for the model."""
        return {
            Qt.DisplayRole: b'display',
            self.DateRole: b'date',
            self.EventTypeRole: b'eventType',
            self.TitleRole: b'title',
            self.CourseRole: b'course',
            self.StatusRole: b'status',
            self.DurationWeightRole: b'durationWeight',
            self.StartTimeRole: b'startTime',
            self.HasSlackRole: b'hasSlack',
            self.HasEmailRole: b'hasEmail'
        }
    
    def add_activity(self, activity):
        """Add an activity to the model."""
        self.beginInsertRows(QModelIndex(), len(self._activities), len(self._activities))
        self._activities.append(activity)
        self.endInsertRows()
    
    def set_activities(self, activities):
        """Set the activities in the model."""
        self.beginResetModel()
        self._activities = activities
        self.endResetModel()
    
    def get_activities(self):
        """Return the activities in the model."""
        return self._activities
    
    def clear_activities(self):
        """Clear all activities from the model."""
        self.beginResetModel()
        self._activities = []
        self.endResetModel()
    
    def load_from_csv(self, filepath):
        """Load activities from a CSV file."""
        try:
            with open(filepath, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                activities = []
                for row in reader:
                    # Add Slack and Email flags (could be determined by other logic in a real app)
                    row['HasSlack'] = True if 'Assignment' in row.get('Event Type', '') else False
                    row['HasEmail'] = True if 'Assignment' in row.get('Event Type', '') else False
                    activities.append(row)
                
                self.set_activities(activities)
                return True
        except FileNotFoundError:
            print(f"Error: The file {filepath} was not found.")
        except IOError:
            print(f"Error: An I/O error occurred while reading {filepath}.")
        except csv.Error as e:
            print(f"Error: CSV reading error in {filepath}: {e}")
        return False


class DateGroupProxyModel(QSortFilterProxyModel):
    """Proxy model for grouping activities by date"""
    
    def __init__(self, parent=None):
        """Initialize the date group proxy model."""
        super().__init__(parent)
        self._dates = []
        self._current_date = None
    
    def set_current_date(self, date):
        """Set the current date filter."""
        self._current_date = date
        self.invalidateFilter()
    
    def filter_accepts_row(self, source_row, source_parent):
        """Return True if the row should be included in the model."""
        if not self._current_date:
            return True
        
        source_model = self.sourceModel()
        index = source_model.index(source_row, 0, source_parent)
        
        activity_date = source_model.data(index, ActivityModel.DateRole)
        if not activity_date:
            return False
        
        # Compare date strings (assuming format is consistent)
        return activity_date == self._current_date
    
    def get_unique_dates(self):
        """Return a list of unique dates in the source model."""
        source_model = self.sourceModel()
        if not source_model:
            return []
        
        dates = set()
        for row in range(source_model.rowCount()):
            index = source_model.index(row, 0)
            date = source_model.data(index, ActivityModel.DateRole)
            if date:
                dates.add(date)
        
        # Sort dates (assuming they are in consistent format)
        return sorted(list(dates))


# UI Components
class CompactDateEdit(QDateEdit):
    """Compact date editor with better UX for date ranges"""
    
    def __init__(self, parent=None):
        """Initialize the compact date editor."""
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("MM/dd/yyyy")
        self.setDate(QDate.currentDate())
        self.setFixedHeight(28)
        self.setToolTip("Click to select a date")


class ClassButton(QPushButton):
    """Button for selecting classes in the sidebar"""
    
    def __init__(self, text="", parent=None, is_selected=False):
        """Initialize the class button."""
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(is_selected)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "class-button")


class FilterButton(QPushButton):
    """Button for filter options"""
    
    def __init__(self, text="", parent=None, is_selected=False):
        """Initialize the filter button."""
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(is_selected)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "filter-button")


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
    
    def size_hint(self, option, index):  # pylint: disable=unused-argument
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
        duration_weight = index.data(ActivityModel.DurationWeightRole)
        start_time = index.data(ActivityModel.StartTimeRole)
        
        # Set up the painter
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Check if item is selected
        if option.state & QAbstractItemView.State_Selected:
            painter.fillRect(option.rect, QColor(SELECTED_BG))
        elif option.state & QAbstractItemView.State_MouseOver:
            painter.fillRect(option.rect, QColor(HOVER_BG))
        else:
            painter.fillRect(option.rect, QColor(CARD_BG))
        
        # Draw border
        painter.setPen(QPen(QColor(BORDER_COLOR)))
        painter.drawRoundedRect(option.rect.adjusted(2, 2, -2, -2), 6, 6)
        
        # Set up text rectangles
        content_rect = option.rect.adjusted(10, 8, -10, -8)
        title_rect = QRect(content_rect.left(), content_rect.top(), 
                          content_rect.width() - 70, 20)
        
        info_rect = QRect(content_rect.left(), title_rect.bottom() + 2,
                         content_rect.width() - 70, 20)
        
        status_rect = QRect(content_rect.left(), info_rect.bottom() + 2,
                           content_rect.width() - 70, 16)
        
        # Draw title
        painter.setPen(QPen(QColor(TEXT_PRIMARY)))
        painter.setFont(QFont(option.font.family(), 10, QFont.Bold))
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, 
                       f"{event_type}: {title}")
        
        # Draw course
        painter.setPen(QPen(QColor(TEXT_SECONDARY)))
        painter.setFont(QFont(option.font.family(), 9))
        painter.drawText(info_rect, Qt.AlignLeft | Qt.AlignVCenter, 
                       f"{course} • {duration_weight}")
        
        # Draw status
        painter.drawText(status_rect, Qt.AlignLeft | Qt.AlignVCenter, 
                       f"Status: {status} • {start_time}")
        
        # Draw icons
        icon_size = 24
        icon_y = content_rect.top() + (content_rect.height() - icon_size) // 2
        
        # Slack icon
        if has_slack and self._slack_icon:
            slack_rect = QRect(content_rect.right() - icon_size * 2, icon_y, 
                              icon_size, icon_size)
            self._slack_icon.paint(painter, slack_rect)
        
        # Email icon
        if has_email and self._email_icon:
            email_rect = QRect(content_rect.right() - icon_size, icon_y, 
                              icon_size, icon_size)
            self._email_icon.paint(painter, email_rect)
        
        painter.restore()


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
        
        # Header widget
        self.header_widget = QWidget()
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(4, 4, 4, 4)
        
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
        
        # Date label
        self.date_label = QLabel(self.date)
        self.date_label.setProperty("class", "date-header")
        
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
        
        # Set up the model
        self.proxy_model = DateGroupProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.set_current_date(self.date)
        self.list_view.setModel(self.proxy_model)
        
        # Set up delegate
        self.delegate = ActivityItemDelegate(self, self.icons_dir)
        self.list_view.setItemDelegate(self.delegate)
        
        self.content_layout.addWidget(self.list_view)
        
        self.layout.addWidget(self.content_widget)
        
        # Add a separator line
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setProperty("class", "separator")
        self.layout.addWidget(self.separator)
    
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
    
    def update_content_height(self):
        """Update the height of the content widget based on list view contents."""
        if not self.expanded:
            return
        
        total_height = 0
        for i in range(self.proxy_model.rowCount()):
            index = self.proxy_model.index(i, 0)
            total_height += self.delegate.size_hint(self.list_view.viewOptions(), index).height() + 2
        
        self.list_view.setFixedHeight(total_height)
        self.content_widget.setFixedHeight(total_height)


class ChatMessage(QFrame):
    """Widget for displaying a single chat message"""
    
    def __init__(self, text, is_user=False, parent=None):
        """Initialize the chat message widget."""
        super().__init__(parent)
        self.is_user = is_user
        self.text = text
        self.setProperty("class", "chat-message-user" if is_user else "chat-message")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 6, 8, 6)
        
        # Avatar placeholder (could be replaced with actual avatars)
        self.avatar = QLabel()
        self.avatar.setFixedSize(32, 32)
        if is_user:
            self.avatar.setText("👤")
        else:
            self.avatar.setText("🤖")
        
        # Message text
        self.message_label = QLabel(text)
        self.message_label.setWordWrap(True)
        
        # Add widgets to layout based on user/assistant
        if is_user:
            self.layout.addStretch()
            self.layout.addWidget(self.message_label)
            self.layout.addWidget(self.avatar)
        else:
            self.layout.addWidget(self.avatar)
            self.layout.addWidget(self.message_label)
            self.layout.addStretch()


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
        
        self.send_button = QPushButton("Send")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)
        
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
            
            # In a real app, this would send to an LLM and receive a response
            # For now, just add a dummy response
            self.add_message("This is a placeholder response from the LLM. In the real application, this would be generated based on your input.", is_user=False)


class MainWindow(QMainWindow):
    """Main application window for REMOTE"""
    def __init__(self):
        """Initialize the main window and its components."""
        super().__init__()
        self.setWindowTitle("REMOTE - Remote Education Management and Organization Tool for Education")
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
        
        # Load sample data
        self.load_sample_data()
        
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
        self.add_class("Data Science", False)
        
        layout.addWidget(self.classes_container)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setProperty("class", "separator")
        layout.addWidget(separator)
        
        # Filters section - grouped with headers
        deadlines_group = QGroupBox("Deadlines")
        deadlines_layout = QVBoxLayout(deadlines_group)
        deadlines_layout.setContentsMargins(8, 16, 8, 8)
        deadlines_layout.setSpacing(2)
        
        self.overdue_btn = FilterButton("Overdue")
        self.submitted_btn = FilterButton("Submitted")
        self.graded_btn = FilterButton("Graded")
        
        deadlines_layout.addWidget(self.overdue_btn)
        deadlines_layout.addWidget(self.submitted_btn)
        deadlines_layout.addWidget(self.graded_btn)
        
        events_group = QGroupBox("Events")
        events_layout = QVBoxLayout(events_group)
        events_layout.setContentsMargins(8, 16, 8, 8)
        events_layout.setSpacing(2)
        
        self.live_events_btn = FilterButton("Live Events", is_selected=True)
        self.past_btn = FilterButton("Past")
        
        events_layout.addWidget(self.live_events_btn)
        events_layout.addWidget(self.past_btn)
        
        layout.addWidget(deadlines_group)
        layout.addWidget(events_group)
        
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
        
        # Header with title
        header = QLabel("Key Activities")
        header.setProperty("class", "content-header")
        layout.addWidget(header)
        
        # Date range selectors
        date_range_layout = QHBoxLayout()
        
        # From date (use compact date edit)
        from_layout = QVBoxLayout()
        from_label = QLabel("From date")
        from_label.setProperty("class", "date-label")
        self.from_date = CompactDateEdit()
        self.from_date.setDate(QDate.currentDate())
        self.from_date.dateChanged.connect(self.update_activity_filters)
        
        from_layout.addWidget(from_label)
        from_layout.addWidget(self.from_date)
        
        # To date (use compact date edit)
        to_layout = QVBoxLayout()
        to_label = QLabel("To date")
        to_label.setProperty("class", "date-label")
        self.to_date = CompactDateEdit()
        # Set default date range (today to 2 weeks from now)
        self.to_date.setDate(QDate.currentDate().addDays(14))
        self.to_date.dateChanged.connect(self.update_activity_filters)
        
        to_layout.addWidget(to_label)
        to_layout.addWidget(self.to_date)
        
        date_range_layout.addLayout(from_layout)
        date_range_layout.addSpacing(16)
        date_range_layout.addLayout(to_layout)
        date_range_layout.addStretch()
        
        layout.addLayout(date_range_layout)
        
        # Create the activity model
        self.activity_model = ActivityModel(self)
        
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
        
        # Get unique dates from model
        proxy = DateGroupProxyModel(self)
        proxy.setSourceModel(self.activity_model)
        
        dates = proxy.get_unique_dates()
        
        # Create a date section for each unique date
        for date in dates:
            date_section = DateAccordionWidget(date, self.activity_model, self, self.icons_dir)
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
        # In a real application, this would apply complex filtering
        # For this prototype, we'll just reload the sample data
        self.populate_activity_dates()
    
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
    
    def load_sample_data(self):
        """Load sample activity data."""
        # Add sample activities
        activities = [
            {
                "Date": "Mar 13",
                "Event Type": "Office Hours",
                "Title": "TA Office Hours",
                "Course": "Database Management Systems",
                "Status": "Scheduled",
                "Duration/Weight": "1 hour",
                "Start Time": "2:00 PM",
                "HasSlack": True,
                "HasEmail": True
            },
            {
                "Date": "Mar 13",
                "Event Type": "Assignment",
                "Title": "Module 07 SQL Lab - ProblemSet02",
                "Course": "Database Management Systems",
                "Status": "Submitted",
                "Duration/Weight": "10%",
                "Start Time": "11:59 PM",
                "HasSlack": True,
                "HasEmail": True
            },
            {
                "Date": "Mar 13",
                "Event Type": "Assignment",
                "Title": "Module 7 Quiz: Introduction to SQL",
                "Course": "Database Management Systems",
                "Status": "Graded (90%)",
                "Duration/Weight": "5%",
                "Start Time": "11:59 PM",
                "HasSlack": True,
                "HasEmail": True
            },
            {
                "Date": "Mar 13",
                "Event Type": "Assignment",
                "Title": "Final Project Checkpoint #2: Project Execution",
                "Course": "Human-Centered Artificial Intelligence",
                "Status": "Due",
                "Duration/Weight": "15%",
                "Start Time": "11:59 PM",
                "HasSlack": True,
                "HasEmail": True
            },
            {
                "Date": "Mar 14",
                "Event Type": "Lecture",
                "Title": "Advanced SQL Concepts",
                "Course": "Database Management Systems",
                "Status": "Scheduled",
                "Duration/Weight": "1.5 hours",
                "Start Time": "10:30 AM",
                "HasSlack": False,
                "HasEmail": True
            },
            {
                "Date": "Mar 16",
                "Event Type": "Assignment",
                "Title": "Final Project Presentation",
                "Course": "Human-Centered Artificial Intelligence",
                "Status": "Upcoming",
                "Duration/Weight": "25%",
                "Start Time": "3:00 PM",
                "HasSlack": True,
                "HasEmail": True
            }
        ]
        
        # Set activities in the model
        self.activity_model.set_activities(activities)
        
        # Populate date sections
        self.populate_activity_dates()
    
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
    sys.exit(app.exec_())

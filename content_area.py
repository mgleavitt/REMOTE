"""
Content area components for REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QDate

from input_components import CompactDateEdit
from date_widgets import DateAccordionWidget
from styles import TEXT_SECONDARY


class ContentArea(QWidget):
    """Main content area widget containing activities and date filters."""
    
    def __init__(self, parent=None):
        """Initialize the content area."""
        super().__init__(parent)
        self.setProperty("class", "content-area")
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
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
    
    def clear_activities_layout(self):
        """Clear all activities from the layout."""
        # Remove all widgets except the stretch at the end
        while self.activities_layout.count() > 1:
            item = self.activities_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def populate_activity_dates(self, filter_proxy_model, icons_dir):
        """Populate activities grouped by date in the content area.
        
        Args:
            filter_proxy_model: The proxy model containing filtered activities
            icons_dir: Directory containing icons for the date widgets
        """
        # Clear current content
        self.clear_activities_layout()
        
        # Get unique dates from filtered model
        dates = set()
        for row in range(filter_proxy_model.rowCount()):
            index = filter_proxy_model.index(row, 0)
            date = filter_proxy_model.data(index, Qt.UserRole + 1)  # Use the actual role value
            if date:
                dates.add(date)
        
        # If no dates (no matching activities), show a message
        if not dates:
            no_results_label = QLabel("No activities match the current filters")
            no_results_label.setAlignment(Qt.AlignCenter)
            style = f"color: {TEXT_SECONDARY}; margin: 20px;"
            no_results_label.setStyleSheet(style)
            self.activities_layout.insertWidget(self.activities_layout.count() - 1, 
                                                no_results_label)
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
            date_section = DateAccordionWidget(date_str, filter_proxy_model, self, icons_dir)
            self.activities_layout.insertWidget(self.activities_layout.count() - 1, date_section)
            date_section.update_content_height()
    
    def connect_date_filters(self, callback):
        """Connect date filter widgets to a callback function.
        
        Args:
            callback: Function to call when date filters change
        """
        self.from_date.dateChanged.connect(callback)
        self.to_date.dateChanged.connect(callback)

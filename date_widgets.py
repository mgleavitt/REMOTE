"""
Date-related widgets for REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListView, QFrame, QAbstractItemView, 
    QStyleOptionViewItem, QToolTip
)
from PySide6.QtCore import (
    Qt, QEvent, QRect
)
from PySide6.QtGui import QIcon

from models import ActivityModel, DateOnlyProxyModel
from delegates import ActivityItemDelegate
from styles import (
    BACKGROUND, BORDER_COLOR, TEXT_PRIMARY
)


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
                # pylint: disable=line-too-long
                slack_rect = QRect(icon_x - (icon_size + icon_spacing), icon_y, icon_size, icon_size)
                # pylint: enable=line-too-long
                
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

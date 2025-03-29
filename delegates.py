"""
Delegate classes for REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

import os

from PySide6.QtWidgets import (
    QStyledItemDelegate, QStyle, QMessageBox, QToolTip
)
from PySide6.QtCore import (
    Qt, QRect, QSize, QEvent
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QIcon
)
from models import ActivityModel
from styles import (
    SELECTED_BG, HOVER_BG, CARD_BG, BORDER_COLOR,
    TEXT_PRIMARY, TEXT_SECONDARY
)


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

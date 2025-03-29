"""
Input UI components for REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

from PySide6.QtWidgets import (
    QPushButton, QDateEdit
)
from PySide6.QtCore import (
    Qt, QDate, QTimer
)
from PySide6.QtGui import (
    QIcon
)


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
        self.setProperty("class", "class-button")  # Use the same class as ClassButton


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
        
        # Clear any selection and move cursor to end
        line_edit = self.lineEdit()
        line_edit.deselect()
        line_edit.setCursorPosition(len(line_edit.text()))
        
        # Use multiple timers with different delays to ensure selection is cleared
        QTimer.singleShot(0, self._clear_selection)
        QTimer.singleShot(100, self._clear_selection)
        
        # Ensure calendar icon is visible
        # First try to set a standard icon if available
        try:
            self.calendarWidget().setWindowIcon(QIcon.fromTheme("calendar"))
        except (AttributeError, RuntimeError):
            # Pass silently if the calendar widget isn't available or properly initialized
            pass
            
        # Setup button text as fallback if icon is not visible
        btn = self.findChild(QPushButton)
        if btn:
            if not btn.icon() or btn.icon().isNull():
                btn.setText("📅")
                btn.setFixedWidth(28)
        self.setToolTip("Click to select a date")
    
    def _clear_selection(self):
        """Clear any text selection and move cursor to end."""
        line_edit = self.lineEdit()
        line_edit.deselect()
        line_edit.setCursorPosition(len(line_edit.text()))
        line_edit.setSelection(0, 0)
        
        # Force an update
        line_edit.update()
    
    def showEvent(self, event):
        """Handle widget show event to ensure no text is selected."""
        super().showEvent(event)
        self._clear_selection()
        
    def focusInEvent(self, event):
        """Handle focus in event to ensure no text is selected."""
        super().focusInEvent(event)
        QTimer.singleShot(0, self._clear_selection)

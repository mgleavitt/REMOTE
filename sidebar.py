"""
Sidebar components for REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame
)
# from PySide6.QtCore import Qt

from input_components import ClassButton, FilterButton
# from styles import TEXT_SECONDARY


class Sidebar(QWidget):
    """Sidebar widget containing class buttons and filters."""
    
    def __init__(self, parent=None):
        """Initialize the sidebar."""
        super().__init__(parent)
        self.setProperty("class", "sidebar")
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
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
        
        events_layout.addWidget(self.past_events_btn)
        events_layout.addWidget(self.now_events_btn)
        events_layout.addWidget(self.upcoming_events_btn)
        
        layout.addWidget(events_container)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def add_class(self, name, is_selected=False):
        """Add a class button to the sidebar.
        
        Args:
            name (str): The name of the class
            is_selected (bool): Whether the class should be initially selected
        """
        class_btn = ClassButton(name, is_selected=is_selected)
        class_btn.setToolTip(f"Toggle {name} visibility")
        self.classes_layout.addWidget(class_btn)
    
    def get_selected_courses(self):
        """Get the set of selected course names.
        
        Returns:
            set: Set of selected course names
        """
        selected_courses = set()
        for i in range(self.classes_layout.count()):
            widget = self.classes_layout.itemAt(i).widget()
            if isinstance(widget, ClassButton) and widget.isChecked():
                selected_courses.add(widget.text())
        return selected_courses
    
    def get_filter_states(self):
        """Get the current state of all filter buttons.
        
        Returns:
            dict: Dictionary containing the state of each filter button
        """
        return {
            'show_overdue': self.overdue_btn.isChecked(),
            'show_submitted': self.submitted_btn.isChecked(),
            'show_graded': self.graded_btn.isChecked(),
            'show_due': self.due_btn.isChecked(),
            'show_past_events': self.past_events_btn.isChecked(),
            'show_now_events': self.now_events_btn.isChecked(),
            'show_upcoming_events': self.upcoming_events_btn.isChecked()
        }
    
    def connect_filters(self, callback):
        """Connect all filter buttons to a callback function.
        
        Args:
            callback: Function to call when any filter button is clicked
        """
        # Connect class buttons
        for i in range(self.classes_layout.count()):
            widget = self.classes_layout.itemAt(i).widget()
            if isinstance(widget, ClassButton):
                widget.clicked.connect(callback)
        
        # Connect deadline filter buttons
        self.overdue_btn.clicked.connect(callback)
        self.submitted_btn.clicked.connect(callback)
        self.graded_btn.clicked.connect(callback)
        self.due_btn.clicked.connect(callback)
        
        # Connect event filter buttons
        self.past_events_btn.clicked.connect(callback)
        self.now_events_btn.clicked.connect(callback)
        self.upcoming_events_btn.clicked.connect(callback)

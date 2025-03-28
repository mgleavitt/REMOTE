"""
Models for REMOTE application handling activities, date grouping, and filtering.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

from datetime import datetime
import csv

from PySide6.QtCore import (
    Qt, QAbstractListModel, QModelIndex, QSortFilterProxyModel,
    QDate
)

class ActivityModel(QAbstractListModel):
    """Data model for activities"""
    
    DateRole = Qt.UserRole + 1
    EventTypeRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    CourseRole = Qt.UserRole + 4
    StatusRole = Qt.UserRole + 5
    StartTimeRole = Qt.UserRole + 6
    HasSlackRole = Qt.UserRole + 7
    HasEmailRole = Qt.UserRole + 8
    
    def __init__(self, parent=None):
        """Initialize the activity model."""
        super().__init__(parent)
        self._activities = []
        
    def rowCount(self, parent=QModelIndex()): # pylint: disable=invalid-name,unused-argument
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
            date = activity.get('Date')
            if isinstance(date, datetime):
                return date.strftime("%b %d")
            return date
        elif role == self.EventTypeRole:
            return activity.get('Event Type', '')
        elif role == self.TitleRole:
            return activity.get('Title', '')
        elif role == self.CourseRole:
            return activity.get('Course', '')
        elif role == self.StatusRole:
            return activity.get('Status', '')
        elif role == self.StartTimeRole:
            return activity.get('Start Time', '')
        elif role == self.HasSlackRole:
            return activity.get('HasSlack')
        elif role == self.HasEmailRole:
            return activity.get('HasEmail')
            
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
    
    def filterAcceptsRow(self, source_row, source_parent):
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


class ActivityFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for filtering activities based on multiple criteria."""
    
    def __init__(self, parent=None):
        """Initialize the activity filter proxy model."""
        super().__init__(parent)
        self._selected_courses = set()
        self._show_overdue = False
        self._show_submitted = False
        self._show_graded = False
        self._show_due = False
        self._show_past_events = False
        self._show_now_events = True
        self._show_upcoming_events = True
        self._from_date = QDate.currentDate().addDays(-14)  # Default: 2 weeks ago
        self._to_date = QDate.currentDate().addDays(14)     # Default: 2 weeks ahead
    
    def set_filter_criteria(self, selected_courses, show_overdue, show_submitted,
                          show_graded, show_due, show_past_events, show_now_events,
                          show_upcoming_events, from_date, to_date):
        """Set all filter criteria at once."""
        self._selected_courses = set(selected_courses)
        self._show_overdue = show_overdue
        self._show_submitted = show_submitted
        self._show_graded = show_graded
        self._show_due = show_due
        self._show_past_events = show_past_events
        self._show_now_events = show_now_events
        self._show_upcoming_events = show_upcoming_events
        self._from_date = from_date
        self._to_date = to_date
        self.invalidateFilter()
    
    def _is_deadline_item(self, index):
        """Check if the item is a deadline item (has submission status)."""
        event_type = index.data(ActivityModel.EventTypeRole)
        if not event_type:
            return False
        
        # Case-insensitive check for assignment types
        return event_type.lower() == "assignment"
    
    def _is_event_item(self, index):
        """Check if the item is an event item (no submission status)."""
        event_type = index.data(ActivityModel.EventTypeRole)
        if not event_type:
            return False
        
        # Case-insensitive check for event types
        event_type_lower = event_type.lower()
        return event_type_lower == "live event"
    
    def _parse_date(self, date_str):
        """Parse date string into QDate object."""
        try:
            # Convert date string (e.g., "Mar 16") to QDate
            item_date = QDate.fromString(date_str, "MMM dd")
            
            # Check if the date is valid
            if not item_date.isValid():
                print(f"Warning: Invalid date format: '{date_str}'")
                return None
            
            # Set the year to current year since it's not in the date string
            current_year = QDate.currentDate().year()
            item_date = item_date.addYears(current_year - item_date.year())
            return item_date
        except (ValueError, TypeError) as e:
            print(f"Error parsing date '{date_str}': {str(e)}")
            return None
    
    def _evaluate_date_range(self, index):
        """Evaluate if the item's date falls within the specified range."""
        date_str = index.data(ActivityModel.DateRole)
        if not date_str:
            return False
            
        item_date = self._parse_date(date_str)
        if not item_date:
            return False
            
        return self._from_date <= item_date <= self._to_date
    
    def _evaluate_courses_filter(self, index):
        """Evaluate if the item belongs to any selected course."""
        if not self._selected_courses:
            return False  # If no courses selected, hide all items
            
        course = index.data(ActivityModel.CourseRole)
        return course in self._selected_courses
    
    def _evaluate_deadlines_filter(self, index):
        """Evaluate if the item passes any of the deadline sub-filters."""
        if not self._is_deadline_item(index):
            return True  # Not a deadline item, so passes this filter
            
        # If no deadline filters are selected, don't show any deadline items
        if not any([self._show_overdue, self._show_submitted, 
                   self._show_graded, self._show_due]):
            return False
            
        date_str = index.data(ActivityModel.DateRole)
        item_date = self._parse_date(date_str)
        if not item_date:
            return False
            
        current_date = QDate.currentDate()
        status = index.data(ActivityModel.StatusRole)
        status_lower = status.lower()
        
        # For overdue items, check if the date is in the past
        if self._show_overdue and "due" in status_lower and item_date < current_date:
            return True
            
        # For submitted items
        if self._show_submitted and "submitted" in status_lower:
            return True
            
        # For graded items
        if self._show_graded and "graded" in status_lower:
            return True
            
        # For due items, check if the date is in the future
        if self._show_due and "due" in status_lower and item_date >= current_date:
            return True
            
        return False
    
    def _evaluate_events_filter(self, index):
        """Evaluate if the item passes any of the events sub-filters."""
        if not self._is_event_item(index):
            return True  # Not an event item, so passes this filter
            
        # If no event filters are selected, don't show any event items
        if not any([self._show_past_events, self._show_now_events, self._show_upcoming_events]):
            return False
            
        status = index.data(ActivityModel.StatusRole)
        status_lower = status.lower()
        
        # Check each sub-filter
        if self._show_past_events and "past" in status_lower:
            return True
        if self._show_now_events and "now" in status_lower:
            return True
        if self._show_upcoming_events and "upcoming" in status_lower:
            return True
            
        return False
    
    def filterAcceptsRow(self, source_row, source_parent):
        """Return True if the row should be included based on all filter criteria."""
        index = self.sourceModel().index(source_row, 0, source_parent)
        
        # Apply date range filter first
        if not self._evaluate_date_range(index):
            return False
            
        # Then check each top-level filter
        if not self._evaluate_courses_filter(index):
            return False
            
        if not self._evaluate_deadlines_filter(index):
            return False
            
        if not self._evaluate_events_filter(index):
            return False
            
        return True


class DateOnlyProxyModel(QSortFilterProxyModel):
    """Proxy model that filters activities to show only those matching a specific date."""
    
    def __init__(self, date_value, parent=None):
        """Initialize the date-only proxy model.
        
        Args:
            date_value: The date to filter activities by
            parent: Parent widget
        """
        super().__init__(parent)
        self.date_value = date_value
        
    def filterAcceptsRow(self, source_row, source_parent):
        """Filter rows to show only those matching the specified date.
        
        Args:
            source_row: Row index in the source model
            source_parent: Parent index in the source model
            
        Returns:
            bool: True if the row's date matches the filter date
        """
        index = self.sourceModel().index(source_row, 0, source_parent)
        item_date = index.data(ActivityModel.DateRole)
        return item_date == self.date_value

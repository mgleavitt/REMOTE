# REMOTE Application Filtering Issues and Fixes

This document outlines the filtering issues in the REMOTE application and provides detailed guidance for fixing each problem.

## Problem: Empty Class Selection Shows All Activities

* **Problem description**: When all class filter buttons are deselected (no classes are selected), the application still displays all activities instead of hiding everything.

* **Root cause**: In the `_evaluate_courses_filter` method of the `ActivityFilterProxyModel` class, when the `_selected_courses` set is empty, it returns `True` instead of `False`:

  ```python
  def _evaluate_courses_filter(self, index):
      """Evaluate if the item belongs to any selected course."""
      if not self._selected_courses:
          return True  # If no courses selected, show all
              
      course = index.data(ActivityModel.CourseRole)
      return course in self._selected_courses
  ```

* **Suggested fix**: Change the return value when no courses are selected to `False` to hide all activities:

  ```python
  def _evaluate_courses_filter(self, index):
      """Evaluate if the item belongs to any selected course."""
      if not self._selected_courses:
          return False  # If no courses selected, hide all items
              
      course = index.data(ActivityModel.CourseRole)
      return course in self._selected_courses
  ```

## Problem: Disconnected Filter Models in DateAccordionWidget

* **Problem description**: The Deadlines and Events filters don't affect the displayed activities, even when they're toggled on/off.

* **Root cause**: The architecture creates a disconnect between the main filtering model and the display. Each `DateAccordionWidget` creates its own separate `DateGroupProxyModel` that only filters by date but doesn't respect the other filters:

  ```python
  # Current code in populate_activity_dates
  for date in sorted(list(dates)):
      date_section = DateAccordionWidget(date, self.activity_model, self, self.icons_dir)
  ```

  ```python
  # Inside DateAccordionWidget.__init__
  self.proxy_model = DateGroupProxyModel(self)
  self.proxy_model.setSourceModel(self.model)
  self.proxy_model.set_current_date(self.date)
  self.list_view.setModel(self.proxy_model)
  ```

  This creates a new proxy model that filters the original data source directly, bypassing the main filter proxy model.

* **Suggested fix**: Modify the `DateAccordionWidget` class to accept the already-filtered proxy model and only apply date-specific filtering on top of it:

  ```python
  # In MainWindow.populate_activity_dates()
  for date in sorted(list(dates)):
      date_section = DateAccordionWidget(date, self.filter_proxy_model, self, self.icons_dir)
  ```

  Then in the `DateAccordionWidget` class, create a custom proxy model that only shows items for the specific date from the already-filtered data:

  ```python
  # Inside DateAccordionWidget.setup_ui()
  class DateOnlyProxyModel(QSortFilterProxyModel):
      def __init__(self, date_value, parent=None):
          super().__init__(parent)
          self.date_value = date_value
          
      def filterAcceptsRow(self, source_row, source_parent):
          index = self.sourceModel().index(source_row, 0, source_parent)
          item_date = index.data(ActivityModel.DateRole)
          return item_date == self.date_value
  
  # Use the custom proxy model
  self.date_only_model = DateOnlyProxyModel(self.date, self)
  self.date_only_model.setSourceModel(self.filtered_model)  # filtered_model passed from MainWindow
  self.list_view.setModel(self.date_only_model)
  ```

## Problem: Unreliable Status String Matching

* **Problem description**: Filtering by status (e.g., "Submitted", "Graded", "Due") may not work reliably due to case sensitivity and exact substring matching.

* **Root cause**: Status comparison in filter evaluation methods uses direct string matching without normalization:

  ```python
  if self._show_overdue and item_date < current_date and "Due" in status:
      return True
  if self._show_submitted and "Submitted" in status:
      return True
  ```

  This requires the exact case and substring to be present, which may fail if the actual status text varies.

* **Suggested fix**: Normalize status strings by converting to lowercase before comparison:

  ```python
  status_lower = status.lower() if status else ""
  
  if self._show_overdue and item_date < current_date and "due" in status_lower:
      return True
  if self._show_submitted and "submitted" in status_lower:
      return True
  if self._show_graded and "graded" in status_lower:
      return True
  if self._show_current and "due" in status_lower and item_date >= current_date:
      return True
  ```

## Problem: Incorrect Default Date Range

* **Problem description**: The default date range should be (current date - 2 weeks) to (current date + 2 weeks), but is currently set to (current date) to (current date + 2 weeks).

* **Root cause**: In the `create_content_area` method of `MainWindow`, the initialization of the from_date is incorrect:

  ```python
  self.from_date = CompactDateEdit()
  self.from_date.setDate(QDate.currentDate())  # Today
  ```

* **Suggested fix**: Change the from_date initialization to be 2 weeks in the past:

  ```python
  self.from_date = CompactDateEdit()
  self.from_date.setDate(QDate.currentDate().addDays(-14))  # 2 weeks ago
  ```

  Also, ensure this default is reflected in the `ActivityFilterProxyModel` initialization:

  ```python
  def __init__(self, parent=None):
      """Initialize the activity filter proxy model."""
      super().__init__(parent)
      self._selected_courses = set()  # Set of selected course names
      # ...other initializations...
      self._from_date = QDate.currentDate().addDays(-14)  # Default: 2 weeks ago
      self._to_date = QDate.currentDate().addDays(14)     # Default: 2 weeks ahead
  ```

## Problem: Date Parsing Logic Lacks Error Handling

* **Problem description**: The current date parsing function is fragile and doesn't handle invalid formats or edge cases gracefully.

* **Root cause**: The `_parse_date` method in `ActivityFilterProxyModel` lacks proper validation and error handling:

  ```python
  def _parse_date(self, date_str):
      """Parse date string into QDate object."""
      try:
          # Convert date string (e.g., "Mar 16") to QDate
          item_date = QDate.fromString(date_str, "MMM dd")
          # Set the year to current year since it's not in the date string
          current_year = QDate.currentDate().year()
          item_date = item_date.addYears(current_year - item_date.year())
          return item_date
      except:
          return None
  ```

* **Suggested fix**: Improve error handling and add validation:

  ```python
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
      except Exception as e:
          print(f"Error parsing date '{date_str}': {str(e)}")
          return None
  ```

## Problem: Lack of Debugging Information

* **Problem description**: When filters don't work as expected, there's no easy way to determine why items are or aren't being displayed.

* **Root cause**: The filtering code doesn't have debugging capabilities to log filter evaluation decisions.

* **Suggested fix**: Add a debug mode flag and logging to the `ActivityFilterProxyModel` class:

  ```python
  def __init__(self, parent=None):
      """Initialize the activity filter proxy model."""
      super().__init__(parent)
      # ...existing initialization...
      self._debug_mode = False  # Set to True to enable detailed filter logging
  
  def set_debug_mode(self, enabled):
      """Enable or disable debug logging."""
      self._debug_mode = enabled
  
  def filterAcceptsRow(self, source_row, source_parent):
      """Return True if the row should be included based on all filter criteria."""
      index = self.sourceModel().index(source_row, 0, source_parent)
      
      # For debugging, get key info about the item
      if self._debug_mode:
          title = index.data(ActivityModel.TitleRole)
          course = index.data(ActivityModel.CourseRole)
          date = index.data(ActivityModel.DateRole)
          event_type = index.data(ActivityModel.EventTypeRole)
          print(f"\nEvaluating filter for: {title} ({course}, {date}, {event_type})")
      
      # Then add debug outputs to each filter evaluation method...
  ```

## Problem: Incorrect Item Type Classification

* **Problem description**: Items may not be correctly classified as "deadline items" or "event items" leading to incorrect filter application.

* **Root cause**: The current implementation uses string comparison to determine item types, which may not match all scenarios:

  ```python
  def _is_deadline_item(self, index):
      """Check if the item is a deadline item (has submission status)."""
      event_type = index.data(ActivityModel.EventTypeRole)
      return event_type == "Assignment"
  
  def _is_event_item(self, index):
      """Check if the item is an event item (no submission status)."""
      event_type = index.data(ActivityModel.EventTypeRole)
      return event_type in ["Lecture", "Office Hours"]
  ```

* **Suggested fix**: Make the item type classification more robust with case-insensitive comparison and consider a more general approach:

  ```python
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
      return event_type_lower in ["lecture", "office hours"]
  ```

## Problem: Filter Button Connection Issues

* **Problem description**: Toggling filter buttons may not correctly update the filter state.

* **Root cause**: In the `MainWindow.create_sidebar` method, filter buttons are created but some may not be properly connected to the `update_activity_filters` method.

* **Suggested fix**: Ensure all filter buttons have their `clicked` signal connected to the `update_activity_filters` method:

  ```python
  def create_sidebar(self):
      # ...existing code...
      
      # Connect all filter buttons to update_activity_filters
      self.overdue_btn.clicked.connect(self.update_activity_filters)
      self.submitted_btn.clicked.connect(self.update_activity_filters)
      self.graded_btn.clicked.connect(self.update_activity_filters)
      self.current_btn.clicked.connect(self.update_activity_filters)
      self.live_events_btn.clicked.connect(self.update_activity_filters)
      self.past_btn.clicked.connect(self.update_activity_filters)
      
      # ...rest of the method...
  ```

## Problem: No Visual Feedback When Filter Results are Empty

* **Problem description**: When filters result in no matching activities, there is no feedback to the user explaining why the list is empty.

* **Root cause**: The application does not check for empty filter results or provide a placeholder message.

* **Suggested fix**: Add a placeholder message when no activities match the current filters:

  ```python
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
          
      # Continue with creating date sections...
  ```

These detailed fixes should provide a coding AI with sufficient information to resolve the filtering issues in the REMOTE application.

"""
Coursera data agent that loads and parses Coursera activity data.
"""
import csv
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
import time
import pytz

from .base_agent import BaseAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone mapping from abbreviated names to IANA identifiers
TZ_MAPPING = {
    'PST': 'America/Los_Angeles',
    'PDT': 'America/Los_Angeles',
    'MST': 'America/Denver',
    'MDT': 'America/Denver',
    'CST': 'America/Chicago',
    'CDT': 'America/Chicago',
    'EST': 'America/New_York',
    'EDT': 'America/New_York',
    'UTC': 'UTC',
    'GMT': 'UTC'
}

class ActivityStatus(Enum):
    """Valid activity statuses."""
    OVERDUE = "Overdue"
    SUBMITTED = "Submitted"
    GRADED = "Graded"
    DUE = "Due"

class LiveEventStatus(Enum):
    """Valid live event statuses."""
    PAST = "Past"
    NOW = "Now"
    UPCOMING = "Upcoming"

class EventType(Enum):
    """Valid event types."""
    LIVE_EVENT = "Live Event"
    ASSIGNMENT = "Assignment"  # Simplified to just two types

class DataAgentCourseraSim(BaseAgent):
    """Agent for loading and parsing Coursera activity data."""

    def __init__(self):
        """Initialize the Coursera data agent."""
        super().__init__()
        self._data: list = []
        self._current_year: int = datetime.now().year

        # Get local timezone using system timezone name
        tz_abbr = time.tzname[0]
        tz_name = TZ_MAPPING.get(tz_abbr, 'UTC')  # Default to UTC if mapping not found
        self._local_tz: pytz.timezone = pytz.timezone(tz_name)
        logger.info("Using timezone: %s (mapped from %s)", tz_name, tz_abbr)

    def load_data(self, source: str) -> bool:
        """Load and parse data from a Coursera CSV file.
        
        Args:
            source: Path to the CSV file
            
        Returns:
            bool: True if data was loaded successfully, False otherwise
        """
        try:
            with open(source, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                self._data = []

                for row_num, row in enumerate(reader, start=2):
                    try:
                        activity = self._parse_row(row)
                        if activity:
                            self._data.append(activity)
                    except ValueError as e:
                        logger.warning("Row %d: %s", row_num, str(e))
                        continue

                return True

        except FileNotFoundError:
            logger.error("File not found: %s", source)
            return False
        except (IOError, OSError) as e:
            logger.error("Error reading file: %s", str(e))
            return False
        except csv.Error as e:
            logger.error("CSV parsing error: %s", str(e))
            return False

    def _parse_status(self, status: str, date: datetime, event_type: str,
                     start_time: str = None) -> str:
        """Parse and normalize the status string.
        
        Args:
            status: Raw status string from CSV
            date: Activity date
            event_type: Type of event (Live Event or Assignment)
            start_time: Start time for live events
            
        Returns:
            str: Normalized status
        """
        current_date = datetime.now(self._local_tz)

        # Handle Live Events differently
        if event_type == EventType.LIVE_EVENT.value:
            # Parse start time if provided
            if start_time and start_time != 'N/A':
                try:
                    # Split time string into parts
                    parts = start_time.split()
                    if len(parts) >= 3:  # Has timezone (e.g., "9:00 AM PDT")
                        time_str = ' '.join(parts[:-1])  # "9:00 AM"
                        tz_abbr = parts[-1]  # "PDT"

                        # Get timezone from mapping
                        tz_name = TZ_MAPPING.get(tz_abbr)
                        if not tz_name:
                            logger.warning(
                                "Unknown timezone abbreviation: %s, using local timezone",
                                tz_abbr)
                            tz_name = self._local_tz.zone

                        # Parse time in format "HH:MM AM/PM"
                        event_time = datetime.strptime(time_str, "%I:%M %p")

                        # Convert date to naive datetime if it's timezone-aware
                        if date.tzinfo is not None:
                            date = date.replace(tzinfo=None)

                        # Combine date and time
                        event_datetime = date.replace(
                            hour=event_time.hour,
                            minute=event_time.minute
                        )

                        # Localize the datetime to the event's timezone
                        event_tz = pytz.timezone(tz_name)
                        event_datetime = event_tz.localize(event_datetime)

                        # Convert to local timezone for comparison
                        event_datetime_local = event_datetime.astimezone(
                            self._local_tz)

                        # Determine status based on current time
                        if event_datetime_local < current_date:
                            return LiveEventStatus.PAST.value
                        elif event_datetime_local > current_date:
                            return LiveEventStatus.UPCOMING.value
                        else:
                            return LiveEventStatus.NOW.value
                    else:  # No timezone (e.g., "9:00 AM")
                        # Parse time in format "HH:MM AM/PM"
                        event_time = datetime.strptime(start_time, "%I:%M %p")

                        # Convert date to naive datetime if it's timezone-aware
                        if date.tzinfo is not None:
                            date = date.replace(tzinfo=None)

                        # Combine date and time
                        event_datetime = date.replace(
                            hour=event_time.hour,
                            minute=event_time.minute
                        )
                        # Assume local timezone
                        event_datetime = self._local_tz.localize(event_datetime)

                        # Determine status based on current time
                        if event_datetime < current_date:
                            return LiveEventStatus.PAST.value
                        elif event_datetime > current_date:
                            return LiveEventStatus.UPCOMING.value
                        else:
                            return LiveEventStatus.NOW.value
                except ValueError as e:
                    logger.warning(
                        "Could not parse start time: %s - %s",
                        start_time, str(e))
                    return LiveEventStatus.UPCOMING.value
            else:
                # If no start time, use date only
                if date.date() < current_date.date():
                    return LiveEventStatus.PAST.value
                elif date.date() > current_date.date():
                    return LiveEventStatus.UPCOMING.value
                else:
                    return LiveEventStatus.NOW.value

        # Handle Assignment statuses
        if "graded" in status.lower():
            return ActivityStatus.GRADED.value

        if "submitted" in status.lower():
            return ActivityStatus.SUBMITTED.value

        if date < current_date and "due" in status.lower():
            return ActivityStatus.OVERDUE.value

        return ActivityStatus.DUE.value

    def _parse_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Parse a single row of data.
        
        Args:
            row: Dictionary containing the row data
            
        Returns:
            Optional[Dict[str, Any]]: Parsed activity data or None if invalid
            
        Raises:
            ValueError: If the row data is invalid
        """
        # Parse date
        try:
            date_str = row['Date']
            # Create datetime with current year and localize it
            date = datetime.strptime(f"{date_str} {self._current_year}",
                                   "%b %d %Y")
            date = self._local_tz.localize(date)
        except ValueError as e:
            raise ValueError(f"Invalid date format: {date_str}") from e

        # Parse event type - map everything except Live Event to Assignment
        event_type = row['Event Type']
        if event_type == EventType.LIVE_EVENT.value:
            parsed_event_type = EventType.LIVE_EVENT.value
        else:
            parsed_event_type = EventType.ASSIGNMENT.value

        # Get start time for live events
        start_time = row.get('Start Time', 'N/A')

        # Parse status with event type and start time
        status = self._parse_status(row['Status'], date, parsed_event_type,
                                  start_time)

        # Create activity dictionary with UI-compatible keys
        activity = {
            'Date': date,  # Return datetime object
            'Event Type': parsed_event_type,
            'Title': row['Title'],
            'Course': row['Course'],
            'Status': status,
            'Start Time': start_time,
            'HasSlack': None,  # Set to None as per requirements
            'HasEmail': None   # Set to None as per requirements
        }

        # Clean up Start Time field
        if activity['Start Time'] == 'N/A' and event_type == EventType.LIVE_EVENT.value:
            raise ValueError("Live events must have a start time")

        return activity

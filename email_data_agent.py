"""
Email data agent for REMOTE application.
Handles loading email data and correlating with educational activities using LLM.
"""
# pylint: disable=no-name-in-module

import os
import json
import logging
from typing import List, Dict, Any, Optional
import re
from datetime import datetime
import hashlib
import time
import threading
import queue

# Import for LLM interaction with Claude
from llm_providers import AnthropicProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailDataAgent:
    """
    Data agent that handles email data management and correlations.

    Loads email data from a JSON file (produced by remote-import-emails.py)
    and provides methods to access and correlate emails with educational activities.
    Uses an LLM for intelligent correlation.
    """

    def __init__(self, llm_provider=None):
        """Initialize the email data agent.

        Args:
            llm_provider: LLM provider for correlation (if None, will use default)
        """
        self.emails = []
        self.email_by_id = {}  # For quick lookups
        self.correlation_cache = {}  # To avoid redundant LLM calls
        self.llm_provider = llm_provider

        # Thread pool for background correlation processing
        self.correlation_queue = queue.Queue()
        self.correlation_thread = None
        self.correlation_results = {}
        self.is_correlating = False

        logger.info("EmailDataAgent initialized")

    def load_data(self, data_file: str) -> bool:
        """Load email data from JSON file.

        Args:
            data_file: Path to the JSON file containing email data

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(data_file):
                logger.error(f"Data file not found: {data_file}")
                return False

            with open(data_file, 'r', encoding='utf-8') as f:
                self.emails = json.load(f)

            # Build lookup dictionary
            self.email_by_id = {email["message_id"]
                : email for email in self.emails}

            logger.info(f"Loaded {len(self.emails)} emails from {data_file}")
            return True

        except (ValueError, IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading email data: {e}")
            return False

    def get_data(self) -> List[Dict[str, Any]]:
        """Return all email data in a format compatible with activity model.

        Returns:
            List of emails in ActivityModel-compatible format
        """
        # Transform to format compatible with ActivityModel
        result = []
        for email in self.emails:
            try:
                # Extract basic information
                subject = email.get("subject", "")
                sender_name = email.get("sender", {}).get("name", "")
                sender_email = email.get("sender", {}).get("email", "")

                # Format the date display
                date_formatted = email.get("date_formatted", "")

                # Determine course context
                course = email.get("course_context", "Unknown Course")

                # Get read status
                status = "Read" if email.get("metadata", {}).get(
                    "is_read", True) else "Unread"

                # Format the time display
                timestamp = email.get("timestamp", "")
                start_time = ""
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        start_time = dt.strftime("%I:%M %p").lstrip("0")
                    except (ValueError, TypeError):
                        start_time = ""

                # Create activity model compatible entry
                formatted_email = {
                    "message_id": email.get("message_id", ""),
                    "Date": date_formatted,
                    "Event Type": "Email",
                    "Title": subject,
                    "Course": course,
                    "Status": status,
                    "Start Time": start_time,
                    "HasSlack": False,
                    "HasEmail": True,
                    "From": f"{sender_name} <{sender_email}>",
                    "Content": email.get("content", ""),
                    "Timestamp": timestamp
                }

                result.append(formatted_email)

            except (KeyError, TypeError) as e:
                logger.warning(f"Error formatting email: {e}")

        return result

    def get_email_by_id(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific email by ID.

        Args:
            email_id: Unique identifier for the email

        Returns:
            The email data or None if not found
        """
        return self.email_by_id.get(email_id)

    def _setup_llm_provider(self):
        """Set up LLM provider if not already provided."""
        if self.llm_provider is None:
            try:
                # Try to load API key from environment
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    logger.error("ANTHROPIC_API_KEY not found in environment")
                    return False

                self.llm_provider = AnthropicProvider(
                    api_key=api_key,
                    model="claude-3-7-sonnet-20250219"
                )
                logger.info("Created default AnthropicProvider")
                return True
            except (ValueError, ImportError) as e:
                logger.error(f"Failed to create LLM provider: {e}")
                return False

        return True

    def _get_cache_key(self, activity_id: str, email_id: str) -> str:
        """Generate a cache key for activity-email correlation."""
        return f"{activity_id}:{email_id}"

    def _llm_correlate(self, activity: Dict[str, Any], email: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to determine correlation between activity and email.

        Args:
            activity: Activity data
            email: Email data

        Returns:
            Correlation result with confidence score and explanation
        """
        if not self._setup_llm_provider():
            logger.error("No LLM provider available for correlation")
            return {
                "is_related": False,
                "confidence": 0,
                "explanation": "LLM provider not available"
            }

        # Create correlation prompt
        prompt = self._create_correlation_prompt(activity, email)

        try:
            # Call LLM
            response = self.llm_provider.generate_response(
                prompt,
                system="You are an expert at determining relationships between educational activities and emails. Be precise and concise.",
                max_tokens=100,
                temperature=0.3
            )

            # Parse response
            result = self._parse_correlation_response(response)

            # Cache result
            cache_key = self._get_cache_key(activity.get(
                "id", "unknown"), email.get("message_id", "unknown"))
            self.correlation_cache[cache_key] = result

            return result

        except Exception as e:
            logger.error(f"Error calling LLM for correlation: {e}")
            return {
                "is_related": False,
                "confidence": 0,
                "explanation": f"Error in LLM correlation: {str(e)}"
            }

    def _create_correlation_prompt(self, activity: Dict[str, Any], email: Dict[str, Any]) -> str:
        """Create a prompt for the LLM to determine correlation.

        Args:
            activity: Activity data
            email: Email data

        Returns:
            Formatted prompt string
        """
        # Format activity data
        activity_title = activity.get("Title", "")
        activity_course = activity.get("Course", "")
        activity_date = activity.get("Date", "")
        activity_type = activity.get("Event Type", "")
        activity_description = activity.get("Description", "")

        # Format email data
        email_subject = email.get("subject", "")
        email_date = email.get("date_formatted", "")
        email_from = f"{email.get('sender', {}).get('name', '')} <{email.get('sender', {}).get('email', '')}>"
        email_body = email.get("content", "")

        # Truncate email body if too long
        if len(email_body) > 1000:
            email_body = email_body[:1000] + "..."

        # Create prompt
        prompt = f"""
You are analyzing the relationship between an educational activity and an email.

ACTIVITY:
Title: {activity_title}
Course: {activity_course}
Date: {activity_date}
Type: {activity_type}
Description: {activity_description}

EMAIL:
Subject: {email_subject}
Date: {email_date}
From: {email_from}
Body: {email_body}

Respond in this format:
RELATED: [Yes/No]
CONFIDENCE: [0-100]
EXPLANATION: [Brief explanation of relationship in 25 words or less]
"""
        return prompt

    def _parse_correlation_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response to extract correlation information.

        Args:
            response: LLM response string

        Returns:
            Dict with is_related, confidence, and explanation
        """
        # Default values
        result = {
            "is_related": False,
            "confidence": 0,
            "explanation": "Unable to determine relationship"
        }

        try:
            # Extract RELATED line
            related_match = re.search(
                r'RELATED:\s*(Yes|No)', response, re.IGNORECASE)
            if related_match:
                result["is_related"] = related_match.group(1).lower() == "yes"

            # Extract CONFIDENCE line
            confidence_match = re.search(r'CONFIDENCE:\s*(\d+)', response)
            if confidence_match:
                result["confidence"] = int(confidence_match.group(1))
                # Normalize to 0-1 range
                result["confidence"] = result["confidence"] / 100.0

            # Extract EXPLANATION line
            explanation_match = re.search(
                r'EXPLANATION:\s*(.*?)(?:\n|$)', response)
            if explanation_match:
                result["explanation"] = explanation_match.group(1).strip()

            return result

        except Exception as e:
            logger.error(f"Error parsing correlation response: {e}")
            return result

    def _filter_candidate_emails(self, activity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter emails to find potential candidates for correlation.

        This reduces the number of emails that need LLM analysis.

        Args:
            activity: Activity data

        Returns:
            List of candidate emails
        """
        candidates = []

        # Try to parse activity date
        activity_date_str = activity.get("Date", "")
        activity_date = None
        try:
            # Parse date like "Apr 8"
            current_year = datetime.now().year
            activity_date = datetime.strptime(
                f"{activity_date_str} {current_year}", "%b %d %Y")
        except (ValueError, TypeError):
            # If parsing fails, skip date-based filtering
            activity_date = None

        # Get activity title and course
        activity_title = activity.get("Title", "").lower()
        activity_course = activity.get("Course", "").lower()

        # Filter emails
        for email in self.emails:
            # Check if already cached
            cache_key = self._get_cache_key(activity.get(
                "id", "unknown"), email.get("message_id", "unknown"))
            if cache_key in self.correlation_cache:
                cached_result = self.correlation_cache[cache_key]
                if cached_result["is_related"] and cached_result["confidence"] > 0.5:
                    candidates.append(email)
                continue

            # Date proximity filter
            if activity_date:
                try:
                    email_date = datetime.fromisoformat(
                        email.get("timestamp", ""))
                    # Check if within 3 days of activity date
                    if abs((email_date - activity_date).days) > 3:
                        continue
                except (ValueError, TypeError):
                    # Skip date filtering if we can't parse the email date
                    pass

            # Simple content match filter
            email_subject = email.get("subject", "").lower()
            email_content = email.get("content", "").lower()
            # Ensure we get empty string if None
            email_course = email.get("course_context", "") or ""
            email_course = email_course.lower()

            # Check for keyword matches
            if (activity_title and activity_title in email_subject) or \
               (activity_course and (activity_course in email_subject or activity_course in email_content)) or \
               (email_course and email_course in activity_title):
                candidates.append(email)
                continue

            # Add some additional candidates to ensure we don't miss correlations
            # that simple keyword matching wouldn't catch
            if len(candidates) < 5:
                candidates.append(email)

        # Limit candidates to reasonable number
        return candidates[:10]

    def find_correlations(self, activity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find emails correlated with an activity.

        Args:
            activity: Activity data

        Returns:
            List of correlated emails with confidence scores
        """
        # Generate stable ID for activity if not present
        if "id" not in activity:
            activity_hash = hashlib.md5()
            activity_str = f"{activity.get('Title', '')}{activity.get('Date', '')}{activity.get('Course', '')}"
            activity_hash.update(activity_str.encode('utf-8'))
            activity["id"] = activity_hash.hexdigest()

        # Check for cached results
        activity_id = activity.get("id", "unknown")
        if activity_id in self.correlation_results:
            return self.correlation_results[activity_id]

        # Filter to find candidate emails
        candidates = self._filter_candidate_emails(activity)

        if not candidates:
            logger.info(
                f"No candidate emails found for activity: {activity.get('Title', '')}")
            return []

        logger.info(
            f"Found {len(candidates)} candidate emails for correlation")

        # Perform LLM correlation for each candidate
        correlated_emails = []
        for email in candidates:
            # Check cache first
            cache_key = self._get_cache_key(
                activity_id, email.get("message_id", "unknown"))
            if cache_key in self.correlation_cache:
                correlation = self.correlation_cache[cache_key]
            else:
                correlation = self._llm_correlate(activity, email)

            # Add to results if related with sufficient confidence
            if correlation["is_related"] and correlation["confidence"] > 0.5:
                # Clone email and add correlation info
                email_with_correlation = dict(email)
                email_with_correlation["correlation"] = correlation
                correlated_emails.append(email_with_correlation)

        # Sort by confidence (highest first)
        correlated_emails.sort(
            key=lambda x: x["correlation"]["confidence"], reverse=True)

        # Cache results
        self.correlation_results[activity_id] = correlated_emails

        return correlated_emails

    def start_background_correlation(self, activities: List[Dict[str, Any]]) -> None:
        """Start background processing of correlations for multiple activities.

        Args:
            activities: List of activities to process
        """
        if self.is_correlating:
            logger.warning("Background correlation already in progress")
            return

        # Create and start background thread
        self.correlation_thread = threading.Thread(
            target=self._background_correlation_worker,
            args=(activities,),
            daemon=True
        )
        self.is_correlating = True
        self.correlation_thread.start()
        logger.info(
            f"Started background correlation for {len(activities)} activities")

    def _background_correlation_worker(self, activities: List[Dict[str, Any]]) -> None:
        """Background worker that processes correlations.

        Args:
            activities: List of activities to process
        """
        try:
            for activity in activities:
                # Skip if already processed
                activity_id = activity.get("id", "unknown")
                if activity_id in self.correlation_results:
                    continue

                # Process correlation
                correlated = self.find_correlations(activity)
                logger.debug(
                    f"Found {len(correlated)} correlated emails for activity {activity_id}")

                # Add small delay to avoid overloading LLM API
                time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error in background correlation: {e}")
        finally:
            self.is_correlating = False
            logger.info("Background correlation completed")

    def get_correlation_status(self) -> Dict[str, Any]:
        """Get status of background correlation processing.

        Returns:
            Status information
        """
        return {
            "is_running": self.is_correlating,
            "activities_processed": len(self.correlation_results),
            "cache_entries": len(self.correlation_cache)
        }

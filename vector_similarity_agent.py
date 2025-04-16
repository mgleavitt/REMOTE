"""
Vector Similarity Email Agent for REMOTE Application

This module implements an email data agent that uses vector similarity
to efficiently correlate educational activities with email communication.
It is designed to integrate with the REMOTE application architecture.

Author: Marc Leavitt
Date: April 2025
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace
import os
import json
import logging
import threading
import queue
import time
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
import numpy as np
import re
from datetime import datetime

# Import sklearn components for vector similarity
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("scikit-learn not installed - vector similarity will be unavailable")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "threshold_strong": 0.5,             # Threshold for strong correlation
    "threshold_moderate": 0.4,           # Threshold for moderate correlation 
    "threshold_weak": 0.3,               # Threshold for weak correlation
    "course_match_boost": 0.2,           # Boost score for course match
    "module_match_boost": 0.15,          # Boost score for module match
    "assignment_match_boost": 0.15,      # Boost score for assignment match
    "date_proximity_boost_max": 0.1,     # Maximum boost for date proximity
    "date_proximity_days": 3,            # Days within which to consider dates proximate
    "ngram_range": (1, 3),               # Range of n-grams to use for TF-IDF
    "tfidf_min_df": 2,                   # Minimum document frequency for TF-IDF terms
    "exact_match_weight": 5,             # Weight for exact matches in token importance
    "max_correlations_per_activity": 5,  # Maximum number of correlations to store per activity
    "compute_immediately": True,         # Whether to compute correlations immediately on load
    "background_processing": True,       # Whether to process in background thread
}

@dataclass
class CorrelationEvidence:
    """Stores evidence for why a correlation was detected."""
    tfidf_similarity: float = 0.0
    course_match: bool = False
    module_match: bool = False
    assignment_match: bool = False
    date_proximity_days: Optional[int] = None
    key_term_matches: List[str] = None
    
    def __post_init__(self):
        if self.key_term_matches is None:
            self.key_term_matches = []
    
    def get_summary(self) -> str:
        """Return a human-readable summary of the evidence."""
        summary_parts = []
        
        if self.course_match:
            summary_parts.append("course match")
        if self.module_match:
            summary_parts.append("module match")
        if self.assignment_match:
            summary_parts.append("assignment match")
        if self.date_proximity_days is not None:
            summary_parts.append(f"date proximity ({self.date_proximity_days} days)")
        if self.key_term_matches:
            term_list = ", ".join(self.key_term_matches[:3])
            if len(self.key_term_matches) > 3:
                term_list += f" and {len(self.key_term_matches) - 3} more"
            summary_parts.append(f"key terms: {term_list}")
        
        if not summary_parts:
            return f"TF-IDF similarity: {self.tfidf_similarity:.2f}"
        
        return f"Evidence: {', '.join(summary_parts)} (TF-IDF: {self.tfidf_similarity:.2f})"

@dataclass
class EmailCorrelation:
    """Represents a correlation between an activity and an email."""
    email_id: str
    email_subject: str
    content_snippet: str
    sender_name: str
    timestamp: str
    raw_similarity: float
    adjusted_similarity: float
    confidence_level: str  # "strong", "moderate", "weak", "none"
    evidence: CorrelationEvidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        return {
            "email_id": self.email_id,
            "email_subject": self.email_subject,
            "content_snippet": self.content_snippet,
            "sender_name": self.sender_name,
            "timestamp": self.timestamp,
            "raw_similarity": float(self.raw_similarity),
            "adjusted_similarity": float(self.adjusted_similarity),
            "confidence_level": self.confidence_level,
            "evidence_summary": self.evidence.get_summary()
        }

class EntityExtractor:
    """Extract educational entities from text."""
    
    # Regular expressions for entity extraction
    COURSE_CODE_PATTERN = r'\b[A-Z]{2,4}\s?\d{3,4}[A-Z]?\b'  # CS101, MATH 200
    MODULE_PATTERN = r'\bmodules?\s*(\d+)\b|\bmodules?\s*([0-9]+[A-Za-z]?)\b'
    ASSIGNMENT_PATTERN = r'\b(?:problem ?sets?|assignments?|labs?|exercises?|homeworks?)\s*(?:#|No\.?|Number|)?\s*(\d+[A-Za-z]?)\b'
    DATE_PATTERN = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b'
    
    @staticmethod
    def extract_course_codes(text: str) -> List[str]:
        """Extract course codes like CS101, MATH 200."""
        if not text:
            return []
        matches = re.findall(EntityExtractor.COURSE_CODE_PATTERN, text, re.IGNORECASE)
        return [match.strip() for match in matches]
    
    @staticmethod
    def extract_module_numbers(text: str) -> List[str]:
        """Extract module numbers like 'Module 7' or 'Module 08'."""
        if not text:
            return []
        matches = re.findall(EntityExtractor.MODULE_PATTERN, text, re.IGNORECASE)
        # Flatten tuples and filter empty matches
        result = []
        for match_tuple in matches:
            for m in match_tuple:
                if m:
                    # Standardize module numbers (remove leading zeros)
                    std_num = m.lstrip('0')
                    if std_num:  # Ensure we're not adding empty strings
                        result.append(std_num)
        return result
    
    @staticmethod
    def extract_assignment_numbers(text: str) -> List[str]:
        """Extract assignment/problem set numbers."""
        if not text:
            return []
        matches = re.findall(EntityExtractor.ASSIGNMENT_PATTERN, text, re.IGNORECASE)
        return [match.strip() for match in matches if match.strip()]
    
    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """Extract dates in standard format."""
        if not text:
            return []
        matches = re.findall(EntityExtractor.DATE_PATTERN, text)
        return [match.strip() for match in matches]
    
    @staticmethod
    def standardize_date(date_str: str) -> Optional[datetime]:
        """Convert date strings to standard datetime objects."""
        if not date_str:
            return None
        
        # Remove ordinal suffixes
        date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
        
        # Try different date formats
        formats = [
            "%b %d",         # Mar 7
            "%B %d",         # March 7
            "%b %d %Y",      # Mar 7 2025
            "%B %d %Y",      # March 7 2025
            "%b. %d",        # Mar. 7
            "%B. %d"         # March. 7
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Set year to current if not specified
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt
            except ValueError:
                continue
        
        return None

class TextPreprocessor:
    """Preprocess text for educational content analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize preprocessor with configuration."""
        self.config = config
        self.vectorizer = None
    
    def extract_structured_features(self, text: str) -> Dict[str, Any]:
        """Extract structured features from text."""
        return {
            "course_codes": EntityExtractor.extract_course_codes(text),
            "module_numbers": EntityExtractor.extract_module_numbers(text),
            "assignment_numbers": EntityExtractor.extract_assignment_numbers(text),
            "dates": EntityExtractor.extract_dates(text)
        }
    
    def standardize_text(self, text: str) -> str:
        """Standardize text for better matching."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Standardize module references
        text = re.sub(r'module\s*(\d+)', r'module \1', text)
        
        # Standardize problem set references
        text = re.sub(r'problem\s*set\s*(\d+)', r'problemset \1', text)
        text = re.sub(r'assignment\s*(\d+)', r'assignment \1', text)
        
        return text.strip()
    
    def prepare_activity_text(self, activity: Dict[str, Any]) -> str:
        """Prepare activity text for vectorization."""
        # Combine relevant fields with appropriate weighting
        title = activity.get("Title", "")
        course = activity.get("Course", "")
        description = activity.get("Description", "")
        event_type = activity.get("Event Type", "")
        status = activity.get("Status", "")
        
        # Emphasize title and course by repeating
        text = f"{title} {title} {course} {course} {description} {event_type} {status}"
        
        return self.standardize_text(text)
    
    def prepare_email_text(self, email: Dict[str, Any]) -> str:
        """Prepare email text for vectorization."""
        # Combine relevant fields
        subject = email.get("subject", "")
        content = email.get("content", "")
        course = email.get("course_context", "")
        
        # Emphasize subject and course context by repeating
        text = f"{subject} {subject} {course} {course} {content}"
        
        return self.standardize_text(text)
    
    def fit_vectorizer(self, texts: List[str]) -> None:
        """Fit TF-IDF vectorizer on a corpus of texts."""
        if not HAS_SKLEARN:
            logger.error("scikit-learn is not installed - cannot create vectorizer")
            return
            
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=self.config["ngram_range"],
            min_df=self.config["tfidf_min_df"]
        )
        self.vectorizer.fit(texts)

class CorrelationAnalyzer:
    """Analyze correlations between activities and emails."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize analyzer with configuration."""
        self.config = config
        self.preprocessor = TextPreprocessor(config)
    
    def calculate_date_proximity(self, activity_date: str, email_date: str) -> Optional[int]:
        """Calculate proximity between activity and email dates in days."""
        std_activity_date = EntityExtractor.standardize_date(activity_date)
        std_email_date = EntityExtractor.standardize_date(email_date)
        
        if std_activity_date and std_email_date:
            days_diff = abs((std_activity_date - std_email_date).days)
            return days_diff
        
        return None
    
    def calculate_date_proximity_boost(self, days_diff: Optional[int]) -> float:
        """Calculate boost based on date proximity."""
        if days_diff is None:
            return 0.0
        
        max_days = self.config["date_proximity_days"]
        max_boost = self.config["date_proximity_boost_max"]
        
        if days_diff > max_days:
            return 0.0
        
        # Linear decay of boost based on days difference
        return max_boost * (1 - (days_diff / max_days))
    
    def find_common_terms(self, text1: str, text2: str) -> List[str]:
        """Find common important terms between two texts."""
        # Simple implementation - in production we'd use a more sophisticated approach
        # with ranked term importance
        words1 = set(re.findall(r'\b\w{3,}\b', text1.lower()))
        words2 = set(re.findall(r'\b\w{3,}\b', text2.lower()))
        
        # Filter out common English stopwords
        stopwords = {"the", "and", "for", "this", "that", "with", "from"}
        common_terms = words1.intersection(words2) - stopwords
        
        return list(common_terms)
    
    def analyze_correlation(
            self, 
            activity: Dict[str, Any], 
            email: Dict[str, Any],
            activity_vector: np.ndarray,
            email_vector: np.ndarray
        ) -> EmailCorrelation:
        """
        Analyze correlation between an activity and an email.
        
        Args:
            activity: Activity data dictionary
            email: Email data dictionary
            activity_vector: TF-IDF vector for activity
            email_vector: TF-IDF vector for email
            
        Returns:
            EmailCorrelation object with correlation details
        """
        # Calculate base TF-IDF similarity
        similarity = cosine_similarity(activity_vector, email_vector)[0][0]
        
        # Extract structured features
        activity_text = self.preprocessor.prepare_activity_text(activity)
        email_text = self.preprocessor.prepare_email_text(email)
        
        activity_features = self.preprocessor.extract_structured_features(activity_text)
        email_features = self.preprocessor.extract_structured_features(email_text)
        
        # Initialize evidence object
        evidence = CorrelationEvidence(tfidf_similarity=similarity)
        
        # Check for course match
        course_match = False
        for a_course in activity_features["course_codes"]:
            for e_course in email_features["course_codes"]:
                if a_course.lower() == e_course.lower():
                    course_match = True
                    break
        
        # If no course codes extracted, try matching course name
        if not course_match and "Course" in activity:
            activity_course = activity["Course"].lower()
            email_course_context = email.get("course_context")
            # Ensure email_course_context is not None before calling lower()
            if email_course_context is not None:
                email_course_context = email_course_context.lower()
                if email_course_context and email_course_context in activity_course:
                    course_match = True
        
        evidence.course_match = course_match
        
        # Check for module match
        module_match = False
        for a_module in activity_features["module_numbers"]:
            for e_module in email_features["module_numbers"]:
                if a_module == e_module:
                    module_match = True
                    break
        
        evidence.module_match = module_match
        
        # Check for assignment match
        assignment_match = False
        for a_assignment in activity_features["assignment_numbers"]:
            for e_assignment in email_features["assignment_numbers"]:
                if a_assignment == e_assignment:
                    assignment_match = True
                    break
        
        evidence.assignment_match = assignment_match
        
        # Calculate date proximity
        activity_date = activity.get("Date", "")
        email_date = email.get("date_formatted", "")
        days_diff = self.calculate_date_proximity(activity_date, email_date)
        evidence.date_proximity_days = days_diff
        
        # Find common key terms
        evidence.key_term_matches = self.find_common_terms(activity_text, email_text)
        
        # Calculate adjusted similarity score with boosts
        adjusted_similarity = similarity
        
        if course_match:
            adjusted_similarity += self.config["course_match_boost"]
        
        if module_match:
            adjusted_similarity += self.config["module_match_boost"]
        
        if assignment_match:
            adjusted_similarity += self.config["assignment_match_boost"]
        
        # Add date proximity boost
        date_boost = self.calculate_date_proximity_boost(days_diff)
        adjusted_similarity += date_boost
        
        # Ensure score doesn't exceed 1.0
        adjusted_similarity = min(adjusted_similarity, 1.0)
        
        # Determine confidence level
        confidence_level = "none"
        if adjusted_similarity >= self.config["threshold_strong"]:
            confidence_level = "strong"
        elif adjusted_similarity >= self.config["threshold_moderate"]:
            confidence_level = "moderate"
        elif adjusted_similarity >= self.config["threshold_weak"]:
            confidence_level = "weak"
        
        # Extract email metadata for result
        sender_name = ""
        if "sender" in email and isinstance(email["sender"], dict):
            sender_name = email["sender"].get("name", "")
        
        timestamp = email.get("timestamp", "")
        
        # Create content snippet
        content = email.get("content", "")
        content_snippet = content[:100] + "..." if len(content) > 100 else content
        
        # Create a result object
        result = EmailCorrelation(
            email_id=email.get("message_id", ""),
            email_subject=email.get("subject", ""),
            content_snippet=content_snippet,
            sender_name=sender_name,
            timestamp=timestamp,
            raw_similarity=similarity,
            adjusted_similarity=adjusted_similarity,
            confidence_level=confidence_level,
            evidence=evidence
        )
        
        return result

class VectorSimilarityEmailAgent:
    """
    Email data agent using vector similarity for correlation detection.
    
    This agent efficiently correlates educational activities with email
    communication using a hybrid approach combining TF-IDF vector similarity
    and structured educational entity matching.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the email data agent.
        
        Args:
            config: Configuration options for the agent
        """
        self.config = config or DEFAULT_CONFIG.copy()
        
        # Check for required dependencies
        if not HAS_SKLEARN:
            logger.warning("scikit-learn not installed - vector similarity will be unavailable")
        
        # Initialize components
        self.preprocessor = TextPreprocessor(self.config)
        self.analyzer = CorrelationAnalyzer(self.config)
        
        # Storage for data
        self.emails = []
        self.email_by_id = {}
        self.email_vectors = {}
        self.activity_vectors = {}
        self.correlation_results = {}
        
        # Threading resources
        self.correlation_queue = queue.Queue()
        self.correlation_thread = None
        self.is_correlating = False
        self.correlation_completed = False
        
        logger.info("VectorSimilarityEmailAgent initialized")
    
    def load_data(self, data_file: str) -> bool:
        """Load email data from JSON file.
        
        Args:
            data_file: Path to the JSON file containing email data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(data_file):
                logger.error("Data file not found: %s", data_file)
                return False
            
            with open(data_file, 'r', encoding='utf-8') as f:
                self.emails = json.load(f)
            
            # Build lookup dictionary
            self.email_by_id = {email["message_id"]: email for email in self.emails if "message_id" in email}
            
            logger.info("Loaded %d emails from %s", len(self.emails), data_file)
            
            # Reset correlation data
            self.email_vectors = {}
            self.activity_vectors = {}
            self.correlation_results = {}
            self.correlation_completed = False
            
            return True
            
        except (ValueError, IOError, json.JSONDecodeError) as e:
            logger.error("Error loading email data: %s", e)
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
                
                # Get sender info
                sender_name = ""
                sender_email = ""
                if "sender" in email and isinstance(email["sender"], dict):
                    sender_name = email["sender"].get("name", "")
                    sender_email = email["sender"].get("email", "")
                
                # Format the date display
                date_formatted = email.get("date_formatted", "")
                
                # Determine course context
                course = email.get("course_context", "Unknown Course")
                
                # Get read status
                status = "Read" if email.get("metadata", {}).get("is_read", True) else "Unread"
                
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
                logger.warning("Error formatting email: %s", e)
        
        return result
    
    def get_email_by_id(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific email by ID.
        
        Args:
            email_id: Unique identifier for the email
            
        Returns:
            The email data or None if not found
        """
        return self.email_by_id.get(email_id)
    
    def preprocess_data(self, activities: List[Dict[str, Any]]) -> None:
        """Preprocess activities and emails for correlation analysis.
        
        Args:
            activities: List of activities to preprocess
        """
        if not HAS_SKLEARN:
            logger.error("scikit-learn is not installed - cannot preprocess data")
            return
            
        if not self.emails:
            logger.warning("No email data loaded - cannot preprocess")
            return
            
        logger.info("Preprocessing data for correlation analysis...")
        
        # Prepare texts for fitting the vectorizer
        activity_texts = [self.preprocessor.prepare_activity_text(a) for a in activities]
        email_texts = [self.preprocessor.prepare_email_text(e) for e in self.emails]
        all_texts = activity_texts + email_texts
        
        # Fit vectorizer on all texts
        self.preprocessor.fit_vectorizer(all_texts)
        
        # Transform activity texts to vectors
        for i, activity in enumerate(activities):
            activity_id = self._get_activity_id(activity)
            self.activity_vectors[activity_id] = self.preprocessor.vectorizer.transform([activity_texts[i]])
        
        # Transform email texts to vectors
        for i, email in enumerate(self.emails):
            email_id = email.get("message_id", f"email_{i}")
            self.email_vectors[email_id] = self.preprocessor.vectorizer.transform([email_texts[i]])
        
        logger.info("Preprocessing complete: %d activities, %d emails", 
                    len(activities), len(self.emails))
    
    def _get_activity_id(self, activity: Dict[str, Any]) -> str:
        """Generate a stable ID for an activity."""
        if "id" in activity:
            return activity["id"]
        
        title = activity.get("Title", "")
        course = activity.get("Course", "")
        date = activity.get("Date", "")
        return f"{title}_{course}_{date}"
    
    def find_correlations(self, activity: Dict[str, Any]) -> List[EmailCorrelation]:
        """Find emails correlated with an activity.
        
        Args:
            activity: Activity data
            
        Returns:
            List of correlated emails
        """
        if not HAS_SKLEARN:
            logger.error("scikit-learn is not installed - cannot find correlations")
            return []
            
        activity_id = self._get_activity_id(activity)
        
        # Check if already processed
        if activity_id in self.correlation_results:
            return self.correlation_results[activity_id]
        
        # Check if activity vector exists
        if activity_id not in self.activity_vectors:
            logger.warning("Activity vector not found: %s", activity_id)
            return []
        
        activity_vector = self.activity_vectors[activity_id]
        results = []
        
        # Calculate correlation for each email
        for email_id, email_vector in self.email_vectors.items():
            email = self.get_email_by_id(email_id)
            if not email:
                continue
                
            result = self.analyzer.analyze_correlation(
                activity, 
                email,
                activity_vector,
                email_vector
            )
            
            # Only include non-zero confidence results
            if result.confidence_level != "none":
                results.append(result)
        
        # Sort by adjusted similarity score
        results.sort(key=lambda x: x.adjusted_similarity, reverse=True)
        
        # Limit results if configured
        max_results = self.config.get("max_correlations_per_activity", 5)
        if max_results and len(results) > max_results:
            results = results[:max_results]
        
        # Store results
        self.correlation_results[activity_id] = results
        
        return results
    
    def process_correlations(self, activities: List[Dict[str, Any]]) -> None:
        """Process correlations for a list of activities.
        
        This method preprocesses the data and finds correlations for all activities.
        
        Args:
            activities: List of activities to process
        """
        if not HAS_SKLEARN:
            logger.error("scikit-learn is not installed - cannot process correlations")
            return
            
        if not self.emails:
            logger.warning("No email data loaded - cannot process correlations")
            return
            
        # Preprocess data
        logger.info("Processing correlations for %d activities...", len(activities))
        self.preprocess_data(activities)
        
        # Process each activity
        for i, activity in enumerate(activities):
            activity_id = self._get_activity_id(activity)
            logger.debug("Processing activity %d/%d: %s", 
                         i+1, len(activities), activity_id)
            
            correlations = self.find_correlations(activity)
            
            # Update activity with correlation information
            if correlations:
                activity["HasEmail"] = True
                activity["EmailCorrelations"] = [c.to_dict() for c in correlations]
            else:
                activity["HasEmail"] = False
                activity["EmailCorrelations"] = []
        
        logger.info("Correlation processing complete")
        self.correlation_completed = True
    
    def start_background_correlation(self, activities: List[Dict[str, Any]]) -> None:
        """Start background processing of correlations for multiple activities.
        
        Args:
            activities: List of activities to process
        """
        if not HAS_SKLEARN:
            logger.error("scikit-learn is not installed - cannot process correlations")
            return
            
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
        logger.info("Started background correlation for %d activities", len(activities))
    
    def _background_correlation_worker(self, activities: List[Dict[str, Any]]) -> None:
        """Background worker that processes correlations.
        
        Args:
            activities: List of activities to process
        """
        try:
            # Preprocess all data first
            self.preprocess_data(activities)
            
            # Process activities in batches
            batch_size = 10
            for i in range(0, len(activities), batch_size):
                batch = activities[i:i+batch_size]
                
                # Process this batch
                for activity in batch:
                    # Skip if already processed
                    activity_id = self._get_activity_id(activity)
                    if activity_id in self.correlation_results:
                        continue
                    
                    # Process correlation
                    correlations = self.find_correlations(activity)
                    
                    # Update activity with correlation information
                    if correlations:
                        activity["HasEmail"] = True
                        activity["EmailCorrelations"] = [c.to_dict() for c in correlations]
                    else:
                        activity["HasEmail"] = False
                        activity["EmailCorrelations"] = []
                
                # Small delay to avoid blocking UI
                time.sleep(0.01)
                
            logger.info("Background correlation completed")
            self.correlation_completed = True
                
        except Exception as e:
            logger.error("Error in background correlation: %s", e)
        finally:
            self.is_correlating = False
    
    def get_correlation_status(self) -> Dict[str, Any]:
        """Get status of background correlation processing.
        
        Returns:
            Status information
        """
        return {
            "is_running": self.is_correlating,
            "activities_processed": len(self.correlation_results),
            "completed": self.correlation_completed
        }

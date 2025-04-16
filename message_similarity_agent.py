"""
Unified Message Similarity Agent for REMOTE Application

This module implements a configurable message similarity agent that can process
both email and Slack messages to correlate them with educational activities.
It uses vector similarity and structured entity matching to identify relevance.

Author: Marc Leavitt
Date: April 2025
"""
# pylint: disable=line-too-long trailing-whitespace

import os
import json
import logging
import threading
import queue
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import re
from datetime import datetime

# Import sklearn components for vector similarity
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("scikit-learn not installed - vector similarity will be unavailable")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "message_type": "email",  # "email" or "slack"
    "field_weights": {
        "subject": 3.0,      # Higher weight for email subjects
        "content": 1.0,      # Base weight for content
        "course_context": 2.0  # Medium weight for course context
    },
    "entity_extraction": {
        "course_code_pattern": r'\b[A-Z]{2,4}\s?\d{3,4}[A-Z]?\b',  # CS101, MATH 200
        "module_pattern": r'\bmodules?\s*(\d+)\b|\bmodules?\s*([0-9]+[A-Za-z]?)\b',
        "assignment_pattern": r'\b(?:problem ?sets?|assignments?|labs?|exercises?|homeworks?)\s*(?:#|No\.?|Number|)?\s*(\d+[A-Za-z]?)\b',
        "date_pattern": r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b'
    },
    "preprocessing": {
        "exclude_message_types": [],  # Message types to exclude
        "exclude_substrings": ["Automatic Reply", "Out of Office"],  # Substrings to exclude
        "ngram_range": [1, 3],  # Range of n-grams for TF-IDF
        "tfidf_min_df": 2,      # Minimum document frequency for TF-IDF
    },
    "correlation": {
        "threshold_strong": 0.5,             # Threshold for strong correlation
        "threshold_moderate": 0.4,           # Threshold for moderate correlation
        "threshold_weak": 0.3,               # Threshold for weak correlation
        "course_match_boost": 0.2,           # Boost for course match
        "module_match_boost": 0.15,          # Boost for module match
        "assignment_match_boost": 0.15,      # Boost for assignment match
        "date_proximity_boost_max": 0.1,     # Maximum boost for date proximity
        "date_proximity_days": 3,            # Days for date proximity
        "exact_match_weight": 5.0,           # Weight for exact matches
    },
    "output": {
        "max_correlations_per_activity": 5,  # Maximum correlations to return
        "compute_immediately": True,         # Compute on load
        "background_processing": True,       # Process in background
    }
}

# Email-specific default config overrides
EMAIL_CONFIG_OVERRIDES = {
    "message_type": "email",
    "field_weights": {
        "subject": 3.0,  # Higher weight for email subjects
        "content": 1.0, 
        "sender_name": 0.5
    },
    "preprocessing": {
        "exclude_message_types": [],
        "exclude_substrings": ["Automatic Reply", "Out of Office", "Do not reply"]
    }
}

# Slack-specific default config overrides
SLACK_CONFIG_OVERRIDES = {
    "message_type": "slack",
    "field_weights": {
        "subject": 1.0,  # Lower weight since subject is reconstructed in Slack
        "content": 2.0,  # Higher weight for message content
        "channel_name": 1.5  # Medium weight for channel name
    },
    "preprocessing": {
        "exclude_message_types": ["channel_join", "channel_leave", "bot_message"],
        "exclude_substrings": []
    }
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
class MessageCorrelation:
    """Represents a correlation between an activity and a message (email or Slack)."""
    message_id: str
    message_subject: str
    content_snippet: str
    sender_name: str
    timestamp: str
    raw_similarity: float
    adjusted_similarity: float
    confidence_level: str  # "strong", "moderate", "weak", "none"
    evidence: CorrelationEvidence
    message_type: str  # "email" or "slack"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for JSON serialization."""
        return {
            "message_id": self.message_id,
            "message_subject": self.message_subject,
            "content_snippet": self.content_snippet,
            "sender_name": self.sender_name,
            "timestamp": self.timestamp,
            "raw_similarity": float(self.raw_similarity),
            "adjusted_similarity": float(self.adjusted_similarity),
            "confidence_level": self.confidence_level,
            "evidence_summary": self.evidence.get_summary(),
            "message_type": self.message_type
        }


class EntityExtractor:
    """Extract educational entities from text based on configured patterns."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize entity extractor with configured patterns.
        
        Args:
            config: Configuration dictionary with pattern definitions
        """
        self.config = config
        self.entity_extraction_config = config.get("entity_extraction", {})
        
        # Get patterns from config or use defaults
        self.course_code_pattern = self.entity_extraction_config.get(
            "course_code_pattern", 
            r'\b[A-Z]{2,4}\s?\d{3,4}[A-Z]?\b'
        )
        self.module_pattern = self.entity_extraction_config.get(
            "module_pattern", 
            r'\bmodules?\s*(\d+)\b|\bmodules?\s*([0-9]+[A-Za-z]?)\b'
        )
        self.assignment_pattern = self.entity_extraction_config.get(
            "assignment_pattern", 
            r'\b(?:problem ?sets?|assignments?|labs?|exercises?|homeworks?)\s*(?:#|No\.?|Number|)?\s*(\d+[A-Za-z]?)\b'
        )
        self.date_pattern = self.entity_extraction_config.get(
            "date_pattern", 
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b'
        )
    
    def extract_course_codes(self, text: str) -> List[str]:
        """Extract course codes like CS101, MATH 200."""
        if not text:
            return []
        matches = re.findall(self.course_code_pattern, text, re.IGNORECASE)
        return [match.strip() for match in matches]
    
    def extract_module_numbers(self, text: str) -> List[str]:
        """Extract module numbers like 'Module 7' or 'Module 08'."""
        if not text:
            return []
        matches = re.findall(self.module_pattern, text, re.IGNORECASE)
        # Flatten tuples and filter empty matches
        result = []
        for match_tuple in matches:
            if isinstance(match_tuple, tuple):
                for m in match_tuple:
                    if m:
                        # Standardize module numbers (remove leading zeros)
                        std_num = m.lstrip('0')
                        if std_num:  # Ensure we're not adding empty strings
                            result.append(std_num)
            else:
                result.append(match_tuple)
        return result
    
    def extract_assignment_numbers(self, text: str) -> List[str]:
        """Extract assignment/problem set numbers."""
        if not text:
            return []
        matches = re.findall(self.assignment_pattern, text, re.IGNORECASE)
        # Handle potential tuple matches
        result = []
        for match in matches:
            if isinstance(match, tuple):
                for m in match:
                    if m and m.strip():
                        result.append(m.strip())
            elif match and match.strip():
                result.append(match.strip())
        return result
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract dates in standard format."""
        if not text:
            return []
        matches = re.findall(self.date_pattern, text)
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
    """Preprocess text for educational content analysis with configuration-driven behavior."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize preprocessor with configuration.
        
        Args:
            config: Configuration dictionary for text preprocessing
        """
        self.config = config
        self.preprocessing_config = config.get("preprocessing", {})
        self.field_weights = config.get("field_weights", {})
        self.message_type = config.get("message_type", "email")
        self.vectorizer = None
        self.entity_extractor = EntityExtractor(config)
    
    def extract_structured_features(self, text: str) -> Dict[str, Any]:
        """Extract structured features from text using configured entity extractor."""
        return {
            "course_codes": self.entity_extractor.extract_course_codes(text),
            "module_numbers": self.entity_extractor.extract_module_numbers(text),
            "assignment_numbers": self.entity_extractor.extract_assignment_numbers(text),
            "dates": self.entity_extractor.extract_dates(text)
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
        """Prepare activity text for vectorization with configured field weights."""
        # Combine relevant fields with appropriate weighting
        title = activity.get("Title", "")
        course = activity.get("Course", "")
        description = activity.get("Description", "")
        event_type = activity.get("Event Type", "")
        status = activity.get("Status", "")
        
        # Apply field weights from configuration
        title_weight = self.field_weights.get("title", 2.0)
        course_weight = self.field_weights.get("course", 2.0)
        
        # Repeat text based on weights (simple weighting approach)
        weighted_title = " ".join([title] * int(title_weight))
        weighted_course = " ".join([course] * int(course_weight))
        
        text = f"{weighted_title} {weighted_course} {description} {event_type} {status}"
        
        return self.standardize_text(text)
    
    def prepare_message_text(self, message: Dict[str, Any]) -> str:
        """Prepare message text for vectorization based on message type and configuration.
        
        Args:
            message: Message data (email or Slack)
            
        Returns:
            Processed text for vectorization
        """
        # Common fields for both message types - ensure we handle None values
        content = message.get("content", "") or ""
        course_context = message.get("course_context", "") or ""
        
        # Apply weights from configuration
        content_weight = self.field_weights.get("content", 1.0)
        course_context_weight = self.field_weights.get("course_context", 2.0)
        
        # Message-type specific field handling
        if self.message_type == "email":
            subject = message.get("subject", "") or ""
            subject_weight = self.field_weights.get("subject", 3.0)
            
            # Get sender info
            sender_name = ""
            if "sender" in message and isinstance(message["sender"], dict):
                sender_name = message["sender"].get("name", "") or ""
            
            sender_weight = self.field_weights.get("sender_name", 0.5)
            
            # Weighted components
            weighted_subject = " ".join([subject] * int(subject_weight))
            weighted_content = " ".join([content] * int(content_weight))
            weighted_course = " ".join([course_context] * int(course_context_weight))
            weighted_sender = " ".join([sender_name] * int(sender_weight))
            
            text = f"{weighted_subject} {weighted_course} {weighted_content} {weighted_sender}"
            
        else:  # slack
            # For Slack, reconstruct subject from channel name or other metadata
            channel_name = ""
            if "recipients" in message and isinstance(message["recipients"], list):
                for recipient in message["recipients"]:
                    if recipient.get("type") == "channel":
                        channel_name = recipient.get("name", "") or ""
                        break
            
            # Use subject field if present (may be reconstructed)
            subject = message.get("subject", channel_name) or ""
            subject_weight = self.field_weights.get("subject", 1.0)
            channel_weight = self.field_weights.get("channel_name", 1.5)
            
            # Weighted components
            weighted_subject = " ".join([subject] * int(subject_weight))
            weighted_channel = " ".join([channel_name] * int(channel_weight))
            weighted_content = " ".join([content] * int(content_weight))
            weighted_course = " ".join([course_context] * int(course_context_weight))
            
            text = f"{weighted_subject} {weighted_channel} {weighted_course} {weighted_content}"
        
        return self.standardize_text(text)
    
    def fit_vectorizer(self, texts: List[str]) -> None:
        """Fit TF-IDF vectorizer on a corpus of texts."""
        if not HAS_SKLEARN:
            logger.error("scikit-learn is not installed - cannot create vectorizer")
            return
        
        # Get n-gram range from config
        ngram_range = self.preprocessing_config.get("ngram_range", [1, 3])
        if isinstance(ngram_range, list) and len(ngram_range) == 2:
            ngram_range = tuple(ngram_range)
        
        # Get minimum document frequency from config    
        min_df = self.preprocessing_config.get("tfidf_min_df", 2)
        
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=ngram_range,
            min_df=min_df
        )
        self.vectorizer.fit(texts)
        logger.info("Fitted TF-IDF vectorizer on %d texts", len(texts))


class CorrelationAnalyzer:
    """Analyze correlations between activities and messages with configuration-driven behavior."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize analyzer with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.correlation_config = config.get("correlation", {})
        self.message_type = config.get("message_type", "email")
        self.preprocessor = TextPreprocessor(config)
        self.entity_extractor = EntityExtractor(config)
    
    def calculate_date_proximity(self, activity_date: str, message_date: str) -> Optional[int]:
        """Calculate proximity between activity and message dates in days."""
        std_activity_date = self.entity_extractor.standardize_date(activity_date)
        std_message_date = self.entity_extractor.standardize_date(message_date)
        
        if std_activity_date and std_message_date:
            days_diff = abs((std_activity_date - std_message_date).days)
            return days_diff
        
        return None
    
    def calculate_date_proximity_boost(self, days_diff: Optional[int]) -> float:
        """Calculate boost based on date proximity using configuration parameters."""
        if days_diff is None:
            return 0.0
        
        max_days = self.correlation_config.get("date_proximity_days", 3)
        max_boost = self.correlation_config.get("date_proximity_boost_max", 0.1)
        
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
        stopwords = {"the", "and", "for", "this", "that", "with", "from", "have", 
                    "was", "are", "has", "been", "were", "will", "any", "all"}
        common_terms = words1.intersection(words2) - stopwords
        
        return list(common_terms)
    
    def analyze_correlation(
            self, 
            activity: Dict[str, Any], 
            message: Dict[str, Any],
            activity_vector: np.ndarray,
            message_vector: np.ndarray
        ) -> MessageCorrelation:
        """
        Analyze correlation between an activity and a message using configuration parameters.
        
        Args:
            activity: Activity data dictionary
            message: Message data dictionary (email or Slack)
            activity_vector: TF-IDF vector for activity
            message_vector: TF-IDF vector for message
            
        Returns:
            MessageCorrelation object with correlation details
        """
        # Calculate base TF-IDF similarity
        similarity = cosine_similarity(activity_vector, message_vector)[0][0]
        
        # Extract structured features
        activity_text = self.preprocessor.prepare_activity_text(activity)
        message_text = self.preprocessor.prepare_message_text(message)
        
        activity_features = self.preprocessor.extract_structured_features(activity_text)
        message_features = self.preprocessor.extract_structured_features(message_text)
        
        # Initialize evidence object
        evidence = CorrelationEvidence(tfidf_similarity=similarity)
        
        # Check for course match
        course_match = False
        for a_course in activity_features["course_codes"]:
            for m_course in message_features["course_codes"]:
                if a_course.lower() == m_course.lower():
                    course_match = True
                    break
        
        # If no course codes extracted, try matching course name
        if not course_match and "Course" in activity:
            activity_course = activity["Course"].lower()
            message_course_context = message.get("course_context")
            # Ensure message_course_context is not None before calling lower()
            if message_course_context is not None:
                message_course_context = message_course_context.lower()
                if message_course_context and message_course_context in activity_course:
                    course_match = True
        
        evidence.course_match = course_match
        
        # Check for module match
        module_match = False
        for a_module in activity_features["module_numbers"]:
            for m_module in message_features["module_numbers"]:
                if a_module == m_module:
                    module_match = True
                    break
        
        evidence.module_match = module_match
        
        # Check for assignment match
        assignment_match = False
        for a_assignment in activity_features["assignment_numbers"]:
            for m_assignment in message_features["assignment_numbers"]:
                if a_assignment == m_assignment:
                    assignment_match = True
                    break
        
        evidence.assignment_match = assignment_match
        
        # Calculate date proximity
        activity_date = activity.get("Date", "")
        message_date = message.get("date_formatted", "")
        days_diff = self.calculate_date_proximity(activity_date, message_date)
        evidence.date_proximity_days = days_diff
        
        # Find common key terms
        evidence.key_term_matches = self.find_common_terms(activity_text, message_text)
        
        # Calculate adjusted similarity score with boosts from configuration
        adjusted_similarity = similarity
        
        if course_match:
            course_boost = self.correlation_config.get("course_match_boost", 0.2)
            adjusted_similarity += course_boost
        
        if module_match:
            module_boost = self.correlation_config.get("module_match_boost", 0.15)
            adjusted_similarity += module_boost
        
        if assignment_match:
            assignment_boost = self.correlation_config.get("assignment_match_boost", 0.15)
            adjusted_similarity += assignment_boost
        
        # Add date proximity boost
        date_boost = self.calculate_date_proximity_boost(days_diff)
        adjusted_similarity += date_boost
        
        # Ensure score doesn't exceed 1.0
        adjusted_similarity = min(adjusted_similarity, 1.0)
        
        # Determine confidence level using thresholds from configuration
        threshold_strong = self.correlation_config.get("threshold_strong", 0.5)
        threshold_moderate = self.correlation_config.get("threshold_moderate", 0.4)
        threshold_weak = self.correlation_config.get("threshold_weak", 0.3)
        
        confidence_level = "none"
        if adjusted_similarity >= threshold_strong:
            confidence_level = "strong"
        elif adjusted_similarity >= threshold_moderate:
            confidence_level = "moderate"
        elif adjusted_similarity >= threshold_weak:
            confidence_level = "weak"
        
        # Extract message metadata for result
        message_id = message.get("message_id", "")
        
        # Extract subject differently based on message type
        if self.message_type == "email":
            message_subject = message.get("subject", "")
        else:  # slack
            # For Slack, use subject if available, otherwise reconstruct from channel
            message_subject = message.get("subject", "")
            if not message_subject and "recipients" in message:
                for recipient in message["recipients"]:
                    if recipient.get("type") == "channel":
                        message_subject = f"Channel: {recipient.get('name', '')}"
                        break
        
        # Extract sender name
        sender_name = ""
        if "sender" in message and isinstance(message["sender"], dict):
            sender_name = message["sender"].get("name", "")
            if not sender_name and self.message_type == "slack":
                sender_name = message["sender"].get("slack_id", "")
        
        # Get timestamp
        timestamp = message.get("timestamp", "")
        
        # Create content snippet
        content = message.get("content", "")
        content_snippet = content[:100] + "..." if len(content) > 100 else content
        
        # Create a result object
        result = MessageCorrelation(
            message_id=message_id,
            message_subject=message_subject,
            content_snippet=content_snippet,
            sender_name=sender_name,
            timestamp=timestamp,
            raw_similarity=similarity,
            adjusted_similarity=adjusted_similarity,
            confidence_level=confidence_level,
            evidence=evidence,
            message_type=self.message_type
        )
        
        return result


class MessageSimilarityAgent:
    """
    Unified message similarity agent that can process both email and Slack messages.
    
    This agent uses vector similarity and structured entity matching to correlate
    educational activities with messages, with all behavior differences driven
    through configuration.
    """
    
    def __init__(self, config: Union[Dict[str, Any], str] = None):
        """Initialize the message similarity agent.
        
        Args:
            config: Configuration dictionary or path to JSON config file
        """
        # Load configuration
        self.config = self._load_config(config)
        
        # Set message type
        self.message_type = self.config.get("message_type", "email")
        logger.info("Initializing MessageSimilarityAgent for message type: %s", 
                   self.message_type)
        
        # Check for required dependencies
        if not HAS_SKLEARN:
            logger.warning("scikit-learn not installed - vector similarity will be unavailable")
        
        # Initialize components with configuration
        self.preprocessor = TextPreprocessor(self.config)
        self.analyzer = CorrelationAnalyzer(self.config)
        
        # Storage for data
        self.messages = []
        self.message_by_id = {}
        self.message_vectors = {}
        self.activity_vectors = {}
        self.correlation_results = {}
        
        # Threading resources
        self.correlation_queue = queue.Queue()
        self.correlation_thread = None
        self.is_correlating = False
        self.correlation_completed = False
        
        logger.info("MessageSimilarityAgent initialized with configuration: %s", 
                   {k: v for k, v in self.config.items() if k != "entity_extraction"})
    
    def _load_config(self, config: Union[Dict[str, Any], str, None]) -> Dict[str, Any]:
        """Load configuration from dictionary, file, or defaults.
        
        Args:
            config: Configuration dictionary, path to config file, or None for defaults
            
        Returns:
            Configuration dictionary
        """
        result_config = DEFAULT_CONFIG.copy()
        
        if config is None:
            logger.info("Using default configuration")
            return result_config
        
        if isinstance(config, str):
            # Load from file
            try:
                with open(config, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                logger.info("Loaded configuration from file: %s", config)
                
                # Deep update the default config
                self._deep_update(result_config, file_config)
                
            except (IOError, json.JSONDecodeError) as e:
                logger.error("Failed to load configuration from %s: %s", config, e)
                logger.info("Falling back to default configuration")
                
        elif isinstance(config, dict):
            # Use provided config dict
            logger.info("Using provided configuration dictionary")
            
            # Deep update the default config
            self._deep_update(result_config, config)
            
        else:
            logger.warning("Invalid configuration type, expected dict or string: %s", 
                         type(config))
        
        # Apply message-type specific overrides
        message_type = result_config.get("message_type", "email")
        if message_type == "email":
            overrides = EMAIL_CONFIG_OVERRIDES
        else:  # slack
            overrides = SLACK_CONFIG_OVERRIDES
        
        # Only apply overrides for settings not explicitly provided
        for key, value in overrides.items():
            if key not in config and key != "message_type":
                if isinstance(value, dict):
                    if key not in result_config:
                        result_config[key] = {}
                    for subkey, subvalue in value.items():
                        if subkey not in result_config[key]:
                            result_config[key][subkey] = subvalue
                else:
                    if key not in result_config:
                        result_config[key] = value
        
        return result_config
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Deep update a nested dictionary with another dictionary.
        
        Args:
            target: Dictionary to update
            source: Dictionary with updates
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # Recursively update nested dictionaries
                self._deep_update(target[key], value)
            else:
                # Otherwise replace or add the value
                target[key] = value
    
    def load_data(self, data_file: str) -> bool:
        """Load message data from JSON file.
        
        Args:
            data_file: Path to the JSON file containing message data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(data_file):
                logger.error("Data file not found: %s", data_file)
                return False
            
            with open(data_file, 'r', encoding='utf-8') as f:
                self.messages = json.load(f)
            
            # Validate message type
            valid_messages = []
            for message in self.messages:
                msg_type = message.get("source_type", "")
                if msg_type == self.message_type or not msg_type:
                    valid_messages.append(message)
            
            if len(valid_messages) < len(self.messages):
                logger.warning("Filtered %d messages that didn't match type '%s'", 
                             len(self.messages) - len(valid_messages), self.message_type)
                self.messages = valid_messages
            
            # Apply exclusion criteria from configuration
            exclude_types = self.config.get("preprocessing", {}).get("exclude_message_types", [])
            exclude_substrings = self.config.get("preprocessing", {}).get("exclude_substrings", [])
            
            if exclude_types or exclude_substrings:
                original_count = len(self.messages)
                filtered_messages = []
                
                for message in self.messages:
                    # Skip excluded message types
                    msg_type = message.get("message_type", "")
                    if msg_type in exclude_types:
                        continue
                    
                    # Skip messages with excluded substrings
                    subject = message.get("subject", "")
                    content = message.get("content", "")
                    excluded = False
                    
                    for substring in exclude_substrings:
                        if (substring in subject) or (substring in content):
                            excluded = True
                            break
                    
                    if not excluded:
                        filtered_messages.append(message)
                
                if len(filtered_messages) < original_count:
                    logger.info("Excluded %d messages based on configuration filters", 
                              original_count - len(filtered_messages))
                    self.messages = filtered_messages
            
            # Build lookup dictionary
            self.message_by_id = {}
            for message in self.messages:
                message_id = message.get("message_id")
                if message_id:
                    self.message_by_id[message_id] = message
            
            logger.info("Loaded %d %s messages from %s", 
                      len(self.messages), self.message_type, data_file)
            
            # Reset correlation data
            self.message_vectors = {}
            self.activity_vectors = {}
            self.correlation_results = {}
            self.correlation_completed = False
            
            return True
            
        except (ValueError, IOError, json.JSONDecodeError) as e:
            logger.error("Error loading message data: %s", e)
            return False
    
    def get_data(self) -> List[Dict[str, Any]]:
        """Return all message data in a format compatible with activity model.
        
        Returns:
            List of messages in ActivityModel-compatible format
        """
        # Transform to format compatible with ActivityModel
        result = []
        for message in self.messages:
            try:
                # Extract basic information
                subject = message.get("subject", "")
                
                # Get sender info
                sender_name = ""
                sender_id = ""
                if "sender" in message and isinstance(message["sender"], dict):
                    sender_name = message["sender"].get("name", "")
                    if self.message_type == "email":
                        sender_id = message["sender"].get("email", "")
                    else:  # slack
                        sender_id = message["sender"].get("slack_id", "")
                
                # Format the date display
                date_formatted = message.get("date_formatted", "")
                
                # Determine course context
                course = message.get("course_context", "Unknown Course")
                
                # Get appropriate status based on message type
                if self.message_type == "email":
                    status = "Read" if message.get("metadata", {}).get("is_read", True) else "Unread"
                else:  # slack
                    # For Slack, use channel or conversation type as status
                    status = "Channel Message"
                    if "recipients" in message and isinstance(message["recipients"], list):
                        for recipient in message["recipients"]:
                            if recipient.get("type") == "dm":
                                status = "Direct Message"
                                break
                
                # Format the time display
                timestamp = message.get("timestamp", "")
                start_time = ""
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        start_time = dt.strftime("%I:%M %p").lstrip("0")
                    except (ValueError, TypeError):
                        start_time = ""
                
                # Create activity model compatible entry
                formatted_message = {
                    "message_id": message.get("message_id", ""),
                    "Date": date_formatted,
                    "Event Type": self.message_type.capitalize(),
                    "Title": subject,
                    "Course": course,
                    "Status": status,
                    "Start Time": start_time,
                    "HasSlack": self.message_type == "slack",
                    "HasEmail": self.message_type == "email",
                    "From": f"{sender_name} <{sender_id}>" if sender_id else sender_name,
                    "Content": message.get("content", ""),
                    "Timestamp": timestamp
                }
                
                result.append(formatted_message)
                
            except (KeyError, TypeError) as e:
                logger.warning("Error formatting message: %s", e)
        
        return result
    
    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific message by ID.
        
        Args:
            message_id: Unique identifier for the message
            
        Returns:
            The message data or None if not found
        """
        return self.message_by_id.get(message_id)
    
    def preprocess_data(self, activities: List[Dict[str, Any]]) -> None:
        """Preprocess activities and messages for correlation analysis.
        
        Args:
            activities: List of activities to preprocess
        """
        if not HAS_SKLEARN:
            logger.error("scikit-learn is not installed - cannot preprocess data")
            return
            
        if not self.messages:
            logger.warning("No message data loaded - cannot preprocess")
            return
            
        logger.info("Preprocessing data for correlation analysis...")
        
        # Prepare texts for fitting the vectorizer
        activity_texts = [self.preprocessor.prepare_activity_text(a) for a in activities]
        message_texts = [self.preprocessor.prepare_message_text(m) for m in self.messages]
        all_texts = activity_texts + message_texts
        
        # Fit vectorizer on all texts
        self.preprocessor.fit_vectorizer(all_texts)
        
        # Transform activity texts to vectors
        for i, activity in enumerate(activities):
            activity_id = self._get_activity_id(activity)
            self.activity_vectors[activity_id] = self.preprocessor.vectorizer.transform([activity_texts[i]])
        
        # Transform message texts to vectors
        for i, message in enumerate(self.messages):
            message_id = message.get("message_id", f"message_{i}")
            self.message_vectors[message_id] = self.preprocessor.vectorizer.transform([message_texts[i]])
        
        logger.info("Preprocessing complete: %d activities, %d messages", 
                    len(activities), len(self.messages))
    
    def _get_activity_id(self, activity: Dict[str, Any]) -> str:
        """Generate a stable ID for an activity."""
        if "id" in activity:
            return activity["id"]
        
        title = activity.get("Title", "")
        course = activity.get("Course", "")
        date = activity.get("Date", "")
        return f"{title}_{course}_{date}"
    
    def find_correlations(self, activity: Dict[str, Any]) -> List[MessageCorrelation]:
        """Find messages correlated with an activity.
        
        Args:
            activity: Activity data
            
        Returns:
            List of correlated messages
        """
        if not HAS_SKLEARN:
            logger.error("scikit-learn is not installed - cannot find correlations")
            return []
            
        # Ensure activity has string values for dates
        activity = self._ensure_string_values(activity)
        
        # Get activity ID once
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
        
        # Calculate correlation for each message
        for message_id, message_vector in self.message_vectors.items():
            message = self.get_message_by_id(message_id)
            if not message:
                continue
                
            result = self.analyzer.analyze_correlation(
                activity, 
                message,
                activity_vector,
                message_vector
            )
            
            # Only include non-zero confidence results
            if result.confidence_level != "none":
                results.append(result)
        
        # Sort by adjusted similarity score
        results.sort(key=lambda x: x.adjusted_similarity, reverse=True)
        
        # Limit results if configured
        max_results = self.config.get("output", {}).get("max_correlations_per_activity", 5)
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
            
        if not self.messages:
            logger.warning("No message data loaded - cannot process correlations")
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
            activity_has_message = f"Has{self.message_type.capitalize()}"
            if correlations:
                activity[activity_has_message] = True
                activity["MessageCorrelations"] = [c.to_dict() for c in correlations]
            else:
                activity[activity_has_message] = False
                activity["MessageCorrelations"] = []
        
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
            # Ensure activities have string values for dates
            string_activities = [self._ensure_string_values(activity) for activity in activities]
            self.preprocess_data(string_activities)
            
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
                    
                    # Ensure string values before processing
                    string_activity = self._ensure_string_values(activity)
                    
                    # Process correlation
                    correlations = self.find_correlations(string_activity)
                    
                    # Update activity with correlation information
                    activity_has_message = f"Has{self.message_type.capitalize()}"
                    if correlations:
                        activity[activity_has_message] = True
                        activity["MessageCorrelations"] = [c.to_dict() for c in correlations]
                    else:
                        activity[activity_has_message] = False
                        activity["MessageCorrelations"] = []
                
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
            "completed": self.correlation_completed,
            "message_type": self.message_type
        }
    
    def save_results(self, output_file: str) -> bool:
        """Save correlation results to a JSON file.
        
        Args:
            output_file: Path to output file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create result structure
            results = {
                "results": [],
                "summary": {
                    "activities_analyzed": len(self.correlation_results),
                    "total_correlations": 0,
                    "strong_correlations": 0,
                    "moderate_correlations": 0,
                    "weak_correlations": 0,
                    "avg_correlations_per_activity": 0,
                    "message_type": self.message_type
                },
                "config": self.config
            }
            
            # Add results for each activity
            for activity_id, correlations in self.correlation_results.items():
                # Find the activity data - this assumes we have activity data in memory
                # which may not be the case in all scenarios
                activity_data = {"id": activity_id}
                
                # Count correlations by confidence level
                strong_count = sum(1 for c in correlations if c.confidence_level == "strong")
                moderate_count = sum(1 for c in correlations if c.confidence_level == "moderate")
                weak_count = sum(1 for c in correlations if c.confidence_level == "weak")
                total_count = len(correlations)
                
                # Update summary counts
                results["summary"]["total_correlations"] += total_count
                results["summary"]["strong_correlations"] += strong_count
                results["summary"]["moderate_correlations"] += moderate_count
                results["summary"]["weak_correlations"] += weak_count
                
                # Group correlations by confidence level
                correlation_dict = {
                    "strong": [c.to_dict() for c in correlations if c.confidence_level == "strong"],
                    "moderate": [c.to_dict() for c in correlations if c.confidence_level == "moderate"],
                    "weak": [c.to_dict() for c in correlations if c.confidence_level == "weak"]
                }
                
                # Add activity result
                results["results"].append({
                    "activity": activity_data,
                    "correlations": correlation_dict,
                    "correlation_counts": {
                        "strong": strong_count,
                        "moderate": moderate_count,
                        "weak": weak_count,
                        "total": total_count
                    }
                })
            
            # Calculate average correlations per activity
            if results["summary"]["activities_analyzed"] > 0:
                results["summary"]["avg_correlations_per_activity"] = (
                    results["summary"]["total_correlations"] / 
                    results["summary"]["activities_analyzed"]
                )
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", 
                      exist_ok=True)
            
            # Write results to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            
            logger.info("Saved correlation results to %s", output_file)
            return True
            
        except Exception as e:
            logger.error("Error saving results: %s", e)
            return False

    def _ensure_string_values(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all values in the activity dictionary are string-compatible.
        
        Args:
            activity: Activity data dictionary
            
        Returns:
            Activity with all values converted to strings where needed
        """
        result = {}
        for key, value in activity.items():
            if isinstance(value, datetime):
                # Convert datetime to string
                result[key] = value.strftime("%b %d")
            elif value is None:
                # Convert None to empty string
                result[key] = ""
            else:
                # Keep other values as is
                result[key] = value
        return result

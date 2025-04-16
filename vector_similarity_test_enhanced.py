"""
Enhanced Vector Similarity Test for Email Correlations

This script implements an improved correlation detection system between
educational activities and emails using a hybrid approach of:
1. Structured feature matching (course, module, assignment identifiers)
2. Enhanced TF-IDF vector similarity with custom weighting
3. Multi-tiered confidence scoring

Usage:
    python enhanced_vector_similarity_test.py --activities PATH --emails PATH --output PATH

Author: Marc Leavitt
Date: April 2025
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace

import argparse
import json
import csv
import os
import re
import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Output to stdout
)
logger = logging.getLogger(__name__)

# Configuration - Can be overridden by command line arguments
DEFAULT_CONFIG = {
    "activity_sample_size": 10,          # Number of activities to test
    "email_sample_size": 20,             # Max emails to compare with each activity
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
    "fuzzy_match_threshold": 0.8,        # Threshold for fuzzy matching
}

@dataclass
class CorrelationEvidence:
    """Stores evidence for why a correlation was detected."""
    tfidf_similarity: float = 0.0
    course_match: bool = False
    module_match: bool = False
    assignment_match: bool = False
    date_proximity_days: Optional[int] = None
    key_term_matches: List[str] = field(default_factory=list)
    
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
class CorrelationResult:
    """Represents a correlation between an activity and an email."""
    email_id: str
    email_subject: str
    content_snippet: str
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
        ) -> CorrelationResult:
        """
        Analyze correlation between an activity and an email.
        
        Args:
            activity: Activity data dictionary
            email: Email data dictionary
            activity_vector: TF-IDF vector for activity
            email_vector: TF-IDF vector for email
            
        Returns:
            CorrelationResult object with correlation details
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
        
        # Create a result object
        result = CorrelationResult(
            email_id=email.get("message_id", ""),
            email_subject=email.get("subject", ""),
            content_snippet=email.get("content", "")[:100] + "..." if len(email.get("content", "")) > 100 else email.get("content", ""),
            raw_similarity=similarity,
            adjusted_similarity=adjusted_similarity,
            confidence_level=confidence_level,
            evidence=evidence
        )
        
        return result

class CorrelationEngine:
    """Engine for finding correlations between activities and emails."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the correlation engine."""
        self.config = config or DEFAULT_CONFIG
        self.preprocessor = TextPreprocessor(self.config)
        self.analyzer = CorrelationAnalyzer(self.config)
        self.activity_vectors = {}
        self.email_vectors = {}
        self.emails_by_id = {}
        
    def preprocess_data(self, activities: List[Dict[str, Any]], emails: List[Dict[str, Any]]) -> None:
        """Preprocess activities and emails for correlation analysis."""
        logger.info("Preprocessing data for correlation analysis...")
        
        # Prepare texts for fitting the vectorizer
        activity_texts = [self.preprocessor.prepare_activity_text(a) for a in activities]
        email_texts = [self.preprocessor.prepare_email_text(e) for e in emails]
        all_texts = activity_texts + email_texts
        
        # Fit vectorizer on all texts
        self.preprocessor.fit_vectorizer(all_texts)
        
        # Transform activity texts to vectors
        for i, activity in enumerate(activities):
            self.activity_vectors[self._get_activity_id(activity)] = self.preprocessor.vectorizer.transform([activity_texts[i]])
        
        # Transform email texts to vectors and store emails by ID
        for i, email in enumerate(emails):
            email_id = email.get("message_id", f"email_{i}")
            self.email_vectors[email_id] = self.preprocessor.vectorizer.transform([email_texts[i]])
            self.emails_by_id[email_id] = email
        
        logger.info("Preprocessing complete: %d activities, %d emails", len(activities), len(emails))
    
    def _get_activity_id(self, activity: Dict[str, Any]) -> str:
        """Generate a stable ID for an activity."""
        if "id" in activity:
            return activity["id"]
        
        title = activity.get("Title", "")
        course = activity.get("Course", "")
        date = activity.get("Date", "")
        return f"{title}_{course}_{date}"
    
    def find_correlations(self, activity: Dict[str, Any], limit: int = None) -> List[CorrelationResult]:
        """Find emails correlated with an activity."""
        activity_id = self._get_activity_id(activity)
        
        if activity_id not in self.activity_vectors:
            logger.warning("Activity vector not found: %s", activity_id)
            return []
        
        activity_vector = self.activity_vectors[activity_id]
        results = []
        
        # Calculate correlation for each email
        for email_id, email_vector in self.email_vectors.items():
            email = self.emails_by_id[email_id]
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
        
        # Limit results if requested
        if limit and len(results) > limit:
            results = results[:limit]
        
        return results
    
    def analyze_all_activities(self, activities: List[Dict[str, Any]], emails: List[Dict[str, Any]], 
                              sample_size: int = None) -> Dict[str, Any]:
        """Analyze all activities and find correlations."""
        # Preprocess data
        self.preprocess_data(activities, emails)
        
        # Sample activities if requested
        if sample_size and len(activities) > sample_size:
            sampled_activities = random.sample(activities, sample_size)
        else:
            sampled_activities = activities
        
        logger.info("Analyzing correlations for %d activities...", len(sampled_activities))
        
        # Process each activity
        results = []
        for activity in sampled_activities:
            correlations = self.find_correlations(
                activity, 
                limit=self.config["email_sample_size"]
            )
            
            # Convert correlations to serializable dictionaries
            correlation_dicts = [c.to_dict() for c in correlations]
            
            # Group by confidence level
            grouped_correlations = {
                "strong": [c for c in correlation_dicts if c["confidence_level"] == "strong"],
                "moderate": [c for c in correlation_dicts if c["confidence_level"] == "moderate"],
                "weak": [c for c in correlation_dicts if c["confidence_level"] == "weak"]
            }
            
            # Add to results
            results.append({
                "activity": {
                    "title": activity.get("Title", ""),
                    "course": activity.get("Course", ""),
                    "date": activity.get("Date", "")
                },
                "correlations": grouped_correlations,
                "correlation_counts": {
                    "strong": len(grouped_correlations["strong"]),
                    "moderate": len(grouped_correlations["moderate"]),
                    "weak": len(grouped_correlations["weak"]),
                    "total": len(correlations)
                }
            })
        
        logger.info("Correlation analysis complete")
        
        # Calculate summary statistics
        total_correlations = sum(r["correlation_counts"]["total"] for r in results)
        avg_correlations = total_correlations / len(results) if results else 0
        
        return {
            "results": results,
            "summary": {
                "activities_analyzed": len(results),
                "total_correlations": total_correlations,
                "avg_correlations_per_activity": avg_correlations,
                "strong_correlations": sum(r["correlation_counts"]["strong"] for r in results),
                "moderate_correlations": sum(r["correlation_counts"]["moderate"] for r in results),
                "weak_correlations": sum(r["correlation_counts"]["weak"] for r in results)
            },
            "config": self.config
        }

def load_activities(csv_path, sample_size=None):
    """Load activities from CSV file."""
    activities = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            activities = list(reader)
            
        logger.info("Loaded %d activities from %s", len(activities), csv_path)
            
        # Take a random sample if requested
        if sample_size and len(activities) > sample_size:
            activities = random.sample(activities, sample_size)
            logger.info("Sampled %d activities for analysis", len(activities))
            
        return activities
    except Exception as e:
        logger.error("Error loading activities: %s", e)
        return []

def load_emails(json_path):
    """Load emails from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            emails = json.load(f)
        logger.info("Loaded %d emails from %s", len(emails), json_path)
        return emails
    except Exception as e:
        logger.error("Error loading emails: %s", e)
        return []

def save_results(results, output_path):
    """Save results to JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        logger.info("Results saved to %s", output_path)
    except Exception as e:
        logger.error("Error saving results: %s", e)

def print_results_summary(results):
    """Print a summary of the results."""
    summary = results["summary"]
    
    logger.info("\n=== ENHANCED VECTOR SIMILARITY RESULTS ===\n")
    logger.info("Activities analyzed: %d", summary['activities_analyzed'])
    logger.info("Total correlations found: %d", summary['total_correlations'])
    logger.info("Average correlations per activity: %.2f", summary['avg_correlations_per_activity'])
    logger.info("Strong correlations: %d", summary['strong_correlations'])
    logger.info("Moderate correlations: %d", summary['moderate_correlations'])
    logger.info("Weak correlations: %d", summary['weak_correlations'])
    
    # Print details for a few sample activities
    logger.info("\n=== SAMPLE ACTIVITY DETAILS ===\n")
    
    for i, activity_result in enumerate(results["results"][:3]):  # Show first 3 activities
        activity = activity_result["activity"]
        counts = activity_result["correlation_counts"]
        
        logger.info("Activity %d: %s (%s)", i+1, activity['title'], activity['course'])
        logger.info("Date: %s", activity['date'])
        logger.info("Found %d correlations: %d strong, %d moderate, %d weak", 
                   counts['total'], counts['strong'], counts['moderate'], counts['weak'])
        
        # Show top correlation of each type
        for level in ["strong", "moderate", "weak"]:
            correlations = activity_result["correlations"][level]
            if correlations:
                top = correlations[0]
                logger.info("\nTop %s correlation:", level)
                logger.info("  Subject: %s", top['email_subject'])
                logger.info("  Score: %.2f (raw: %.2f)", top['adjusted_similarity'], top['raw_similarity'])
                logger.info("  %s", top['evidence_summary'])
        
        logger.info("\n%s\n", "-" * 50)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Enhanced Vector Similarity Test for Email Correlations'
    )
    parser.add_argument(
        '--activities', 
        default=None,
        help='Path to the CSV file containing activities'
    )
    parser.add_argument(
        '--emails', 
        default=None,
        help='Path to the JSON file containing emails'
    )
    parser.add_argument(
        '--output', 
        default='enhanced_correlation_results.json',
        help='Path for the output JSON file'
    )
    parser.add_argument(
        '--sample_size', 
        type=int,
        default=DEFAULT_CONFIG["activity_sample_size"],
        help='Number of activities to sample for analysis'
    )
    parser.add_argument(
        '--config', 
        default=None,
        help='Path to JSON configuration file'
    )
    return parser.parse_args()

def load_config(config_path):
    """Load configuration from a JSON file."""
    if not config_path:
        return DEFAULT_CONFIG
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info("Loaded configuration from %s", config_path)
        
        # Convert ngram_range from list to tuple
        if "ngram_range" in config:
            config["ngram_range"] = tuple(config["ngram_range"])
        
        # Merge with default config to ensure all values are present
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        return merged_config
    except Exception as e:
        logger.error("Error loading configuration: %s", e)
        return DEFAULT_CONFIG

def main():
    """Run the enhanced vector similarity test."""
    args = parse_arguments()
    
    # Set default paths if not provided
    if not args.activities:
        args.activities = os.path.join(os.getcwd(), "data", "Coursera", "screenscrape.csv")
    
    if not args.emails:
        args.emails = os.path.join(os.getcwd(), "data", "email", "imported", "emails.json")
    
    # Load configuration
    config = load_config(args.config)
    config["activity_sample_size"] = args.sample_size  # Override from command line
    
    logger.info("=== ENHANCED VECTOR SIMILARITY TEST ===")
    logger.info("Activities: %s", args.activities)
    logger.info("Emails: %s", args.emails)
    logger.info("Output: %s", args.output)
    
    # Load data
    activities = load_activities(args.activities)
    emails = load_emails(args.emails)
    
    if not activities or not emails:
        logger.error("Failed to load data")
        return
    
    # Run correlation analysis
    engine = CorrelationEngine(config)
    results = engine.analyze_all_activities(
        activities, 
        emails, 
        sample_size=config["activity_sample_size"]
    )
    
    # Save and print results
    save_results(results, args.output)
    print_results_summary(results)
    
    logger.info("Enhanced vector similarity test complete!")

if __name__ == "__main__":
    main()

"""
Vector Similarity Feasibility Test for Email Correlations

This script tests whether vector similarity is a viable approach for correlating
activities with emails in the REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace

import json
import csv
import random
import logging

# import os
# import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Output to stdout
)
logger = logging.getLogger(__name__)

# Configuration
ACTIVITY_SAMPLE_SIZE = 5  # Number of activities to test
EMAIL_SAMPLE_SIZE = 20    # Max emails to compare with each activity
SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score to consider a match

# Paths - update these to match your environment
COURSERA_DATA_PATH = "/Users/marcleavitt/dev/REMOTE/data/Coursera/screenscrape.csv"
EMAIL_DATA_PATH = "/Users/marcleavitt/dev/REMOTE/data/email/imported/email-messages.json"

# Output path for results
RESULTS_PATH = "vector_similarity_results.json"

def load_activities(csv_path, sample_size=ACTIVITY_SAMPLE_SIZE):
    """Load activities from CSV file."""
    
    activities = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Filter out Live Events
            activities = [row for row in reader if row.get('Event Type', '').lower() != 'live event']
            
        logger.info("Found %d non-Live Event activities", len(activities))
            
        # Take a random sample if we have more than sample_size
        if len(activities) > sample_size:
            activities = random.sample(activities, sample_size)
            logger.info("Selected random sample of %d activities", len(activities))
            
        return activities
    except Exception as e:
        logger.error("Error loading activities: %s", e)
        return []

def load_emails(json_path):
    """Load emails from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            emails = json.load(f)
        logger.info("Loaded %d emails for testing", len(emails))
        return emails
    except Exception as e:
        logger.error("Error loading emails: %s", e)
        return []

def prepare_activity_text(activity):
    """Prepare activity text for vectorization."""
    # Combine relevant fields
    fields = [
        activity.get("Title", ""),
        activity.get("Course", ""),
        activity.get("Description", ""),
        activity.get("Event Type", ""),
        activity.get("Status", "")
    ]
    return " ".join(field for field in fields if field)

def prepare_email_text(email):
    """Prepare email text for vectorization."""
    # Combine relevant fields
    subject = email.get("subject", "")
    content = email.get("content", "")
    course = email.get("course_context", "")
    return f"{subject} {course} {content}"

def find_correlations(activities, emails):
    """Find correlations between activities and emails using vector similarity."""
    results = []
    
    # Prepare email texts
    email_texts = [prepare_email_text(email) for email in emails]
    
    # Initialize vectorizer with emails
    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        email_vectors = vectorizer.fit_transform(email_texts)
    except Exception as e:
        logger.error("Error generating email vectors: %s", e)
        return results
    
    # Process each activity
    for activity in activities:
        activity_text = prepare_activity_text(activity)
        
        try:
            # Transform activity text to vector using same vectorizer
            activity_vector = vectorizer.transform([activity_text])
            
            # Calculate similarity with all emails
            similarities = cosine_similarity(activity_vector, email_vectors)[0]
            
            # Get indices of emails above threshold
            matches = []
            for idx, score in enumerate(similarities):
                if score > SIMILARITY_THRESHOLD:
                    email = emails[idx]
                    matches.append({
                        "email_subject": email.get("subject", ""),
                        "similarity_score": float(score),
                        "email_id": email.get("message_id", ""),
                        # Include snippet of email content
                        "content_snippet": email.get("content", "")[:100] + "..." if len(email.get("content", "")) > 100 else email.get("content", "")
                    })
            
            # Sort matches by similarity score (highest first)
            matches.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # Limit number of matches
            matches = matches[:EMAIL_SAMPLE_SIZE]
            
            # Add to results
            results.append({
                "activity": {
                    "title": activity.get("Title", ""),
                    "course": activity.get("Course", ""),
                    "date": activity.get("Date", "")
                },
                "matches": matches,
                "match_count": len(matches)
            })
            
        except Exception as e:
            logger.error("Error processing activity '%s': %s", activity.get('Title', ''), e)
    
    return results

def save_results(results, output_path=RESULTS_PATH):
    """Save results to JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        logger.info("Results saved to %s", output_path)
    except Exception as e:
        logger.error("Error saving results: %s", e)

def print_results_summary(results):
    """Print a summary of the results."""
    logger.info("\n=== VECTOR SIMILARITY RESULTS ===\n")
    
    for i, result in enumerate(results):
        activity = result["activity"]
        matches = result["matches"]
        
        logger.info("Activity %d: %s (%s)", i+1, activity['title'], activity['course'])
        logger.info("Found %d potential correlations above threshold %f", len(matches), SIMILARITY_THRESHOLD)
        
        if matches:
            logger.info("\nTop 3 matches:")
            for j, match in enumerate(matches[:3]):
                logger.info("  %d. Score: %.2f - %s", j+1, match['similarity_score'], match['email_subject'])
                logger.info("     Snippet: %s...", match['content_snippet'][:50])
        
        logger.info("\n" + "-" * 50 + "\n")
    
    # Overall stats
    total_matches = sum(r["match_count"] for r in results)
    avg_matches = total_matches / len(results) if results else 0
    
    logger.info("Overall: %d activities tested, %d total matches", len(results), total_matches)
    logger.info("Average matches per activity: %.1f", avg_matches)
    logger.info("Detailed results saved to %s", RESULTS_PATH)

def main():
    """Run the feasibility test."""
    logger.info("=== VECTOR SIMILARITY FEASIBILITY TEST ===")
    
    # Load data
    activities = load_activities(COURSERA_DATA_PATH)
    emails = load_emails(EMAIL_DATA_PATH)
    
    if not activities or not emails:
        logger.error("Failed to load data")
        return
    
    # Find correlations
    logger.info("Testing correlations with threshold %f...", SIMILARITY_THRESHOLD)
    results = find_correlations(activities, emails)
    
    # Save and print results
    save_results(results)
    print_results_summary(results)
    
    logger.info("Feasibility test complete!")

if __name__ == "__main__":
    main()

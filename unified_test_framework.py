"""
Unified Test Framework for Message Similarity Analysis

This module provides a testing framework for evaluating message similarity
correlations between educational activities and different message types (email/Slack).
It supports configurable test parameters and produces detailed result reports.

Author: Marc Leavitt
Date: April 2025
"""
# pylint: disable=line-too-long trailing-whitespace

import os
import json
import csv
import argparse
import logging
import random
import time
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

# Import the unified message similarity agent
from message_similarity_agent import MessageSimilarityAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedTestFramework:
    """Test framework for message similarity with activities across message types."""
    
    def __init__(self, config: Union[Dict[str, Any], str] = None):
        """Initialize the test framework.
        
        Args:
            config: Configuration dictionary or path to config file
        """
        # Load configuration
        self.config = self._load_config(config)
        
        # Create agent with the same configuration
        self.agent = MessageSimilarityAgent(self.config)
        
        # Initialize test data
        self.activities = []
        self.sampled_activities = []
        self.results = {}
        
        logger.info("Initialized Unified Test Framework for message type: %s", 
                   self.config.get("message_type", "email"))
    
    def _load_config(self, config: Union[Dict[str, Any], str, None]) -> Dict[str, Any]:
        """Load configuration for test framework.
        
        Args:
            config: Configuration dictionary, path to config file, or None
            
        Returns:
            Loaded configuration
        """
        default_test_config = {
            "activity_sample_size": 10,
            "exclude_activity_types": [],
            "exclude_substrings": []
        }
        
        if config is None:
            # Just use default test config
            logger.info("Using default test configuration")
            return default_test_config
        
        # Load configuration
        loaded_config = {}
        if isinstance(config, str):
            try:
                with open(config, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                logger.info("Loaded configuration from file: %s", config)
            except (IOError, json.JSONDecodeError) as e:
                logger.error("Failed to load configuration from file: %s", e)
                logger.info("Falling back to default test configuration")
                loaded_config = default_test_config
        elif isinstance(config, dict):
            loaded_config = config
            logger.info("Using provided configuration dictionary")
        else:
            logger.warning("Invalid configuration type: %s", type(config))
            loaded_config = default_test_config
        
        # Add default test config values if not present
        for key, value in default_test_config.items():
            if key not in loaded_config:
                loaded_config[key] = value
        
        return loaded_config
    
    def load_activities(self, csv_path: str) -> bool:
        """Load activities from CSV file.
        
        Args:
            csv_path: Path to CSV file with activities
            
        Returns:
            True if successful, False otherwise
        """
        try:            
            if not os.path.exists(csv_path):
                logger.error("Activities CSV file not found: %s", csv_path)
                return False
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.activities = list(reader)
            
            logger.info("Loaded %d activities from %s", len(self.activities), csv_path)
            
            # Apply activity filtering
            self._filter_activities()
            
            return True
            
        except ImportError:
            logger.error("csv module not available")
            return False
        except Exception as e:
            logger.error("Error loading activities: %s", e)
            return False
    
    def _filter_activities(self) -> None:
        """Filter activities based on configuration."""
        if not self.activities:
            return
        
        original_count = len(self.activities)
        
        # Get exclusion criteria from config
        exclude_types = self.config.get("exclude_activity_types", [])
        exclude_substrings = self.config.get("exclude_substrings", [])
        
        if not exclude_types and not exclude_substrings:
            logger.info("No activity filtering criteria specified")
            return
        
        filtered_activities = []
        for activity in self.activities:
            # Check event type
            event_type = activity.get("Event Type", "")
            if event_type in exclude_types:
                continue
            
            # Check title for excluded substrings
            title = activity.get("Title", "")
            excluded = False
            for substring in exclude_substrings:
                if substring in title:
                    excluded = True
                    break
            
            if not excluded:
                filtered_activities.append(activity)
        
        filtered_count = len(filtered_activities)
        if filtered_count < original_count:
            logger.info("Filtered activities: %d -> %d (removed %d)", 
                       original_count, filtered_count, original_count - filtered_count)
            self.activities = filtered_activities
    
    def sample_activities(self) -> List[Dict[str, Any]]:
        """Sample activities for testing based on configuration.
        
        Returns:
            List of sampled activities
        """
        if not self.activities:
            logger.warning("No activities to sample")
            return []
        
        # Get sample size from config
        sample_size = self.config.get("activity_sample_size", 10)
        
        # Sample activities
        if sample_size >= len(self.activities):
            logger.info("Using all %d activities (sample size >= total)", len(self.activities))
            self.sampled_activities = self.activities
        else:
            logger.info("Sampling %d activities from %d total", sample_size, len(self.activities))
            self.sampled_activities = random.sample(self.activities, sample_size)
        
        return self.sampled_activities
    
    def load_messages(self, message_file: str) -> bool:
        """Load messages from JSON file.
        
        Args:
            message_file: Path to JSON file with messages
            
        Returns:
            True if successful, False otherwise
        """
        return self.agent.load_data(message_file)
    
    def run_test(self, activities: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Run correlation test on activities.
        
        Args:
            activities: List of activities to test, or None to use sampled activities
            
        Returns:
            Test results
        """
        test_activities = activities or self.sampled_activities
        
        if not test_activities:
            logger.error("No activities to test")
            return {}
        
        if not self.agent.messages:
            logger.error("No messages loaded for testing")
            return {}
        
        # Record start time
        start_time = time.time()
        
        # Process correlations
        logger.info("Running correlation test on %d activities", len(test_activities))
        self.agent.process_correlations(test_activities)
        
        # Record end time
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Collect results
        results = self._collect_results(test_activities, execution_time)
        self.results = results
        
        logger.info("Test completed in %.2f seconds", execution_time)
        logger.info("Found %d total correlations (%d strong, %d moderate, %d weak)",
                   results["summary"]["total_correlations"],
                   results["summary"]["strong_correlations"],
                   results["summary"]["moderate_correlations"],
                   results["summary"]["weak_correlations"])
        
        return results
    
    def _collect_results(self, activities: List[Dict[str, Any]], 
                        execution_time: float) -> Dict[str, Any]:
        """Collect test results into a structured format.
        
        Args:
            activities: Tested activities
            execution_time: Test execution time in seconds
            
        Returns:
            Structured test results
        """
        message_type = self.config.get("message_type", "email")
        message_field = f"Has{message_type.capitalize()}"
        correlations_field = "MessageCorrelations"
        
        # Count correlations
        strong_count = 0
        moderate_count = 0
        weak_count = 0
        total_count = 0
        
        # Create activity results
        activity_results = []
        
        for activity in activities:
            # Get correlation data
            has_correlations = activity.get(message_field, False)
            correlations = activity.get(correlations_field, [])
            
            # Count by confidence level
            activity_strong = sum(1 for c in correlations if c.get("confidence_level") == "strong")
            activity_moderate = sum(1 for c in correlations if c.get("confidence_level") == "moderate")
            activity_weak = sum(1 for c in correlations if c.get("confidence_level") == "weak")
            activity_total = len(correlations)
            
            # Add to overall counts
            strong_count += activity_strong
            moderate_count += activity_moderate
            weak_count += activity_weak
            total_count += activity_total
            
            # Group correlations by confidence level
            grouped_correlations = {
                "strong": [c for c in correlations if c.get("confidence_level") == "strong"],
                "moderate": [c for c in correlations if c.get("confidence_level") == "moderate"],
                "weak": [c for c in correlations if c.get("confidence_level") == "weak"]
            }
            
            # Add activity result
            activity_result = {
                "activity": {
                    "title": activity.get("Title", ""),
                    "course": activity.get("Course", ""),
                    "date": activity.get("Date", ""),
                    "type": activity.get("Event Type", "")
                },
                "correlations": grouped_correlations,
                "correlation_counts": {
                    "strong": activity_strong,
                    "moderate": activity_moderate,
                    "weak": activity_weak,
                    "total": activity_total
                }
            }
            
            activity_results.append(activity_result)
        
        # Calculate average correlations per activity
        avg_correlations = total_count / len(activities) if activities else 0
        
        # Create results structure
        results = {
            "test_info": {
                "message_type": message_type,
                "timestamp": datetime.now().isoformat(),
                "execution_time_seconds": execution_time,
                "activities_tested": len(activities),
                "messages_analyzed": len(self.agent.messages)
            },
            "summary": {
                "activities_analyzed": len(activities),
                "total_correlations": total_count,
                "strong_correlations": strong_count,
                "moderate_correlations": moderate_count,
                "weak_correlations": weak_count,
                "avg_correlations_per_activity": avg_correlations,
                "activity_filtering": {
                    "original_count": len(self.activities),
                    "filtered_count": len(activities),
                    "exclude_types": self.config.get("exclude_activity_types", []),
                    "exclude_substrings": self.config.get("exclude_substrings", [])
                }
            },
            "results": activity_results,
            "config": self.config
        }
        
        return results
    
    def save_results(self, output_file: str) -> bool:
        """Save test results to JSON file.
        
        Args:
            output_file: Path to output file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.results:
            logger.error("No results to save")
            return False
        
        try:
            # Create directory if it doesn't exist
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Write results to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2)
            
            logger.info("Saved test results to %s", output_file)
            return True
            
        except (IOError, TypeError) as e:
            logger.error("Error saving results: %s", e)
            return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Unified test framework for message similarity analysis'
    )
    parser.add_argument(
        '--config',
        default=None,
        help='Path to configuration file'
    )
    parser.add_argument(
        '--activities',
        required=True,
        help='Path to activities CSV file'
    )
    parser.add_argument(
        '--messages',
        required=True,
        help='Path to messages JSON file (email or Slack)'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Path to output JSON file'
    )
    parser.add_argument(
        '--message-type',
        choices=['email', 'slack'],
        default=None,
        help='Override message type in config'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=None,
        help='Override activity sample size in config'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for activity sampling'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        logger.info("Random seed set to %d", args.seed)
    
    # Load configuration
    config = None
    if args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info("Loaded configuration from %s", args.config)
        except (IOError, json.JSONDecodeError) as e:
            logger.error("Error loading configuration: %s", e)
            return 1
    
    # Apply command line overrides
    if config is None:
        config = {}
        
    if args.message_type:
        config["message_type"] = args.message_type
        
    if args.sample_size:
        config["activity_sample_size"] = args.sample_size
    
    # Create test framework
    framework = UnifiedTestFramework(config)
    
    # Load activities
    if not framework.load_activities(args.activities):
        logger.error("Failed to load activities from %s", args.activities)
        return 1
    
    # Load messages
    if not framework.load_messages(args.messages):
        logger.error("Failed to load messages from %s", args.messages)
        return 1
    
    # Sample activities
    framework.sample_activities()
    
    # Run test
    results = framework.run_test()
    
    if not results:
        logger.error("Test failed")
        return 1
    
    # Save results
    if args.output:
        output_file = args.output
    else:
        # Generate default output filename
        message_type = config.get("message_type", "email")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{message_type}_similarity_results_{timestamp}.json"
    
    if not framework.save_results(output_file):
        logger.error("Failed to save results to %s", output_file)
        return 1
    
    logger.info("Test completed successfully")
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)

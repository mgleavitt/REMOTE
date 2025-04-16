"""
Configuration Generator for Vector Similarity Testing

This script generates different configuration scenarios for testing
the enhanced vector similarity approach, allowing for experimentation
with different parameter combinations to find optimal settings.

Usage:
    python config_generator.py --output_dir /path/to/configs

Author: Marc Leavitt
Date: April 2025
"""

import os
import json
import argparse
import itertools
from typing import List
import logging

# pylint: disable=line-too-long

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Output to stdout
)
logger = logging.getLogger(__name__)

# Base configuration (similar to DEFAULT_CONFIG in the main script)
BASE_CONFIG = {
    # Thresholds for correlation confidence levels
    "threshold_strong": 0.5,             # Threshold for strong correlation
    "threshold_moderate": 0.4,           # Threshold for moderate correlation
    "threshold_weak": 0.3,               # Threshold for weak correlation

    # Boost values for structured matching
    "course_match_boost": 0.2,           # Boost score for course match
    "module_match_boost": 0.15,          # Boost score for module match
    "assignment_match_boost": 0.15,      # Boost score for assignment match
    "date_proximity_boost_max": 0.1,     # Maximum boost for date proximity
    "date_proximity_days": 3,            # Days within which to consider dates proximate

    # TF-IDF settings
    "ngram_range": (1, 3),               # Range of n-grams to use for TF-IDF
    "tfidf_min_df": 2,                   # Minimum document frequency for TF-IDF terms
    "exact_match_weight": 5,             # Weight for exact matches in token importance

    # Activity filtering
    # Activity types to exclude (e.g., "Live Event")
    "exclude_activity_types": [],
    # Exclude activities with these substrings in title
    "exclude_substrings": [],

    # Testing parameters
    "activity_sample_size": 15,          # Number of activities to test
    "email_sample_size": 20,             # Max emails to compare with each activity
    "max_correlations_per_activity": 5   # Maximum correlations to store per activity
}

# Parameter variations to test
PARAMETER_VARIATIONS = {
    "threshold_strong": [0.45, 0.5, 0.55, 0.6],
    "threshold_moderate": [0.35, 0.4, 0.45],
    "threshold_weak": [0.25, 0.3, 0.35],
    "course_match_boost": [0.15, 0.2, 0.25],
    "module_match_boost": [0.1, 0.15, 0.2],
    "assignment_match_boost": [0.1, 0.15, 0.2],
    "date_proximity_boost_max": [0.05, 0.1, 0.15],
    "date_proximity_days": [2, 3, 5],
    "ngram_range": [(1, 2), (1, 3), (2, 3)],
    "tfidf_min_df": [1, 2, 3]
}

# Common activity filtering scenarios
ACTIVITY_FILTERS = {
    "no_live_events": {
        "exclude_activity_types": ["Live Event"],
        "exclude_substrings": []
    },
    "no_office_hours": {
        "exclude_activity_types": ["Live Event"],
        "exclude_substrings": ["Office Hours"]
    },
    "assignments_only": {
        "exclude_activity_types": ["Live Event"],
        "exclude_substrings": ["Office Hours", "Quiz"]
    },
    "quizzes_only": {
        "exclude_activity_types": ["Live Event", "Assignment"],
        "exclude_substrings": ["Office Hours"]
    }
}

# Scenario definitions (focused parameter sets)
SCENARIOS = [
    {
        "name": "baseline",
        "description": "Baseline configuration",
        "parameters": {}  # Use defaults
    },
    {
        "name": "high_threshold",
        "description": "Higher thresholds for confidence levels",
        "parameters": {
            "threshold_strong": 0.6,
            "threshold_moderate": 0.45,
            "threshold_weak": 0.35
        }
    },
    {
        "name": "low_threshold",
        "description": "Lower thresholds for confidence levels",
        "parameters": {
            "threshold_strong": 0.45,
            "threshold_moderate": 0.35,
            "threshold_weak": 0.25
        }
    },
    {
        "name": "high_boosts",
        "description": "Higher boosts for structured matching",
        "parameters": {
            "course_match_boost": 0.25,
            "module_match_boost": 0.2,
            "assignment_match_boost": 0.2,
            "date_proximity_boost_max": 0.15
        }
    },
    {
        "name": "low_boosts",
        "description": "Lower boosts for structured matching",
        "parameters": {
            "course_match_boost": 0.15,
            "module_match_boost": 0.1,
            "assignment_match_boost": 0.1,
            "date_proximity_boost_max": 0.05
        }
    },
    {
        "name": "ngram_focus",
        "description": "Focus on higher order n-grams",
        "parameters": {
            "ngram_range": (2, 3),
            "tfidf_min_df": 1
        }
    },
    {
        "name": "date_focus",
        "description": "Focus on date proximity",
        "parameters": {
            "date_proximity_boost_max": 0.15,
            "date_proximity_days": 5
        }
    },
    {
        "name": "module_assignment_focus",
        "description": "Focus on module and assignment matching",
        "parameters": {
            "module_match_boost": 0.2,
            "assignment_match_boost": 0.2,
            "course_match_boost": 0.15
        }
    }
]


def tuple_to_list(obj):
    """Convert tuples to lists for JSON serialization."""
    if isinstance(obj, tuple):
        return list(obj)
    return obj


def generate_scenario_configs(output_dir: str, filter_scenario: str = None) -> None:
    """Generate configuration files for predefined scenarios.

    Args:
        output_dir: Directory to write configuration files
        filter_scenario: Optional activity filter scenario to apply
    """
    os.makedirs(output_dir, exist_ok=True)

    # Create scenario configs
    for scenario in SCENARIOS:
        # Start with base config
        config = BASE_CONFIG.copy()

        # Update with scenario-specific parameters
        config.update(scenario["parameters"])

        # Add activity filtering if specified
        if filter_scenario and filter_scenario in ACTIVITY_FILTERS:
            config.update(ACTIVITY_FILTERS[filter_scenario])
            scenario_name = f"{scenario['name']}_{filter_scenario}"
        else:
            scenario_name = scenario["name"]

        # Add metadata
        config["scenario_name"] = scenario_name
        config["scenario_description"] = scenario["description"]

        # Write to file
        filename = os.path.join(output_dir, f"scenario_{scenario_name}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, default=tuple_to_list)

        logger.info("Generated scenario config: %s", filename)


def generate_grid_search_configs(output_dir: str,
                                 max_configs: int = 10,
                                 filter_scenario: str = None) -> None:
    """Generate configurations for grid search of parameter combinations.

    Args:
        output_dir: Directory to write configuration files
        max_configs: Maximum number of configurations to generate
        filter_scenario: Optional activity filter scenario to apply
    """
    os.makedirs(output_dir, exist_ok=True)

    # Choose a subset of parameters to vary to limit combinatorial explosion
    parameter_subsets = [
        ["threshold_strong", "threshold_moderate", "threshold_weak"],
        ["course_match_boost", "module_match_boost", "assignment_match_boost"],
        ["date_proximity_boost_max", "date_proximity_days"],
        ["ngram_range", "tfidf_min_df"]
    ]

    config_count = 0

    # Generate configs for each parameter subset
    for subset in parameter_subsets:
        # Create parameter combinations for this subset
        param_values = [PARAMETER_VARIATIONS[param] for param in subset]
        combinations = list(itertools.product(*param_values))

        # Limit number of combinations if needed
        if len(combinations) > max_configs // len(parameter_subsets):
            combinations = combinations[:max_configs // len(parameter_subsets)]

        # Generate a config for each combination
        for combo in combinations:
            # Start with base config
            config = BASE_CONFIG.copy()

            # Update with combination values
            for param, value in zip(subset, combo):
                config[param] = value

            # Add activity filtering if specified
            if filter_scenario and filter_scenario in ACTIVITY_FILTERS:
                config.update(ACTIVITY_FILTERS[filter_scenario])
                filter_suffix = f"_{filter_scenario}"
            else:
                filter_suffix = ""

            # Add metadata
            param_str = "_".join([f"{p}" for p in subset])
            config["grid_search_params"] = subset

            # Write to file
            filename = os.path.join(
                output_dir,
                f"grid_{param_str}{filter_suffix}_{config_count}.json"
            )
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, default=tuple_to_list)

            config_count += 1
            if config_count >= max_configs:
                break

        if config_count >= max_configs:
            break

    logger.info("Generated %d grid search configurations", config_count)


def generate_activity_filter_configs(output_dir: str) -> None:
    """Generate configurations with different activity filtering options.

    Args:
        output_dir: Directory to write configuration files
    """
    os.makedirs(output_dir, exist_ok=True)

    # Create a config for each filter scenario
    for filter_name, filter_config in ACTIVITY_FILTERS.items():
        # Start with base config
        config = BASE_CONFIG.copy()

        # Add filter configuration
        config.update(filter_config)

        # Add metadata
        config["filter_scenario"] = filter_name
        config["filter_description"] = f"Filter for {filter_name.replace('_', ' ')}"

        # Write to file
        filename = os.path.join(output_dir, f"filter_{filter_name}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, default=tuple_to_list)

        logger.info("Generated filter config: %s", filename)


def generate_custom_filter_config(output_dir: str,
                                  exclude_types: List[str] = None,
                                  exclude_substrings: List[str] = None,
                                  name: str = "custom_filter") -> None:
    """Generate a custom configuration with specific activity filtering.

    Args:
        output_dir: Directory to write configuration files
        exclude_types: List of activity types to exclude
        exclude_substrings: List of substrings to exclude from activity titles
        name: Name for the configuration file
    """
    os.makedirs(output_dir, exist_ok=True)

    # Start with base config
    config = BASE_CONFIG.copy()

    # Add filter configuration
    if exclude_types:
        config["exclude_activity_types"] = exclude_types

    if exclude_substrings:
        config["exclude_substrings"] = exclude_substrings

    # Add metadata
    excluded_types_str = ", ".join(exclude_types) if exclude_types else "none"
    excluded_substrings_str = ", ".join(
        exclude_substrings) if exclude_substrings else "none"

    config["filter_description"] = (
        f"Custom filter excluding types: {excluded_types_str} "
        f"and substrings: {excluded_substrings_str}"
    )

    # Write to file
    filename = os.path.join(output_dir, f"{name}.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, default=tuple_to_list)

    logger.info("Generated custom filter config: %s", filename)


def generate_combined_configs(output_dir: str) -> None:
    """Generate combined configurations with both parameter tuning and activity filtering.

    Args:
        output_dir: Directory to write configuration files
    """
    os.makedirs(output_dir, exist_ok=True)

    # Select the most promising scenarios and filters
    selected_scenarios = ["baseline", "module_assignment_focus", "date_focus"]
    selected_filters = ["no_live_events",
                        "no_office_hours", "assignments_only"]

    for scenario_name in selected_scenarios:
        # Find the scenario configuration
        scenario = next(
            (s for s in SCENARIOS if s["name"] == scenario_name), None)
        if not scenario:
            continue

        for filter_name in selected_filters:
            if filter_name not in ACTIVITY_FILTERS:
                continue

            # Start with base config
            config = BASE_CONFIG.copy()

            # Add scenario parameters
            config.update(scenario["parameters"])

            # Add filter configuration
            config.update(ACTIVITY_FILTERS[filter_name])

            # Add metadata
            config["scenario_name"] = scenario_name
            config["filter_scenario"] = filter_name
            config["description"] = f"{scenario['description']} with {filter_name.replace('_', ' ')} filtering"

            # Write to file
            filename = os.path.join(
                output_dir, f"combined_{scenario_name}_{filter_name}.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, default=tuple_to_list)

            logger.info("Generated combined config: %s", filename)


def generate_optimization_configs(output_dir: str) -> None:
    """Generate focused optimization configurations based on observed patterns.

    Args:
        output_dir: Directory to write configuration files
    """
    os.makedirs(output_dir, exist_ok=True)

    # Define optimization strategies - these would be based on results from earlier runs
    strategies = [
        {
            "name": "module_date_match_opt",
            "description": "Optimized settings for module and date matching",
            "parameters": {
                "module_match_boost": 0.25,
                "date_proximity_boost_max": 0.15,
                "date_proximity_days": 3,
                "threshold_strong": 0.55,
                "threshold_moderate": 0.4,
                "threshold_weak": 0.3,
                "exclude_activity_types": ["Live Event"],
                "exclude_substrings": ["Office Hours"]
            }
        },
        {
            "name": "course_match_opt",
            "description": "Optimized settings for course matching",
            "parameters": {
                "course_match_boost": 0.3,
                "threshold_strong": 0.5,
                "threshold_moderate": 0.4,
                "threshold_weak": 0.3,
                "tfidf_min_df": 1,
                "ngram_range": (1, 3),
                "exclude_activity_types": ["Live Event"],
                "exclude_substrings": []
            }
        },
        {
            "name": "balanced_opt",
            "description": "Balanced optimization of all parameters",
            "parameters": {
                "course_match_boost": 0.2,
                "module_match_boost": 0.2,
                "assignment_match_boost": 0.2,
                "date_proximity_boost_max": 0.1,
                "date_proximity_days": 3,
                "threshold_strong": 0.52,
                "threshold_moderate": 0.42,
                "threshold_weak": 0.32,
                "tfidf_min_df": 2,
                "ngram_range": (1, 3),
                "exclude_activity_types": ["Live Event"],
                "exclude_substrings": ["Office Hours"]
            }
        }
    ]

    # Create optimization configs
    for strategy in strategies:
        # Start with base config
        config = BASE_CONFIG.copy()

        # Update with strategy-specific parameters
        config.update(strategy["parameters"])

        # Add metadata
        config["optimization_name"] = strategy["name"]
        config["optimization_description"] = strategy["description"]

        # Write to file
        filename = os.path.join(output_dir, f"opt_{strategy['name']}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, default=tuple_to_list)

        logger.info("Generated optimization config: %s", filename)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate configurations for vector similarity testing'
    )
    parser.add_argument(
        '--output_dir',
        default='configs',
        help='Directory to write configuration files'
    )
    parser.add_argument(
        '--scenarios_only',
        action='store_true',
        help='Generate only predefined scenario configurations'
    )
    parser.add_argument(
        '--grid_search_only',
        action='store_true',
        help='Generate only grid search configurations'
    )
    parser.add_argument(
        '--optimization_only',
        action='store_true',
        help='Generate only optimization configurations'
    )
    parser.add_argument(
        '--filters_only',
        action='store_true',
        help='Generate only activity filter configurations'
    )
    parser.add_argument(
        '--filter_scenario',
        choices=list(ACTIVITY_FILTERS.keys()),
        help='Activity filter scenario to apply to all configurations'
    )
    parser.add_argument(
        '--exclude_types',
        nargs='+',
        help='Activity types to exclude (e.g., "Live Event")'
    )
    parser.add_argument(
        '--exclude_substrings',
        nargs='+',
        help='Exclude activities with these substrings in title (e.g., "Office Hours")'
    )
    parser.add_argument(
        '--custom_filter_name',
        default='custom_filter',
        help='Name for the custom filter configuration'
    )
    parser.add_argument(
        '--max_grid_configs',
        type=int,
        default=10,
        help='Maximum number of grid search configurations to generate'
    )
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_arguments()

    logger.info("Generating configuration files for vector similarity testing...")

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate custom filter configuration if specified
    if args.exclude_types or args.exclude_substrings:
        generate_custom_filter_config(
            args.output_dir,
            exclude_types=args.exclude_types,
            exclude_substrings=args.exclude_substrings,
            name=args.custom_filter_name
        )

    # Generate configurations based on command line arguments
    if args.scenarios_only:
        generate_scenario_configs(
            os.path.join(args.output_dir, 'scenarios'),
            args.filter_scenario
        )
    elif args.grid_search_only:
        generate_grid_search_configs(
            os.path.join(args.output_dir, 'grid_search'),
            args.max_grid_configs,
            args.filter_scenario
        )
    elif args.optimization_only:
        generate_optimization_configs(
            os.path.join(args.output_dir, 'optimization'))
    elif args.filters_only:
        generate_activity_filter_configs(
            os.path.join(args.output_dir, 'filters'))
    else:
        # Generate all configuration types
        generate_scenario_configs(
            os.path.join(args.output_dir, 'scenarios'),
            args.filter_scenario
        )
        generate_grid_search_configs(
            os.path.join(args.output_dir, 'grid_search'),
            args.max_grid_configs,
            args.filter_scenario
        )
        generate_optimization_configs(
            os.path.join(args.output_dir, 'optimization'))
        generate_activity_filter_configs(
            os.path.join(args.output_dir, 'filters'))
        generate_combined_configs(os.path.join(args.output_dir, 'combined'))

    logger.info("Configuration generation complete!")


if __name__ == "__main__":
    main()

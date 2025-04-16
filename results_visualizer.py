#!/usr/bin/env python3
"""
Results Visualizer for Vector Similarity Tests

This script generates visualizations and summaries from vector similarity test results.
It supports analyzing single result files or comparing multiple results.

Usage:
    python results_visualizer.py --result results/baseline_results.json
    python results_visualizer.py --compare results/baseline_results.json results/no_office_hours_results.json
    python results_visualizer.py --directory results/ --pattern *_results.json

Author: Marc Leavitt
Date: April 2025
"""

import json
import os
import glob
import argparse
import logging
from typing import Dict, List, Any, Union
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_result_file(filepath: str) -> Dict[str, Any]:
    """Load a result file from JSON."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except (IOError, json.JSONDecodeError) as e:
        logger.error("Failed to load result file %s: %s", filepath, e)
        return {}

def summarize_single_result(result_data: Dict[str, Any], output_prefix: str = None) -> None:
    """Summarize a single result file with tables and charts."""
    if not result_data:
        logger.error("No result data to summarize")
        return
    
    # Extract summary
    summary = result_data.get('summary', {})
    config = result_data.get('config', {})
    results = result_data.get('results', [])
    
    # Print basic summary
    print("\n=== VECTOR SIMILARITY TEST SUMMARY ===\n")
    print(f"Activities analyzed: {summary.get('activities_analyzed', 0)}")
    print(f"Total correlations found: {summary.get('total_correlations', 0)}")
    print(f"Strong correlations: {summary.get('strong_correlations', 0)}")
    print(f"Moderate correlations: {summary.get('moderate_correlations', 0)}")
    print(f"Weak correlations: {summary.get('weak_correlations', 0)}")
    print(f"Average correlations per activity: {summary.get('avg_correlations_per_activity', 0):.2f}")
    
    # Print activity filtering details if available
    if 'activity_filtering' in summary:
        filtering = summary['activity_filtering']
        print("\nActivity Filtering:")
        print(f"Original count: {filtering.get('original_count', 0)}")
        print(f"Filtered count: {filtering.get('filtered_count', 0)}")
        print(f"Excluded types: {', '.join(filtering.get('exclude_types', []))}")
        print(f"Excluded substrings: {', '.join(filtering.get('exclude_substrings', []))}")
    
    # Print key configuration parameters
    print("\nKey Configuration Parameters:")
    for param in ['threshold_strong', 'threshold_moderate', 'threshold_weak', 
                 'course_match_boost', 'module_match_boost', 'assignment_match_boost']:
        if param in config:
            print(f"{param}: {config[param]}")
    
    # Create table of activities with correlation counts
    print("\nActivities with Correlations:")
    headers = ["Activity", "Course", "Type", "Strong", "Moderate", "Weak", "Total"]
    rows = []
    
    for result in results:
        activity = result.get('activity', {})
        counts = result.get('correlation_counts', {})
        
        rows.append([
            activity.get('title', ''),
            activity.get('course', ''),
            activity.get('type', ''),
            counts.get('strong', 0),
            counts.get('moderate', 0),
            counts.get('weak', 0),
            counts.get('total', 0)
        ])
    
    # Sort by total correlations (descending)
    rows.sort(key=lambda x: x[6], reverse=True)
    
    # Print table using tabulate
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    
    # Generate visualizations if output prefix provided
    if output_prefix:
        generate_visualizations(result_data, output_prefix)

def generate_visualizations(result_data: Dict[str, Any], output_prefix: str) -> None:
    """Generate visualizations from result data."""
    summary = result_data.get('summary', {})
    results = result_data.get('results', [])
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_prefix) if os.path.dirname(output_prefix) else '.', exist_ok=True)
    
    # 1. Correlation distribution pie chart
    plt.figure(figsize=(8, 6))
    labels = ['Strong', 'Moderate', 'Weak']
    sizes = [
        summary.get('strong_correlations', 0),
        summary.get('moderate_correlations', 0),
        summary.get('weak_correlations', 0)
    ]
    colors = ['#4CAF50', '#FFC107', '#F44336']
    
    if sum(sizes) > 0:  # Only create pie chart if there are correlations
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
        plt.axis('equal')
        plt.title('Correlation Distribution by Confidence Level')
        plt.savefig(f"{output_prefix}_correlation_distribution.png")
        logger.info("Generated correlation distribution chart: %s_correlation_distribution.png", 
                   output_prefix)
    
    # 2. Activity correlation counts bar chart
    if results:
        plt.figure(figsize=(12, 8))
        
        # Get top 10 activities by total correlations
        activity_data = []
        for result in results:
            activity = result.get('activity', {})
            counts = result.get('correlation_counts', {})
            
            activity_data.append({
                'title': activity.get('title', ''),
                'strong': counts.get('strong', 0),
                'moderate': counts.get('moderate', 0),
                'weak': counts.get('weak', 0),
                'total': counts.get('total', 0)
            })
        
        # Sort by total and take top 10
        activity_data.sort(key=lambda x: x['total'], reverse=True)
        top_activities = activity_data[:10]
        
        # Create stacked bar chart
        labels = [a['title'][:20] + '...' if len(a['title']) > 20 else a['title'] for a in top_activities]
        strong_vals = [a['strong'] for a in top_activities]
        moderate_vals = [a['moderate'] for a in top_activities]
        weak_vals = [a['weak'] for a in top_activities]
        
        if any(strong_vals) or any(moderate_vals) or any(weak_vals):  # Only create chart if there are correlations
            # Create bar chart
            fig, ax = plt.subplots(figsize=(12, 8))
            
            bar_width = 0.6
            x = range(len(labels))
            
            # Create stacked bars
            ax.bar(x, strong_vals, bar_width, label='Strong', color='#4CAF50')
            ax.bar(x, moderate_vals, bar_width, bottom=strong_vals, label='Moderate', color='#FFC107')
            
            # Calculate the bottom position for weak correlations
            bottom_weak = [s + m for s, m in zip(strong_vals, moderate_vals)]
            ax.bar(x, weak_vals, bar_width, bottom=bottom_weak, label='Weak', color='#F44336')
            
            # Add labels and title
            ax.set_ylabel('Number of Correlations')
            ax.set_title('Top Activities by Correlation Count')
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=45, ha='right')
            ax.legend()
            
            # Adjust layout and save
            plt.tight_layout()
            plt.savefig(f"{output_prefix}_top_activities.png")
            logger.info("Generated top activities chart: %s_top_activities.png", output_prefix)
    
    # 3. Course distribution chart
    if results:
        plt.figure(figsize=(10, 6))
        
        # Count correlations by course
        course_counts = {}
        for result in results:
            activity = result.get('activity', {})
            course = activity.get('course', 'Unknown')
            total = result.get('correlation_counts', {}).get('total', 0)
            
            if course not in course_counts:
                course_counts[course] = 0
            course_counts[course] += total
        
        if course_counts:  # Only create chart if there are courses with correlations
            # Create bar chart
            courses = list(course_counts.keys())
            counts = [course_counts[c] for c in courses]
            
            plt.bar(courses, counts, color='#2196F3')
            plt.xlabel('Course')
            plt.ylabel('Number of Correlations')
            plt.title('Correlations by Course')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(f"{output_prefix}_course_distribution.png")
            logger.info("Generated course distribution chart: %s_course_distribution.png", 
                       output_prefix)

def compare_results(result_files: List[str], output_prefix: str = None) -> None:
    """Compare multiple result files."""
    if len(result_files) < 2:
        logger.error("Need at least two result files to compare")
        return
    
    # Load all result files
    results_data = []
    for filepath in result_files:
        data = load_result_file(filepath)
        if data:
            # Extract file name without path and extension
            name = os.path.splitext(os.path.basename(filepath))[0]
            # Remove _results suffix if present
            if name.endswith('_results'):
                name = name[:-8]
            results_data.append((name, data))
    
    if len(results_data) < 2:
        logger.error("Failed to load enough valid result files for comparison")
        return
    
    # Compare summary statistics
    print("\n=== RESULTS COMPARISON ===\n")
    
    # Create comparison table
    headers = ["Configuration", "Activities", "Total", "Strong", "Moderate", "Weak", "Avg/Activity"]
    rows = []
    
    for name, data in results_data:
        summary = data.get('summary', {})
        
        rows.append([
            name,
            summary.get('activities_analyzed', 0),
            summary.get('total_correlations', 0),
            summary.get('strong_correlations', 0),
            summary.get('moderate_correlations', 0),
            summary.get('weak_correlations', 0),
            f"{summary.get('avg_correlations_per_activity', 0):.2f}"
        ])
    
    # Sort by total correlations (descending)
    rows.sort(key=lambda x: x[2], reverse=True)
    
    # Print table using tabulate
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    
    # Generate comparison charts if output prefix provided
    if output_prefix:
        generate_comparison_charts(results_data, output_prefix)

def generate_comparison_charts(results_data: List[tuple], output_prefix: str) -> None:
    """Generate charts comparing multiple result files."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_prefix) if os.path.dirname(output_prefix) else '.', exist_ok=True)
    
    # Extract names and summary data
    names = [name for name, _ in results_data]
    summaries = [data.get('summary', {}) for _, data in results_data]
    
    # 1. Correlation counts comparison
    plt.figure(figsize=(12, 8))
    
    # Extract data
    x = range(len(names))
    total_vals = [s.get('total_correlations', 0) for s in summaries]
    strong_vals = [s.get('strong_correlations', 0) for s in summaries]
    moderate_vals = [s.get('moderate_correlations', 0) for s in summaries]
    weak_vals = [s.get('weak_correlations', 0) for s in summaries]
    
    # Bar width
    width = 0.2
    
    # Create grouped bar chart
    plt.bar([i - 1.5*width for i in x], strong_vals, width, label='Strong', color='#4CAF50')
    plt.bar([i - 0.5*width for i in x], moderate_vals, width, label='Moderate', color='#FFC107')
    plt.bar([i + 0.5*width for i in x], weak_vals, width, label='Weak', color='#F44336')
    plt.bar([i + 1.5*width for i in x], total_vals, width, label='Total', color='#2196F3')
    
    # Add labels and title
    plt.xlabel('Configuration')
    plt.ylabel('Number of Correlations')
    plt.title('Correlation Counts by Configuration')
    plt.xticks(x, names, rotation=45, ha='right')
    plt.legend()
    
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_correlation_comparison.png")
    logger.info("Generated correlation comparison chart: %s_correlation_comparison.png", 
               output_prefix)
    
    # 2. Average correlations per activity
    plt.figure(figsize=(10, 6))
    
    # Extract data
    avg_vals = [s.get('avg_correlations_per_activity', 0) for s in summaries]
    
    # Create bar chart
    plt.bar(names, avg_vals, color='#673AB7')
    plt.xlabel('Configuration')
    plt.ylabel('Average Correlations per Activity')
    plt.title('Average Correlations per Activity by Configuration')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_avg_correlations.png")
    logger.info("Generated average correlations chart: %s_avg_correlations.png", 
               output_prefix)
    
    # 3. Configuration parameters comparison
    config_params = ['threshold_strong', 'threshold_moderate', 'threshold_weak', 
                   'course_match_boost', 'module_match_boost', 'assignment_match_boost']
    
    # Create DataFrame for configuration parameters
    config_data = []
    for name, data in results_data:
        config = data.get('config', {})
        row = {'Config': name}
        for param in config_params:
            row[param] = config.get(param, None)
        config_data.append(row)
    
    # Create table with tabulate
    if config_data:
        df = pd.DataFrame(config_data)
        config_table = tabulate(df, headers='keys', tablefmt="grid", showindex=False)
        
        with open(f"{output_prefix}_config_comparison.txt", 'w') as f:
            f.write("Configuration Parameters Comparison\n\n")
            f.write(config_table)
        
        logger.info("Generated configuration comparison table: %s_config_comparison.txt", 
                   output_prefix)

def analyze_directory(directory: str, pattern: str, output_prefix: str = None) -> None:
    """Analyze all result files in a directory matching a pattern."""
    if not os.path.isdir(directory):
        logger.error("Directory does not exist: %s", directory)
        return
    
    # Find files matching the pattern
    pattern_path = os.path.join(directory, pattern)
    files = glob.glob(pattern_path)
    
    if not files:
        logger.error("No files found matching pattern: %s", pattern_path)
        return
    
    logger.info("Found %d result files matching pattern", len(files))
    
    if len(files) == 1:
        # Single file analysis
        data = load_result_file(files[0])
        if data:
            output_name = output_prefix or os.path.splitext(os.path.basename(files[0]))[0]
            summarize_single_result(data, output_name)
    else:
        # Multiple file comparison
        compare_results(files, output_prefix or "results_comparison")

def export_to_html(result_data: Dict[str, Any], output_file: str) -> None:
    """Export results to an HTML report."""
    if not result_data:
        logger.error("No result data to export")
        return
    
    try:
        import pandas as pd
        
        summary = result_data.get('summary', {})
        config = result_data.get('config', {})
        results = result_data.get('results', [])
        
        # Create HTML report
        html = ['<html><head><title>Vector Similarity Test Results</title>']
        
        # Add simple styling
        html.append('''
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1, h2 { color: #333; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            .summary { display: flex; flex-wrap: wrap; }
            .summary-item { margin-right: 30px; margin-bottom: 10px; }
            .summary-label { font-weight: bold; }
            .config-table { max-width: 500px; }
        </style>
        ''')
        
        html.append('</head><body>')
        html.append('<h1>Vector Similarity Test Results</h1>')
        
        # Summary section
        html.append('<h2>Summary</h2>')
        html.append('<div class="summary">')
        
        summary_items = [
            ('Activities Analyzed', summary.get('activities_analyzed', 0)),
            ('Total Correlations', summary.get('total_correlations', 0)),
            ('Strong Correlations', summary.get('strong_correlations', 0)),
            ('Moderate Correlations', summary.get('moderate_correlations', 0)),
            ('Weak Correlations', summary.get('weak_correlations', 0)),
            ('Avg Correlations/Activity', f"{summary.get('avg_correlations_per_activity', 0):.2f}")
        ]
        
        for label, value in summary_items:
            html.append(f'<div class="summary-item"><span class="summary-label">{label}:</span> {value}</div>')
        
        html.append('</div>')
        
        # Activity filtering section if available
        if 'activity_filtering' in summary:
            filtering = summary['activity_filtering']
            html.append('<h2>Activity Filtering</h2>')
            html.append('<div class="summary">')
            
            filter_items = [
                ('Original Count', filtering.get('original_count', 0)),
                ('Filtered Count', filtering.get('filtered_count', 0)),
                ('Excluded Types', ', '.join(filtering.get('exclude_types', []))),
                ('Excluded Substrings', ', '.join(filtering.get('exclude_substrings', [])))
            ]
            
            for label, value in filter_items:
                html.append(f'<div class="summary-item"><span class="summary-label">{label}:</span> {value}</div>')
            
            html.append('</div>')
        
        # Configuration section
        html.append('<h2>Configuration</h2>')
        
        # Convert config to DataFrame and render as HTML table
        config_items = [(k, v) for k, v in config.items()]
        config_df = pd.DataFrame(config_items, columns=['Parameter', 'Value'])
        html.append('<div class="config-table">')
        html.append(config_df.to_html(index=False))
        html.append('</div>')
        
        # Activities table
        html.append('<h2>Activities with Correlations</h2>')
        
        # Create DataFrame for activities
        activity_data = []
        for result in results:
            activity = result.get('activity', {})
            counts = result.get('correlation_counts', {})
            
            activity_data.append({
                'Title': activity.get('title', ''),
                'Course': activity.get('course', ''),
                'Type': activity.get('type', ''),
                'Strong': counts.get('strong', 0),
                'Moderate': counts.get('moderate', 0),
                'Weak': counts.get('weak', 0),
                'Total': counts.get('total', 0)
            })
        
        # Sort by total correlations (descending)
        activity_df = pd.DataFrame(activity_data)
        activity_df = activity_df.sort_values('Total', ascending=False)
        
        html.append(activity_df.to_html(index=False))
        
        # Close HTML document
        html.append('</body></html>')
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))
        
        logger.info("Exported HTML report to %s", output_file)
        
    except ImportError:
        logger.error("pandas is required for HTML export")
    except Exception as e:
        logger.error("Error exporting to HTML: %s", e)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Visualize and summarize vector similarity test results'
    )
    parser.add_argument(
        '--result',
        help='Path to a single result file'
    )
    parser.add_argument(
        '--compare',
        nargs='+',
        help='Paths to multiple result files to compare'
    )
    parser.add_argument(
        '--directory',
        help='Directory containing result files'
    )
    parser.add_argument(
        '--pattern',
        default='*_results.json',
        help='Pattern for matching result files in directory'
    )
    parser.add_argument(
        '--output',
        help='Output prefix for visualization files'
    )
    parser.add_argument(
        '--html',
        help='Output HTML report file'
    )
    return parser.parse_args()

def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Check if any action is specified
    if not any([args.result, args.compare, args.directory]):
        logger.error("No action specified. Use --help for usage information.")
        return
    
    # Set output prefix based on arguments or default
    output_prefix = args.output
    
    # Process single result file
    if args.result:
        data = load_result_file(args.result)
        if data:
            # Default output prefix based on result filename
            if not output_prefix:
                output_prefix = os.path.splitext(os.path.basename(args.result))[0]
            
            summarize_single_result(data, output_prefix)
            
            # Generate HTML report if requested
            if args.html:
                export_to_html(data, args.html)
    
    # Compare multiple result files
    elif args.compare:
        compare_results(args.compare, output_prefix or "results_comparison")
    
    # Analyze directory
    elif args.directory:
        analyze_directory(args.directory, args.pattern, output_prefix)

if __name__ == "__main__":
    main()
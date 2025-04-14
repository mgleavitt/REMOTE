#!/usr/bin/env python3
"""
Remote Education Management and Organization Tool for Education (REMOTE)
Slack Data Import Module

This program imports Slack conversations and converts them to a common data format
that can be processed alongside email data in the REMOTE application.
"""

# pylint: disable=trailing-whitespace

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime

# Try to import Slack SDK (optional, for API approach)
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    HAS_SLACK_SDK = True
except ImportError:
    HAS_SLACK_SDK = False

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Import Slack data for REMOTE.')
    parser.add_argument('--input_dir', '--workspace', help='Directory containing Slack export data')
    parser.add_argument('--output_file', required=True, help='Path to output JSON file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--pretty', action='store_true', help='Output formatted JSON')
    parser.add_argument('--api_token', help='Slack API token (if using API instead of export)')
    parser.add_argument('--channels', help='Comma-separated list of channels to import (all channels if omitted)')
    return parser.parse_args()

def setup_logging(verbose=False):
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_unicode(text):
    """Clean invisible Unicode characters from text."""
    if not text:
        return text
    
    # Remove zero-width characters
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    
    # Replace problematic characters
    text = text.replace('\u2028', ' ').replace('\u2029', ' ')
    
    return text

def extract_course_context(text, channel_name=None, channel_topic=None):
    """Extract course context from message text, channel name, or channel topic."""
    # Extract course codes like CS101, MATH200, etc.
    course_pattern = r'\b([A-Z]{2,4})\s*[.-]?\s*(\d{2,4}[A-Z]?)\b'
    
    contexts = []
    
    # Check channel name first (most reliable)
    if channel_name:
        channel_matches = re.findall(course_pattern, channel_name, re.IGNORECASE)
        if channel_matches:
            contexts.extend([f"{dept}{num}" for dept, num in channel_matches])
    
    # Check channel topic
    if channel_topic:
        topic_matches = re.findall(course_pattern, channel_topic, re.IGNORECASE)
        if topic_matches:
            contexts.extend([f"{dept}{num}" for dept, num in topic_matches])
    
    # Finally check message text
    if text:
        text_matches = re.findall(course_pattern, text, re.IGNORECASE)
        if text_matches:
            contexts.extend([f"{dept}{num}" for dept, num in text_matches])
    
    # Make unique and join with commas if multiple courses
    unique_contexts = list(set(contexts))
    
    if unique_contexts:
        return ",".join(unique_contexts)
    
    # If no course context found, check for common academic keywords
    academic_keywords = ['assignment', 'homework', 'project', 'exam', 'quiz', 'lecture', 'class']
    if text and any(keyword in text.lower() for keyword in academic_keywords):
        return "ACADEMIC"
    
    return None

def convert_slack_timestamp(ts):
    """Convert Slack timestamp to ISO 8601 format and formatted date."""
    # Slack timestamps are Unix timestamps in seconds
    dt = datetime.fromtimestamp(float(ts))
    iso_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    formatted_date = dt.strftime('%b %d')
    return iso_timestamp, formatted_date

def import_from_export(input_dir, channels=None):
    """Import Slack data from an export directory."""
    logging.info("Importing Slack data from export directory: %s", input_dir)
    
    if not os.path.isdir(input_dir):
        logging.error("Input directory does not exist: %s", input_dir)
        sys.exit(1)
    
    all_messages = []
    channels_processed = 0
    
    # Process channels
    channels_dir = os.path.join(input_dir, 'channels')
    if os.path.isdir(channels_dir):
        for channel_dir in os.listdir(channels_dir):
            channel_path = os.path.join(channels_dir, channel_dir)
            
            # Skip if not a directory
            if not os.path.isdir(channel_path):
                continue
            
            # Skip if not in the specified channels (if channels filter is provided)
            if channels and channel_dir not in channels.split(','):
                logging.debug("Skipping channel %s (not in filter)", channel_dir)
                continue
            
            # Read channel info
            channel_info = {}
            info_path = os.path.join(channel_path, 'channel.json')
            if os.path.isfile(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    channel_info = json.load(f)
            
            # Process message files
            messages = []
            for filename in os.listdir(channel_path):
                if filename.endswith('.json') and filename != 'channel.json':
                    file_path = os.path.join(channel_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        channel_messages = json.load(f)
                        messages.extend(channel_messages)
            
            if messages:
                channel_name = channel_info.get('name', channel_dir)
                channel_topic = channel_info.get('topic', {}).get('value', '')
                channel_id = channel_info.get('id', '')
                
                # Process messages for this channel
                channel_messages = process_channel_messages(
                    messages, channel_name, channel_topic, channel_id
                )
                all_messages.extend(channel_messages)
                
                logging.info("Processed %d messages from channel: %s", len(channel_messages), channel_name)
                channels_processed += 1
    
    # Process direct messages (DMs)
    dms_dir = os.path.join(input_dir, 'direct_messages')
    if os.path.isdir(dms_dir):
        for dm_dir in os.listdir(dms_dir):
            dm_path = os.path.join(dms_dir, dm_dir)
            
            # Skip if not a directory
            if not os.path.isdir(dm_path):
                continue
            
            # Process message files
            messages = []
            for filename in os.listdir(dm_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(dm_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        dm_messages = json.load(f)
                        messages.extend(dm_messages)
            
            if messages:
                # Process messages for this DM
                dm_messages = process_dm_messages(messages, dm_dir)
                all_messages.extend(dm_messages)
                
                logging.info("Processed %d messages from DM: %s", len(dm_messages), dm_dir)
    
    logging.info("Total: Processed %d messages from %d channels", len(all_messages), channels_processed)
    return all_messages

def process_channel_messages(messages, channel_name, channel_topic, channel_id):
    """Process messages from a channel and convert to common schema."""
    processed_messages = []
    threads = {}  # Map parent ts to thread messages
    
    # First, organize messages by threads
    for msg in messages:
        # Skip if not a user message
        if 'user' not in msg or 'subtype' in msg and msg['subtype'] != 'thread_broadcast':
            continue
        
        # Check if it's a threaded reply
        thread_ts = msg.get('thread_ts')
        if thread_ts and thread_ts != msg.get('ts'):
            if thread_ts not in threads:
                threads[thread_ts] = []
            threads[thread_ts].append(msg)
    
    # Process messages
    for msg in messages:
        # Skip if not a user message
        if 'user' not in msg or ('subtype' in msg and msg['subtype'] != 'thread_broadcast'):
            continue
        
        # Get basic message info
        ts = msg.get('ts', '')
        text = clean_unicode(msg.get('text', ''))
        user_id = msg.get('user', '')
        
        # Convert timestamp
        iso_timestamp, formatted_date = convert_slack_timestamp(ts)
        
        # Extract course context
        course_context = extract_course_context(text, channel_name, channel_topic)
        
        # Skip non-academic messages if no course context found
        if not course_context:
            logging.debug("Skipping message: No academic context found")
            continue
        
        # Generate message schema
        message_schema = {
            "message_id": ts,
            "source_type": "slack",
            "timestamp": iso_timestamp,
            "date_formatted": formatted_date,
            "sender": {
                "name": user_id,  # Will be resolved to actual name later
                "slack_id": user_id
            },
            "recipients": [
                {
                    "name": channel_name,
                    "type": "channel",
                    "channel_id": channel_id
                }
            ],
            "subject": channel_name,
            "content": text,
            "thread_id": msg.get('thread_ts', ts),
            "parent_message_id": msg.get('thread_ts') if msg.get('thread_ts') != ts else None,
            "course_context": course_context,
            "metadata": {
                "has_attachments": 'files' in msg,
                "attachments": [],
                "reactions": [],
                "mentions": extract_mentions(text)
            }
        }
        
        # Add attachments
        if 'files' in msg:
            for file in msg['files']:
                attachment = {
                    "filename": file.get('name', ''),
                    "url": file.get('url_private', ''),
                    "size": file.get('size', 0)
                }
                message_schema["metadata"]["attachments"].append(attachment)
        
        # Add reactions
        if 'reactions' in msg:
            for reaction in msg['reactions']:
                reaction_schema = {
                    "name": reaction.get('name', ''),
                    "count": reaction.get('count', 0),
                    "users": reaction.get('users', [])
                }
                message_schema["metadata"]["reactions"].append(reaction_schema)
        
        processed_messages.append(message_schema)
    
    return processed_messages

def process_dm_messages(messages, dm_id):
    """Process messages from a direct message and convert to common schema."""
    processed_messages = []
    
    for msg in messages:
        # Skip if not a user message
        if 'user' not in msg or 'subtype' in msg:
            continue
        
        # Get basic message info
        ts = msg.get('ts', '')
        text = clean_unicode(msg.get('text', ''))
        user_id = msg.get('user', '')
        
        # Convert timestamp
        iso_timestamp, formatted_date = convert_slack_timestamp(ts)
        
        # Extract course context
        course_context = extract_course_context(text)
        
        # Skip non-academic messages if no course context found
        if not course_context:
            continue
        
        # Generate message schema
        message_schema = {
            "message_id": ts,
            "source_type": "slack",
            "timestamp": iso_timestamp,
            "date_formatted": formatted_date,
            "sender": {
                "name": user_id,  # Will be resolved to actual name later
                "slack_id": user_id
            },
            "recipients": [
                {
                    "name": "Direct Message",
                    "type": "dm",
                    "channel_id": dm_id
                }
            ],
            "subject": "Direct Message",
            "content": text,
            "thread_id": msg.get('thread_ts', ts),
            "parent_message_id": msg.get('thread_ts') if msg.get('thread_ts') != ts else None,
            "course_context": course_context,
            "metadata": {
                "has_attachments": 'files' in msg,
                "attachments": [],
                "reactions": [],
                "mentions": extract_mentions(text)
            }
        }
        
        # Add attachments
        if 'files' in msg:
            for file in msg['files']:
                attachment = {
                    "filename": file.get('name', ''),
                    "url": file.get('url_private', ''),
                    "size": file.get('size', 0)
                }
                message_schema["metadata"]["attachments"].append(attachment)
        
        # Add reactions
        if 'reactions' in msg:
            for reaction in msg['reactions']:
                reaction_schema = {
                    "name": reaction.get('name', ''),
                    "count": reaction.get('count', 0),
                    "users": reaction.get('users', [])
                }
                message_schema["metadata"]["reactions"].append(reaction_schema)
        
        processed_messages.append(message_schema)
    
    return processed_messages

def extract_mentions(text):
    """Extract user mentions from message text."""
    mention_pattern = r'<@([A-Z0-9]+)>'
    return re.findall(mention_pattern, text)

def import_from_api(token, channels=None):
    """Import Slack data using the Slack API."""
    if not HAS_SLACK_SDK:
        logging.error("Slack SDK not installed. Install with: pip install slack_sdk")
        sys.exit(1)
    
    logging.info("Importing Slack data using the API")
    
    client = WebClient(token=token)
    all_messages = []
    
    try:
        # Get list of channels
        response = client.conversations_list()
        all_channels = response['channels']
        
        # Filter channels if specified
        if channels:
            channel_list = channels.split(',')
            filtered_channels = [c for c in all_channels if c['name'] in channel_list]
        else:
            filtered_channels = all_channels
        
        # Process each channel
        for channel in filtered_channels:
            channel_id = channel['id']
            channel_name = channel['name']
            channel_topic = channel.get('topic', {}).get('value', '')
            
            logging.info("Processing channel: %s", channel_name)
            
            # Get channel history
            try:
                result = client.conversations_history(channel=channel_id)
                messages = result['messages']
                
                # Process messages for this channel
                channel_messages = process_api_messages(
                    messages, channel_name, channel_topic, channel_id, client
                )
                all_messages.extend(channel_messages)
                
                logging.info("Processed %d messages from channel: %s", len(channel_messages), channel_name)
                
            except SlackApiError as e:
                logging.error("Error getting history for channel %s: %s", channel_name, str(e))
    
    except SlackApiError as e:
        logging.error("Error connecting to Slack API: %s", str(e))
        sys.exit(1)
    
    return all_messages

def process_api_messages(messages, channel_name, channel_topic, channel_id, client):
    """Process messages from the API and convert to common schema."""
    processed_messages = []
    
    for msg in messages:
        # Skip if not a user message
        if 'user' not in msg or 'subtype' in msg:
            continue
        
        # Get basic message info
        ts = msg.get('ts', '')
        text = clean_unicode(msg.get('text', ''))
        user_id = msg.get('user', '')
        
        # Convert timestamp
        iso_timestamp, formatted_date = convert_slack_timestamp(ts)
        
        # Extract course context
        course_context = extract_course_context(text, channel_name, channel_topic)
        
        # Skip non-academic messages if no course context found
        if not course_context:
            continue
        
        # Generate message schema
        message_schema = {
            "message_id": ts,
            "source_type": "slack",
            "timestamp": iso_timestamp,
            "date_formatted": formatted_date,
            "sender": {
                "name": user_id,  # Will be resolved to actual name later
                "slack_id": user_id
            },
            "recipients": [
                {
                    "name": channel_name,
                    "type": "channel",
                    "channel_id": channel_id
                }
            ],
            "subject": channel_name,
            "content": text,
            "thread_id": msg.get('thread_ts', ts),
            "parent_message_id": msg.get('thread_ts') if msg.get('thread_ts') != ts else None,
            "course_context": course_context,
            "metadata": {
                "has_attachments": False,  # Will check for files in a separate API call
                "attachments": [],
                "reactions": [],
                "mentions": extract_mentions(text)
            }
        }
        
        # If this is a parent message with replies, get the thread replies
        if 'thread_ts' in msg and msg['thread_ts'] == ts and msg.get('reply_count', 0) > 0:
            try:
                # Get thread replies
                thread_result = client.conversations_replies(
                    channel=channel_id,
                    ts=ts
                )
                
                # Skip the parent message (already processed)
                thread_messages = thread_result['messages'][1:]
                
                # TODO: Process thread messages (similar to above)
                # This would involve creating message schemas for each reply
                # and adding them to processed_messages
                
            except SlackApiError as e:
                logging.error("Error getting thread replies: %s", str(e))
        
        processed_messages.append(message_schema)
    
    return processed_messages

def resolve_user_names(messages, input_dir=None, client=None):
    """Resolve user IDs to names."""
    user_cache = {}
    
    # If using export, read users from users.json
    if input_dir:
        users_file = os.path.join(input_dir, 'users.json')
        if os.path.isfile(users_file):
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
                for user in users:
                    user_id = user.get('id')
                    real_name = user.get('real_name', user.get('name', user_id))
                    user_cache[user_id] = real_name
    
    # If using API, get users via API
    elif client:
        try:
            response = client.users_list()
            users = response['members']
            for user in users:
                user_id = user.get('id')
                real_name = user.get('real_name', user.get('name', user_id))
                user_cache[user_id] = real_name
        except Exception as e:
            logging.error("Error fetching users from API: %s", str(e))
    
    # Update messages with user names
    for message in messages:
        user_id = message['sender']['slack_id']
        if user_id in user_cache:
            message['sender']['name'] = user_cache[user_id]
    
    return messages

def write_json_output(messages, output_file, pretty=False):
    """Write messages to JSON output file."""
    logging.info("Writing %d messages to %s", len(messages), output_file)
    
    # Create directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Write JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        else:
            json.dump(messages, f, ensure_ascii=False)

def main():
    """Main entry point."""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    logging.info("Starting Slack data import")
    
    # Validate arguments
    if not args.input_dir and not args.api_token:
        logging.error("Either --input_dir or --api_token must be specified")
        sys.exit(1)
    
    # Import data
    messages = []
    if args.input_dir:
        messages = import_from_export(args.input_dir, args.channels)
    elif args.api_token:
        messages = import_from_api(args.api_token, args.channels)
    
    # Resolve user names
    if args.input_dir:
        messages = resolve_user_names(messages, input_dir=args.input_dir)
    elif args.api_token and HAS_SLACK_SDK:
        client = WebClient(token=args.api_token)
        messages = resolve_user_names(messages, client=client)
    
    # Write output
    write_json_output(messages, args.output_file, args.pretty)
    
    logging.info("Slack data import complete. %d messages written to %s", len(messages), args.output_file)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
remote-import-emails.py

This script imports .eml files and converts them to a standardized JSON format
for use in the REMOTE (Remote Education Management and Organization Tool for Education)
application. The output JSON follows a common schema that works for both email
and Slack messages.

Usage:
    python remote-import-emails.py --input_dir /path/to/eml/files --output_file emails.json

Author: [Your Name]
Date: April 2025
"""

# pylint: disable=trailing-whitespace

import os
import sys
import json
import argparse
from email import policy
from email import utils
from email import errors
from email.parser import BytesParser
from email.header import decode_header
from datetime import datetime
import re
import logging
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Import .eml files and convert to standardized JSON format'
    )
    parser.add_argument(
        '--input_dir', 
        default=os.getcwd(),
        help='Directory containing .eml files (default: current directory)'
    )
    parser.add_argument(
        '--output_file', 
        default='emails.json',
        help='Path for the output JSON file (default: email-messages.json)'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable detailed logging'
    )
    parser.add_argument(
        '--pretty', 
        action='store_true',
        help='Format JSON output with indentation'
    )
    return parser.parse_args()

def decode_string(encoded_string):
    """Decode encoded header strings to Unicode."""
    if encoded_string is None:
        return ""
    
    if isinstance(encoded_string, str):
        return encoded_string
    
    try:
        decoded_parts = decode_header(encoded_string)
        decoded_string = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_string += part.decode(encoding, errors='replace')
                else:
                    decoded_string += part.decode('utf-8', errors='replace')
            elif isinstance(part, str):
                decoded_string += part
        return decoded_string
    except (UnicodeDecodeError, LookupError) as e:
        logger.warning("Error decoding string: %s", e)
        if isinstance(encoded_string, bytes):
            return encoded_string.decode('utf-8', errors='replace')
        return clean_unicode_string(decoded_string)

def clean_unicode_string(s):
    """Clean a Unicode string by removing problematic invisible characters."""
    if not s:
        return ""
    
    # Define a translation table for control characters (0x00-0x1F except for \t, \n, \r)
    control_chars = ''.join(chr(i) for i in range(32) if i not in (9, 10, 13))
    translation_table = dict.fromkeys(map(ord, control_chars), None)
    
    # Also remove other problematic invisible characters
    for c in '\u200B\u200C\u200D\u200E\u200F\uFEFF':  # Zero-width characters and BOM
        translation_table[ord(c)] = None
    
    # Apply the translation table and normalize whitespace
    cleaned = s.translate(translation_table)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()
    
def extract_course_context(subject, body):
    """
    Attempt to extract course context from email subject and body.
    This is a simple heuristic approach that looks for common course code patterns.
    """
    # Look for common course code patterns like CS101, MATH 200, etc.
    course_patterns = [
        r'\b[A-Z]{2,4}\s?\d{3,4}[A-Z]?\b',  # CS101, MATH 200, PHYS 101A
        r'\b[A-Z]{2,4}-\d{3,4}[A-Z]?\b',    # CS-101, MATH-200
        r'\bCourse\s+\d+\b',                # Course 101
        r'\bClass\s+\d+\b'                  # Class 101
    ]
    
    text = f"{subject} {body}"
    
    for pattern in course_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    # Check for specific course keywords
    course_keywords = ["homework", "assignment", "lecture", "class", "course", "exam", "quiz"]
    for keyword in course_keywords:
        if keyword.lower() in text.lower():
            # Look for nearby words that might be a subject
            subject_pattern = (
                r'\b(?:math|science|biology|chemistry|physics|history|'
                r'english|computer|cs|programming)\b'
            )
            matches = re.finditer(subject_pattern, text.lower())
            for match in matches:
                # Check if keyword is nearby (within 50 characters)
                keyword_pos = text.lower().find(keyword.lower())
                if keyword_pos != -1 and abs(keyword_pos - match.start()) < 50:
                    return match.group(0).upper()
    
    return None

def parse_eml_file(file_path):
    """Parse an .eml file and extract its contents and metadata."""
    try:
        with open(file_path, 'rb') as file:
            message = BytesParser(policy=policy.default).parse(file)
        
        # Extract basic headers
        subject = decode_string(message.get('Subject', ''))
        from_header = decode_string(message.get('From', ''))
        to_header = decode_string(message.get('To', ''))
        cc_header = decode_string(message.get('Cc', ''))
        bcc_header = decode_string(message.get('Bcc', ''))
        date_header = message.get('Date', '')
        
        # Parse sender information
        sender_name, sender_email = utils.parseaddr(from_header)
        sender_name = decode_string(sender_name) or sender_email.split('@')[0]
        
        # Parse recipient information
        recipients = []
        
        # To recipients
        for recipient in to_header.split(','):
            if recipient.strip():
                name, email_addr = utils.parseaddr(recipient)
                name = decode_string(name) or email_addr.split('@')[0]
                if email_addr:
                    recipients.append({
                        "name": name,
                        "email": email_addr,
                        "type": "to"
                    })
        
        # CC recipients
        for recipient in cc_header.split(','):
            if recipient.strip():
                name, email_addr = utils.parseaddr(recipient)
                name = decode_string(name) or email_addr.split('@')[0]
                if email_addr:
                    recipients.append({
                        "name": name,
                        "email": email_addr,
                        "type": "cc"
                    })
        
        # BCC recipients
        for recipient in bcc_header.split(','):
            if recipient.strip():
                name, email_addr = utils.parseaddr(recipient)
                name = decode_string(name) or email_addr.split('@')[0]
                if email_addr:
                    recipients.append({
                        "name": name,
                        "email": email_addr,
                        "type": "bcc"
                    })
        
        # Parse date
        if date_header:
            try:
                timestamp = utils.parsedate_to_datetime(date_header)
                date_formatted = timestamp.strftime("%b %d")
            except (TypeError, ValueError):
                # Fallback to current time if date parsing fails
                timestamp = datetime.now()
                date_formatted = timestamp.strftime("%b %d")
        else:
            timestamp = datetime.now()
            date_formatted = timestamp.strftime("%b %d")
        
        # Extract body content
        body = ""
        attachments = []
        
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip container multipart sections
                if content_type.startswith("multipart/"):
                    continue
                
                # Handle attachments
                if "attachment" in content_disposition or "inline" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = decode_string(filename)
                        attachments.append({
                            "filename": filename,
                            "content_type": content_type,
                            "size": len(part.get_payload(decode=True) or b'')
                        })
                    continue
                
                # Handle text content
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body += payload.decode(charset, errors='replace')
                        except (LookupError, UnicodeDecodeError):
                            body += payload.decode('utf-8', errors='replace')
                
                # If no text/plain part was found, try html
                elif content_type == "text/html" and not body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            # Very simple HTML to text conversion
                            html_body = payload.decode(charset, errors='replace')
                            # Remove HTML tags
                            body += re.sub(r'<[^>]+>', ' ', html_body)
                            # Normalize whitespace
                            body = re.sub(r'\s+', ' ', body).strip()
                            body = clean_unicode_string(body)

                        except (LookupError, UnicodeDecodeError):
                            html_body = payload.decode('utf-8', errors='replace')
                            body += re.sub(r'<[^>]+>', ' ', html_body)
                            body = re.sub(r'\s+', ' ', body).strip()
        else:
            # Not multipart - get the payload directly
            payload = message.get_payload(decode=True)
            if payload:
                charset = message.get_content_charset() or 'utf-8'
                try:
                    body = payload.decode(charset, errors='replace')
                except (LookupError, UnicodeDecodeError):
                    body = payload.decode('utf-8', errors='replace')
                
                # If it's HTML, convert to plain text
                if message.get_content_type() == "text/html":
                    body = re.sub(r'<[^>]+>', ' ', body)
                    body = re.sub(r'\s+', ' ', body).strip()
                    body = clean_unicode_string(body)
        # Extract message ID from headers or generate one
        message_id = message.get('Message-ID', '').strip('<>')
        if not message_id:
            # Generate a stable ID based on content
            content_hash = hashlib.md5()
            content_hash.update(f"{from_header}{to_header}{subject}{date_header}".encode('utf-8'))
            message_id = f"{content_hash.hexdigest()}@remote.generated"
        
        # Generate thread ID based on subject
        # This is a simple approach - for a more robust solution you'd need
        # to track In-Reply-To and References headers
        thread_id = None
        if subject:
            # Remove Re:, Fwd:, etc. to group related subjects
            clean_subject = re.sub(r'^(?:Re|Fwd|Fw|FYI|FWD):\s*', '', subject, flags=re.IGNORECASE)
            thread_hash = hashlib.md5()
            thread_hash.update(clean_subject.encode('utf-8'))
            thread_id = f"{thread_hash.hexdigest()}@remote.thread"
        
        # Attempt to extract course context
        course_context = extract_course_context(subject, body)
        
        # Determine if message is read (this is a placeholder - in a real system
        # this would be determined by the email client's read/unread status)
        is_read = True  # Assuming all imported messages are read
        
        # Determine if the message is a reply
        is_reply = subject.lower().startswith('re:')
        parent_message_id = None
        if is_reply:
            # In a real implementation, this would extract the parent message ID
            # from the In-Reply-To header
            in_reply_to = message.get('In-Reply-To', '').strip('<>')
            if in_reply_to:
                parent_message_id = in_reply_to
        
        return {
            "message_id": message_id,
            "source_type": "email",
            "timestamp": timestamp.isoformat(),
            "date_formatted": date_formatted,
            "sender": {
                "name": sender_name,
                "email": sender_email
            },
            "recipients": recipients,
            "subject": subject,
            "content": body,
            "thread_id": thread_id,
            "parent_message_id": parent_message_id,
            "course_context": course_context,
            "metadata": {
                "has_attachments": len(attachments) > 0,
                "attachments": attachments,
                "importance": "normal",  # Placeholder - could parse Importance header
                "is_read": is_read
            }
        }
    except (IOError, errors.MessageError) as e:
        logger.error("Error parsing %s: %s", file_path, e)
        return None

def process_email_files(input_dir, verbose=False):
    """
    Process all .eml files in the input directory and convert to common format.
    """
    emails = []
    
    if verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check if directory exists
    if not os.path.isdir(input_dir):
        logger.error("Input directory does not exist: %s", input_dir)
        return emails
    
    # List all .eml files
    eml_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.eml')]
    
    if not eml_files:
        logger.warning("No .eml files found in %s", input_dir)
        return emails
    
    logger.info("Found %d .eml files to process", len(eml_files))
    
    # Process each file
    for i, file_name in enumerate(eml_files):
        file_path = os.path.join(input_dir, file_name)
        logger.debug("Processing file %d/%d: %s", i+1, len(eml_files), file_name)
        
        email_data = parse_eml_file(file_path)
        if email_data:
            emails.append(email_data)
            if verbose:
                logger.debug("Successfully parsed: %s", email_data['subject'])
    
    logger.info("Successfully processed %d emails", len(emails))
    return emails

def write_json_output(emails, output_file, pretty=False):
    """Write the processed emails to a JSON file."""
    try:
        # Clean emails before writing
        for email in emails:
            # Clean string fields in the top level
            for key, value in list(email.items()):
                if isinstance(value, str):
                    email[key] = clean_unicode_string(value)
            
            # Clean the email content specifically
            if "content" in email:
                email["content"] = clean_unicode_string(email["content"])
            
            # Clean sender info
            if "sender" in email and isinstance(email["sender"], dict):
                for key, value in list(email["sender"].items()):
                    if isinstance(value, str):
                        email["sender"][key] = clean_unicode_string(value)
            
            # Clean recipient info
            if "recipients" in email and isinstance(email["recipients"], list):
                for recipient in email["recipients"]:
                    if isinstance(recipient, dict):
                        for key, value in list(recipient.items()):
                            if isinstance(value, str):
                                recipient[key] = clean_unicode_string(value)
        
        # Rest of function remains the same
        with open(output_file, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(emails, f, indent=2, ensure_ascii=False)
            else:
                json.dump(emails, f, ensure_ascii=False)
        logger.info("Successfully wrote %d emails to %s", len(emails), output_file)
        return True
    except (IOError, json.JSONDecodeError) as e:
        logger.error("Error writing output file: %s", e)
        return False
def main():
    """Main execution function."""
    args = parse_arguments()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    logger.info("Processing emails from: %s", args.input_dir)
    logger.info("Output will be written to: %s", args.output_file)
    
    # Process the email files
    emails = process_email_files(args.input_dir, args.verbose)
    
    if emails:
        # Write the output
        success = write_json_output(emails, args.output_file, args.pretty)
        if success:
            logger.info("Email import completed successfully")
        else:
            logger.error("Failed to write output file")
            return 1
    else:
        logger.warning("No emails were processed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

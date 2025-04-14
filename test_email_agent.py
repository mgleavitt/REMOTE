from email_data_agent import EmailDataAgent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize the email data agent
    agent = EmailDataAgent()
    
    # Path to the email data file
    data_file = "/Users/marcleavitt/dev/REMOTE/data/email/imported/emails.json"
    
    # Load the data
    success = agent.load_data(data_file)
    if not success:
        logger.error("Failed to load email data")
        return
    
    # Get all email data
    emails = agent.get_data()
    logger.info(f"Successfully loaded {len(emails)} emails")
    
    # Print some basic statistics
    if emails:
        logger.info("Sample email data:")
        sample_email = emails[0]
        logger.info(f"Date: {sample_email['Date']}")
        logger.info(f"Subject: {sample_email['Title']}")
        logger.info(f"From: {sample_email['From']}")
        logger.info(f"Course: {sample_email['Course']}")

if __name__ == "__main__":
    main() 
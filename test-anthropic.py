"""
Test script to verify that the Anthropic API is working correctly.
Run this separately from the main application to isolate API issues.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name, unnecessary-pass

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    logger.error("Failed to import anthropic library - make sure it's installed")
    print("ERROR: The anthropic package is not installed.")
    print("Install it with: pip install anthropic")
    exit(1)

def test_anthropic_api():
    """Test the Anthropic API with a simple prompt."""
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        print("Set it with: export ANTHROPIC_API_KEY=your_api_key")
        return False
    
    print(f"Using API key: {api_key[:5]}...{api_key[-4:]}")
    
    try:
        # Initialize client
        client = anthropic.Anthropic(api_key=api_key)
        print("Successfully initialized Anthropic client")
        
        # Test prompt
        test_prompt = "Say hello and introduce yourself in one short paragraph."
        
        print("\nSending test prompt to Anthropic API...")
        # Note: No await needed - this is a synchronous call in the current API
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",  # Using a more recent model
            max_tokens=1024,
            temperature=0.7,
            system="You are a helpful AI assistant for testing purposes.",
            messages=[
                {"role": "user", "content": test_prompt}
            ]
        )
        
        # Extract and print response
        try:
            response_text = response.content[0].text
            print("\nReceived response:\n----------")
            print(response_text)
            print("----------")
            print("\nAPI test SUCCESSFUL!")
            return True
        except (IndexError, AttributeError) as e:
            logger.error("Error extracting response: %s", str(e))
            print(f"ERROR: Could not extract response from API result: {str(e)}")
            print(f"Raw response: {response}")
            return False
            
    except (ValueError, RuntimeError, ImportError, ConnectionError) as e:
        logger.error("Error testing Anthropic API: %s", str(e))
        print(f"\nERROR: Could not connect to Anthropic API: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Anthropic API connection...")
    success = test_anthropic_api()  # No need for asyncio.run
    if success:
        print("\nThe Anthropic API is working correctly.")
        print(
            "If your app is still having issues, "
            "the problem is in the integration code, not the API."
        )
    else:
        print("\nThe Anthropic API test FAILED.")
        print("Please fix the API issues before continuing with the app.")

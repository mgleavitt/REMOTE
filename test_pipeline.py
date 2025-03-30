"""
Simplified test component that bypasses the LLM API.
This can be used to verify that the pipeline works without LLM API calls.
"""
import logging
from typing import Any, Coroutine, Union

from llm_components import LLMComponent, Message, MessageType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestCoreComponent(LLMComponent):
    """Test component that returns canned responses without LLM calls."""
    
    def __init__(self, name: str = "TestCore"):
        """Initialize the test core component."""
        super().__init__(name)
        logger.info("TestCoreComponent initialized - USING TEST MODE")
    
    def process_input(self, message: Message) -> Union[None, Coroutine[Any, Any, None]]:
        """Process an input message with canned responses.
        
        Args:
            message: The message to process
            
        Returns:
            None - this is a synchronous method
        """
        # Only process appropriate message types
        if message.type not in [MessageType.USER_INPUT, MessageType.VALIDATED_INPUT]:
            logger.info("TestCore ignoring message with type: %s", message.type)
            return None
            
        # Log that we received a message to process
        logger.info("TestCore received message: %s", message.content[:50])
        
        # Create a test response
        response_text = self._get_canned_response(message.content)
        
        # Create output message
        output_message = Message(
            content=response_text,
            thinking="This is a test thinking output that would normally come from Claude.",
            msg_type=MessageType.CORE_RESPONSE
        )
        
        self.send_status("Test response generated")
        logger.info("Sending test response to UI: %s", response_text[:50])
        self.send_output(output_message)
        
        return None  # No coroutine to await
    
    def _get_canned_response(self, user_input: str) -> str:
        """Generate a canned response based on user input."""
        user_input_lower = user_input.lower()
        
        if "hello" in user_input_lower or "hi" in user_input_lower:
            return "Hello! I'm a test assistant. I'm responding with a canned message to verify that the message pipeline is working correctly. How can I help you today?"
            
        if "help" in user_input_lower:
            return "I'm a test assistant designed to verify that your message pipeline is working correctly. This response is not coming from Claude or any LLM - it's a pre-written message to check the UI flow."
            
        if "?" in user_input:
            return "That's an interesting question! In test mode, I don't have access to real AI capabilities. This is just a pre-programmed response to verify that messages can flow from the UI to the core component and back to the UI."
            
        # Default response
        return f"I received your message: '{user_input}'. This is a test response to verify that the pipeline is working correctly. No LLM API call was made to generate this response."

"""
Core LLM component for processing user queries.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

import logging

from llm_components import LLMComponent, Message, MessageType
from llm_providers import LLMBaseProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoreLLMComponent(LLMComponent):
    """Core LLM component that processes user queries."""
    
    def __init__(self, llm_provider: LLMBaseProvider, 
                system_prompt: str = "", 
                name: str = "CoreLLM"):
        """Initialize the Core LLM component.
        
        Args:
            llm_provider: The LLM provider to use
            system_prompt: System prompt for the LLM
            name: Component name
        """
        super().__init__(name)
        self.llm_provider = llm_provider
        self.system_prompt = system_prompt or """
        You are an educational assistant for a university student.
        Provide helpful, accurate, and educational responses.
        Focus on being clear, concise, and informative.
        """
    
    async def process_input(self, message: Message) -> None:
        """Process an input message by sending it to the LLM.
        
        Args:
            message: The message to process
        """
        # Only process appropriate message types
        if message.type not in [MessageType.USER_INPUT, MessageType.VALIDATED_INPUT]:
            logger.info("Ignoring message with type: %s", message.type)
            return
        
        try:
            self.send_status("Processing message...")
            
            # Generate response from LLM with thinking if available
            response = await self.llm_provider.generate_response(
                message.content,
                system=self.system_prompt,
                max_tokens=2048,  # Adjust as needed
                temperature=0.7   # Adjust as needed
            )
            
            # Check if response includes thinking
            if isinstance(response, tuple) and len(response) == 2:
                content, thinking = response
            else:
                content = response
                thinking = None
            
            # Create output message
            output_message = Message(
                content=content,
                thinking=thinking,
                msg_type=MessageType.CORE_RESPONSE
            )
            
            self.send_status("Response generated")
            self.send_output(output_message)
            
        except (ValueError, RuntimeError) as e:
            logger.error("Error in CoreLLM: %s", str(e))
            error_message = Message(
                content=f"Failed to generate response: {str(e)}",
                msg_type=MessageType.ERROR
            )
            self.send_output(error_message)


class InputClassifierComponent(LLMComponent):
    """Component that classifies and validates user input."""
    
    def __init__(self, llm_provider: LLMBaseProvider, 
                system_prompt: str = "", 
                name: str = "InputClassifier"):
        """Initialize the input classifier component.
        
        Args:
            llm_provider: The LLM provider to use
            system_prompt: System prompt for the classifier
            name: Component name
        """
        super().__init__(name)
        self.llm_provider = llm_provider
        self.system_prompt = system_prompt or """
        You are a message classifier for an educational assistant.
        Your job is to ensure messages are appropriate and on-topic for an educational context.
        Respond with VALID if the message is appropriate, or INVALID [reason] if not.
        """
    
    async def process_input(self, message: Message) -> None:
        """Process and validate user input.
        
        Args:
            message: The message to process
        """
        if message.type != MessageType.USER_INPUT:
            return
        
        try:
            self.send_status("Validating input...")
            
            classification = await self.llm_provider.generate_response(
                message.content,
                system=self.system_prompt,
                max_tokens=50  # Short response for classification
            )
            
            # If we got a tuple back (response, thinking), use just the response
            if isinstance(classification, tuple):
                classification = classification[0]
            
            if classification.startswith("VALID"):
                # Pass through the original message content with a new type
                validated_message = Message(
                    content=message.content,
                    msg_type=MessageType.VALIDATED_INPUT,
                    metadata={"classification": "valid"}
                )
                self.send_output(validated_message)
            else:
                # Extract reason from INVALID [reason]
                reason = classification.replace("INVALID", "").strip()
                if not reason:
                    reason = "Input was flagged as inappropriate"
                
                error_message = Message(
                    content=f"Your message couldn't be processed: {reason}",
                    msg_type=MessageType.ERROR
                )
                self.send_output(error_message)
                
        except (ValueError, RuntimeError) as e:
            logger.error("Error in InputClassifier: %s", str(e))
            error_message = Message(
                content=f"Error validating input: {str(e)}",
                msg_type=MessageType.ERROR
            )
            self.send_output(error_message)


class OutputClassifierComponent(LLMComponent):
    """Component that validates LLM output before presenting to user."""
    
    def __init__(self, llm_provider: LLMBaseProvider, 
                system_prompt: str = "", 
                name: str = "OutputClassifier"):
        """Initialize the output classifier component.
        
        Args:
            llm_provider: The LLM provider to use
            system_prompt: System prompt for the classifier
            name: Component name
        """
        super().__init__(name)
        self.llm_provider = llm_provider
        self.system_prompt = system_prompt or """
        You are a response validator for an educational assistant.
        Your job is to ensure responses are appropriate, accurate, and helpful.
        Respond with VALID if the response is appropriate, or INVALID [reason] if not.
        """
    
    async def process_input(self, message: Message) -> None:
        """Process and validate LLM output.
        
        Args:
            message: The message to process
        """
        if message.type != MessageType.CORE_RESPONSE:
            return
        
        try:
            self.send_status("Validating output...")
            
            classification = await self.llm_provider.generate_response(
                message.content,
                system=self.system_prompt,
                max_tokens=50  # Short response for classification
            )
            
            # If we got a tuple back (response, thinking), use just the response
            if isinstance(classification, tuple):
                classification = classification[0]
            
            if classification.startswith("VALID"):
                # Pass through the original message content with a new type
                validated_message = Message(
                    content=message.content,
                    thinking=message.thinking,  # Preserve thinking
                    msg_type=MessageType.VALIDATED_OUTPUT,
                    metadata={"classification": "valid"}
                )
                self.send_output(validated_message)
            else:
                # Extract reason from INVALID [reason]
                reason = classification.replace("INVALID", "").strip()
                if not reason:
                    reason = "Response was flagged as inappropriate"
                
                error_message = Message(
                    content=("The system generated an inappropriate response. "
                            "Please try a different query."),
                    msg_type=MessageType.ERROR,
                    metadata={"original_content": message.content, "reason": reason}
                )
                self.send_output(error_message)
                
        except (ValueError, RuntimeError) as e:
            logger.error("Error in OutputClassifier: %s", str(e))
            error_message = Message(
                content=f"Error validating output: {str(e)}",
                msg_type=MessageType.ERROR
            )
            self.send_output(error_message)

"""
Core LLM component for processing user queries.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name, unnecessary-pass

import logging
import traceback
from typing import Any, Coroutine, Union

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
        logger.info("CoreLLMComponent initialized with provider: %s", type(llm_provider).__name__)
    
    def process_input(self, message: Message) -> Union[None, Coroutine[Any, Any, None]]:
        """Process an input message by sending it to the LLM.
        
        Args:
            message: The message to process
            
        Returns:
            Coroutine that processes the message
        """
        # Only process appropriate message types
        if message.type not in [MessageType.USER_INPUT, MessageType.VALIDATED_INPUT]:
            logger.info("CoreLLM ignoring message with type: %s", message.type)
            return None
            
        # Log that we received a message to process
        logger.info("CoreLLM received message to process: %s", message.content[:50])
        
        # Return the coroutine for processing
        return self._process_input_impl(message)
    
    async def _process_input_impl(self, message: Message) -> None:
        """Implementation of process_input that handles the async work."""
        try:
            self.send_status("Processing message...")
            logger.info("CoreLLM starting to process message...")
            
            # Add a test response to verify if messages can flow back to the UI
            test_response = Message(
                content="[DEBUG] This is a test response to verify messages can flow back to UI. The real LLM call will follow.",
                msg_type=MessageType.CORE_RESPONSE
            )
            self.send_output(test_response)
            logger.info("Sent debug test response to UI")
            
            # Generate response from LLM with thinking if available
            try:
                logger.info("Preparing to send request to LLM provider...")
                
                # Log all parameters being sent to the provider
                logger.info("System prompt: %s", self.system_prompt[:50])
                logger.info("Using provider type: %s", type(self.llm_provider).__name__)
                
                # Explicitly catch any exceptions that might happen in the API call
                try:
                    logger.info("About to call generate_response...")
                    response = await self.llm_provider.generate_response(
                        message.content,
                        system=self.system_prompt,
                        max_tokens=2048,
                        temperature=0.7
                    )
                    logger.info("Received response from LLM provider")
                except Exception as api_error:
                    logger.error("API call failed: %s", str(api_error))
                    logger.error(traceback.format_exc())
                    raise ValueError(f"API call failed: {str(api_error)}") from api_error
                
                # Check if response includes thinking
                logger.info("Processing response of type: %s", type(response))
                if isinstance(response, tuple) and len(response) == 2:
                    content, thinking = response
                    logger.info("Response includes thinking (%d chars)", len(thinking) if thinking else 0)
                else:
                    content = response
                    thinking = None
                    logger.info("Response does not include thinking")
                
                # Create output message
                logger.info("Creating output message with content: %s", content[:50])
                output_message = Message(
                    content=content,
                    thinking=thinking,
                    msg_type=MessageType.CORE_RESPONSE
                )
                
                self.send_status("Response generated")
                logger.info("Sending response back to UI: %s", content[:50])
                self.send_output(output_message)
                
            except Exception as e:
                logger.error("Error generating response: %s", str(e))
                logger.error(traceback.format_exc())
                raise ValueError(f"Failed to generate response: {str(e)}") from e
            
        except (ValueError, RuntimeError) as e:
            logger.error("Error in CoreLLM: %s", str(e))
            logger.error(traceback.format_exc())
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
    
    def process_input(self, message: Message) -> Union[None, Coroutine[Any, Any, None]]:
        """Process and validate user input.
        
        Args:
            message: The message to process
            
        Returns:
            Coroutine that processes the message
        """
        return self._process_input_impl(message)
    
    async def _process_input_impl(self, message: Message) -> None:
        """Implementation of process_input that handles the async work."""
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
    
    def process_input(self, message: Message) -> Union[None, Coroutine[Any, Any, None]]:
        """Process and validate LLM output.
        
        Args:
            message: The message to process
            
        Returns:
            Coroutine that processes the message
        """
        return self._process_input_impl(message)
    
    async def _process_input_impl(self, message: Message) -> None:
        """Implementation of process_input that handles the async work."""
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

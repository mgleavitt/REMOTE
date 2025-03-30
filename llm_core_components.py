"""
Core LLM component for processing user queries (Synchronous version).
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name, unnecessary-pass

import logging
import traceback
import concurrent.futures

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
        # Create a thread pool for API calls
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        logger.info("CoreLLMComponent initialized with provider: %s", type(llm_provider).__name__)
    
    def process_input(self, message: Message) -> None:
        """Process an input message by sending it to the LLM.
        
        Args:
            message: The message to process
        """
        # Only process appropriate message types
        if message.type not in [MessageType.USER_INPUT, MessageType.VALIDATED_INPUT]:
            logger.info("CoreLLM ignoring message with type: %s", message.type)
            return
            
        # Log that we received a message to process
        logger.info("CoreLLM received message to process: %s", message.content[:50])
        
        try:
            self.send_status("Processing message...")
            logger.info("Starting to process message...")
            
            # Run the API call in a background thread but wait for it to complete
            def call_llm():
                try:
                    logger.info("Calling LLM provider...")
                    response = self.llm_provider.generate_response(
                        message.content,
                        system=self.system_prompt,
                        max_tokens=2048,
                        temperature=0.7
                    )
                    logger.info("LLM provider returned a response")
                    return response
                except Exception as e:
                    logger.error("Error in LLM call: %s", str(e))
                    logger.error(traceback.format_exc())
                    raise e
            
            # Submit the API call to the thread pool
            logger.info("Submitting API call to thread pool")
            future = self._executor.submit(call_llm)
            
            try:
                # Wait for the result with a timeout
                logger.info("Waiting for API response (with timeout)")
                response = future.result(timeout=60)  # 60-second timeout
                logger.info("Received API response")
                
                # Check if response includes thinking
                if isinstance(response, tuple) and len(response) == 2:
                    content, thinking = response
                    logger.info(
                        "Response includes thinking (%d chars)",
                        len(thinking) if thinking else 0
                    )
                else:
                    content = response
                    thinking = None
                    logger.info("Response does not include thinking")
                
                # Create output message
                output_message = Message(
                    content=content,
                    thinking=thinking,
                    msg_type=MessageType.CORE_RESPONSE
                )
                
                self.send_status("Response generated")
                logger.info("Sending response back to UI: %s", content[:50])
                self.send_output(output_message)
                
            except concurrent.futures.TimeoutError:
                logger.error("LLM API call timed out after 60 seconds")
                error_message = Message(
                    content="Request to the LLM timed out. Please try again later.",
                    msg_type=MessageType.ERROR
                )
                self.send_output(error_message)
                
        except (ValueError, RuntimeError, ImportError, ConnectionError, TimeoutError) as e:
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
        # Create a thread pool for API calls
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
    def process_input(self, message: Message) -> None:
        """Process and validate user input.
        
        Args:
            message: The message to process
        """
        if message.type != MessageType.USER_INPUT:
            return
        
        try:
            self.send_status("Validating input...")
            
            # Run the validation in a background thread
            def validate_input():
                return self.llm_provider.generate_response(
                    message.content,
                    system=self.system_prompt,
                    max_tokens=50  # Short response for classification
                )
            
            # Submit the validation to the thread pool
            future = self._executor.submit(validate_input)
            
            try:
                # Wait for the result with a timeout
                classification = future.result(timeout=30)
                
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
                    
            except concurrent.futures.TimeoutError:
                logger.error("Validation timed out after 30 seconds")
                error_message = Message(
                    content="Validation timed out. Please try again later.",
                    msg_type=MessageType.ERROR
                )
                self.send_output(error_message)
                
        except (ValueError, RuntimeError, ImportError, ConnectionError, TimeoutError) as e:
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
        # Create a thread pool for API calls
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
    def process_input(self, message: Message) -> None:
        """Process and validate LLM output.
        
        Args:
            message: The message to process
        """
        if message.type != MessageType.CORE_RESPONSE:
            return
        
        try:
            self.send_status("Validating output...")
            
            # Run the validation in a background thread
            def validate_output():
                return self.llm_provider.generate_response(
                    message.content,
                    system=self.system_prompt,
                    max_tokens=50  # Short response for classification
                )
            
            # Submit the validation to the thread pool
            future = self._executor.submit(validate_output)
            
            try:
                # Wait for the result with a timeout
                classification = future.result(timeout=30)
                
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
                    
            except concurrent.futures.TimeoutError:
                logger.error("Validation timed out after 30 seconds")
                error_message = Message(
                    content="Validation timed out. Please try again later.",
                    msg_type=MessageType.ERROR
                )
                self.send_output(error_message)
                
        except (ValueError, RuntimeError, ImportError, ConnectionError, TimeoutError) as e:
            logger.error("Error in OutputClassifier: %s", str(e))
            error_message = Message(
                content=f"Error validating output: {str(e)}",
                msg_type=MessageType.ERROR
            )
            self.send_output(error_message)

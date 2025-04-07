"""
Enhanced classifier components for REMOTE application.
"""
# pylint: disable=no-name-in-module, trailing-whitespace, line-too-long
import re
import logging
import traceback
import concurrent.futures
from typing import Optional

from llm_components import LLMComponent, Message, MessageType
from llm_providers import LLMBaseProvider
from constitution_manager import ConstitutionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InputClassifierComponent(LLMComponent):
    """Component that classifies and validates user input based on a constitution."""
    
    def __init__(self, llm_provider: LLMBaseProvider, 
                constitution_manager: Optional[ConstitutionManager] = None,
                constitution_name: str = "input-classifier-constitution", 
                name: str = "InputClassifier"):
        """Initialize the input classifier component.
        
        Args:
            llm_provider: The LLM provider to use
            constitution_manager: Manager for loading constitutions
            constitution_name: Name of the constitution file to use
            name: Component name
        """
        super().__init__(name)
        self.llm_provider = llm_provider
        self.constitution_manager = constitution_manager or ConstitutionManager()
        self.constitution_name = constitution_name
        
        # Generate the system prompt from the constitution
        self.system_prompt = self.constitution_manager.get_system_prompt(self.constitution_name)
        
        # Create a thread pool for API calls
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Standard rejection message for educational setting
        self.rejection_message = "I'm sorry, but I can't process that request as it appears to violate our educational guidelines."
        
        logger.info("%s initialized with constitution: %s", self.name, self.constitution_name)
    
    def process_input(self, message: Message) -> None:
        """Process and validate user input according to the constitution.
        
        Args:
            message: The message to process
        """
        # Only process user input messages
        if message.type != MessageType.USER_INPUT:
            logger.info("%s ignoring message with type: %s", self.name, message.type)
            self.send_output(message)  # Pass through other message types
            return
        
        try:
            self.send_status("Validating input...")
            logger.info("%s validating input: %s", self.name, message.content[:50])
            
            # Load the full constitution for context
            constitution_text = self.constitution_manager.load_constitution(self.constitution_name)
            if not constitution_text:
                logger.warning("%s failed to load constitution, passing message through", self.name)
                self.send_output(message)  # Pass through if constitution not available
                return
            
            # Prepare the validation prompt
            validation_prompt = (
                "Your task is to evaluate if the following user input complies with our educational constitution. "
                "Respond with 'VALID' if it complies, or 'INVALID: [reason]' if it doesn't.\n\n"
                f"User input: {message.content}\n\n"
                "Consider the educational context and evaluate based on these constitutional guidelines:\n\n"
                f"{constitution_text[:2000]}"  # Limit to 2000 chars to avoid token limits
            )
            
            # Run the validation in a background thread
            def validate_input():
                try:
                    logger.info("%s calling LLM provider for validation", self.name)
                    
                    response = self.llm_provider.generate_response(
                        validation_prompt,
                        system=self.system_prompt,
                        max_tokens=150,  # Short response for classification
                        temperature=0.3   # Lower temperature for more consistent results
                    )
                    
                    logger.info("%s received validation response", self.name)
                    return response
                except Exception as e:
                    logger.error("%s error in validation: %s", self.name, str(e))
                    logger.error(traceback.format_exc())
                    raise e
            
            # Submit the validation to the thread pool
            future = self._executor.submit(validate_input)
            
            try:
                # Wait for the result with a timeout
                result = future.result(timeout=30)  # 30-second timeout
                
                # Extract classification and thinking if available
                if isinstance(result, tuple) and len(result) == 2:
                    classification, thinking = result
                else:
                    classification = result
                    thinking = None
                
                logger.info("%s classification result: %s", self.name, classification[:20])
                
                # Process the classification result
                if classification.upper().startswith("VALID"):
                    # Pass through the original message with a new type
                    validated_message = Message(
                        content=message.content,
                        msg_type=MessageType.VALIDATED_INPUT,
                        thinking=thinking,
                        metadata={"classification": "valid"}
                    )
                    logger.info("%s message validated, passing through", self.name)
                    self.send_output(validated_message)
                else:
                    # Extract reason from INVALID [reason]
                    reason_match = re.search(r"INVALID:?\s*(.*)", classification, re.IGNORECASE)
                    reason = reason_match.group(1).strip() if reason_match else "Input violates educational guidelines"
                    
                    # Create rejection message with prescribed text
                    error_message = Message(
                        content=self.rejection_message,  # Use the instance variable
                        msg_type=MessageType.ERROR,
                        thinking=thinking,
                        metadata={
                            "original_content": message.content, 
                            "reason": reason,
                            "classification": "invalid"
                        }
                    )
                    logger.info("%s message rejected: %s", self.name, reason[:50])
                    
                    # Send error message directly to UI component
                    if hasattr(self, 'ui_component'):
                        self.ui_component.process_input(error_message)
                    else:
                        # Fallback if UI reference not available
                        self.send_output(error_message)
                    
                    # Do NOT forward message to Core LLM
                    return
                    
            except concurrent.futures.TimeoutError:
                logger.error("%s validation timed out after 30 seconds", self.name)
                # Create timeout error message
                error_message = Message(
                    content="Input validation timed out. Please try again.",
                    msg_type=MessageType.ERROR
                )
                self.send_output(error_message)
                
        except (ValueError, RuntimeError, ImportError, ConnectionError) as e:
            logger.error("%s error in process_input: %s", self.name, str(e))
            logger.error(traceback.format_exc())
            # Create and send error message
            error_message = Message(
                content=f"Error validating input: {str(e)}",
                msg_type=MessageType.ERROR
            )
            self.send_output(error_message)


class OutputClassifierComponent(LLMComponent):
    """Component that validates LLM output based on a constitution."""
    
    def __init__(self, llm_provider: LLMBaseProvider, 
                constitution_manager: Optional[ConstitutionManager] = None,
                constitution_name: str = "output-classifier-constitution", 
                name: str = "OutputClassifier"):
        """Initialize the output classifier component.
        
        Args:
            llm_provider: The LLM provider to use
            constitution_manager: Manager for loading constitutions
            constitution_name: Name of the constitution file to use
            name: Component name
        """
        super().__init__(name)
        self.llm_provider = llm_provider
        self.constitution_manager = constitution_manager or ConstitutionManager()
        self.constitution_name = constitution_name
        
        # Generate the system prompt from the constitution
        self.system_prompt = self.constitution_manager.get_system_prompt(self.constitution_name)
        
        # Create a thread pool for API calls
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Standard rejection message for educational setting
        self.rejection_message = "I apologize, but I can't provide that response as it may not meet our educational standards."
        
        logger.info("%s initialized with constitution: %s", self.name, self.constitution_name)
    
    def process_input(self, message: Message) -> None:
        """Process and validate LLM output according to the constitution.
        
        Args:
            message: The message to process
        """
        # Only process core response messages
        if message.type != MessageType.CORE_RESPONSE:
            logger.info("%s ignoring message with type: %s", self.name, message.type)
            self.send_output(message)  # Pass through other message types
            return
        
        try:
            self.send_status("Validating output...")
            logger.info("%s validating output: %s", self.name, message.content[:50])
            
            # Load the full constitution for context
            constitution_text = self.constitution_manager.load_constitution(self.constitution_name)
            if not constitution_text:
                logger.warning("%s failed to load constitution, passing message through", self.name)
                self.send_output(message)  # Pass through if constitution not available
                return
            
            # Prepare the validation prompt
            validation_prompt = (
                "Your task is to evaluate if the following AI response complies with our educational constitution. "
                "Respond with 'VALID' if it complies, or 'INVALID: [reason]' if it doesn't.\n\n"
                f"AI response: {message.content}\n\n"
                "Consider the educational context and evaluate based on these constitutional guidelines:\n\n"
                f"{constitution_text[:2000]}"  # Limit to 2000 chars to avoid token limits
            )
            
            # Run the validation in a background thread
            def validate_output():
                try:
                    logger.info("%s calling LLM provider for validation", self.name)
                    response = self.llm_provider.generate_response(
                        validation_prompt,
                        system=self.system_prompt,
                        max_tokens=150,  # Short response for classification
                        temperature=0.3   # Lower temperature for more consistent results
                    )
                    logger.info("%s received validation response", self.name)
                    return response
                except Exception as e:
                    logger.error("%s error in validation: %s", self.name, str(e))
                    logger.error(traceback.format_exc())
                    raise e
            
            # Submit the validation to the thread pool
            future = self._executor.submit(validate_output)
            
            try:
                # Wait for the result with a timeout
                result = future.result(timeout=30)  # 30-second timeout
                
                # Extract classification and thinking if available
                if isinstance(result, tuple) and len(result) == 2:
                    classification, thinking = result
                else:
                    classification = result
                    thinking = None
                
                logger.info("%s classification result: %s", self.name, classification[:20])
                
                # Process the classification result
                if classification.upper().startswith("VALID"):
                    # Pass through the original message with a new type
                    validated_message = Message(
                        content=message.content,
                        msg_type=MessageType.VALIDATED_OUTPUT,
                        thinking=message.thinking,
                        metadata={
                            "classification": "valid",
                            "validation_thinking": thinking
                        }
                    )
                    logger.info("%s message validated, passing through", self.name)
                    self.send_output(validated_message)
                else:
                    # Extract reason from INVALID [reason]
                    reason_match = re.search(r"INVALID:?\s*(.*)", classification, re.IGNORECASE)
                    reason = reason_match.group(1).strip() if reason_match else "Output doesn't meet educational guidelines"
                    
                    # Create rejection message with prescribed text
                    error_message = Message(
                        content=self.rejection_message,  # Use the instance variable
                        msg_type=MessageType.ERROR,
                        thinking=thinking,
                        metadata={
                            "original_content": message.content, 
                            "original_thinking": message.thinking,
                            "reason": reason,
                            "classification": "invalid"
                        }
                    )
                    logger.info("%s message rejected: %s", self.name, reason[:50])
                    
                    # Send error message directly to UI component
                    if hasattr(self, 'ui_component'):
                        self.ui_component.process_input(error_message)
                    else:
                        # Fallback if UI reference not available
                        self.send_output(error_message)
                    
                    # Do NOT forward message to chat UI
                    return
                    
            except concurrent.futures.TimeoutError:
                logger.error("%s validation timed out after 30 seconds", self.name)
                # Create timeout error message
                error_message = Message(
                    content="Output validation timed out. Please try again.",
                    msg_type=MessageType.ERROR
                )
                self.send_output(error_message)
                
        except (ValueError, RuntimeError, ImportError, ConnectionError) as e:
            logger.error("%s error in process_input: %s", self.name, str(e))
            logger.error(traceback.format_exc())
            # Create and send error message
            error_message = Message(
                content=f"Error validating output: {str(e)}",
                msg_type=MessageType.ERROR
            )
            self.send_output(error_message)

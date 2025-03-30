"""
LLM provider implementations for REMOTE application (Synchronous version).
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name, unnecessary-pass

from abc import ABC, abstractmethod
import logging
import traceback
import concurrent.futures
from typing import Optional, Union, Tuple
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import anthropic
    HAS_ANTHROPIC = True
    logger.info("Anthropic library imported successfully")
except ImportError:
    HAS_ANTHROPIC = False
    logger.error("Failed to import anthropic library - make sure it's installed")

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class LLMBaseProvider(ABC):
    """Base class for LLM provider integrations."""
    
    @abstractmethod
    def generate_response(self, 
                         prompt: str, 
                         **kwargs) -> Union[str, Tuple[str, Optional[str]]]:
        """Generate a response from the LLM.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional arguments for the LLM
            
        Returns:
            Either a response string, or a tuple of (response, thinking)
        """
        pass

class AnthropicProvider:
    """
    AnthropicProvider implementation with proper thinking tags support and token handling.
    """
    
    def __init__(self, api_key: str, model: str = "claude-3-7-sonnet-20250219"):
        """Initialize the Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-7-sonnet-20250219)
        """
        self.api_key = api_key
        self.model = model
        self._thinking_enabled = False
        self._thinking_budget = 4000  #Budget that works with default max_tokens
        self._client = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Verify the API key is not empty
        if not api_key:
            logger.error("Empty API key provided to AnthropicProvider")
            raise ValueError("Anthropic API key cannot be empty")
            
        logger.info("AnthropicProvider initialized with model: %s", model)
        logger.info("API key length: %d characters", len(api_key))
    
    @property
    def client(self):
        """Lazy-load the Anthropic client to avoid import overhead if not used."""
        if self._client is None:
            if not HAS_ANTHROPIC:
                error_msg = (
                    "The anthropic package is required. "
                    "Install it with: pip install anthropic"
                )
                logger.error(error_msg)
                raise ImportError(error_msg)
            try:
                self._client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("Initialized Anthropic client with model %s", self.model)
            except Exception as e:
                logger.error("Failed to initialize Anthropic client: %s", str(e))
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Failed to initialize Anthropic client: {str(e)}") from e
                
        return self._client
    
    def enable_thinking(self, budget_tokens: int = 4000) -> None:
        """Enable capturing of thinking tags.
        
        Args:
            budget_tokens: Budget for thinking tokens (minimum 1024)
        """
        self._thinking_enabled = True
        self._thinking_budget = max(1024, budget_tokens)  # Ensure minimum budget
        logger.info("Thinking tags enabled with budget of %d tokens", self._thinking_budget)

    def disable_thinking(self) -> None:
        """Disable capturing of thinking tags."""
        self._thinking_enabled = False
        logger.info("Disabled thinking tags")
    
    def _make_api_call(self, api_params):
        """Make the actual API call in a thread-safe manner.
        
        Args:
            api_params: Parameters for the API call
            
        Returns:
            The API response
        """
        try:
            model = api_params.get('model', self.model)
            logger.info("Making API call to Anthropic with model: %s", model)
            start_time = time.time()
            response = self.client.messages.create(**api_params)
            elapsed_time = time.time() - start_time
            logger.info("API call completed in %.2f seconds", elapsed_time)
            return response
        except Exception as e:
            logger.error("Error calling Anthropic API: %s", str(e))
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error calling Anthropic API: {str(e)}") from e
    
    def generate_response(self, 
                        prompt: str, 
                        **kwargs) -> Union[str, Tuple[str, Optional[str]]]:
        """Generate a response using Anthropic Claude with optional thinking.
        
        This method is synchronous but uses a thread pool to avoid blocking.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional arguments for Claude
            
        Returns:
            Either response text, or tuple of (response, thinking)
        """
        try:
            logger.info("Generating response for prompt: %s", prompt[:50])
            
            # Prepare the messages format
            messages = kwargs.get('messages', [{"role": "user", "content": prompt}])
            
            # If no messages were provided but a system message was,
            # use the system message with the prompt
            system = kwargs.get('system', "")
            if 'messages' not in kwargs and system:
                messages = [{"role": "user", "content": prompt}]
            
            # Get max_tokens from kwargs or use default
            max_tokens = kwargs.get('max_tokens', 4096)
            
            # Get temperature - start with user's preference or default
            temperature = kwargs.get('temperature', 0.7)
            
            # Prepare API parameters
            api_params = {
                "model": kwargs.get('model', self.model),
                "messages": messages,
            }
            
            # Add system message if provided
            if system:
                api_params["system"] = system
                logger.info("Using system prompt: %s", system[:50])
            
            # Add thinking parameter if enabled and adjust other parameters accordingly
            if self._thinking_enabled:
                # When thinking is enabled, temperature MUST be 1.0
                temperature = 1.0
                logger.info("Setting temperature to 1.0 as required when thinking is enabled")
                
                # Ensure max_tokens is greater than thinking budget
                if max_tokens <= self._thinking_budget:
                    max_tokens = self._thinking_budget + 1024  # Add buffer for response
                    logger.info(
                        "Increased max_tokens to %d to accommodate thinking budget",
                        max_tokens
                    )
                
                api_params["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": self._thinking_budget
                }
                logger.info("Thinking enabled with budget of %d tokens", self._thinking_budget)
            
            # Add max_tokens and temperature after possibly adjusting them
            api_params["max_tokens"] = max_tokens
            api_params["temperature"] = temperature
            
            # Log the API call parameters (exclude messages for brevity)
            log_params = {k: v for k, v in api_params.items() if k != 'messages'}
            logger.info("Calling Anthropic API with params: %s", log_params)
            
            # Run API call in a separate thread to avoid blocking
            logger.info("Submitting API call to thread pool")
            future = self._executor.submit(self._make_api_call, api_params)
            
            try:
                # Wait for the API call to complete with a timeout
                logger.info("Waiting for API response (with timeout)")
                message = future.result(timeout=60)  # 60-second timeout
                logger.info("Received response from Anthropic API")
            except concurrent.futures.TimeoutError as exc:
                logger.error("API call timed out after 60 seconds")
                raise TimeoutError("Anthropic API call timed out after 60 seconds") from exc
            
            # Extract response and thinking
            try:
                # Initialize variables
                response_text = None
                thinking_text = None
                
                # Process each content block based on type
                for content_block in message.content:
                    if hasattr(content_block, 'type'):
                        if content_block.type == 'text' and hasattr(content_block, 'text'):
                            response_text = content_block.text
                            logger.info("Extracted text response: %s", response_text[:50])
                        elif (content_block.type == 'thinking' and 
                              hasattr(content_block, 'thinking')):
                            thinking_text = content_block.thinking
                            logger.info("Extracted thinking (%d chars)", len(thinking_text))
                
                # Make sure we have a response text
                if not response_text:
                    raise ValueError("No text response found in API result")
                
                # Return response with thinking if available
                if thinking_text:
                    return (response_text, thinking_text)
                else:
                    return response_text
                
            except (IndexError, AttributeError) as e:
                logger.error("Error extracting response from API result: %s", str(e))
                logger.error("API response structure: %s", str(message))
                raise ValueError(f"Could not extract response from API result: {str(e)}") from e
            
        except (ValueError, RuntimeError, ImportError, TimeoutError) as exc:
            logger.error("Error generating response from Anthropic: %s", str(exc))
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error generating response from Anthropic: {str(exc)}") from exc

class OpenAIProvider(LLMBaseProvider):
    """OpenAI API provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """Initialize the OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4)
        """
        self.api_key = api_key
        self.model = model
        self._client = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
    @property
    def client(self):
        """Lazy-load the OpenAI client to avoid import overhead if not used."""
        if self._client is None:
            if not HAS_OPENAI:
                raise ImportError(
                    "The openai package is required. Install it with: pip install openai"
                )
            self._client = openai.OpenAI(api_key=self.api_key)
            logger.info("Initialized OpenAI client with model %s", self.model)
        return self._client
    
    def generate_response(self, 
                         prompt: str, 
                         **kwargs) -> str:
        """Generate a response using OpenAI.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional arguments for the model
            
        Returns:
            The generated response text
        """
        try:
            # Prepare the messages format
            messages = kwargs.get('messages', [])
            if not messages:
                system_content = kwargs.get('system', "You are a helpful assistant.")
                messages = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ]
            
            # Define the API call function
            def make_api_call():
                return self.client.chat.completions.create(
                    model=kwargs.get('model', self.model),
                    messages=messages,
                    max_tokens=kwargs.get('max_tokens', 1024),
                    temperature=kwargs.get('temperature', 0.7)
                )
            
            # Run API call in a separate thread
            future = self._executor.submit(make_api_call)
            
            try:
                # Wait for result with a timeout
                response = future.result(timeout=60)
            except concurrent.futures.TimeoutError as exc:
                logger.error("OpenAI API call timed out after 60 seconds")
                raise TimeoutError("OpenAI API call timed out after 60 seconds") from exc
            
            return response.choices[0].message.content
            
        except (ValueError, RuntimeError, ImportError, TimeoutError) as exc:
            logger.error("Error generating response from OpenAI: %s", str(exc))
            raise RuntimeError(f"Error generating response from OpenAI: {str(exc)}") from exc

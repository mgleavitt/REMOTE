"""
LLM provider implementations for REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name, unnecessary-pass

from abc import ABC, abstractmethod
import logging
import traceback
from typing import Optional, Union, Tuple

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
    async def generate_response(self, 
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
    """Anthropic Claude API provider implementation."""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        """Initialize the Anthropic provider."""
        self.api_key = api_key
        self.model = model
        self._thinking_enabled = False
        self._thinking_length = 0
        self._client = None
        
        logger.info("AnthropicProvider initialized with model: %s", model)
        logger.info("API key length: %d characters", len(api_key))
    
    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            if not HAS_ANTHROPIC:
                error_msg = "The anthropic package is required. Install it with: pip install anthropic"
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
    
    def enable_thinking(self, max_thinking_length: int = 4000) -> None:
        """Enable capturing of thinking tags."""
        self._thinking_enabled = True
        self._thinking_length = max_thinking_length
        logger.info("Enabled thinking tags with max length %s", max_thinking_length)

    def disable_thinking(self) -> None:
        """Disable capturing of thinking tags."""
        self._thinking_enabled = False
        self._thinking_length = 0
        logger.info("Disabled thinking tags")
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a response using Anthropic Claude.
        
        This is marked as async for interface compatibility but uses
        synchronous API calls under the hood.
        """
        try:
            logger.info("Starting generate_response with prompt: %s", prompt[:50])
            
            # Prepare messages
            system = kwargs.get('system', "")
            messages = [{"role": "user", "content": prompt}]
            
            # Log parameters
            logger.info("Using system prompt: %s", system[:50] if system else "None")
            logger.info("Using model: %s", self.model)
            
            # Simple direct API call for debugging
            try:
                logger.info("Making API call to Anthropic...")
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=kwargs.get('max_tokens', 1024),
                    temperature=kwargs.get('temperature', 0.7),
                    system=system,
                    messages=messages
                )
                logger.info("API call completed successfully")
            except Exception as e:
                logger.error("API call failed: %s", str(e))
                logger.error(traceback.format_exc())
                raise RuntimeError(f"API call failed: {str(e)}") from e
            
            # Extract text from response
            try:
                logger.info("Extracting text from response")
                logger.info("Response type: %s", type(response))
                logger.info("Response structure: %s", str(response)[:100])
                
                response_text = response.content[0].text
                logger.info("Extracted response text: %s", response_text[:50])
                return response_text
            except (IndexError, AttributeError) as e:
                logger.error("Failed to extract text from response: %s", str(e))
                logger.error("Response structure: %s", str(response))
                raise ValueError(f"Failed to extract text from response: {str(e)}") from e
                
        except Exception as e:
            logger.error("Error in generate_response: %s", str(e))
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Error generating response: {str(e)}") from e

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
    
    async def generate_response(self, 
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
            
            # Generate response
            response = self.client.chat.completions.create(
                model=kwargs.get('model', self.model),
                messages=messages,
                max_tokens=kwargs.get('max_tokens', 1024),
                temperature=kwargs.get('temperature', 0.7)
            )
            
            return response.choices[0].message.content
            
        except (ValueError, RuntimeError, ImportError) as exc:
            logger.error("Error generating response from OpenAI: %s", str(exc))
            raise RuntimeError(f"Error generating response from OpenAI: {str(exc)}") from exc

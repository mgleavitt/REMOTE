"""
LLM provider implementations for REMOTE application.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

from abc import ABC, abstractmethod
import logging
from typing import Optional, Union, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

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


class AnthropicProvider(LLMBaseProvider):
    """Anthropic Claude API provider implementation with thinking support."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        """Initialize the Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-sonnet-20240229)
        """
        self.api_key = api_key
        self.model = model
        self._thinking_enabled = False
        self._thinking_length = 0
        self._client = None
    
    @property
    def client(self):
        """Lazy-load the Anthropic client to avoid import overhead if not used."""
        if self._client is None:
            if not HAS_ANTHROPIC:
                raise ImportError(
                    "The anthropic package is required. Install it with: pip install anthropic"
                )
            self._client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("Initialized Anthropic client with model %s", self.model)
        return self._client
    
    def enable_thinking(self, max_thinking_length: int = 4000) -> None:
        """Enable capturing of thinking tags.
        
        Args:
            max_thinking_length: Maximum number of characters for thinking
        """
        self._thinking_enabled = True
        self._thinking_length = max_thinking_length
        logger.info("Enabled thinking tags with max length %s", max_thinking_length)

    def disable_thinking(self) -> None:
        """Disable capturing of thinking tags."""
        self._thinking_enabled = False
        self._thinking_length = 0
        logger.info("Disabled thinking tags")
    
    async def generate_response(self, 
                               prompt: str, 
                               **kwargs) -> Union[str, Tuple[str, Optional[str]]]:
        """Generate a response using Anthropic Claude with optional thinking.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional arguments for Claude
            
        Returns:
            Either response text, or tuple of (response, thinking)
        """
        try:
            # Prepare the messages format
            messages = kwargs.get('messages', [{"role": "user", "content": prompt}])
            
            # If no messages were provided but a system message was,
            # use the system message with the prompt
            system = kwargs.get('system', "")
            if 'messages' not in kwargs and system:
                messages = [{"role": "user", "content": prompt}]
            
            # Prepare API parameters
            api_params = {
                "model": kwargs.get('model', self.model),
                "max_tokens": kwargs.get('max_tokens', 1024),
                "temperature": kwargs.get('temperature', 0.7),
                "messages": messages,
            }
            
            # Add system message if provided
            if system:
                api_params["system"] = system
            
            # Add thinking parameters if enabled
            if self._thinking_enabled:
                api_params["max_thinking_length"] = self._thinking_length
                api_params["max_thinking_tokens"] = kwargs.get('max_thinking_tokens', 
                                                             self._thinking_length // 4)
            
            # Generate response
            message = self.client.messages.create(**api_params)
            
            # Extract response and thinking
            response = message.content[0].text
            
            # Check if thinking is available and enabled
            if self._thinking_enabled and hasattr(message, 'thinking'):
                thinking = message.thinking
                return response, thinking
            
            return response
            
        except (ValueError, RuntimeError, ImportError) as exc:
            logger.error("Error generating response from Anthropic: %s", str(exc))
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

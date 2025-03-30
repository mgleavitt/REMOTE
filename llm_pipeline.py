"""
LLM Pipeline for managing the flow of messages through LLM components (Synchronous version).
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, invalid-name

import logging
import os
from typing import Dict, Optional, Callable

from llm_components import LLMComponent
from llm_core_components import (
    CoreLLMComponent, InputClassifierComponent, OutputClassifierComponent
)
from llm_providers import AnthropicProvider, OpenAIProvider, LLMBaseProvider
from llm_ui_components import ChatUIComponent, StatusManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMPipeline:
    """Manager for creating and connecting LLM components."""
    
    def __init__(self):
        """Initialize the LLM pipeline."""
        self.components = {}
        self.providers = {}
        self.status_manager = None
    
    def create_status_manager(self):
        """Create and return a status manager for UI updates."""
        self.status_manager = StatusManager()
        return self.status_manager
    
    def create_anthropic_provider(self, api_key: Optional[str] = None, 
                                model: str = "claude-3-7-sonnet-20250219",
                                enable_thinking: bool = False,
                                thinking_budget: int = 4000) -> AnthropicProvider:
        """Create an Anthropic provider.
        
        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)
            model: Anthropic model to use
            enable_thinking: Whether to enable thinking tags
            max_thinking_length: Maximum length for thinking output
            
        Returns:
            The initialized provider
        """
        # Get API key from environment if not provided
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "Anthropic API key not provided and ANTHROPIC_API_KEY not found in environment"
                )
        
        # Create the provider
        provider = AnthropicProvider(api_key=api_key, model=model)
        
        # Enable thinking if requested
        if enable_thinking:
            provider.enable_thinking(budget_tokens=thinking_budget)
        
        # Add to providers dictionary
        self.providers["anthropic"] = provider
        return provider
    
    def create_openai_provider(self, api_key: Optional[str] = None,
                             model: str = "gpt-4") -> OpenAIProvider:
        """Create an OpenAI provider.
        
        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if None)
            model: OpenAI model to use
            
        Returns:
            The initialized provider
        """
        # Get API key from environment if not provided
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key not provided and OPENAI_API_KEY not found in environment"
                )
        
        # Create the provider
        provider = OpenAIProvider(api_key=api_key, model=model)
        
        # Add to providers dictionary
        self.providers["openai"] = provider
        return provider
    
    def create_ui_component(self, chat_widget, 
                          status_callback: Optional[Callable] = None) -> ChatUIComponent:
        """Create a UI component connected to an existing ChatWidget.
        
        Args:
            chat_widget: The existing ChatWidget instance
            status_callback: Optional callback for status updates
            
        Returns:
            The initialized UI component
        """
        # Create component
        component = ChatUIComponent(chat_widget, status_callback)
        
        # Add to components dictionary
        self.components["ui"] = component
        return component
    
    def create_core_component(self, provider: LLMBaseProvider,
                           system_prompt: str = "") -> CoreLLMComponent:
        """Create a Core LLM component.
        
        Args:
            provider: The LLM provider to use
            system_prompt: System prompt for the LLM
            
        Returns:
            The initialized Core component
        """
        # Create component
        component = CoreLLMComponent(provider, system_prompt)
        
        # Add to components dictionary
        self.components["core"] = component
        return component
    
    def create_input_classifier(self, provider: LLMBaseProvider,
                             system_prompt: str = "") -> InputClassifierComponent:
        """Create an input classifier component.
        
        Args:
            provider: The LLM provider to use
            system_prompt: System prompt for the classifier
            
        Returns:
            The initialized input classifier component
        """
        # Create component
        component = InputClassifierComponent(provider, system_prompt)
        
        # Add to components dictionary
        self.components["input_classifier"] = component
        return component
    
    def create_output_classifier(self, provider: LLMBaseProvider,
                              system_prompt: str = "") -> OutputClassifierComponent:
        """Create an output classifier component.
        
        Args:
            provider: The LLM provider to use
            system_prompt: System prompt for the classifier
            
        Returns:
            The initialized output classifier component
        """
        # Create component
        component = OutputClassifierComponent(provider, system_prompt)
        
        # Add to components dictionary
        self.components["output_classifier"] = component
        return component
    
    def setup_basic_pipeline(self, chat_widget, 
                          provider: Optional[LLMBaseProvider] = None,
                          system_prompt: str = "") -> Dict[str, LLMComponent]:
        """Set up a basic UI → Core → UI pipeline.
        
        Args:
            chat_widget: The existing ChatWidget instance
            provider: The LLM provider to use (creates Anthropic if None)
            system_prompt: System prompt for the Core LLM
            
        Returns:
            Dictionary of created components
        """
        logger.info("Setting up basic pipeline...")
        
        try:
            # Create status manager if not already created
            if not self.status_manager:
                logger.info("Creating status manager")
                self.status_manager = StatusManager()
            
            # Create provider if not provided
            if provider is None:
                try:
                    logger.info("Creating Anthropic provider")
                    provider = self.create_anthropic_provider(enable_thinking=True)
                    logger.info("Anthropic provider created successfully")
                except (ValueError, ImportError) as e:
                    logger.error("Failed to create Anthropic provider: %s", str(e))
                    raise RuntimeError(f"Failed to create Anthropic provider: {str(e)}") from e
            
            # Create UI component with status manager callback
            logger.info("Creating UI component")
            ui_component = self.create_ui_component(
                chat_widget, 
                status_callback=self.status_manager.update_status
            )
            logger.info("UI component created successfully")
            
            # Create Core component
            logger.info("Creating Core component")
            core_component = self.create_core_component(
                provider,
                system_prompt=system_prompt
            )
            logger.info("Core component created successfully")
            
            # Connect components
            logger.info("Connecting components")
            ui_component.connect_output(core_component)
            core_component.connect_output(ui_component)
            
            # Set status callbacks
            core_component.set_status_callback(self.status_manager.update_status)
            
            logger.info("Basic pipeline setup complete")
            return self.components
            
        except Exception as e:
            logger.error("Error setting up basic pipeline: %s", str(e))
            # Clean up any partially created components
            self.components.clear()
            self.providers.clear()
            raise RuntimeError(f"Failed to set up basic pipeline: {str(e)}") from e
    
    def add_input_classifier(self, 
                           provider: Optional[LLMBaseProvider] = None,
                           system_prompt: str = "") -> Dict[str, LLMComponent]:
        """Add an input classifier to an existing pipeline.
        
        Args:
            provider: The LLM provider to use (uses Anthropic if None)
            system_prompt: System prompt for the classifier
            
        Returns:
            Updated dictionary of components
        """
        # Verify UI and Core components exist
        if "ui" not in self.components or "core" not in self.components:
            raise ValueError("Basic UI → Core pipeline must be set up first")
        
        # Use the existing provider if not specified
        if provider is None:
            if "anthropic" in self.providers:
                provider = self.providers["anthropic"]
            else:
                provider = self.create_anthropic_provider()
        
        # Create input classifier
        input_classifier = self.create_input_classifier(provider, system_prompt)
        
        # Set status callback
        input_classifier.set_status_callback(self.status_manager.update_status)
        
        # Update connections
        ui_component = self.components["ui"]
        core_component = self.components["core"]
        
        # Disconnect direct UI → Core connection
        # Note: This isn't actually needed with our implementation,
        # as it won't cause issues to have multiple connections
        
        # Connect UI → Classifier → Core
        ui_component.connect_output(input_classifier)
        input_classifier.connect_output(core_component)
        
        logger.info("Added input classifier to pipeline")
        return self.components
    
    def add_output_classifier(self, 
                           provider: Optional[LLMBaseProvider] = None,
                           system_prompt: str = "") -> Dict[str, LLMComponent]:
        """Add an output classifier to an existing pipeline.
        
        Args:
            provider: The LLM provider to use (uses Anthropic if None)
            system_prompt: System prompt for the classifier
            
        Returns:
            Updated dictionary of components
        """
        # Verify UI and Core components exist
        if "ui" not in self.components or "core" not in self.components:
            raise ValueError("Basic UI → Core pipeline must be set up first")
        
        # Use the existing provider if not specified
        if provider is None:
            if "anthropic" in self.providers:
                provider = self.providers["anthropic"]
            else:
                provider = self.create_anthropic_provider()
        
        # Create output classifier
        output_classifier = self.create_output_classifier(provider, system_prompt)
        
        # Set status callback
        output_classifier.set_status_callback(self.status_manager.update_status)
        
        # Update connections
        ui_component = self.components["ui"]
        core_component = self.components["core"]
        
        # Disconnect direct Core → UI connection
        # Note: This isn't actually needed with our implementation,
        # as it won't cause issues to have multiple connections
        
        # Connect Core → Classifier → UI
        core_component.connect_output(output_classifier)
        output_classifier.connect_output(ui_component)
        
        logger.info("Added output classifier to pipeline")
        return self.components

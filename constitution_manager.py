"""
Constitution manager for loading and managing constitution files for REMOTE application.
"""
# pylint: disable=no-name-in-module, trailing-whitespace
import os
import re
import logging
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConstitutionManager:
    """Manager for loading and caching constitution files."""
    
    def __init__(self, constitutions_dir: str = None):
        """Initialize the constitution manager.
        
        Args:
            constitutions_dir: Directory containing constitution files
        """
        self.constitutions_dir = constitutions_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "constitutions"
        )
        self._constitutions_cache: Dict[str, str] = {}
        self._principles_cache: Dict[str, List[str]] = {}
        
        # Ensure the constitutions directory exists
        os.makedirs(self.constitutions_dir, exist_ok=True)
        
        logger.info("ConstitutionManager initialized with directory: %s", self.constitutions_dir)
    
    def load_constitution(self, constitution_name: str) -> Optional[str]:
        """Load a constitution from the file system.
        
        Args:
            constitution_name: Name of the constitution file (without extension)
            
        Returns:
            The constitution text, or None if not found
        """
        # Check if already cached
        if constitution_name in self._constitutions_cache:
            logger.info("Returning cached constitution: %s", constitution_name)
            return self._constitutions_cache[constitution_name]
        
        # Build the file path with .md extension
        file_path = os.path.join(self.constitutions_dir, f"{constitution_name}.md")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                constitution_text = file.read()
                
            # Cache the constitution
            self._constitutions_cache[constitution_name] = constitution_text
            logger.info("Loaded constitution: %s", constitution_name)
            return constitution_text
            
        except FileNotFoundError:
            logger.error("Constitution file not found: %s", file_path)
            return None
        except IOError as e:
            logger.error("Error reading constitution file: %s - %s", file_path, str(e))
            return None
    
    def extract_principles(self, constitution_name: str, max_principles: int = 5) -> List[str]:
        """Extract key principles from a constitution.
        
        Args:
            constitution_name: Name of the constitution file
            max_principles: Maximum number of principles to extract
            
        Returns:
            List of key principles, or empty list if not found
        """
        # Check if already cached
        if constitution_name in self._principles_cache:
            logger.info("Returning cached principles for: %s", constitution_name)
            return self._principles_cache[constitution_name]
        
        # Load the constitution if not already cached
        constitution = self.load_constitution(constitution_name)
        if not constitution:
            return []
        
        # Extract principles using regex patterns
        principles = []
        
        # Look for "## Fundamental Principles" or similar sections
        principles_section_match = re.search(
            r"## (?:Fundamental |Key )?Principles\s+(.+?)(?:\n##|\Z)", 
            constitution, 
            re.DOTALL
        )
        
        if principles_section_match:
            section_content = principles_section_match.group(1)
            
            # Extract numbered or bullet points
            principle_matches = re.findall(
                r'\d+\.\s+(.*?)(?:\n\d+\.|\n\n|\Z)',
                section_content,
                re.DOTALL
            )
            if principle_matches:
                principles.extend([p.strip() for p in principle_matches])
            
            # Extract bullet points if no numbered points found
            if not principles:
                principle_matches = re.findall(
                    r'- (.*?)(?:\n-|\n\n|\Z)',
                    section_content,
                    re.DOTALL
                )
                principles.extend([p.strip() for p in principle_matches])
        
        # If no principles found in dedicated section, look for headers
        if not principles:
            principle_matches = re.findall(r'### (\d+\.\s+[^#\n]+)', constitution, re.DOTALL)
            principles.extend([p.strip() for p in principle_matches])
        
        # Limit to max_principles
        principles = principles[:max_principles]
        
        # Cache the principles
        self._principles_cache[constitution_name] = principles
        logger.info("Extracted %d principles from: %s", len(principles), constitution_name)
        
        return principles
    
    def get_system_prompt(self, constitution_name: str) -> str:
        """Generate a system prompt from a constitution."""
        principles = self.extract_principles(constitution_name)
        
        if not principles:
            logger.warning("No principles found for system prompt: %s", constitution_name)
            return "You are a constitutional validator for educational AI safety."
        
        # Create a system prompt with the principles
        system_prompt = (
            "You are a constitutional validator for educational AI safety. "
            "You must evaluate messages according to these key principles:\n\n"
        )
        
        for i, principle in enumerate(principles, 1):
            system_prompt += f"{i}. {principle}\n"
        
        system_prompt += (
            "\nRespond with 'VALID' if the input complies with these principles "
            "or 'INVALID: [reason]' if it doesn't. "
            "IMPORTANT: Your complete response MUST be either just the word 'VALID' or "
            "'INVALID: [reason]'. The reason will be used internally but NEVER shown to users. "
            "The user will only see a standardized message."
        )
        
        return system_prompt

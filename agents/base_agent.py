"""
Base agent class that defines the interface for all agents in the REMOTE application.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseAgent(ABC):
    """Base class for all agents in the REMOTE application."""

    def __init__(self):
        """Initialize the base agent."""
        self._data: List[Dict[str, Any]] = []

    @abstractmethod
    def load_data(self, source: str) -> bool:
        """Load data from the specified source.
        
        Args:
            source: Path to the data source
            
        Returns:
            bool: True if data was loaded successfully, False otherwise
        """
        # pylint: disable=unnecessary-pass
        pass

    def get_data(self) -> List[Dict[str, Any]]:
        """Get all loaded data.
        
        Returns:
            List[Dict[str, Any]]: List of data items
        """
        return self._data

    def clear_data(self) -> None:
        """Clear all loaded data."""
        self._data = []

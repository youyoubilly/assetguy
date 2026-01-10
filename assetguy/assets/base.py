"""Base asset class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class Asset(ABC):
    """Base class for all asset types."""
    
    def __init__(self, path: Path):
        """Initialize asset.
        
        Args:
            path: Path to the asset file
        """
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Asset not found: {path}")
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get asset information.
        
        Returns:
            Dictionary containing asset metadata
        """
        pass
    
    @property
    def exists(self) -> bool:
        """Check if asset file exists."""
        return self.path.exists()
    
    @property
    def size_bytes(self) -> int:
        """Get file size in bytes."""
        return self.path.stat().st_size if self.path.exists() else 0

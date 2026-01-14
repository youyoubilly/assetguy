"""Static image asset class."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from PIL import Image
from .base import Asset


class ImageAsset(Asset):
    """Static image asset with metadata and manipulation capabilities."""
    
    # Supported image formats
    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff', '.tif'}
    
    def __init__(self, path: Path):
        """Initialize image asset.
        
        Args:
            path: Path to image file
        """
        super().__init__(path)
        self._info: Optional[Dict[str, Any]] = None
        self._is_animated_webp: Optional[bool] = None
    
    @classmethod
    def find_all(cls, directory: Path) -> List['ImageAsset']:
        """Recursively find all image files in the directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of ImageAsset instances
        """
        images = []
        directory_path = Path(directory)
        
        for ext in cls.SUPPORTED_FORMATS:
            images.extend(directory_path.rglob(f'*{ext}'))
            images.extend(directory_path.rglob(f'*{ext.upper()}'))
        
        return [cls(img_path) for img_path in sorted(images)]
    
    def get_info(self) -> Dict[str, Any]:
        """Get image information.
        
        Returns:
            Dictionary containing image metadata
        """
        if self._info is not None:
            return self._info.copy()
        
        try:
            with Image.open(self.path) as img:
                width, height = img.size
                file_size = self.size_bytes
                
                self._info = {
                    'width': width,
                    'height': height,
                    'file_size': file_size,
                    'format': img.format,
                    'mode': img.mode,
                }
                
                return self._info.copy()
        except Exception as e:
            raise ValueError(f"Error reading image: {e}")
    
    def is_supported(self) -> bool:
        """Check if image format is supported.
        
        Returns:
            True if format is supported
        """
        return self.path.suffix.lower() in self.SUPPORTED_FORMATS
    
    def is_animated_webp(self) -> bool:
        """Check if WebP file is animated.
        
        Returns:
            True if WebP file is animated, False otherwise
        """
        if self._is_animated_webp is not None:
            return self._is_animated_webp
        
        if self.path.suffix.lower() != '.webp':
            self._is_animated_webp = False
            return False
        
        try:
            with Image.open(self.path) as img:
                # PIL's Image object has is_animated attribute for WebP
                if hasattr(img, 'is_animated'):
                    self._is_animated_webp = img.is_animated
                    return self._is_animated_webp
                
                # Fallback: try to seek to frame 1
                try:
                    img.seek(1)
                    self._is_animated_webp = True
                    return True
                except EOFError:
                    self._is_animated_webp = False
                    return False
        except Exception:
            self._is_animated_webp = False
            return False

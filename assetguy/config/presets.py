"""Preset definitions for different use cases."""

from typing import Dict, Any

# Preset definitions
PRESETS: Dict[str, Dict[str, Any]] = {
    "docs": {
        "width": 800,
        "fps": 10,
        "colors": 128,
        "description": "Optimized for documentation (smaller file size, lower FPS)"
    },
    "web": {
        "width": 1200,
        "fps": 12,
        "colors": 256,
        "description": "Optimized for web use (balanced quality and size)"
    },
    "marketing": {
        "width": 1920,
        "fps": 15,
        "colors": 256,
        "description": "High quality for marketing materials (larger file size)"
    }
}


def get_preset(name: str) -> Dict[str, Any]:
    """Get preset configuration by name.
    
    Args:
        name: Preset name (docs, web, marketing)
        
    Returns:
        Preset configuration dictionary
        
    Raises:
        KeyError: If preset name doesn't exist
    """
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise KeyError(f"Unknown preset '{name}'. Available presets: {available}")
    return PRESETS[name].copy()


def list_presets() -> Dict[str, Dict[str, Any]]:
    """List all available presets.
    
    Returns:
        Dictionary of all presets
    """
    return PRESETS.copy()

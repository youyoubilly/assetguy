"""Unified configuration manager for assetguy."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from ..utils.paths import expand_path


class ConfigManager:
    """Manages user configuration file in ~/.assetguy/config.yaml"""
    
    CONFIG_DIR = Path.home() / ".assetguy"
    CONFIG_FILE = CONFIG_DIR / "config.yaml"
    
    DEFAULT_CONFIG = {
        # GIF defaults
        "gif_default_fps": 10,
        "gif_default_colors": 256,
        "gif_default_width": None,  # None means keep original
        
        # Image defaults
        "image_default_quality": 95,
        "image_default_format": None,  # None means keep original
        
        # Video defaults (for future video-keyframes integration)
        "video_output_path": None,  # None means use video directory
        "video_threshold": 0.1,
        "video_method": "histogram",
        "video_image_format": "png",
        "video_min_gap": 0.1,
        "video_frame_skip": 5,
        "video_frame_name_pattern": "frame_{number:04d}.{ext}",
        "video_always_capture_first": True,
        "video_jpg_quality": 95,
        
        # General defaults
        "default_preset": None,  # None means no default preset
    }
    
    def __init__(self):
        """Initialize config manager and ensure config file exists."""
        self._config: Optional[Dict[str, Any]] = None
        self._ensure_config_exists()
    
    def _ensure_config_exists(self):
        """Create config directory and default config file if they don't exist."""
        if not self.CONFIG_DIR.exists():
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        if not self.CONFIG_FILE.exists():
            self._write_config(self.DEFAULT_CONFIG.copy())
    
    def _read_config(self) -> Dict[str, Any]:
        """Read configuration from file."""
        if not self.CONFIG_FILE.exists():
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f) or {}
                # Merge with defaults to ensure all keys exist
                merged = self.DEFAULT_CONFIG.copy()
                merged.update(config)
                return merged
        except Exception as e:
            print(f"Warning: Could not read config file: {e}")
            return self.DEFAULT_CONFIG.copy()
    
    def _write_config(self, config: Dict[str, Any]):
        """Write configuration to file."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise Exception(f"Could not write config file: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        if self._config is None:
            self._config = self._read_config()
        return self._config.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a specific config value."""
        config = self.get_config()
        return config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a config value and save to file."""
        config = self.get_config()
        
        # Validate value based on key
        if key in ["gif_default_fps", "video_min_gap"]:
            value = float(value)
            if value < 0:
                raise ValueError(f"{key} must be >= 0")
        elif key in ["gif_default_colors", "video_frame_skip", "image_default_quality", "video_jpg_quality"]:
            value = int(value)
            if key in ["image_default_quality", "video_jpg_quality"]:
                if not 1 <= value <= 100:
                    raise ValueError(f"{key} must be between 1 and 100")
            elif key in ["gif_default_colors"]:
                if value < 2 or value > 256:
                    raise ValueError(f"{key} must be between 2 and 256")
            elif key == "video_frame_skip":
                if value < 1:
                    raise ValueError(f"{key} must be >= 1")
        elif key == "video_threshold":
            value = float(value)
            if not 0.0 <= value <= 1.0:
                raise ValueError("video_threshold must be between 0.0 and 1.0")
        elif key == "video_method":
            if value not in ["ssim", "histogram", "pixel_diff", "combined"]:
                raise ValueError("video_method must be one of: ssim, histogram, pixel_diff, combined")
        elif key in ["video_image_format", "image_default_format"]:
            if value is not None and value not in ["png", "jpg", "jpeg", "webp"]:
                raise ValueError(f"{key} must be one of: png, jpg, jpeg, webp, or None")
        elif key in ["video_always_capture_first"]:
            value = bool(value) if not isinstance(value, bool) else value
        elif key in ["gif_default_width", "video_output_path", "default_preset"]:
            # Expand paths if provided
            if value is not None and value != "":
                if key == "video_output_path":
                    value = str(expand_path(value) or value)
                else:
                    value = value  # Keep as-is for width and preset
        
        config[key] = value
        self._write_config(config)
        self._config = config
    
    def reset(self):
        """Reset config to defaults."""
        self._write_config(self.DEFAULT_CONFIG.copy())
        self._config = None
    
    def get_config_path(self) -> str:
        """Get the path to the config file."""
        return str(self.CONFIG_FILE)

"""Unified asset inspection operations."""

from pathlib import Path
from typing import Dict, Any, Optional

from ..assets.gif import GifAsset
from ..assets.image import ImageAsset
from ..assets.video import VideoAsset
from ..utils.formatting import format_file_size


def detect_asset_type(path: Path) -> Optional[str]:
    """Detect asset type from file path.
    
    Args:
        path: Path to asset file
        
    Returns:
        Asset type ('gif', 'image', 'video') or None if unknown
    """
    suffix = path.suffix.lower()
    
    if suffix == '.gif':
        return 'gif'
    elif suffix in ImageAsset.SUPPORTED_FORMATS:
        return 'image'
    elif suffix in {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}:
        return 'video'
    
    return None


def inspect_asset(path: Path) -> Dict[str, Any]:
    """Inspect an asset and return its information.
    
    Args:
        path: Path to asset file
        
    Returns:
        Dictionary containing asset information
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Asset not found: {path}")
    
    asset_type = detect_asset_type(path)
    
    if asset_type == 'gif':
        asset = GifAsset(path)
        info = asset.get_info()
        if not info:
            # Check if ImageMagick is available
            from ..tools.detector import get_imagemagick_command
            magick_cmd = get_imagemagick_command()
            if not magick_cmd:
                raise ValueError(
                    f"Could not read GIF information from {path}. "
                    "ImageMagick is required but not found. "
                    "Please install ImageMagick:\n"
                    "  macOS: brew install imagemagick\n"
                    "  Ubuntu/Debian: sudo apt-get install imagemagick\n"
                    "  Windows: Download from https://imagemagick.org/script/download.php"
                )
            else:
                raise ValueError(
                    f"Could not read GIF information from {path}. "
                    f"ImageMagick command '{magick_cmd}' is available but failed to read the file. "
                    "The file may be corrupted or in an unsupported format."
                )
        
        return {
            'type': 'gif',
            'path': str(path),
            'size_bytes': asset.size_bytes,
            'size_formatted': format_file_size(asset.size_bytes),
            'width': info['width'],
            'height': info['height'],
            'frames': info['frames'],
            'fps': info['fps'],
            'duration': info['duration'],
            'colors': info['colors'],
        }
    
    elif asset_type == 'image':
        asset = ImageAsset(path)
        info = asset.get_info()
        
        return {
            'type': 'image',
            'path': str(path),
            'size_bytes': asset.size_bytes,
            'size_formatted': format_file_size(asset.size_bytes),
            'width': info['width'],
            'height': info['height'],
            'format': info['format'],
            'mode': info['mode'],
        }
    
    elif asset_type == 'video':
        asset = VideoAsset(path)
        info = asset.get_info()
        if not info:
            # Check if FFmpeg is available
            from ..tools.detector import check_ffmpeg
            ffmpeg_available, _ = check_ffmpeg()
            if not ffmpeg_available:
                raise ValueError(
                    f"Could not read video information from {path}. "
                    "FFmpeg is required but not found. "
                    "Please install FFmpeg:\n"
                    "  macOS: brew install ffmpeg\n"
                    "  Ubuntu/Debian: sudo apt-get install ffmpeg\n"
                    "  Windows: Download from https://ffmpeg.org/download.html"
                )
            else:
                raise ValueError(
                    f"Could not read video information from {path}. "
                    "FFmpeg is available but failed to read the file. "
                    "The file may be corrupted or in an unsupported format."
                )
        
        return {
            'type': 'video',
            'path': str(path),
            'size_bytes': asset.size_bytes,
            'size_formatted': format_file_size(asset.size_bytes),
            'width': info['width'],
            'height': info['height'],
            'duration': info['duration'],
            'fps': info['fps'],
            'codec': info['codec'],
            'bitrate_kbps': info['bitrate_kbps'],
            'frame_count': info['frame_count'],
        }
    
    else:
        raise ValueError(f"Unknown or unsupported asset type: {path.suffix}")


def print_inspection(info: Dict[str, Any]):
    """Print formatted asset inspection information.
    
    Args:
        info: Inspection dictionary from inspect_asset()
    """
    print("\n" + "=" * 60)
    print(f"📊 Asset Information: {info['path']}")
    print("=" * 60)
    
    print(f"Type: {info['type'].upper()}")
    print(f"File Size: {info['size_formatted']} ({info['size_bytes']:,} bytes)")
    
    if info['type'] == 'gif':
        print(f"Dimensions (Width × Height): {info['width']} × {info['height']} px")
        print(f"Frames: {info['frames']}")
        print(f"FPS: {info['fps']:.2f}")
        print(f"Duration: {info['duration']:.2f} seconds")
        print(f"Colors (approx): {info['colors']}")
    
    elif info['type'] == 'image':
        print(f"Dimensions (Width × Height): {info['width']} × {info['height']} px")
        print(f"Format: {info['format']}")
        print(f"Mode: {info['mode']}")
    
    elif info['type'] == 'video':
        print(f"Dimensions (Width × Height): {info['width']} × {info['height']} px")
        print(f"Duration: {info['duration']:.2f} seconds")
        print(f"FPS: {info['fps']:.2f}")
        print(f"Codec: {info['codec']}")
        print(f"Bitrate: {info['bitrate_kbps']:.0f} kbps")
        print(f"Frames: {info['frame_count']}")
    
    print("=" * 60 + "\n")

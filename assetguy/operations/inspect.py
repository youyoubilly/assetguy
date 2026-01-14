"""Unified asset inspection operations."""

import json
import subprocess
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
        
        # Check if this is an animated WebP
        if path.suffix.lower() == '.webp' and asset.is_animated_webp():
            # Use ffprobe to get animation metadata
            from ..tools.detector import check_ffmpeg
            ffmpeg_available, _ = check_ffmpeg()
            
            if not ffmpeg_available:
                # Fallback to basic image info if FFmpeg not available
                return {
                    'type': 'image',
                    'path': str(path),
                    'size_bytes': asset.size_bytes,
                    'size_formatted': format_file_size(asset.size_bytes),
                    'width': info['width'],
                    'height': info['height'],
                    'format': info['format'],
                    'mode': info['mode'],
                    'is_animated': True,
                    'note': 'FFmpeg required for full animated WebP metadata'
                }
            
            # Get animated WebP metadata using ffprobe and PIL
            try:
                # First, use PIL to count frames
                from PIL import Image
                frame_count = 0
                with Image.open(path) as img:
                    while True:
                        try:
                            img.seek(frame_count)
                            frame_count += 1
                        except EOFError:
                            break  # Reached end of frames
                
                # Try to get FPS and duration from ffprobe
                result = subprocess.run(
                    [
                        "ffprobe",
                        "-v", "quiet",
                        "-print_format", "json",
                        "-show_format",
                        "-show_streams",
                        str(path)
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                data = json.loads(result.stdout)
                
                # Find video stream
                video_stream = None
                for stream in data.get("streams", []):
                    if stream.get("codec_type") == "video":
                        video_stream = stream
                        break
                
                fps = 0
                duration = 0
                
                if video_stream:
                    # Extract FPS
                    fps_str = video_stream.get("r_frame_rate", "0/1")
                    if "/" in fps_str:
                        num, den = map(int, fps_str.split("/"))
                        fps = num / den if den > 0 else 0
                    else:
                        fps = float(fps_str) if fps_str else 0
                    
                    # Try to get duration from stream first, then format
                    duration = float(video_stream.get("duration", 0))
                    if duration == 0:
                        duration = float(data.get("format", {}).get("duration", 0))
                
                # If duration is still 0 but we have frame count and FPS, calculate it
                if duration == 0 and frame_count > 0 and fps > 0:
                    duration = frame_count / fps
                # If FPS is 0 but we have duration and frame count, calculate FPS
                elif fps == 0 and frame_count > 0 and duration > 0:
                    fps = frame_count / duration
                # If both are 0, try to get frame count from ffprobe
                elif frame_count == 0:
                    if video_stream:
                        frame_count = int(video_stream.get("nb_frames", 0))
                    if frame_count == 0 and fps > 0 and duration > 0:
                        frame_count = int(fps * duration)
                
                return {
                    'type': 'image',
                    'path': str(path),
                    'size_bytes': asset.size_bytes,
                    'size_formatted': format_file_size(asset.size_bytes),
                    'width': info['width'],
                    'height': info['height'],
                    'format': info['format'],
                    'mode': info['mode'],
                    'is_animated': True,
                    'frames': frame_count,
                    'fps': fps,
                    'duration': duration,
                }
            except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError):
                # If ffprobe fails, return basic info with animation flag
                return {
                    'type': 'image',
                    'path': str(path),
                    'size_bytes': asset.size_bytes,
                    'size_formatted': format_file_size(asset.size_bytes),
                    'width': info['width'],
                    'height': info['height'],
                    'format': info['format'],
                    'mode': info['mode'],
                    'is_animated': True,
                }
        
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
        if info.get('is_animated'):
            print(f"Animated: Yes")
            if 'frames' in info:
                print(f"Frames: {info['frames']}")
            if 'fps' in info:
                print(f"FPS: {info['fps']:.2f}")
            if 'duration' in info:
                print(f"Duration: {info['duration']:.2f} seconds")
            if 'note' in info:
                print(f"Note: {info['note']}")
    
    elif info['type'] == 'video':
        print(f"Dimensions (Width × Height): {info['width']} × {info['height']} px")
        print(f"Duration: {info['duration']:.2f} seconds")
        print(f"FPS: {info['fps']:.2f}")
        print(f"Codec: {info['codec']}")
        print(f"Bitrate: {info['bitrate_kbps']:.0f} kbps")
        print(f"Frames: {info['frame_count']}")
    
    print("=" * 60 + "\n")

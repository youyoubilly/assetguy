"""Video asset class."""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from .base import Asset
from ..tools.detector import check_ffmpeg


class VideoAsset(Asset):
    """Video asset with metadata and manipulation capabilities."""
    
    def __init__(self, path: Path):
        """Initialize video asset.
        
        Args:
            path: Path to video file
        """
        super().__init__(path)
        self._info: Optional[Dict[str, Any]] = None
    
    def get_info(self) -> Dict[str, Any]:
        """Extract video information using ffprobe.
        
        Returns:
            Dictionary containing video metadata, or None if extraction fails
        """
        if self._info is not None:
            return self._info.copy()
        
        # Check if ffprobe is available
        ffmpeg_available, _ = check_ffmpeg()
        if not ffmpeg_available:
            return None
        
        try:
            # Use ffprobe to get video information
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(self.path)
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
            
            if not video_stream:
                return None
            
            # Extract dimensions
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            
            # Extract FPS
            fps_str = video_stream.get("r_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = map(int, fps_str.split("/"))
                fps = num / den if den > 0 else 0
            else:
                fps = float(fps_str) if fps_str else 0
            
            # Extract duration
            duration = float(data.get("format", {}).get("duration", 0))
            
            # Extract codec
            codec = video_stream.get("codec_name", "unknown")
            
            # Extract bitrate
            bitrate_str = data.get("format", {}).get("bit_rate", "0")
            bitrate = int(bitrate_str) if bitrate_str else 0
            bitrate_kbps = bitrate / 1000 if bitrate > 0 else 0
            
            # Get frame count if available
            frame_count = int(video_stream.get("nb_frames", 0))
            if frame_count == 0 and fps > 0 and duration > 0:
                frame_count = int(fps * duration)
            
            self._info = {
                'width': width,
                'height': height,
                'fps': fps,
                'duration': duration,
                'codec': codec,
                'bitrate': bitrate,
                'bitrate_kbps': bitrate_kbps,
                'frame_count': frame_count,
            }
            
            return self._info.copy()
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError, KeyError) as e:
            return None

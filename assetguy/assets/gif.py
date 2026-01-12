"""GIF asset class."""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from .base import Asset
from ..tools.detector import get_imagemagick_command
from ..tools.executor import run
from ..utils.formatting import filesize_mb


class GifAsset(Asset):
    """GIF asset with metadata and manipulation capabilities."""
    
    def __init__(self, path: Path):
        """Initialize GIF asset.
        
        Args:
            path: Path to GIF file
        """
        super().__init__(path)
        self._info: Optional[Dict[str, Any]] = None
    
    def get_info(self) -> Dict[str, Any]:
        """Extract GIF information using ImageMagick identify command.
        
        Returns:
            Dictionary containing GIF metadata, or None if extraction fails
        """
        if self._info is not None:
            return self._info.copy()
        
        magick_cmd = get_imagemagick_command()
        if not magick_cmd:
            return None
        
        try:
            # Get basic info: dimensions, colors, delay
            result = subprocess.run(
                [magick_cmd, "identify", "-format", "%w %h %k %T\n", str(self.path)],
                capture_output=True,
                text=True,
                check=True
            )
            
            lines = result.stdout.strip().split('\n')
            if not lines or not lines[0]:
                return None
            
            # Parse first frame for dimensions
            first_line = lines[0].split()
            width = int(first_line[0])
            height = int(first_line[1])
            
            # Count frames
            frame_count = len([line for line in lines if line.strip()])
            
            # Extract colors and delays from all frames
            all_colors = []
            delays = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            all_colors.append(int(parts[2]))  # %k (colors) is 3rd field
                        except (ValueError, IndexError):
                            pass
                    if len(parts) >= 4:
                        try:
                            delays.append(int(parts[3]))  # %T (delay) is 4th field
                        except (ValueError, IndexError):
                            pass
            
            # Use max colors across all frames
            if all_colors:
                colors = max(all_colors)
            else:
                colors = int(first_line[2]) if len(first_line) >= 3 else 0
            
            # Validate that delays count matches frame count
            if len(delays) != frame_count:
                if len(delays) < frame_count:
                    last_delay = delays[-1] if delays else 10
                    delays.extend([last_delay] * (frame_count - len(delays)))
                else:
                    delays = delays[:frame_count]
            
            avg_delay = sum(delays) / len(delays) if delays else 0
            fps = round(100 / avg_delay, 2) if avg_delay > 0 else 0
            
            # Calculate total duration in seconds (delays are in centiseconds)
            total_duration = sum(delays) / 100.0 if delays else 0
            
            self._info = {
                'width': width,
                'height': height,
                'colors': colors,
                'frames': frame_count,
                'fps': fps,
                'avg_delay': avg_delay,
                'duration': total_duration,
                'delays': delays
            }
            
            return self._info.copy()
        except (subprocess.CalledProcessError, ValueError, IndexError):
            return None
    
    def time_range_to_frames(self, start_time: float, end_time: Optional[float]) -> Optional[Tuple[int, int]]:
        """Convert time range (in seconds) to frame range.
        
        Args:
            start_time: Start time in seconds (float)
            end_time: End time in seconds (float, or None to mean end of GIF)
        
        Returns:
            Tuple (start_frame, end_frame) or None if invalid
        """
        info = self.get_info()
        if not info:
            return None
        
        delays = info.get('delays', [])
        total_duration = info.get('duration', 0)
        
        if not delays or len(delays) == 0:
            return None
        
        if start_time < 0:
            start_time = 0
        if end_time is None or end_time > total_duration:
            end_time = total_duration
        if start_time >= end_time:
            return None
        
        # Calculate cumulative time for each frame
        cumulative_times = []
        cumulative = 0.0
        for delay in delays:
            cumulative += delay / 100.0
            cumulative_times.append(cumulative)
        
        # Find start frame: first frame that overlaps with start_time
        start_frame = 0
        prev_time = 0.0
        for i, cum_time in enumerate(cumulative_times):
            if cum_time > start_time:
                start_frame = i
                break
            prev_time = cum_time
        
        # Find end frame: last frame that overlaps with end_time
        prev_time = 0.0
        end_frame = len(delays) - 1
        for i, cum_time in enumerate(cumulative_times):
            if prev_time > end_time:
                end_frame = max(0, i - 1)
                break
            prev_time = cum_time
        
        if start_frame > end_frame:
            return None
        
        return (start_frame, end_frame)
    
    def scale_delays_proportionally(self, delays: List[int], target_fps: float) -> List[int]:
        """Scale delays proportionally to achieve target FPS while preserving relative timing.
        
        Args:
            delays: List of frame delays in centiseconds
            target_fps: Target FPS to achieve
        
        Returns:
            List of scaled delays in centiseconds
        """
        if not delays or target_fps <= 0:
            return delays
        
        # Calculate target delay (in centiseconds)
        target_delay = 100 / target_fps
        
        # Calculate original average delay
        original_avg_delay = sum(delays) / len(delays) if delays else target_delay
        
        if original_avg_delay == 0:
            return delays
        
        # Calculate scale factor
        scale_factor = original_avg_delay / target_delay
        
        # Scale each delay proportionally
        scaled_delays = [max(1, round(delay / scale_factor)) for delay in delays]
        
        return scaled_delays
    
    def frame_range_to_time(self, start_frame: int, end_frame: int) -> Optional[Tuple[float, float]]:
        """Convert frame range to time range.
        
        Args:
            start_frame: Start frame index (0-based)
            end_frame: End frame index (0-based, inclusive)
        
        Returns:
            Tuple (start_time, end_time) in seconds, or None if invalid
        """
        info = self.get_info()
        if not info:
            return None
        
        delays = info.get('delays', [])
        total_frames = info.get('frames', 0)
        
        if not delays or total_frames == 0:
            return None
        
        # Validate frame range
        if start_frame < 0 or end_frame >= total_frames or start_frame > end_frame:
            return None
        
        # Calculate start time: sum of delays before start_frame
        start_time = sum(delays[:start_frame]) / 100.0
        
        # Calculate end time: sum of delays up to and including end_frame
        end_time = sum(delays[:end_frame + 1]) / 100.0
        
        return (start_time, end_time)
    
    def frames_to_time_points(self, frame_numbers: List[int]) -> List[float]:
        """Convert frame numbers to time points for splitting.
        
        Args:
            frame_numbers: List of frame indices (0-based)
        
        Returns:
            List of time points in seconds (frame start times)
        """
        info = self.get_info()
        if not info:
            return []
        
        delays = info.get('delays', [])
        total_frames = info.get('frames', 0)
        
        if not delays or total_frames == 0:
            return []
        
        # Build array of frame start times
        # frame_start_times[i] = time when frame i starts
        frame_start_times = [0.0]  # Frame 0 starts at 0
        cumulative = 0.0
        
        # Calculate start time for each subsequent frame
        # Frame i starts after all previous frames' delays
        for delay in delays[:-1]:  # All but last delay
            cumulative += delay / 100.0
            frame_start_times.append(cumulative)
        
        # Convert frame numbers to time points
        time_points = []
        for frame_num in frame_numbers:
            if 0 <= frame_num < len(frame_start_times):
                time_points.append(frame_start_times[frame_num])
        
        return time_points
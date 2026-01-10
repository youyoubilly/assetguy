"""Asset optimization operations."""

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from ..assets.gif import GifAsset
from ..tools.detector import get_imagemagick_command
from ..tools.executor import run
from ..utils.formatting import filesize_mb


def split_gif(
    gif_asset: GifAsset,
    split_points: List[float],
    output_dir: Path,
    width: Optional[int] = None,
    fps: Optional[float] = None,
    fps_mode: str = "normalize",
    colors: Optional[int] = None
) -> List[Path]:
    """Split a GIF at specified time points, creating multiple output files.
    
    Args:
        gif_asset: GifAsset instance
        split_points: List of time points (in seconds) to split at
        output_dir: Directory to save output files
        width: Optional target width for optimization
        fps: Optional target FPS for optimization
        fps_mode: "normalize" (equal delays) or "preserve" (scale delays)
        colors: Optional number of colors for optimization
    
    Returns:
        List of output file paths
    """
    if not split_points:
        return []
    
    magick_cmd = get_imagemagick_command()
    if not magick_cmd:
        raise RuntimeError("ImageMagick not found. Please install ImageMagick first.")
    
    info = gif_asset.get_info()
    if not info:
        raise ValueError("Could not read GIF information")
    
    # Sort and validate split points
    split_points = sorted([float(p) for p in split_points])
    total_duration = info['duration']
    delays = info.get('delays', [])
    
    # Filter out invalid points and add boundaries
    valid_points = [0.0]
    for point in split_points:
        if 0 < point < total_duration:
            valid_points.append(point)
    valid_points.append(total_duration)
    
    # Remove duplicates
    valid_points = sorted(list(set(valid_points)))
    
    if len(valid_points) < 2:
        print("⚠️  Warning: No valid split points. Keeping original GIF.")
        return []
    
    output_files = []
    input_path = gif_asset.path
    input_name = input_path.stem
    input_ext = input_path.suffix
    
    print(f"\n✂️  Splitting GIF into {len(valid_points) - 1} segments...")
    
    for i in range(len(valid_points) - 1):
        start_time = valid_points[i]
        end_time = valid_points[i + 1]
        
        # Convert time range to frame range
        frame_range = gif_asset.time_range_to_frames(start_time, end_time)
        if not frame_range:
            print(f"⚠️  Warning: Could not extract segment {i+1} ({start_time:.2f}-{end_time:.2f}s). Skipping.")
            continue
        
        start_frame, end_frame = frame_range
        
        # Generate output filename
        output_filename = f"{input_name}_part{i+1}{input_ext}"
        output_path = output_dir / output_filename
        
        # Coalesce before extraction to prevent visual corruption with disposal methods
        coalesce_fd, coalesce_file = tempfile.mkstemp(suffix='.gif', prefix='gif_coalesce_')
        os.close(coalesce_fd)
        
        extract_fd, extract_file = tempfile.mkstemp(suffix='.gif', prefix='gif_split_')
        os.close(extract_fd)
        
        try:
            # Step 1: Coalesce all frames
            coalesce_cmd = [magick_cmd, str(input_path), "-coalesce", coalesce_file]
            run(coalesce_cmd)
            
            # Step 2: Extract frame range from coalesced GIF
            extract_cmd = [magick_cmd, f"{coalesce_file}[{start_frame}-{end_frame}]", extract_file]
            run(extract_cmd)
            
            # Step 3: Build optimization command
            opt_cmd = [magick_cmd, extract_file]
            
            # Coalesce again if we need to modify delays (for FPS adjustment)
            if fps:
                opt_cmd += ["-coalesce"]
            
            # Add resize if specified
            if width:
                opt_cmd += ["-resize", f"{width}x"]
            
            # Add FPS adjustment if specified
            if fps:
                if fps_mode == "preserve":
                    # Get delays for this segment
                    segment_delays = delays[start_frame:end_frame+1] if delays else []
                    if segment_delays:
                        scaled_delays = gif_asset.scale_delays_proportionally(segment_delays, fps)
                        # Use average of scaled delays (ImageMagick -set delay sets same for all frames)
                        avg_scaled_delay = int(sum(scaled_delays) / len(scaled_delays)) if scaled_delays else int(100 / fps)
                        opt_cmd += ["-set", "delay", str(avg_scaled_delay)]
                    else:
                        delay = int(100 / fps)
                        opt_cmd += ["-set", "delay", str(delay)]
                else:
                    # Normalize mode: equal delays for all frames
                    delay = int(100 / fps)
                    opt_cmd += ["-set", "delay", str(delay)]
            
            # Add color reduction if specified
            if colors:
                opt_cmd += ["-colors", str(colors)]
            
            # Add optimization and output
            opt_cmd += ["-layers", "Optimize", str(output_path)]
            
            # Run optimization
            run(opt_cmd)
            
            # Clean up temp files
            if os.path.exists(coalesce_file):
                os.remove(coalesce_file)
            if os.path.exists(extract_file):
                os.remove(extract_file)
        except Exception as e:
            print(f"   ✗ Segment {i+1} failed: {e}")
            if os.path.exists(coalesce_file):
                os.remove(coalesce_file)
            if os.path.exists(extract_file):
                os.remove(extract_file)
            continue
        
        output_files.append(output_path)
        segment_duration = end_time - start_time
        print(f"   ✓ Created segment {i+1}: {output_filename} ({start_time:.2f}-{end_time:.2f}s, {segment_duration:.2f}s)")
    
    return output_files

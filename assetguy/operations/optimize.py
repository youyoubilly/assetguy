"""Asset optimization operations."""

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from ..assets.gif import GifAsset
from ..assets.image import ImageAsset
from ..tools.detector import get_imagemagick_command
from ..tools.executor import run
from ..utils.formatting import filesize_mb, format_file_size


def parse_frame_range(input_str: str, max_frames: int) -> Optional[Tuple[int, int]]:
    """Parse frame range input string (e.g., "10-50").
    
    Args:
        input_str: Input string in format "start-end"
        max_frames: Maximum number of frames (for validation)
    
    Returns:
        Tuple (start_frame, end_frame) or None if invalid
    """
    if not input_str or '-' not in input_str:
        return None
    
    try:
        parts = input_str.split('-')
        if len(parts) != 2:
            return None
        
        start = int(parts[0].strip())
        end = int(parts[1].strip())
        
        if start < 0 or end >= max_frames or start > end:
            return None
        
        return (start, end)
    except (ValueError, IndexError):
        return None


def parse_split_frames(input_str: str, max_frames: int) -> Optional[List[int]]:
    """Parse comma-separated frame numbers for splitting.
    
    Args:
        input_str: Input string with comma-separated frame numbers (e.g., "10,50")
        max_frames: Maximum number of frames (for validation)
    
    Returns:
        List of frame numbers or None if invalid
    """
    if not input_str:
        return None
    
    try:
        frame_strs = [p.strip() for p in input_str.split(',') if p.strip()]
        frames = [int(f) for f in frame_strs]
        
        # Validate all frames are in range
        if any(f < 0 or f >= max_frames for f in frames):
            return None
        
        return frames
    except ValueError:
        return None


def parse_time_range(input_str: str, max_duration: float) -> Optional[Tuple[float, float]]:
    """Parse time range input string (e.g., "2.5-5.0").
    
    Args:
        input_str: Input string in format "start-end"
        max_duration: Maximum duration in seconds (for validation)
    
    Returns:
        Tuple (start_time, end_time) or None if invalid
    """
    if not input_str or '-' not in input_str:
        return None
    
    try:
        parts = input_str.split('-')
        if len(parts) != 2:
            return None
        
        start = float(parts[0].strip())
        end = float(parts[1].strip())
        
        if start < 0 or end > max_duration or start >= end:
            return None
        
        return (start, end)
    except (ValueError, IndexError):
        return None


def parse_split_times(input_str: str, max_duration: float) -> Optional[List[float]]:
    """Parse comma-separated time points for splitting.
    
    Args:
        input_str: Input string with comma-separated time points (e.g., "2.5,5.0")
        max_duration: Maximum duration in seconds (for validation)
    
    Returns:
        List of time points or None if invalid
    """
    if not input_str:
        return None
    
    try:
        time_strs = [p.strip() for p in input_str.split(',') if p.strip()]
        times = [float(t) for t in time_strs]
        
        # Validate all times are in range
        if any(t < 0 or t >= max_duration for t in times):
            return None
        
        return times
    except ValueError:
        return None


def parse_split_trim_input(
    input_str: str,
    max_duration: float,
    max_frames: int,
    gif_asset: GifAsset
) -> Optional[Dict[str, Any]]:
    """Parse unified split/trim input that auto-detects operation type.
    
    Examples:
    - "2.5, 3.5" → split at time points
    - "0-2.5, 3.5-4.5" → trim multiple time ranges
    - "f:10, 50" → split at frame points
    - "f:10-50" → trim frame range
    - "2.5" → split at single time point
    - "" → skip operation
    
    Args:
        input_str: Input string to parse
        max_duration: Maximum duration in seconds (for validation)
        max_frames: Maximum number of frames (for validation)
        gif_asset: GifAsset instance for frame-to-time conversion
    
    Returns:
        Dictionary with 'mode' ('split' or 'trim'), 'points' or 'ranges', and 'is_frame' flag,
        or None if input is empty/invalid
    """
    if not input_str or not input_str.strip():
        return None
    
    input_str = input_str.strip()
    
    # Check for frame prefix
    is_frame = input_str.startswith(('f:', 'frame:'))
    if is_frame:
        input_str = input_str.split(':', 1)[1].strip()
        if not input_str:
            return None
    
    # Check for trim mode (contains '-')
    if '-' in input_str:
        # Parse multiple ranges if comma-separated
        parts = [p.strip() for p in input_str.split(',') if p.strip()]
        ranges = []
        
        for part in parts:
            if '-' in part:
                # Parse as range
                if is_frame:
                    range_tuple = parse_frame_range(part, max_frames)
                else:
                    range_tuple = parse_time_range(part, max_duration)
                
                if range_tuple:
                    ranges.append(range_tuple)
        
        if ranges:
            return {
                'mode': 'trim',
                'ranges': ranges,
                'is_frame': is_frame
            }
        else:
            # Invalid ranges
            return None
    
    # Otherwise it's split mode (comma-separated or single number)
    elif ',' in input_str or input_str.strip():
        if is_frame:
            # Parse frame numbers
            points = parse_split_frames(input_str, max_frames)
            if points:
                # Convert frames to time points
                time_points = gif_asset.frames_to_time_points(points)
                if time_points:
                    return {
                        'mode': 'split',
                        'points': time_points,
                        'is_frame': True
                    }
        else:
            # Parse time points
            points = parse_split_times(input_str, max_duration)
            if points:
                return {
                    'mode': 'split',
                    'points': points,
                    'is_frame': False
                }
        
        # Try single number
        try:
            if is_frame:
                single_frame = int(input_str.strip())
                if 0 <= single_frame < max_frames:
                    time_points = gif_asset.frames_to_time_points([single_frame])
                    if time_points:
                        return {
                            'mode': 'split',
                            'points': time_points,
                            'is_frame': True
                        }
            else:
                single_time = float(input_str.strip())
                if 0 <= single_time < max_duration:
                    return {
                        'mode': 'split',
                        'points': [single_time],
                        'is_frame': False
                    }
        except ValueError:
            pass
    
    return None


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


def trim_gif(
    gif_asset: GifAsset,
    output_path: Optional[Path] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    width: Optional[int] = None,
    fps: Optional[float] = None,
    fps_mode: str = "normalize",
    colors: Optional[int] = None
) -> Dict[str, Any]:
    """Trim a GIF to extract a single range (time-based or frame-based).
    
    Args:
        gif_asset: GifAsset instance
        output_path: Optional output path (default: generate from input)
        start_time: Start time in seconds (for time-based trimming)
        end_time: End time in seconds (for time-based trimming)
        start_frame: Start frame index (for frame-based trimming)
        end_frame: End frame index (for frame-based trimming)
        width: Optional target width for optimization
        fps: Optional target FPS for optimization
        fps_mode: "normalize" (equal delays) or "preserve" (scale delays)
        colors: Optional number of colors for optimization
    
    Returns:
        Dictionary with optimization results (from format_optimization_result)
    
    Raises:
        RuntimeError: If ImageMagick not found
        ValueError: If GIF info cannot be read or parameters are invalid
    """
    magick_cmd = get_imagemagick_command()
    if not magick_cmd:
        raise RuntimeError("ImageMagick not found. Please install ImageMagick first.")
    
    info = gif_asset.get_info()
    if not info:
        raise ValueError("Could not read GIF information")
    
    # Determine frame range from time or frame parameters
    frame_range = None
    
    if start_frame is not None and end_frame is not None:
        # Frame-based trimming
        total_frames = info.get('frames', 0)
        if start_frame < 0 or end_frame >= total_frames or start_frame > end_frame:
            raise ValueError(f"Invalid frame range: {start_frame}-{end_frame} (valid: 0-{total_frames-1})")
        frame_range = (start_frame, end_frame)
    elif start_time is not None:
        # Time-based trimming
        frame_range = gif_asset.time_range_to_frames(start_time, end_time)
        if not frame_range:
            raise ValueError(f"Invalid time range: {start_time}-{end_time}")
    else:
        raise ValueError("Must provide either time range (start_time/end_time) or frame range (start_frame/end_frame)")
    
    start_frame, end_frame = frame_range
    
    input_path = gif_asset.path
    input_size = gif_asset.size_bytes
    
    # Generate output path if not provided
    if output_path is None:
        output_path = generate_output_filename(input_path, suffix="_trimmed")
    
    delays = info.get('delays', [])
    
    # Coalesce before extraction to prevent visual corruption with disposal methods
    coalesce_fd, coalesce_file = tempfile.mkstemp(suffix='.gif', prefix='gif_coalesce_')
    os.close(coalesce_fd)
    
    extract_fd, extract_file = tempfile.mkstemp(suffix='.gif', prefix='gif_trim_')
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
                    # Use average of scaled delays
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
        
        # Get output file size
        output_size = output_path.stat().st_size
        
        # Format and return result
        result = format_optimization_result(input_path, output_path, input_size, output_size)
        return result
        
    except Exception as e:
        # Clean up temp files on error
        if os.path.exists(coalesce_file):
            os.remove(coalesce_file)
        if os.path.exists(extract_file):
            os.remove(extract_file)
        raise


def generate_output_filename(input_path: Path, suffix: str = "_optimized") -> Path:
    """Generate output filename for optimized asset.
    
    Args:
        input_path: Path to input file
        suffix: Suffix to add before extension (default: "_optimized")
        
    Returns:
        Path to output file
    """
    stem = input_path.stem
    ext = input_path.suffix
    return input_path.parent / f"{stem}{suffix}{ext}"


def format_optimization_result(
    input_path: Path,
    output_path: Path,
    input_size: int,
    output_size: int
) -> Dict[str, Any]:
    """Format optimization result with file size comparison.
    
    Args:
        input_path: Path to input file
        output_path: Path to output file
        input_size: Input file size in bytes
        output_size: Output file size in bytes
        
    Returns:
        Dictionary with optimization results
    """
    reduction = input_size - output_size
    reduction_percent = (reduction / input_size * 100) if input_size > 0 else 0
    
    return {
        'input_path': str(input_path),
        'output_path': str(output_path),
        'input_size': input_size,
        'input_size_formatted': format_file_size(input_size),
        'output_size': output_size,
        'output_size_formatted': format_file_size(output_size),
        'reduction': reduction,
        'reduction_formatted': format_file_size(reduction),
        'reduction_percent': reduction_percent
    }


def print_optimization_result(result: Dict[str, Any]):
    """Print formatted optimization result.
    
    Args:
        result: Result dictionary from format_optimization_result()
    """
    print("\n" + "=" * 60)
    print("✅ Optimization Complete")
    print("=" * 60)
    print(f"Input:  {result['input_path']}")
    print(f"        {result['input_size_formatted']} ({result['input_size']:,} bytes)")
    print(f"Output: {result['output_path']}")
    print(f"        {result['output_size_formatted']} ({result['output_size']:,} bytes)")
    print(f"\nReduction: {result['reduction_formatted']} ({result['reduction_percent']:.1f}%)")
    print("=" * 60 + "\n")


def optimize_gif(
    gif_asset: GifAsset,
    output_path: Optional[Path] = None,
    width: Optional[int] = None,
    fps: Optional[float] = None,
    fps_mode: str = "normalize",
    colors: Optional[int] = None
) -> Dict[str, Any]:
    """Optimize a GIF file with resize, FPS adjustment, and color reduction.
    
    Args:
        gif_asset: GifAsset instance
        output_path: Optional output path (default: generate from input)
        width: Optional target width in pixels
        fps: Optional target FPS
        fps_mode: "normalize" (equal delays) or "preserve" (scale delays)
        colors: Optional number of colors for optimization
        
    Returns:
        Dictionary with optimization results (from format_optimization_result)
        
    Raises:
        RuntimeError: If ImageMagick not found
        ValueError: If GIF info cannot be read
    """
    magick_cmd = get_imagemagick_command()
    if not magick_cmd:
        raise RuntimeError("ImageMagick not found. Please install ImageMagick first.")
    
    info = gif_asset.get_info()
    if not info:
        raise ValueError("Could not read GIF information")
    
    input_path = gif_asset.path
    input_size = gif_asset.size_bytes
    
    # Generate output path if not provided
    if output_path is None:
        output_path = generate_output_filename(input_path)
    
    # Use temp file for processing
    temp_fd, temp_file = tempfile.mkstemp(suffix='.gif', prefix='gif_optimize_')
    os.close(temp_fd)
    
    try:
        # Build optimization command
        opt_cmd = [magick_cmd, str(input_path)]
        
        # Coalesce frames before any modifications
        opt_cmd += ["-coalesce"]
        
        # Add resize if specified
        if width:
            opt_cmd += ["-resize", f"{width}x"]
        
        # Add FPS adjustment if specified
        if fps:
            if fps_mode == "preserve":
                # Get original delays and scale proportionally
                delays = info.get('delays', [])
                if delays:
                    scaled_delays = gif_asset.scale_delays_proportionally(delays, fps)
                    # Use average of scaled delays
                    avg_scaled_delay = int(sum(scaled_delays) / len(scaled_delays))
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
        
        # Add optimization and output to temp file
        opt_cmd += ["-layers", "Optimize", temp_file]
        
        # Run optimization
        run(opt_cmd)
        
        # Move temp file to output path
        if os.path.exists(temp_file):
            os.rename(temp_file, output_path)
        else:
            raise RuntimeError("Optimization failed: output file not created")
        
        # Get output file size
        output_size = output_path.stat().st_size
        
        # Format and return result
        result = format_optimization_result(input_path, output_path, input_size, output_size)
        return result
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise


def optimize_image(
    image_asset: ImageAsset,
    output_path: Optional[Path] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    scale: Optional[float] = None
) -> Dict[str, Any]:
    """Optimize an image file with proportional resizing.
    
    Args:
        image_asset: ImageAsset instance
        output_path: Optional output path (default: generate from input)
        width: Optional target width in pixels
        height: Optional target height in pixels
        scale: Optional scale factor (e.g., 0.5 for 50%)
        
    Returns:
        Dictionary with optimization results (from format_optimization_result)
        
    Raises:
        ValueError: If no resize parameter provided or image cannot be read
    """
    from PIL import Image
    
    input_path = image_asset.path
    input_size = image_asset.size_bytes
    
    # Validate that at least one resize parameter is provided
    if not any([width, height, scale]):
        raise ValueError("At least one resize parameter (width, height, or scale) must be provided")
    
    # Generate output path if not provided
    if output_path is None:
        output_path = generate_output_filename(input_path)
    
    try:
        with Image.open(input_path) as img:
            original_width, original_height = img.size
            
            # Calculate new dimensions
            if scale:
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
            elif width:
                scale_factor = width / original_width
                new_width = width
                new_height = int(original_height * scale_factor)
            elif height:
                scale_factor = height / original_height
                new_width = int(original_width * scale_factor)
                new_height = height
            else:
                raise ValueError("No resize parameter provided")
            
            # Resize with high-quality resampling
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save with appropriate quality settings
            # Preserve original format and optimize where possible
            save_kwargs = {}
            if img.format == 'JPEG':
                save_kwargs['quality'] = 85
                save_kwargs['optimize'] = True
            elif img.format == 'PNG':
                save_kwargs['optimize'] = True
            elif img.format == 'WEBP':
                save_kwargs['quality'] = 85
                save_kwargs['method'] = 6
            
            # Save to output path
            resized_img.save(output_path, **save_kwargs)
        
        # Get output file size
        output_size = output_path.stat().st_size
        
        # Format and return result
        result = format_optimization_result(input_path, output_path, input_size, output_size)
        return result
        
    except Exception as e:
        raise ValueError(f"Error optimizing image: {e}")

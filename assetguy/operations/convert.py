"""Video to GIF conversion operations."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from ..assets.video import VideoAsset
from ..tools.detector import get_imagemagick_command, check_ffmpeg
from ..tools.executor import run
from ..utils.formatting import format_file_size


def format_conversion_result(
    input_path: Path,
    output_path: Path,
    input_size: int,
    output_size: int
) -> Dict[str, Any]:
    """Format conversion result with file size comparison.
    
    Args:
        input_path: Path to input file
        output_path: Path to output file
        input_size: Input file size in bytes
        output_size: Output file size in bytes
    
    Returns:
        Dictionary with conversion results
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


def print_conversion_result(result: Dict[str, Any]):
    """Print formatted conversion result.
    
    Args:
        result: Result dictionary from format_conversion_result()
    """
    print("\n" + "=" * 60)
    print("✅ Conversion Complete")
    print("=" * 60)
    print(f"Input:  {result['input_path']}")
    print(f"        {result['input_size_formatted']} ({result['input_size']:,} bytes)")
    print(f"Output: {result['output_path']}")
    print(f"        {result['output_size_formatted']} ({result['output_size']:,} bytes)")
    if result['reduction'] > 0:
        print(f"\nSize: {result['reduction_formatted']} ({result['reduction_percent']:.1f}% smaller)")
    else:
        print(f"\nSize: {result['reduction_formatted']} ({abs(result['reduction_percent']):.1f}% larger)")
    print("=" * 60 + "\n")


def convert_video_to_gif(
    video_asset: VideoAsset,
    output_path: Optional[Path] = None,
    width: Optional[int] = None,
    fps: Optional[float] = None,
    colors: Optional[int] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> Dict[str, Any]:
    """Convert a video file to GIF format.
    
    Args:
        video_asset: VideoAsset instance
        output_path: Optional output path (default: generate from input)
        width: Optional target width in pixels
        fps: Optional target FPS
        colors: Optional number of colors for optimization
        start_time: Optional start time in seconds (for trimming)
        end_time: Optional end time in seconds (for trimming)
    
    Returns:
        Dictionary with conversion results (from format_conversion_result)
    
    Raises:
        RuntimeError: If FFmpeg or ImageMagick not found
        ValueError: If video info cannot be read or parameters are invalid
    """
    # Check FFmpeg availability
    ffmpeg_available, _ = check_ffmpeg()
    if not ffmpeg_available:
        raise RuntimeError("FFmpeg not found. Please install FFmpeg first.")
    
    info = video_asset.get_info()
    if not info:
        raise ValueError("Could not read video information")
    
    input_path = video_asset.path
    input_size = video_asset.size_bytes
    
    # Generate output path if not provided
    if output_path is None:
        stem = input_path.stem
        output_path = input_path.parent / f"{stem}.gif"
    
    # Validate time range
    duration = info['duration']
    if start_time is not None and start_time < 0:
        start_time = 0
    if end_time is not None and end_time > duration:
        end_time = duration
    if start_time is not None and end_time is not None and start_time >= end_time:
        raise ValueError(f"Invalid time range: {start_time}-{end_time}")
    
    # Calculate duration for conversion
    if start_time is not None and end_time is not None:
        convert_duration = end_time - start_time
    elif start_time is not None:
        convert_duration = duration - start_time
    else:
        convert_duration = duration
    
    # Use temp file for initial conversion
    temp_fd, temp_file = tempfile.mkstemp(suffix='.gif', prefix='video_convert_')
    os.close(temp_fd)
    
    try:
        # Build FFmpeg command
        ffmpeg_cmd = ["ffmpeg", "-y"]  # -y to overwrite output
        
        # Add time range if specified
        # Note: -ss before -i is faster but less accurate, -ss after -i is more accurate
        # We'll use -ss before -i for speed, and -t for duration
        if start_time is not None:
            ffmpeg_cmd.extend(["-ss", str(start_time)])
        
        # Input file
        ffmpeg_cmd.extend(["-i", str(input_path)])
        
        # Duration (must come after -i)
        if start_time is not None or end_time is not None:
            ffmpeg_cmd.extend(["-t", str(convert_duration)])
        
        # Build video filter
        vf_parts = []
        
        # Set FPS if specified
        if fps:
            vf_parts.append(f"fps={fps}")
        
        # Resize if specified
        if width:
            vf_parts.append(f"scale={width}:-1")
        
        # Combine video filters
        if vf_parts:
            ffmpeg_cmd.extend(["-vf", ",".join(vf_parts)])
        
        # Output to temp file
        ffmpeg_cmd.append(temp_file)
        
        # Run FFmpeg conversion (suppress verbose output)
        run(ffmpeg_cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
        # Apply color reduction if specified
        if colors:
            magick_cmd = get_imagemagick_command()
            if not magick_cmd:
                # If ImageMagick not available, just use the temp file as output
                if os.path.exists(temp_file):
                    os.rename(temp_file, output_path)
                else:
                    raise RuntimeError("FFmpeg conversion failed: output file not created")
            else:
                # Use ImageMagick to reduce colors
                final_fd, final_file = tempfile.mkstemp(suffix='.gif', prefix='gif_colors_')
                os.close(final_fd)
                
                try:
                    color_cmd = [magick_cmd, temp_file, "-colors", str(colors), final_file]
                    run(color_cmd)
                    
                    # Move final file to output path
                    if os.path.exists(final_file):
                        os.rename(final_file, output_path)
                    else:
                        raise RuntimeError("Color reduction failed: output file not created")
                except Exception as e:
                    # If color reduction fails, use the temp file
                    if os.path.exists(temp_file):
                        os.rename(temp_file, output_path)
                    else:
                        raise
                finally:
                    # Clean up temp files
                    if os.path.exists(final_file):
                        try:
                            os.remove(final_file)
                        except:
                            pass
        else:
            # No color reduction, just move temp file to output
            if os.path.exists(temp_file):
                os.rename(temp_file, output_path)
            else:
                raise RuntimeError("FFmpeg conversion failed: output file not created")
        
        # Get output file size
        output_size = output_path.stat().st_size
        
        # Format and return result
        result = format_conversion_result(input_path, output_path, input_size, output_size)
        return result
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        raise


def convert_video_to_webp(
    video_asset: VideoAsset,
    output_path: Optional[Path] = None,
    width: Optional[int] = None,
    fps: Optional[float] = None,
    quality: Optional[int] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> Dict[str, Any]:
    """Convert a video file to WebP animation format.
    
    Args:
        video_asset: VideoAsset instance
        output_path: Optional output path (default: generate from input)
        width: Optional target width in pixels
        fps: Optional target FPS
        quality: Optional quality setting (0-100, default: 85)
        start_time: Optional start time in seconds (for trimming)
        end_time: Optional end time in seconds (for trimming)
    
    Returns:
        Dictionary with conversion results (from format_conversion_result)
    
    Raises:
        RuntimeError: If FFmpeg not found
        ValueError: If video info cannot be read or parameters are invalid
    """
    # Check FFmpeg availability
    ffmpeg_available, _ = check_ffmpeg()
    if not ffmpeg_available:
        raise RuntimeError("FFmpeg not found. Please install FFmpeg first.")
    
    info = video_asset.get_info()
    if not info:
        raise ValueError("Could not read video information")
    
    input_path = video_asset.path
    input_size = video_asset.size_bytes
    
    # Generate output path if not provided
    if output_path is None:
        stem = input_path.stem
        output_path = input_path.parent / f"{stem}.webp"
    
    # Validate time range
    duration = info['duration']
    if start_time is not None and start_time < 0:
        start_time = 0
    if end_time is not None and end_time > duration:
        end_time = duration
    if start_time is not None and end_time is not None and start_time >= end_time:
        raise ValueError(f"Invalid time range: {start_time}-{end_time}")
    
    # Calculate duration for conversion
    if start_time is not None and end_time is not None:
        convert_duration = end_time - start_time
    elif start_time is not None:
        convert_duration = duration - start_time
    else:
        convert_duration = duration
    
    # Validate quality
    if quality is None:
        quality = 85  # Default quality
    else:
        quality = max(0, min(100, quality))  # Clamp to 0-100
    
    # Use temp file for conversion
    temp_fd, temp_file = tempfile.mkstemp(suffix='.webp', prefix='video_convert_')
    os.close(temp_fd)
    
    try:
        # Build FFmpeg command
        ffmpeg_cmd = ["ffmpeg", "-y"]  # -y to overwrite output
        
        # Add time range if specified
        if start_time is not None:
            ffmpeg_cmd.extend(["-ss", str(start_time)])
        
        # Input file
        ffmpeg_cmd.extend(["-i", str(input_path)])
        
        # Duration (must come after -i)
        if start_time is not None or end_time is not None:
            ffmpeg_cmd.extend(["-t", str(convert_duration)])
        
        # Build video filter
        vf_parts = []
        
        # Set FPS if specified
        if fps:
            vf_parts.append(f"fps={fps}")
        
        # Resize if specified
        if width:
            vf_parts.append(f"scale={width}:-1")
        
        # Combine video filters
        if vf_parts:
            ffmpeg_cmd.extend(["-vf", ",".join(vf_parts)])
        
        # WebP codec settings
        ffmpeg_cmd.extend(["-c:v", "libwebp"])
        ffmpeg_cmd.extend(["-quality", str(quality)])
        ffmpeg_cmd.extend(["-loop", "0"])  # Infinite loop like GIF
        
        # Output to temp file
        ffmpeg_cmd.append(temp_file)
        
        # Run FFmpeg conversion (suppress verbose output)
        run(ffmpeg_cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
        # Move temp file to output path
        if os.path.exists(temp_file):
            os.rename(temp_file, output_path)
        else:
            raise RuntimeError("FFmpeg conversion failed: output file not created")
        
        # Get output file size
        output_size = output_path.stat().st_size
        
        # Format and return result
        result = format_conversion_result(input_path, output_path, input_size, output_size)
        return result
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        raise

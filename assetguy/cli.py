"""Command-line interface for assetguy."""

import click
import sys
from pathlib import Path
from typing import Optional

from .operations.inspect import inspect_asset, print_inspection, detect_asset_type
from .operations.compare import compare_assets, print_comparison
from .operations.optimize import (
    optimize_gif, 
    optimize_image, 
    print_optimization_result, 
    format_optimization_result,
    generate_output_filename,
    split_gif,
    trim_gif,
    parse_frame_range,
    parse_split_frames,
    parse_time_range,
    parse_split_times,
    parse_split_trim_input
)
from .utils.formatting import format_file_size
from .assets.gif import GifAsset
from .assets.image import ImageAsset
from .config.manager import ConfigManager
from .config.presets import get_preset, list_presets
from .utils.paths import strip_quotes


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """AssetGuy - Unified CLI tool for optimizing, converting, and managing assets."""
    pass


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--json", is_flag=True, help="Output in JSON format")
def inspect(file_path: str, json: bool):
    """Inspect an asset file and display its information.
    
    FILE_PATH: Path to the asset file to inspect
    """
    try:
        path = Path(strip_quotes(file_path))
        info = inspect_asset(path)
        
        if json:
            import json
            click.echo(json.dumps(info, indent=2))
        else:
            print_inspection(info)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file1", type=click.Path(exists=True))
@click.argument("file2", type=click.Path(exists=True))
@click.option("--json", is_flag=True, help="Output in JSON format")
def compare(file1: str, file2: str, json: bool):
    """Compare two asset files.
    
    FILE1: Path to first asset file
    FILE2: Path to second asset file
    """
    try:
        path1 = Path(strip_quotes(file1))
        path2 = Path(strip_quotes(file2))
        
        comparison = compare_assets(path1, path2)
        
        if json:
            import json
            click.echo(json.dumps(comparison, indent=2))
        else:
            print_comparison(comparison)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--preset", type=click.Choice(["docs", "web", "marketing"]), help="Use a preset configuration")
@click.option("--width", type=int, help="Target width in pixels")
@click.option("--fps", type=float, help="Target FPS (for GIFs)")
@click.option("--colors", type=int, help="Number of colors (for GIFs)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--overwrite", is_flag=True, help="Overwrite output file if it exists (non-interactive mode)")
@click.option("--non-interactive", is_flag=True, help="Run in non-interactive mode")
@click.option("--json", is_flag=True, help="Output result in JSON format")
def optimize(file_path: str, preset: Optional[str], width: Optional[int], 
             fps: Optional[float], colors: Optional[int], output: Optional[str],
             overwrite: bool, non_interactive: bool, json: bool):
    """Optimize an asset file (GIF or image).
    
    FILE_PATH: Path to the asset file to optimize
    
    Supports both GIF and image optimization with presets, interactive prompts,
    and non-interactive mode for automation.
    """
    try:
        path = Path(strip_quotes(file_path))
        
        if not path.exists():
            click.echo(f"Error: File not found: {path}", err=True)
            sys.exit(1)
        
        # Detect asset type
        asset_type = detect_asset_type(path)
        if asset_type not in ['gif', 'image']:
            click.echo(f"Error: Unsupported asset type. Supported: GIF and images", err=True)
            sys.exit(1)
        
        # Load preset if provided
        preset_config = {}
        if preset:
            try:
                preset_config = get_preset(preset)
            except KeyError as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
        
        # Merge preset with CLI flags (CLI flags override preset)
        opt_width = width if width is not None else preset_config.get('width')
        opt_fps = fps if fps is not None else preset_config.get('fps')
        opt_colors = colors if colors is not None else preset_config.get('colors')
        
        # Show current asset info
        if not non_interactive:
            click.echo("")
            inspect_info = inspect_asset(path)
            print_inspection(inspect_info)
        
        # Get GIF info for split/trim operations
        gif_info = None
        if asset_type == 'gif':
            gif_asset_temp = GifAsset(path)
            gif_info = gif_asset_temp.get_info()
        
        # Handle output path
        output_path = None
        if output:
            output_path = Path(strip_quotes(output))
        else:
            output_path = generate_output_filename(path)
        
        # Check if output file exists
        if output_path.exists() and not overwrite:
            if non_interactive:
                click.echo(f"Error: Output file exists: {output_path}. Use --overwrite to overwrite.", err=True)
                sys.exit(1)
            else:
                if not click.confirm(f"⚠️ Output file {output_path} already exists. Overwrite?"):
                    click.echo("Operation cancelled.")
                    sys.exit(0)
        
        # Interactive mode: prompt for missing parameters
        if not non_interactive:
            if asset_type == 'gif' and gif_info:
                # Unified split/trim input
                gif_asset = GifAsset(path)
                split_trim_input = click.prompt(
                    "✂️  Time range or split points (e.g., 2.5,3.5 for split, 0-2.5 for trim, f:10,50 for frames, Enter to skip)",
                    default="",
                    type=str
                ).strip()
                
                if split_trim_input:
                    parsed = parse_split_trim_input(
                        split_trim_input,
                        gif_info['duration'],
                        gif_info['frames'],
                        gif_asset
                    )
                    
                    if parsed:
                        if parsed['mode'] == 'split':
                            # Handle split operation
                            output_dir = output_path.parent if output_path else path.parent
                            output_files = split_gif(
                                gif_asset,
                                split_points=parsed['points'],
                                output_dir=output_dir,
                                width=opt_width,
                                fps=opt_fps,
                                fps_mode="normalize",
                                colors=opt_colors
                            )
                            
                            if output_files:
                                click.echo(f"\n✅ Created {len(output_files)} segment(s):")
                                for i, output_file in enumerate(output_files, 1):
                                    size = output_file.stat().st_size
                                    click.echo(f"   {i}. {output_file.name} ({format_file_size(size)})")
                            else:
                                click.echo("⚠️  Warning: No segments were created.", err=True)
                            sys.exit(0)
                        
                        elif parsed['mode'] == 'trim':
                            # Handle trim operation(s) - may be multiple ranges
                            trim_ranges = parsed['ranges']
                            output_files = []
                            
                            for i, trim_range in enumerate(trim_ranges):
                                # Generate output filename for each trim
                                if len(trim_ranges) > 1:
                                    # Multiple trims: use numbered suffix
                                    output_name = output_path.stem
                                    output_ext = output_path.suffix
                                    trim_output_path = output_path.parent / f"{output_name}_trim{i+1}{output_ext}"
                                else:
                                    # Single trim: use original output path
                                    trim_output_path = output_path
                                
                                try:
                                    if parsed['is_frame']:
                                        # Frame-based trim
                                        result = trim_gif(
                                            gif_asset,
                                            output_path=trim_output_path,
                                            start_frame=trim_range[0],
                                            end_frame=trim_range[1],
                                            width=opt_width,
                                            fps=opt_fps,
                                            fps_mode="normalize",
                                            colors=opt_colors
                                        )
                                    else:
                                        # Time-based trim
                                        result = trim_gif(
                                            gif_asset,
                                            output_path=trim_output_path,
                                            start_time=trim_range[0],
                                            end_time=trim_range[1],
                                            width=opt_width,
                                            fps=opt_fps,
                                            fps_mode="normalize",
                                            colors=opt_colors
                                        )
                                    
                                    output_files.append(trim_output_path)
                                    
                                except Exception as e:
                                    click.echo(f"⚠️  Warning: Failed to create trim {i+1}: {e}", err=True)
                            
                            if output_files:
                                if json:
                                    import json
                                    result = {
                                        'operation': 'trim',
                                        'input_path': str(path),
                                        'output_files': [str(f) for f in output_files],
                                        'count': len(output_files)
                                    }
                                    click.echo(json.dumps(result, indent=2))
                                else:
                                    click.echo(f"\n✅ Created {len(output_files)} trimmed file(s):")
                                    for i, output_file in enumerate(output_files, 1):
                                        size = output_file.stat().st_size
                                        click.echo(f"   {i}. {output_file.name} ({format_file_size(size)})")
                            else:
                                click.echo("⚠️  Warning: No trimmed files were created.", err=True)
                            sys.exit(0)
                    else:
                        click.echo("⚠️  Warning: Invalid input format. Skipping split/trim.", err=True)
                
                # Continue with normal optimization prompts
                if opt_width is None:
                    width_input = click.prompt("📏 Target width (press Enter to skip)", default="", type=str)
                    opt_width = int(width_input) if width_input.strip() else None
                
                if opt_fps is None:
                    fps_input = click.prompt("⏱️ Target FPS [recommended: 8-12] (Enter to skip)", default="", type=str)
                    opt_fps = float(fps_input) if fps_input.strip() else None
                
                if opt_colors is None:
                    colors_input = click.prompt("🎨 Number of colors [recommended: 32/64/128] (Enter to keep)", default="", type=str)
                    opt_colors = int(colors_input) if colors_input.strip() else None
                
                # Prompt for output filename if not provided
                if not output:
                    default_output = str(output_path)
                    output_input = click.prompt("💾 Output filename", default=default_output, type=str)
                    output_path = Path(output_input)
            
            elif asset_type == 'image':
                if opt_width is None:
                    width_input = click.prompt("📏 Target width (press Enter to skip)", default="", type=str)
                    opt_width = int(width_input) if width_input.strip() else None
                
                # Prompt for output filename if not provided
                if not output:
                    default_output = str(output_path)
                    output_input = click.prompt("💾 Output filename", default=default_output, type=str)
                    output_path = Path(output_input)
        
        # Validate that at least one optimization parameter is provided
        if asset_type == 'gif':
            if not any([opt_width, opt_fps, opt_colors]):
                click.echo("Error: At least one optimization parameter (--width, --fps, or --colors) or --preset must be provided.", err=True)
                sys.exit(1)
        elif asset_type == 'image':
            if opt_width is None:
                click.echo("Error: --width or --preset must be provided for image optimization.", err=True)
                sys.exit(1)
        
        # Perform optimization
        click.echo("\n🔄 Optimizing asset...")
        
        if asset_type == 'gif':
            gif_asset = GifAsset(path)
            result = optimize_gif(
                gif_asset,
                output_path=output_path,
                width=opt_width,
                fps=opt_fps,
                fps_mode="normalize",
                colors=opt_colors
            )
        elif asset_type == 'image':
            image_asset = ImageAsset(path)
            result = optimize_image(
                image_asset,
                output_path=output_path,
                width=opt_width
            )
        else:
            click.echo(f"Error: Unsupported asset type: {asset_type}", err=True)
            sys.exit(1)
        
        # Display results
        if json:
            import json
            click.echo(json.dumps(result, indent=2))
        else:
            print_optimization_result(result)
        
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def config():
    """Manage configuration settings."""
    pass


@config.command()
def show():
    """Show current configuration."""
    config = ConfigManager()
    settings = config.get_config()
    
    click.echo("Current configuration:")
    click.echo(f"  Config file: {config.get_config_path()}")
    click.echo("")
    for key, value in settings.items():
        click.echo(f"  {key}: {value}")


@config.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str):
    """Set a configuration value.
    
    KEY: Configuration key to set
    VALUE: Value to set
    """
    config = ConfigManager()
    
    try:
        config.set(key, value)
        click.echo(f"✓ Set {key} = {value}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@config.command()
@click.argument("key")
def get(key: str):
    """Get a configuration value.
    
    KEY: Configuration key to get
    """
    config = ConfigManager()
    value = config.get(key)
    if value is not None:
        click.echo(f"{key}: {value}")
    else:
        click.echo(f"Key '{key}' not found", err=True)
        sys.exit(1)


@config.command()
def reset():
    """Reset configuration to defaults."""
    config = ConfigManager()
    if click.confirm("🔄 Are you sure you want to reset all settings to defaults?"):
        config.reset()
        click.echo("✓ Configuration reset to defaults")
    else:
        click.echo("Reset cancelled")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--time-points", type=str, help="Comma-separated time points to split at (e.g., '2.5,5.0')")
@click.option("--frame-points", type=str, help="Comma-separated frame numbers to split at (e.g., '10,50')")
@click.option("--time-range", type=str, help="Time range to extract (e.g., '2.5-5.0')")
@click.option("--frame-range", type=str, help="Frame range to extract (e.g., '10-50')")
@click.option("--width", type=int, help="Target width in pixels")
@click.option("--fps", type=float, help="Target FPS (for GIFs)")
@click.option("--colors", type=int, help="Number of colors (for GIFs)")
@click.option("--output", "-o", type=click.Path(), help="Output directory or file path")
@click.option("--overwrite", is_flag=True, help="Overwrite output files if they exist")
@click.option("--non-interactive", is_flag=True, help="Run in non-interactive mode")
@click.option("--json", is_flag=True, help="Output result in JSON format")
def split(file_path: str, time_points: Optional[str], frame_points: Optional[str],
          time_range: Optional[str], frame_range: Optional[str],
          width: Optional[int], fps: Optional[float], colors: Optional[int],
          output: Optional[str], overwrite: bool, non_interactive: bool, json: bool):
    """Split or trim a GIF file by time or frame ranges.
    
    FILE_PATH: Path to the GIF file to split/trim
    
    Use --time-points or --frame-points to split into multiple files.
    Use --time-range or --frame-range to trim/extract a single range.
    """
    try:
        path = Path(strip_quotes(file_path))
        
        if not path.exists():
            click.echo(f"Error: File not found: {path}", err=True)
            sys.exit(1)
        
        # Detect asset type
        asset_type = detect_asset_type(path)
        if asset_type != 'gif':
            click.echo(f"Error: Split/trim only supports GIF files. Got: {asset_type}", err=True)
            sys.exit(1)
        
        gif_asset = GifAsset(path)
        info = gif_asset.get_info()
        if not info:
            # Check if ImageMagick is available
            from .tools.detector import get_imagemagick_command
            magick_cmd = get_imagemagick_command()
            if not magick_cmd:
                click.echo(
                    "Error: Could not read GIF information. ImageMagick is required but not found.\n"
                    "Please install ImageMagick:\n"
                    "  macOS: brew install imagemagick\n"
                    "  Ubuntu/Debian: sudo apt-get install imagemagick\n"
                    "  Windows: Download from https://imagemagick.org/script/download.php",
                    err=True
                )
            else:
                click.echo(
                    f"Error: Could not read GIF information. "
                    f"ImageMagick command '{magick_cmd}' is available but failed to read the file. "
                    "The file may be corrupted or in an unsupported format.",
                    err=True
                )
            sys.exit(1)
        
        # Show current asset info
        if not non_interactive:
            click.echo("")
            inspect_info = inspect_asset(path)
            print_inspection(inspect_info)
        
        # Determine operation mode and parameters
        split_points = None
        trim_range = None
        trim_ranges = None  # For multiple trim ranges
        is_frame_based_trim = False  # Track if trim is frame-based
        is_split = False
        is_trim = False
        
        # Check for split operations
        if time_points:
            split_points = parse_split_times(time_points, info['duration'])
            if not split_points:
                click.echo(f"Error: Invalid time points: {time_points}", err=True)
                sys.exit(1)
            is_split = True
        elif frame_points:
            frame_nums = parse_split_frames(frame_points, info['frames'])
            if not frame_nums:
                click.echo(f"Error: Invalid frame points: {frame_points}", err=True)
                sys.exit(1)
            # Convert frames to time points
            split_points = gif_asset.frames_to_time_points(frame_nums)
            if not split_points:
                click.echo(f"Error: Could not convert frame points to time points", err=True)
                sys.exit(1)
            is_split = True
        
        # Check for trim operations
        elif time_range:
            # Support multiple ranges (comma-separated)
            if ',' in time_range:
                # Multiple ranges
                parts = [p.strip() for p in time_range.split(',') if p.strip()]
                trim_ranges = []
                for part in parts:
                    range_tuple = parse_time_range(part, info['duration'])
                    if range_tuple:
                        trim_ranges.append(range_tuple)
                if trim_ranges:
                    trim_range = trim_ranges[0]  # For backward compatibility
                    is_trim = True
                    is_frame_based_trim = False
                else:
                    click.echo(f"Error: Invalid time ranges: {time_range}", err=True)
                    sys.exit(1)
            else:
                trim_range = parse_time_range(time_range, info['duration'])
                if not trim_range:
                    click.echo(f"Error: Invalid time range: {time_range}", err=True)
                    sys.exit(1)
                trim_ranges = [trim_range]
                is_trim = True
                is_frame_based_trim = False
        elif frame_range:
            # Support multiple ranges (comma-separated)
            if ',' in frame_range:
                # Multiple ranges
                parts = [p.strip() for p in frame_range.split(',') if p.strip()]
                trim_ranges = []
                for part in parts:
                    range_tuple = parse_frame_range(part, info['frames'])
                    if range_tuple:
                        trim_ranges.append(range_tuple)
                if trim_ranges:
                    trim_range = trim_ranges[0]  # For backward compatibility
                    is_trim = True
                    is_frame_based_trim = True
                else:
                    click.echo(f"Error: Invalid frame ranges: {frame_range}", err=True)
                    sys.exit(1)
            else:
                trim_range = parse_frame_range(frame_range, info['frames'])
                if not trim_range:
                    click.echo(f"Error: Invalid frame range: {frame_range}", err=True)
                    sys.exit(1)
                trim_ranges = [trim_range]
                is_trim = True
                is_frame_based_trim = True
        
        # Interactive mode: prompt if no operation specified
        if not is_split and not is_trim and not non_interactive:
            split_trim_input = click.prompt(
                "✂️  Time range or split points (e.g., 2.5,3.5 for split, 0-2.5 for trim, f:10,50 for frames, Enter to skip)",
                default="",
                type=str
            ).strip()
            
            if split_trim_input:
                parsed = parse_split_trim_input(
                    split_trim_input,
                    info['duration'],
                    info['frames'],
                    gif_asset
                )
                
                if parsed:
                    if parsed['mode'] == 'split':
                        split_points = parsed['points']
                        is_split = True
                    elif parsed['mode'] == 'trim':
                        trim_ranges = parsed['ranges']
                        trim_range = trim_ranges[0] if trim_ranges else None
                        is_trim = True
                        is_frame_based_trim = parsed['is_frame']
                else:
                    click.echo("Error: Invalid input format", err=True)
                    sys.exit(1)
        
        # Validate that an operation was specified
        if not is_split and not is_trim:
            click.echo("Error: Must specify --time-points, --frame-points, --time-range, or --frame-range", err=True)
            sys.exit(1)
        
        # Handle output path
        if output:
            output_path = Path(strip_quotes(output))
            # If it's a directory for split, use it; otherwise treat as file path
            if is_split and output_path.is_dir():
                pass  # Use as-is
            elif is_split:
                # For split, if output is a file, use its parent as directory
                output_path = output_path.parent
        else:
            if is_split:
                output_path = path.parent
            else:
                output_path = generate_output_filename(path, suffix="_trimmed")
        
        # Interactive prompts for optimization options
        if not non_interactive:
            if width is None:
                width_input = click.prompt("📏 Target width (press Enter to skip)", default="", type=str)
                width = int(width_input) if width_input.strip() else None
            
            if fps is None:
                fps_input = click.prompt("⏱️ Target FPS [recommended: 8-12] (Enter to skip)", default="", type=str)
                fps = float(fps_input) if fps_input.strip() else None
            
            if colors is None:
                colors_input = click.prompt("🎨 Number of colors [recommended: 32/64/128] (Enter to keep)", default="", type=str)
                colors = int(colors_input) if colors_input.strip() else None
        
        # Perform split or trim operation
        click.echo("\n🔄 Processing...")
        
        if is_split:
            # Split operation
            output_files = split_gif(
                gif_asset,
                split_points=split_points,
                output_dir=output_path if output_path.is_dir() else output_path.parent,
                width=width,
                fps=fps,
                fps_mode="normalize",
                colors=colors
            )
            
            if output_files:
                if json:
                    import json
                    result = {
                        'operation': 'split',
                        'input_path': str(path),
                        'output_files': [str(f) for f in output_files],
                        'count': len(output_files)
                    }
                    click.echo(json.dumps(result, indent=2))
                else:
                    click.echo(f"\n✅ Created {len(output_files)} segment(s):")
                    for i, output_file in enumerate(output_files, 1):
                        size = output_file.stat().st_size
                        click.echo(f"   {i}. {output_file.name} ({format_file_size(size)})")
            else:
                click.echo("Error: No segments were created", err=True)
                sys.exit(1)
        
        elif is_trim:
            # Trim operation(s) - may be multiple ranges
            if trim_ranges is None:
                trim_ranges = [trim_range] if trim_range else []
            
            output_files = []
            
            for i, current_range in enumerate(trim_ranges):
                # Generate output filename for each trim
                if len(trim_ranges) > 1:
                    # Multiple trims: use numbered suffix
                    output_name = output_path.stem if output_path.is_file() else path.stem
                    output_ext = output_path.suffix if output_path.is_file() else path.suffix
                    trim_output_path = output_path.parent / f"{output_name}_trim{i+1}{output_ext}" if output_path.is_file() else path.parent / f"{output_name}_trim{i+1}{output_ext}"
                else:
                    # Single trim: use original output path
                    trim_output_path = output_path
                
                try:
                    if is_frame_based_trim:
                        # Frame-based trim
                        result = trim_gif(
                            gif_asset,
                            output_path=trim_output_path,
                            start_frame=current_range[0],
                            end_frame=current_range[1],
                            width=width,
                            fps=fps,
                            fps_mode="normalize",
                            colors=colors
                        )
                    else:
                        # Time-based trim
                        result = trim_gif(
                            gif_asset,
                            output_path=trim_output_path,
                            start_time=current_range[0],
                            end_time=current_range[1],
                            width=width,
                            fps=fps,
                            fps_mode="normalize",
                            colors=colors
                        )
                    
                    output_files.append(trim_output_path)
                    
                except Exception as e:
                    click.echo(f"⚠️  Warning: Failed to create trim {i+1}: {e}", err=True)
            
            if output_files:
                if json:
                    import json
                    result = {
                        'operation': 'trim',
                        'input_path': str(path),
                        'output_files': [str(f) for f in output_files],
                        'count': len(output_files)
                    }
                    click.echo(json.dumps(result, indent=2))
                else:
                    if len(output_files) > 1:
                        click.echo(f"\n✅ Created {len(output_files)} trimmed file(s):")
                        for i, output_file in enumerate(output_files, 1):
                            size = output_file.stat().st_size
                            click.echo(f"   {i}. {output_file.name} ({format_file_size(size)})")
                    else:
                        # Single file - use optimization result format
                        result = format_optimization_result(path, output_files[0], path.stat().st_size, output_files[0].stat().st_size)
                        print_optimization_result(result)
            else:
                click.echo("Error: No trimmed files were created", err=True)
                sys.exit(1)
        
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def presets():
    """List available presets."""
    presets_dict = list_presets()
    
    click.echo("Available presets:")
    click.echo("")
    for name, config in presets_dict.items():
        click.echo(f"  {name}:")
        click.echo(f"    {config.get('description', 'No description')}")
        for key, value in config.items():
            if key != 'description':
                click.echo(f"    {key}: {value}")
        click.echo("")


@cli.command()
def check():
    """Check availability of required external tools."""
    from .tools.detector import check_imagemagick, check_ffmpeg
    
    click.echo("Checking external dependencies...")
    click.echo("")
    
    # Check ImageMagick
    magick_available, magick_version = check_imagemagick()
    if magick_available:
        click.echo(f"✓ ImageMagick: {magick_version}")
    else:
        click.echo("✗ ImageMagick: Not found")
        click.echo("  Required for GIF operations")
        click.echo("  Install: brew install imagemagick (macOS) or sudo apt-get install imagemagick (Linux)")
    
    # Check FFmpeg
    ffmpeg_available, ffmpeg_version = check_ffmpeg()
    if ffmpeg_available:
        click.echo(f"✓ FFmpeg: {ffmpeg_version}")
    else:
        click.echo("✗ FFmpeg: Not found (optional, for video operations)")
    
    click.echo("")


def main():
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()

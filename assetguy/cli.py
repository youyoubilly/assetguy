"""Command-line interface for assetguy."""

import click
import sys
from pathlib import Path
from typing import Optional

from .operations.inspect import inspect_asset, print_inspection, detect_asset_type
from .operations.compare import compare_assets, print_comparison
from .operations.optimize import optimize_gif, optimize_image, print_optimization_result, generate_output_filename
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
            info = inspect_asset(path)
            print_inspection(info)
        
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
                if not click.confirm(f"Output file {output_path} already exists. Overwrite?"):
                    click.echo("Operation cancelled.")
                    sys.exit(0)
        
        # Interactive mode: prompt for missing parameters
        if not non_interactive:
            if asset_type == 'gif':
                if opt_width is None:
                    width_input = click.prompt("Target width (press Enter to skip)", default="", type=str)
                    opt_width = int(width_input) if width_input.strip() else None
                
                if opt_fps is None:
                    fps_input = click.prompt("Target FPS (press Enter to skip)", default="", type=str)
                    opt_fps = float(fps_input) if fps_input.strip() else None
                
                if opt_colors is None:
                    colors_input = click.prompt("Number of colors (press Enter to skip)", default="", type=str)
                    opt_colors = int(colors_input) if colors_input.strip() else None
                
                # Prompt for output filename if not provided
                if not output:
                    default_output = str(output_path)
                    output_input = click.prompt("Output filename", default=default_output, type=str)
                    output_path = Path(output_input)
            
            elif asset_type == 'image':
                if opt_width is None:
                    width_input = click.prompt("Target width (press Enter to skip)", default="", type=str)
                    opt_width = int(width_input) if width_input.strip() else None
                
                # Prompt for output filename if not provided
                if not output:
                    default_output = str(output_path)
                    output_input = click.prompt("Output filename", default=default_output, type=str)
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
    if click.confirm("Are you sure you want to reset all settings to defaults?"):
        config.reset()
        click.echo("✓ Configuration reset to defaults")
    else:
        click.echo("Reset cancelled")


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


def main():
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()

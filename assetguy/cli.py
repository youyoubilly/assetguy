"""Command-line interface for assetguy."""

import click
import sys
from pathlib import Path
from typing import Optional

from .operations.inspect import inspect_asset, print_inspection
from .operations.compare import compare_assets, print_comparison
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
@click.option("--non-interactive", is_flag=True, help="Run in non-interactive mode")
def optimize(file_path: str, preset: Optional[str], width: Optional[int], 
             fps: Optional[float], colors: Optional[int], non_interactive: bool):
    """Optimize an asset file.
    
    FILE_PATH: Path to the asset file to optimize
    
    Note: Full optimization features (trimming, splitting) are coming in v0.1.1
    """
    click.echo("⚠️  Optimization command is under development.")
    click.echo("   Basic optimization will be available in v0.1.1")
    click.echo(f"   File: {file_path}")
    
    if preset:
        try:
            preset_config = get_preset(preset)
            click.echo(f"   Preset: {preset}")
            click.echo(f"   Preset config: {preset_config}")
        except KeyError as e:
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

"""Asset comparison operations."""

import os
from pathlib import Path
from typing import Dict, Any

from ..assets.gif import GifAsset
from ..utils.formatting import filesize_mb, format_file_size


def compare_assets(asset1_path: Path, asset2_path: Path) -> Dict[str, Any]:
    """Compare two assets and return comparison data.
    
    Args:
        asset1_path: Path to first asset
        asset2_path: Path to second asset
        
    Returns:
        Dictionary containing comparison results
    """
    # For now, only support GIF comparison
    # TODO: Extend to support other asset types
    
    if not asset1_path.exists():
        raise FileNotFoundError(f"Asset not found: {asset1_path}")
    if not asset2_path.exists():
        raise FileNotFoundError(f"Asset not found: {asset2_path}")
    
    # Determine asset types and create asset objects
    asset1 = GifAsset(asset1_path)
    asset2 = GifAsset(asset2_path)
    
    info1 = asset1.get_info()
    info2 = asset2.get_info()
    
    if not info1:
        raise ValueError(f"Could not read information from {asset1_path}")
    if not info2:
        raise ValueError(f"Could not read information from {asset2_path}")
    
    # Get file sizes
    size1 = filesize_mb(asset1_path)
    size1_bytes = asset1.size_bytes
    size2 = filesize_mb(asset2_path)
    size2_bytes = asset2.size_bytes
    
    # Calculate percentage differences
    def calc_percent_diff(val1, val2):
        if val1 == 0:
            return "N/A" if val2 == 0 else float('inf')
        return ((val2 - val1) / val1) * 100
    
    def format_diff_descriptive(val1, val2):
        """Format difference with descriptive text."""
        diff = calc_percent_diff(val1, val2)
        if diff == "N/A":
            return "N/A"
        if isinstance(diff, float) and diff == float('inf'):
            return "+∞"
        if isinstance(diff, (int, float)):
            if abs(diff) < 0.1:
                return "Same"
            elif diff > 0:
                return f"+{diff:.1f}% (larger)"
            else:
                return f"{abs(diff):.1f}% (smaller)"
        return str(diff)
    
    # Build comparison dictionary
    comparison = {
        "asset1": {
            "path": str(asset1_path),
            "size_mb": size1,
            "size_bytes": size1_bytes,
            "width": info1['width'],
            "height": info1['height'],
            "frames": info1['frames'],
            "duration": info1['duration'],
            "fps": info1['fps'],
            "colors": info1['colors'],
        },
        "asset2": {
            "path": str(asset2_path),
            "size_mb": size2,
            "size_bytes": size2_bytes,
            "width": info2['width'],
            "height": info2['height'],
            "frames": info2['frames'],
            "duration": info2['duration'],
            "fps": info2['fps'],
            "colors": info2['colors'],
        },
        "differences": {
            "size_mb": {
                "diff": size2 - size1,
                "percent": calc_percent_diff(size1, size2),
                "description": format_diff_descriptive(size1, size2)
            },
            "size_bytes": {
                "diff": size2_bytes - size1_bytes,
                "percent": calc_percent_diff(size1_bytes, size2_bytes),
                "description": format_diff_descriptive(size1_bytes, size2_bytes)
            },
            "dimensions": {
                "same": (info1['width'] == info2['width'] and info1['height'] == info2['height']),
                "width_diff": info2['width'] - info1['width'],
                "height_diff": info2['height'] - info1['height']
            },
            "frames": {
                "diff": info2['frames'] - info1['frames'],
                "same": info1['frames'] == info2['frames']
            },
            "duration": {
                "diff": info2['duration'] - info1['duration'],
                "percent": calc_percent_diff(info1['duration'], info2['duration']),
                "description": format_diff_descriptive(info1['duration'], info2['duration'])
            },
            "fps": {
                "diff": info2['fps'] - info1['fps'],
                "same": abs(info2['fps'] - info1['fps']) < 0.01
            },
            "colors": {
                "diff": info2['colors'] - info1['colors'],
                "same": info1['colors'] == info2['colors']
            }
        }
    }
    
    return comparison


def print_comparison(comparison: Dict[str, Any]):
    """Print a formatted comparison table.
    
    Args:
        comparison: Comparison dictionary from compare_assets()
    """
    asset1 = comparison['asset1']
    asset2 = comparison['asset2']
    diffs = comparison['differences']
    
    print("\n" + "=" * 70)
    print("📊 Asset Comparison")
    print("=" * 70)
    
    print(f"\n📁 Asset 1: {asset1['path']}")
    print(f"📁 Asset 2: {asset2['path']}")
    
    print("\n" + "-" * 90)
    print(f"{'Property':<20} {'Asset 1':<20} {'Asset 2':<20} {'Difference':<25}")
    print("-" * 90)
    
    # File size
    diff_size = diffs['size_mb']['description']
    print(f"{'File Size (MB)':<20} {asset1['size_mb']:<20.2f} {asset2['size_mb']:<20.2f} {diff_size:<25}")
    print(f"{'File Size (bytes)':<20} {asset1['size_bytes']:<20,} {asset2['size_bytes']:<20,} {diffs['size_bytes']['description']:<25}")
    
    # Dimensions
    dim1 = f"{asset1['width']} × {asset1['height']}"
    dim2 = f"{asset2['width']} × {asset2['height']}"
    dim_diff = "Same" if diffs['dimensions']['same'] else "Different"
    print(f"{'Dimensions':<20} {dim1:<20} {dim2:<20} {dim_diff:<10}")
    
    # Frame count
    frames1 = asset1['frames']
    frames2 = asset2['frames']
    frames_diff = diffs['frames']['diff']
    frames_diff_str = f"{frames_diff:+d}" if frames_diff != 0 else "0"
    print(f"{'Frames':<20} {frames1:<20} {frames2:<20} {frames_diff_str:<10}")
    
    # Duration
    dur1 = asset1['duration']
    dur2 = asset2['duration']
    dur_diff = diffs['duration']['description']
    print(f"{'Duration (sec)':<20} {dur1:<20.2f} {dur2:<20.2f} {dur_diff:<25}")
    
    # FPS
    fps1 = asset1['fps']
    fps2 = asset2['fps']
    fps_diff = diffs['fps']['diff']
    if diffs['fps']['same']:
        fps_diff_str = "Same"
    elif fps_diff > 0:
        fps_diff_str = f"+{fps_diff:.2f} (higher)"
    else:
        fps_diff_str = f"{fps_diff:.2f} (lower)"
    print(f"{'FPS':<20} {fps1:<20.2f} {fps2:<20.2f} {fps_diff_str:<25}")
    
    # Colors
    colors1 = asset1['colors']
    colors2 = asset2['colors']
    colors_diff = diffs['colors']['diff']
    if colors_diff == 0:
        colors_diff_str = "Same"
    elif colors_diff > 0:
        colors_diff_str = f"+{colors_diff} (more)"
    else:
        colors_diff_str = f"{colors_diff} (fewer)"
    print(f"{'Colors (approx)':<20} {colors1:<20} {colors2:<20} {colors_diff_str:<25}")
    
    print("-" * 90)
    
    # Summary
    size_saved = asset1['size_mb'] - asset2['size_mb']
    size_saved_pct = diffs['size_mb']['percent']
    if isinstance(size_saved_pct, (int, float)):
        if size_saved_pct < 0:
            print(f"\n✅ Asset 2 is {abs(size_saved_pct):.1f}% smaller ({abs(size_saved):.2f} MB saved)")
        elif size_saved_pct > 0:
            print(f"\n⚠️  Asset 2 is {abs(size_saved_pct):.1f}% larger ({abs(size_saved):.2f} MB more)")
        else:
            print(f"\n📊 Both assets have the same file size")
    print()

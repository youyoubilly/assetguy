"""Operations for asset manipulation."""

from .inspect import inspect_asset, detect_asset_type, print_inspection
from .compare import compare_assets, print_comparison
from .optimize import (
    split_gif,
    trim_gif,
    optimize_gif,
    optimize_image,
    generate_output_filename,
    format_optimization_result,
    print_optimization_result,
    parse_frame_range,
    parse_split_frames,
    parse_time_range,
    parse_split_times,
    parse_split_trim_input
)

__all__ = [
    'inspect_asset',
    'detect_asset_type',
    'print_inspection',
    'compare_assets',
    'print_comparison',
    'split_gif',
    'trim_gif',
    'optimize_gif',
    'optimize_image',
    'generate_output_filename',
    'format_optimization_result',
    'print_optimization_result',
    'parse_frame_range',
    'parse_split_frames',
    'parse_time_range',
    'parse_split_times',
    'parse_split_trim_input',
]

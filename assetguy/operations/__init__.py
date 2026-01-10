"""Operations for asset manipulation."""

from .inspect import inspect_asset, detect_asset_type, print_inspection
from .compare import compare_assets, print_comparison
from .optimize import split_gif

__all__ = [
    'inspect_asset',
    'detect_asset_type',
    'print_inspection',
    'compare_assets',
    'print_comparison',
    'split_gif',
]

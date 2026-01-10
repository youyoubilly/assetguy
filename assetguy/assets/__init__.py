"""Asset classes for different media types."""

from .base import Asset
from .gif import GifAsset
from .image import ImageAsset

__all__ = ['Asset', 'GifAsset', 'ImageAsset']

"""Asset classes for different media types."""

from .base import Asset
from .gif import GifAsset
from .image import ImageAsset
from .video import VideoAsset

__all__ = ['Asset', 'GifAsset', 'ImageAsset', 'VideoAsset']

"""Detect availability of external tools (ImageMagick, FFmpeg, etc.)."""

import shutil
import subprocess
from typing import Optional, Tuple


def check_command(command: str, version_flag: str = "--version") -> Tuple[bool, Optional[str]]:
    """Check if a command is available and get its version.
    
    Args:
        command: Command name to check
        version_flag: Flag to pass to get version (default: --version)
        
    Returns:
        Tuple of (is_available, version_string)
        version_string is None if command not found
    """
    if not shutil.which(command):
        return False, None
    
    try:
        result = subprocess.run(
            [command, version_flag],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0] if result.stdout else "unknown"
            return True, version
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    return False, None


def check_imagemagick() -> Tuple[bool, Optional[str]]:
    """Check if ImageMagick is available.
    
    Returns:
        Tuple of (is_available, version_string)
    """
    # Try 'magick' command first (ImageMagick 7+)
    available, version = check_command("magick")
    if available:
        return True, version
    
    # Fallback to 'convert' (ImageMagick 6)
    available, version = check_command("convert")
    if available:
        # Verify it's actually ImageMagick, not something else
        try:
            result = subprocess.run(
                ["convert", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "ImageMagick" in result.stdout:
                return True, result.stdout.strip().split('\n')[0]
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
    
    return False, None


def check_ffmpeg() -> Tuple[bool, Optional[str]]:
    """Check if FFmpeg is available.
    
    Returns:
        Tuple of (is_available, version_string)
    """
    return check_command("ffmpeg", version_flag="-version")


def get_imagemagick_command() -> Optional[str]:
    """Get the ImageMagick command to use (magick or convert).
    
    Returns:
        Command name ('magick' or 'convert'), or None if not available
    """
    available, _ = check_imagemagick()
    if not available:
        return None
    
    # Prefer 'magick' (ImageMagick 7+)
    if shutil.which("magick"):
        return "magick"
    
    # Fallback to 'convert' (ImageMagick 6)
    if shutil.which("convert"):
        return "convert"
    
    return None

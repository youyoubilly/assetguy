"""Formatting utilities for file sizes, time, etc."""

import os


def format_file_size(size_bytes):
    """Convert bytes to human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def filesize_mb(path):
    """Get file size in megabytes.
    
    Args:
        path: Path to file
        
    Returns:
        File size in MB (float)
    """
    return os.path.getsize(path) / (1024 * 1024)

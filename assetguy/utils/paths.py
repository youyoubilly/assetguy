"""Path handling utilities."""

import os
from pathlib import Path
from typing import Union


def strip_quotes(path: Union[str, Path]) -> str:
    """Remove surrounding quotes (single or double) from a path string.
    
    Args:
        path: Path string that may have quotes
        
    Returns:
        Path string without quotes
    """
    path_str = str(path).strip()
    if (path_str.startswith('"') and path_str.endswith('"')) or \
       (path_str.startswith("'") and path_str.endswith("'")):
        return path_str[1:-1]
    return path_str


def expand_path(path: Union[str, Path, None]) -> Union[Path, None]:
    """Expand ~ and environment variables in a path.
    
    Args:
        path: Path string, Path object, or None
        
    Returns:
        Expanded Path object, or None if input was None
    """
    if path is None:
        return None
    path_str = str(path)
    if not path_str or path_str == "":
        return None
    expanded = os.path.expanduser(os.path.expandvars(path_str))
    return Path(expanded)

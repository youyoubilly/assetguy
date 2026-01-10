"""Safe subprocess execution wrapper."""

import subprocess
from typing import List, Optional


def run(cmd: List[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a command with error checking.
    
    Args:
        cmd: Command and arguments as list
        check: If True, raise CalledProcessError on non-zero exit
        **kwargs: Additional arguments to subprocess.run
        
    Returns:
        CompletedProcess object
        
    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
    return subprocess.run(cmd, check=check, **kwargs)

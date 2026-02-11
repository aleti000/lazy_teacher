#!/usr/bin/env python3
"""
Shared imports and constants for Lazy Teacher.
"""

import os
import sys
import yaml
import logging
import warnings
import time
from pathlib import Path
import proxmoxer
from functools import wraps

warnings.filterwarnings("ignore", message=".*Unverified HTTPS request.*")

# Setup logger
logging.basicConfig(
    filename='lazy_teacher.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
CONFIG_DIR = Path('config')
CONFIG_DIR.mkdir(exist_ok=True)

BRIDGE_PREFIX = 'vmbr'
PVE_REALM = '@pve'
VLAN_SEPARATOR = '.'
STATIC_PREFIX = '**'
BACK_OPTION = '0'

DEFAULT_CONN = None


class SimpleConsole:
    """Simple console replacement without rich dependency."""
    
    def print(self, *args, **kwargs):
        """Print with basic color support using ANSI codes."""
        message = ' '.join(str(arg) for arg in args)
        
        # Parse basic markup like [red]text[/red]
        message = self._parse_markup(message)
        
        print(message, **kwargs)
    
    def _parse_markup(self, text: str) -> str:
        """Convert simple markup to ANSI codes."""
        colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'bold': '\033[1m',
            'reset': '\033[0m'
        }
        
        import re
        
        # Find all [tag]content[/tag] patterns
        pattern = r'\[(\w+)\](.*?)\[/\1\]'
        
        def replace_tag(match):
            tag = match.group(1)
            content = match.group(2)
            if tag in colors:
                return f"{colors[tag]}{content}{colors['reset']}"
            return content
        
        # Handle nested tags by applying repeatedly
        for _ in range(5):  # Max nesting depth
            new_text = re.sub(pattern, replace_tag, text)
            if new_text == text:
                break
            text = new_text
        
        return text
    
    def clear(self):
        """Clear console screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def status(self, message: str, spinner: str = None):
        """Simple status context manager (no spinner, just prints)."""
        return StatusContext(message)


class StatusContext:
    """Simple status context manager."""
    
    def __init__(self, message: str):
        self.message = message
    
    def __enter__(self):
        print(f"\033[94m{self.message}\033[0m")
        return self
    
    def __exit__(self, *args):
        pass


# Initialize simple console
console = SimpleConsole()
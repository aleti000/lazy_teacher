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
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

warnings.filterwarnings("ignore", message=".*Unverified HTTPS request.*")

# Setup logger
logging.basicConfig(
    filename='lazy_teacher.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize console
console = Console()

# Constants
CONFIG_DIR = Path('config')
CONFIG_DIR.mkdir(exist_ok=True)

BRIDGE_PREFIX = 'vmbr'
PVE_REALM = '@pve'
VLAN_SEPARATOR = '.'
STATIC_PREFIX = '**'
BACK_OPTION = '0'

DEFAULT_CONN = None

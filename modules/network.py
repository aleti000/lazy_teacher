#!/usr/bin/env python3
"""
Network module for Lazy Teacher.
Provides functions for network management and synchronization.
"""

from . import shared

def reload_network(proxmox, node):
    """Reload network configuration."""
    try:
        proxmox.nodes(node).network.put()
    except Exception as e:
        shared.logger.error(f"Ошибка перезагрузки сети на ноде {node}: {e}")

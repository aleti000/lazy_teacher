#!/usr/bin/env python3
"""
Network module for Lazy Teacher.
Provides optimized functions for network management and synchronization.
"""

import time
import logging
from typing import Any, Optional, Dict

from . import shared
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)

def reload_network(proxmox: Any, node: str, timeout: int = 30) -> bool:
    """
    Reload network configuration on a Proxmox node with enhanced error handling.

    Args:
        proxmox: Proxmox API connection object
        node: Name of the node to reload network on
        timeout: Timeout in seconds for the network reload operation

    Returns:
        True if reload was successful, False otherwise
    """
    with OperationTimer(logger, f"Reload network on {node}"):
        if not node or not isinstance(node, str):
            logger.error("Invalid node parameter provided for network reload")
            return False

        logger.info(f"Initiating network reload on node '{node}' with {timeout}s timeout")

        start_time = time.time()
        try:
            # Execute network reload
            result = proxmox.nodes(node).network.put()

            # Wait for operation to settle (brief pause for network reconfiguration)
            time.sleep(2)

            elapsed = time.time() - start_time
            logger.info(f"Network reload completed on node '{node}' in {elapsed:.1f}s")

            # Log result details if available
            if result:
                logger.debug(f"Network reload result: {result}")

            log_operation(logger, "Network reload successful",
                         success=True, node=node, duration=elapsed)
            return True

        except Exception as e:
            elapsed = time.time() - start_time
            log_error(logger, e, f"Network reload on {node}")

            # Provide user-friendly error messages based on error type
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                shared.console.print(f"[red]Превышено время ожидания перезагрузки сети на ноде {node}[/red]")
            elif "permission" in error_msg or "unauthorized" in error_msg:
                shared.console.print(f"[red]Недостаточно прав для перезагрузки сети на ноде {node}[/red]")
            elif "network" in error_msg or "connection" in error_msg:
                shared.console.print(f"[red]Ошибка подключения при перезагрузке сети на ноде {node}[/red]")
            else:
                shared.console.print(f"[red]Ошибка перезагрузки сети на ноде {node}: {e}[/red]")

            log_operation(logger, "Network reload failed",
                         success=False, node=node, duration=elapsed, error=str(e))
            return False

def get_node_network_status(proxmox: Any, node: str) -> Optional[Dict[str, Any]]:
    """
    Get current network configuration status for a node.

    Args:
        proxmox: Proxmox API connection object
        node: Name of the node to check

    Returns:
        Network configuration dict if successful, None otherwise
    """
    with OperationTimer(logger, f"Get network status for {node}"):
        try:
            network_config = proxmox.nodes(node).network.get()
            logger.debug(f"Retrieved network config for node {node}: {len(network_config.get('data', []))} interfaces")
            return network_config
        except Exception as e:
            log_error(logger, e, f"Get network status for {node}")
            return None

def apply_network_changes(proxmox: Any, node: str, changes: Dict[str, Any]) -> bool:
    """
    Apply network configuration changes to a node.

    Args:
        proxmox: Proxmox API connection object
        node: Name of the node to apply changes to
        changes: Dictionary of network changes to apply

    Returns:
        True if changes were applied successfully, False otherwise
    """
    with OperationTimer(logger, f"Apply network changes on {node}"):
        if not changes:
            logger.warning(f"No changes provided for network update on node {node}")
            return True

        try:
            # Apply changes via the network API
            proxmox.nodes(node).network.put(changes)

            logger.info(f"Network changes applied to node {node}: {len(changes)} modifications")
            log_operation(logger, "Network changes applied",
                         success=True, node=node, changes_count=len(changes))
            return True

        except Exception as e:
            log_error(logger, e, f"Apply network changes on {node}")
            shared.console.print(f"[red]Не удалось применить изменения сети на ноде {node}: {e}[/red]")
            return False

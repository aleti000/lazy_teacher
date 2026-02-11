#!/usr/bin/env python3
"""
Tasks module for Lazy Teacher.
Provides unified task waiting functionality.
"""

import time
import logging
from .logger import get_logger, log_error, OperationTimer

logger = get_logger(__name__)

def wait_for_task(
    proxmox,
    node: str,
    task_id: str,
    task_type: str = "generic",
    timeout: int = 300,
    check_interval: float = 2.0,
    raise_exceptions: bool = True
) -> bool:
    """
    Universal function for waiting for Proxmox tasks to complete.

    Args:
        proxmox: ProxmoxAPI connection instance
        node: Node name where task is running
        task_id: Task identifier
        task_type: Type of task for logging ("clone", "migration", "template", etc.)
        timeout: Maximum time to wait in seconds
        check_interval: Time between status checks in seconds
        raise_exceptions: If True, raises exceptions on failure. If False, returns False.

    Returns:
        bool: True if task completed successfully, False otherwise (if raise_exceptions=False)

    Raises:
        Exception: If task failed and raise_exceptions=True
        TimeoutError: If task timed out
    """
    operation = f"Waiting for {task_type} task {task_id}"

    with OperationTimer(logger, operation):
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                status = proxmox.nodes(node).tasks(task_id).status.get()

                if status['status'] == 'stopped':
                    exit_status = status.get('exitstatus', '')
                    if exit_status.startswith('OK'):
                        logger.info(f"{task_type.title()} task completed successfully", extra={
                            'task_id': task_id,
                            'node': node,
                            'duration': time.time()-start_time
                        })
                        return True
                    else:
                        error_msg = f"{task_type.title()} task failed: {exit_status}"
                        logger.error(error_msg, extra={
                            'task_id': task_id,
                            'node': node
                        })
                        if raise_exceptions:
                            raise Exception(error_msg)
                        return False

            except Exception as e:
                error_msg = f"Error checking {task_type} task status: {e}"
                log_error(logger, e, f"Check {task_type} task status (task_id={task_id}, node={node})")
                if raise_exceptions:
                    raise Exception(error_msg) from e
                return False

            time.sleep(check_interval)

        timeout_msg = f"Timeout waiting for {task_type} task to complete"
        logger.error(timeout_msg, extra={
            'task_id': task_id,
            'node': node,
            'timeout': timeout
        })
        if raise_exceptions:
            raise TimeoutError(timeout_msg)
        return False

# Legacy function aliases for backward compatibility
def wait_for_clone_task(proxmox, node, task_id, timeout=1800):
    """Wait for clone task to complete (legacy function).
    
    Default timeout: 1800 seconds (30 minutes) - full clone can take a long time.
    """
    return wait_for_task(proxmox, node, task_id, "clone", timeout, 2.0, True)

def wait_for_migration_task(proxmox, node, task_id, timeout=1200):
    """Wait for migration task to complete (legacy function)."""
    return wait_for_task(proxmox, node, task_id, "migration", timeout, 5.0, True)

def wait_for_snapshot_task(proxmox, node, task_id, timeout=600):
    """Wait for snapshot task to complete (create or delete).
    
    Default timeout: 600 seconds (10 minutes).
    """
    return wait_for_task(proxmox, node, task_id, "snapshot", timeout, 2.0, True)

def wait_for_template_task(proxmox, node, task_id, timeout=1800):
    """Wait for template task to complete (legacy function).
    
    Default timeout: 1800 seconds (30 minutes).
    """
    return wait_for_task(proxmox, node, task_id, "template", timeout, 2.0, True)

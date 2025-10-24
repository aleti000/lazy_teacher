#!/usr/bin/env python3
"""
Tasks module for Lazy Teacher.
Provides functions for waiting for Proxmox tasks.
"""

import time
from . import shared

def wait_for_clone_task(proxmox, node, task_id, timeout=600):
    """Wait for clone task to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = proxmox.nodes(node).tasks(task_id).status.get()
            if status['status'] == 'stopped':
                if status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    raise Exception(f"Clone failed: {status.get('exitstatus')}")
        except Exception as e:
            raise Exception(f"Error checking clone task: {e}")
        time.sleep(2)
    raise TimeoutError("Timeout waiting for clone task to complete")

def wait_for_migration_task(proxmox, node, task_id, timeout=1200):
    """Wait for migration task to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = proxmox.nodes(node).tasks(task_id).status.get()
            if status['status'] == 'stopped':
                if status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    raise Exception(f"Migration failed: {status.get('exitstatus')}")
        except Exception as e:
            raise Exception(f"Error checking migration task: {e}")
        time.sleep(5)
    raise TimeoutError("Timeout waiting for migration task to complete")

def wait_for_task(proxmox, node, task_id, timeout=300):
    """
    Ожидает завершения задачи Proxmox.
    Возвращает True при успехе, False при ошибке или таймауте.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            task_status = proxmox.nodes(node).tasks(task_id).status.get()
            if task_status['status'] == 'stopped':
                if task_status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    print(f"Task failed: {task_status.get('exitstatus')}")
                    return False
        except Exception as e:
            print(f"Error checking task status: {e}")
            return False
        time.sleep(2)
    print("Timeout waiting for task to complete")
    return False

def wait_for_template_task(proxmox, node, task_id, timeout=600):
    """Wait for template task to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = proxmox.nodes(node).tasks(task_id).status.get()
            if status['status'] == 'stopped':
                if status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    raise Exception(f"Template creation failed: {status.get('exitstatus')}")
        except Exception as e:
            raise Exception(f"Error checking template task: {e}")
        time.sleep(2)
    raise TimeoutError("Timeout waiting for template creation task to complete")

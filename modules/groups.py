#!/usr/bin/env python3
"""
Groups module for Lazy Teacher.
Provides management for stand deployment groups.
Groups are created during deployment and stored in config/groups.yaml
"""

import yaml
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging
from . import shared
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)

GROUPS_FILE = shared.CONFIG_DIR / 'groups.yaml'


def get_groups() -> Dict[str, Any]:
    """
    Load groups from groups.yaml.
    
    Returns:
        Dictionary with groups:
        {
            "de-4sa": {
                "stand_config": "de_stand.yaml",
                "user_list": "4sa_list.yaml",
                "users": ["user1@pve", "user2@pve"],
                "created_at": "2026-02-10 14:30:00"
            }
        }
    """
    if not GROUPS_FILE.exists():
        logger.debug(f"Groups file {GROUPS_FILE} not found, returning empty dict")
        return {}
    
    try:
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        logger.debug(f"Loaded {len(data)} groups")
        return data
    except Exception as e:
        log_error(logger, e, "Load groups", file=str(GROUPS_FILE))
        return {}


def save_groups(groups: Dict[str, Any]) -> bool:
    """
    Save groups to groups.yaml.
    
    Args:
        groups: Groups dictionary
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
            yaml.safe_dump(groups, f, default_flow_style=False, allow_unicode=True)
        logger.debug(f"Saved {len(groups)} groups")
        return True
    except Exception as e:
        log_error(logger, e, "Save groups", file=str(GROUPS_FILE))
        return False


def create_group(group_name: str, stand_config: str, 
                user_list: str, users: List[str]) -> bool:
    """
    Create a new deployment group.
    
    Args:
        group_name: Name of the group (e.g., "de-4sa")
        stand_config: Stand configuration filename
        user_list: User list filename
        users: List of usernames in this group
        
    Returns:
        True if created successfully
    """
    groups = get_groups()
    
    groups[group_name] = {
        'stand_config': stand_config,
        'user_list': user_list,
        'users': users,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    logger.info(f"Created group '{group_name}' with {len(users)} users")
    log_operation(logger, "Create group", group_name=group_name, users_count=len(users))
    
    return save_groups(groups)


def get_group(group_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific group by name.
    
    Args:
        group_name: Name of the group
        
    Returns:
        Group dictionary or None if not found
    """
    groups = get_groups()
    return groups.get(group_name)


def group_exists(group_name: str) -> bool:
    """
    Check if a group exists.
    
    Args:
        group_name: Name of the group
        
    Returns:
        True if group exists
    """
    groups = get_groups()
    return group_name in groups


def delete_group(group_name: str) -> bool:
    """
    Delete a group.
    
    Args:
        group_name: Name of the group to delete
        
    Returns:
        True if deleted successfully
    """
    groups = get_groups()
    
    if group_name in groups:
        del groups[group_name]
        logger.info(f"Deleted group '{group_name}'")
        log_operation(logger, "Delete group", group_name=group_name)
        return save_groups(groups)
    
    logger.warning(f"Group '{group_name}' not found for deletion")
    return False


def get_group_users(group_name: str) -> List[str]:
    """
    Get list of users in a group.
    
    Args:
        group_name: Name of the group
        
    Returns:
        List of usernames (may be empty)
    """
    group = get_group(group_name)
    if group:
        return group.get('users', [])
    return []


def add_user_to_group(group_name: str, username: str) -> bool:
    """
    Add a user to an existing group.
    
    Args:
        group_name: Name of the group
        username: Username to add
        
    Returns:
        True if added successfully
    """
    groups = get_groups()
    
    if group_name not in groups:
        logger.warning(f"Group '{group_name}' not found")
        return False
    
    if 'users' not in groups[group_name]:
        groups[group_name]['users'] = []
    
    if username not in groups[group_name]['users']:
        groups[group_name]['users'].append(username)
        logger.info(f"Added user '{username}' to group '{group_name}'")
        return save_groups(groups)
    
    logger.debug(f"User '{username}' already in group '{group_name}'")
    return True


def remove_user_from_group(group_name: str, username: str) -> bool:
    """
    Remove a user from a group.
    
    Args:
        group_name: Name of the group
        username: Username to remove
        
    Returns:
        True if removed successfully
    """
    groups = get_groups()
    
    if group_name not in groups:
        logger.warning(f"Group '{group_name}' not found")
        return False
    
    if 'users' in groups[group_name] and username in groups[group_name]['users']:
        groups[group_name]['users'].remove(username)
        logger.info(f"Removed user '{username}' from group '{group_name}'")
        
        # Delete group if no users left
        if not groups[group_name]['users']:
            logger.info(f"Group '{group_name}' has no users, deleting")
            del groups[group_name]
        
        return save_groups(groups)
    
    logger.debug(f"User '{username}' not in group '{group_name}'")
    return True


def get_groups_list() -> List[str]:
    """
    Get list of all group names.
    
    Returns:
        List of group names
    """
    groups = get_groups()
    return list(groups.keys())


def get_groups_with_users() -> Dict[str, List[str]]:
    """
    Get all groups with their users.
    
    Returns:
        Dictionary mapping group names to user lists
    """
    groups = get_groups()
    return {name: data.get('users', []) for name, data in groups.items()}


def find_user_group(username: str) -> Optional[str]:
    """
    Find which group a user belongs to.
    
    Args:
        username: Username to search for
        
    Returns:
        Group name if found, None otherwise
    """
    groups = get_groups()
    
    for group_name, group_data in groups.items():
        if username in group_data.get('users', []):
            return group_name
    
    return None


def generate_group_name(stand_config: str, user_list: str) -> str:
    """
    Generate group name from stand config and user list names.
    
    Args:
        stand_config: Stand configuration filename (e.g., "de_stand.yaml")
        user_list: User list filename (e.g., "4sa_list.yaml")
        
    Returns:
        Group name (e.g., "de-4sa")
    """
    # Remove suffixes and get base names
    stand_name = Path(stand_config).stem.replace('_stand', '')
    list_name = Path(user_list).stem.replace('_list', '')
    
    return f"{stand_name}-{list_name}"
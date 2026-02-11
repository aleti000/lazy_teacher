#!/usr/bin/env python3
"""
Sync Templates module for Lazy Teacher.
Provides optimized functions for template synchronization across Proxmox nodes.
Now uses centralized templates.yaml registry instead of stand config files.
"""

import string
import random
from typing import Dict, List, Optional, Any, Set
import logging

from . import shared
from .templates import (
    get_template_registry, get_replica_vmid, get_source_node,
    register_template, register_replica, verify_template_on_node,
    ensure_template_on_node
)
from .tasks import wait_for_clone_task, wait_for_template_task, wait_for_migration_task
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)
console = shared.console


def get_unique_templates(stand: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """
    Extract unique templates from stand configuration.
    
    Args:
        stand: Stand configuration dictionary
        
    Returns:
        Dictionary mapping template_vmid to template info:
        {
            100: {
                'source_node': 'pve1',
                'machines': ['gw', 'srv']  # Machine names using this template
            }
        }
    """
    templates = {}
    
    for machine in stand.get('machines', []):
        template_vmid = machine.get('template_vmid')
        template_node = machine.get('template_node')
        
        if template_vmid is None:
            logger.warning(f"Machine {machine.get('name', 'unknown')} missing template_vmid")
            continue
            
        if template_vmid not in templates:
            templates[template_vmid] = {
                'source_node': template_node,
                'machines': []
            }
        
        templates[template_vmid]['machines'].append(machine.get('name', 'unknown'))
        
        # Update source node if not set
        if not templates[template_vmid]['source_node']:
            templates[template_vmid]['source_node'] = template_node
    
    logger.debug(f"Found {len(templates)} unique templates in stand")
    return templates


def sync_templates(prox, stand: Dict[str, Any], nodes: List[str]) -> bool:
    """
    Sync templates to all nodes using centralized templates.yaml registry.
    
    This function:
    1. Extracts unique templates from stand config
    2. Checks templates.yaml registry for existing replicas
    3. Creates missing replicas and registers them in templates.yaml
    4. Updates stand config with replica VMIDs for backward compatibility
    
    Args:
        prox: Proxmox API connection object
        stand: Stand configuration dictionary containing machines
        nodes: List of all available nodes
        
    Returns:
        True if any templates were synchronized, False if no changes were made
    """
    if not stand or not nodes:
        logger.warning("Invalid input: stand or nodes is empty")
        return False

    with OperationTimer(logger, "Sync templates across nodes"):
        logger.info(f"Starting template synchronization for {len(nodes)} nodes")
        
        # Get unique templates from stand
        templates = get_unique_templates(stand)
        if not templates:
            logger.warning("No valid machines with template_vmid found in stand")
            return False
        
        updated = False
        
        # Process each template
        for template_vmid, template_info in templates.items():
            source_node = template_info['source_node']
            machine_names = template_info['machines']
            
            if not source_node:
                logger.error(f"Template {template_vmid} has no source node")
                continue
            
            logger.info(f"Processing template {template_vmid} (source: {source_node}, used by: {machine_names})")
            
            # Register template in global registry if not exists
            register_template(template_vmid, source_node)
            
            # Sync to each target node
            for target_node in nodes:
                if target_node == source_node:
                    continue
                
                # Check if replica already exists in registry and is valid
                replica_vmid = get_replica_vmid(template_vmid, target_node)
                
                if replica_vmid and verify_template_on_node(prox, target_node, replica_vmid):
                    logger.debug(f"Template {template_vmid} replica {replica_vmid} already exists on {target_node}")
                    continue
                
                # Create replica
                console.print(f"[cyan]Синхронизация шаблона {template_vmid} на ноду {target_node}...[/cyan]")
                
                new_replica_vmid = ensure_template_on_node(
                    prox, template_vmid, source_node, target_node
                )
                
                if new_replica_vmid:
                    updated = True
                    # Update stand config with replica info for backward compatibility
                    _update_stand_replicas(stand, template_vmid, target_node, new_replica_vmid)
                    console.print(f"[green]Шаблон {template_vmid} синхронизирован на {target_node} (VMID: {new_replica_vmid})[/green]")
                else:
                    console.print(f"[red]Ошибка синхронизации шаблона {template_vmid} на {target_node}[/red]")
        
        logger.info(f"Template synchronization {'completed with updates' if updated else 'completed - no changes needed'}")
        return updated


def _update_stand_replicas(stand: Dict[str, Any], template_vmid: int, 
                          target_node: str, replica_vmid: int) -> None:
    """
    Update stand configuration with replica VMID for backward compatibility.
    
    Args:
        stand: Stand configuration dictionary
        template_vmid: Original template VMID
        target_node: Node where replica exists
        replica_vmid: Replica VMID on target node
    """
    for machine in stand.get('machines', []):
        if machine.get('template_vmid') == template_vmid:
            if 'replicas' not in machine:
                machine['replicas'] = {}
            machine['replicas'][target_node] = replica_vmid
            logger.debug(f"Updated stand config: machine {machine.get('name')} replica on {target_node} = {replica_vmid}")


def get_template_vmid_for_node(stand: Dict[str, Any], machine: Dict[str, Any], 
                               target_node: str, prox=None) -> Optional[int]:
    """
    Get the appropriate template VMID for a target node.
    
    First checks machine's replicas dict, then checks global registry,
    then falls back to original template_vmid.
    
    Args:
        stand: Stand configuration (for backward compatibility)
        machine: Machine configuration dictionary
        target_node: Target node name
        prox: Optional Proxmox connection for verification
        
    Returns:
        Template VMID to use on target node
    """
    template_vmid = machine.get('template_vmid')
    
    if not template_vmid:
        return None
    
    # First check machine's replicas (backward compatibility)
    replicas = machine.get('replicas', {})
    if target_node in replicas:
        return int(replicas[target_node])
    
    # Then check global registry
    replica_vmid = get_replica_vmid(template_vmid, target_node)
    if replica_vmid:
        return replica_vmid
    
    # If target node is source node, use original
    source_node = machine.get('template_node')
    if target_node == source_node:
        return template_vmid
    
    # If we have prox connection, try to ensure template exists
    if prox and source_node:
        new_replica = ensure_template_on_node(prox, template_vmid, source_node, target_node)
        if new_replica:
            # Update stand config for backward compatibility
            _update_stand_replicas(stand, template_vmid, target_node, new_replica)
            return new_replica
    
    # Fallback to original
    return template_vmid


def sync_all_templates_in_cluster(prox, nodes: List[str]) -> bool:
    """
    Sync all known templates from registry to all nodes.
    Useful for initial cluster setup or maintenance.
    
    Args:
        prox: Proxmox API connection
        nodes: List of all nodes in cluster
        
    Returns:
        True if any sync performed
    """
    registry = get_template_registry()
    
    if not registry:
        logger.info("No templates in registry to sync")
        return False
    
    updated = False
    
    for template_vmid_str, template_data in registry.items():
        template_vmid = int(template_vmid_str)
        source_node = template_data.get('source_node')
        
        if not source_node:
            logger.warning(f"Template {template_vmid} has no source node in registry")
            continue
        
        for target_node in nodes:
            if target_node == source_node:
                continue
            
            replica_vmid = get_replica_vmid(template_vmid, target_node)
            
            if replica_vmid and verify_template_on_node(prox, target_node, replica_vmid):
                continue
            
            console.print(f"[cyan]Синхронизация шаблона {template_vmid} на {target_node}...[/cyan]")
            
            new_replica = ensure_template_on_node(prox, template_vmid, source_node, target_node)
            
            if new_replica:
                updated = True
                console.print(f"[green]Шаблон {template_vmid} -> {target_node} (VMID: {new_replica})[/green]")
    
    return updated
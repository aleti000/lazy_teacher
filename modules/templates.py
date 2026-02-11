#!/usr/bin/env python3
"""
Templates Registry module for Lazy Teacher.
Provides centralized template management across Proxmox nodes.
Stores template replica mappings in config/templates.yaml
"""

import yaml
from pathlib import Path
from typing import Dict, Optional, Any
import logging
from . import shared
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)

TEMPLATES_FILE = shared.CONFIG_DIR / 'templates.yaml'


def get_template_registry() -> Dict[str, Any]:
    """
    Load template registry from templates.yaml.
    
    Returns:
        Dictionary with template mappings:
        {
            "100": {  # Original VMID as string
                "source_node": "pve1",
                "replicas": {
                    "pve2": 1000,
                    "pve3": 1001
                }
            }
        }
    """
    if not TEMPLATES_FILE.exists():
        logger.debug(f"Templates file {TEMPLATES_FILE} not found, returning empty registry")
        return {}
    
    try:
        with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        logger.debug(f"Loaded template registry with {len(data)} templates")
        return data
    except Exception as e:
        log_error(logger, e, "Load template registry", file=str(TEMPLATES_FILE))
        return {}


def save_template_registry(registry: Dict[str, Any]) -> bool:
    """
    Save template registry to templates.yaml.
    
    Args:
        registry: Template registry dictionary
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            yaml.safe_dump(registry, f, default_flow_style=False, allow_unicode=True)
        logger.debug(f"Saved template registry with {len(registry)} templates")
        return True
    except Exception as e:
        log_error(logger, e, "Save template registry", file=str(TEMPLATES_FILE))
        return False


def get_replica_vmid(original_vmid: int, target_node: str) -> Optional[int]:
    """
    Get replica VMID for a template on a specific node.
    
    Args:
        original_vmid: Original template VMID
        target_node: Target node name
        
    Returns:
        Replica VMID if exists, None otherwise
    """
    registry = get_template_registry()
    template_key = str(original_vmid)
    
    if template_key in registry:
        replicas = registry[template_key].get('replicas', {})
        replica_vmid = replicas.get(target_node)
        if replica_vmid:
            logger.debug(f"Found replica {replica_vmid} for template {original_vmid} on {target_node}")
            return int(replica_vmid)
    
    return None


def get_source_node(original_vmid: int) -> Optional[str]:
    """
    Get source node for a template.
    
    Args:
        original_vmid: Original template VMID
        
    Returns:
        Source node name if exists, None otherwise
    """
    registry = get_template_registry()
    template_key = str(original_vmid)
    
    if template_key in registry:
        return registry[template_key].get('source_node')
    
    return None


def register_template(original_vmid: int, source_node: str) -> bool:
    """
    Register a new template in the registry.
    
    Args:
        original_vmid: Original template VMID
        source_node: Node where the original template exists
        
    Returns:
        True if registered successfully
    """
    registry = get_template_registry()
    template_key = str(original_vmid)
    
    if template_key not in registry:
        registry[template_key] = {
            'source_node': source_node,
            'replicas': {}
        }
    else:
        # Update source node if different
        registry[template_key]['source_node'] = source_node
    
    return save_template_registry(registry)


def register_replica(original_vmid: int, source_node: str, 
                    target_node: str, replica_vmid: int) -> bool:
    """
    Register a template replica in the registry.
    
    Args:
        original_vmid: Original template VMID
        source_node: Node where the original template exists
        target_node: Node where the replica was created
        replica_vmid: VMID of the replica on target node
        
    Returns:
        True if registered successfully
    """
    registry = get_template_registry()
    template_key = str(original_vmid)
    
    if template_key not in registry:
        registry[template_key] = {
            'source_node': source_node,
            'replicas': {}
        }
    else:
        # Update source node
        registry[template_key]['source_node'] = source_node
    
    # Register replica
    if 'replicas' not in registry[template_key]:
        registry[template_key]['replicas'] = {}
    
    registry[template_key]['replicas'][target_node] = replica_vmid
    
    logger.info(f"Registered replica: template {original_vmid} -> {replica_vmid} on {target_node}")
    return save_template_registry(registry)


def remove_replica(original_vmid: int, target_node: str) -> bool:
    """
    Remove a replica entry from the registry.
    
    Args:
        original_vmid: Original template VMID
        target_node: Node to remove replica for
        
    Returns:
        True if removed successfully
    """
    registry = get_template_registry()
    template_key = str(original_vmid)
    
    if template_key in registry and 'replicas' in registry[template_key]:
        if target_node in registry[template_key]['replicas']:
            del registry[template_key]['replicas'][target_node]
            logger.info(f"Removed replica for template {original_vmid} on {target_node}")
            return save_template_registry(registry)
    
    return False


def get_all_nodes_with_template(original_vmid: int) -> list:
    """
    Get all nodes that have a replica of the template.
    
    Args:
        original_vmid: Original template VMID
        
    Returns:
        List of node names (including source node)
    """
    registry = get_template_registry()
    template_key = str(original_vmid)
    
    nodes = []
    
    if template_key in registry:
        # Add source node
        source = registry[template_key].get('source_node')
        if source:
            nodes.append(source)
        
        # Add replica nodes
        replicas = registry[template_key].get('replicas', {})
        nodes.extend(replicas.keys())
    
    return nodes


def verify_template_on_node(prox, node: str, vmid: int) -> bool:
    """
    Verify if template exists and is actually a template on the specified node.
    
    Args:
        prox: Proxmox API connection
        node: Node name
        vmid: VM ID to check
        
    Returns:
        True if template exists and is valid, False otherwise
    """
    try:
        vms_on_node = prox.nodes(node).qemu.get()
        template_present = any(
            vm['vmid'] == vmid and vm.get('template') == 1
            for vm in vms_on_node
        )
        if template_present:
            logger.debug(f"Template {vmid} verified on node {node}")
        return template_present
    except Exception as e:
        logger.warning(f"Failed to verify template {vmid} on node {node}: {e}")
        return False


def ensure_template_on_node(prox, original_vmid: int, source_node: str, 
                           target_node: str) -> Optional[int]:
    """
    Ensure template exists on target node. 
    Returns replica VMID if exists or after creation.
    
    Args:
        prox: Proxmox API connection
        original_vmid: Original template VMID
        source_node: Node where original template exists
        target_node: Target node for replica
        
    Returns:
        Replica VMID on target node, or None if failed
    """
    from .tasks import wait_for_clone_task, wait_for_template_task, wait_for_migration_task
    
    # Check registry first
    replica_vmid = get_replica_vmid(original_vmid, target_node)
    
    if replica_vmid:
        # Verify it actually exists
        if verify_template_on_node(prox, target_node, replica_vmid):
            logger.debug(f"Template {original_vmid} replica {replica_vmid} exists on {target_node}")
            return replica_vmid
        else:
            # Remove invalid entry
            remove_replica(original_vmid, target_node)
            logger.warning(f"Removed invalid replica entry for {original_vmid} on {target_node}")
    
    # Need to create replica
    with OperationTimer(logger, f"Create template replica {original_vmid} -> {target_node}"):
        try:
            # Generate new VMID for clone
            clone_vmid = int(prox.cluster.nextid.get())
            safe_name = f"tpl-{original_vmid}-{target_node}"
            
            logger.info(f"Creating template clone {clone_vmid} from {original_vmid} on {source_node}")
            shared.console.print(f"[cyan]Создание реплики шаблона {original_vmid} на {target_node}...[/cyan]")
            
            # Create full clone
            clone_task_id = prox.nodes(source_node).qemu(original_vmid).clone.post(
                newid=clone_vmid,
                name=safe_name,
                full=1
            )
            
            # Wait for clone completion
            wait_for_clone_task(prox, source_node, clone_task_id)
            
            # Convert to template
            template_task_id = prox.nodes(source_node).qemu(clone_vmid).template.post()
            wait_for_template_task(prox, source_node, template_task_id)
            
            # Migrate to target node
            migrate_result = prox.nodes(source_node).qemu(clone_vmid).migrate.post(
                target=target_node,
                online=0
            )
            
            if migrate_result:
                migrate_upid = migrate_result.get('data') if isinstance(migrate_result, dict) else migrate_result
                if migrate_upid and wait_for_migration_task(prox, source_node, migrate_upid):
                    # Register in global registry
                    register_replica(original_vmid, source_node, target_node, clone_vmid)
                    
                    shared.console.print(f"[green]Реплика шаблона {original_vmid} создана на {target_node} (VMID: {clone_vmid})[/green]")
                    log_operation(logger, "Template replica created",
                                success=True,
                                original_vmid=original_vmid,
                                replica_vmid=clone_vmid,
                                source_node=source_node,
                                target_node=target_node)
                    return clone_vmid
            
            logger.error(f"Failed to migrate template {clone_vmid} to {target_node}")
            return None
            
        except Exception as e:
            log_error(logger, e, f"Create template replica {original_vmid} -> {target_node}")
            return None
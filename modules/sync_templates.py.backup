
#!/usr/bin/env python3
"""
Sync Templates module for Lazy Teacher.
Provides optimized functions for template synchronization across Proxmox nodes.
"""

import string
import random
from typing import Dict, List, Optional, Any, Tuple, Set, DefaultDict
from collections import defaultdict
import logging

from . import shared
from .tasks import wait_for_clone_task as wait_clone_func, wait_for_template_task as wait_template_func, wait_for_migration_task as wait_migration_func
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)
console = shared.console

def _group_machines_by_template(stand: Dict[str, Any]) -> DefaultDict[int, List[Dict[str, Any]]]:
    """
    Group machines by their template VMID to avoid redundant operations.

    Args:
        stand: Stand configuration dictionary

    Returns:
        Dictionary mapping template_vmid to list of machines
    """
    template_groups: DefaultDict[int, List[Dict[str, Any]]] = defaultdict(list)

    for machine in stand.get('machines', []):
        template_vmid = machine.get('template_vmid')
        if template_vmid is not None:
            template_groups[template_vmid].append(machine)
        else:
            logger.warning(f"Machine {machine.get('name', 'unknown')} missing template_vmid")

    logger.debug(f"Grouped machines into {len(template_groups)} template groups")
    return template_groups

def _verify_template_exists(prox, node: str, vmid: int) -> bool:
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

def _remove_invalid_replica(machines: List[Dict[str, Any]], node: str) -> None:
    """
    Remove invalid replica entries from machines when verification fails.

    Args:
        machines: List of machines using the same template
        node: Node where replica was supposed to exist
    """
    for machine in machines:
        if 'replicas' in machine and node in machine['replicas']:
            del machine['replicas'][node]
            logger.debug(f"Removed invalid replica entry for node {node} from machine {machine.get('name')}")

def _create_template_replica(prox, original_node: str, template_vmid: int,
                           target_node: str, machines: List[Dict[str, Any]]) -> bool:
    """
    Create and migrate a template replica to target node.

    Args:
        prox: Proxmox API connection
        original_node: Source node where template exists
        template_vmid: Template VMID to replicate
        target_node: Target node for migration
        machines: Machines that will have this replica assigned

    Returns:
        True if replica created successfully, False otherwise
    """
    try:
        # Generate new VMID for clone
        clone_vmid = prox.cluster.nextid.get()
        safe_name = f"tpl-{original_node}-{template_vmid}"

        logger.info(f"Creating template clone {clone_vmid} from {template_vmid} on {original_node}")

        # Create full clone
        clone_task_id = prox.nodes(original_node).qemu(template_vmid).clone.post(
            newid=clone_vmid,
            name=safe_name,
            full=1
        )

        # Wait for clone completion
        try:
            wait_clone_func(prox, original_node, clone_task_id)
        except Exception as e:
            log_error(logger, e, f"Clone template {template_vmid}")
            return False

        # Convert to template
        try:
            template_task_id = prox.nodes(original_node).qemu(clone_vmid).template.post()
            wait_template_func(prox, original_node, template_task_id)
        except Exception as e:
            log_error(logger, e, f"Convert to template {clone_vmid}")
            return False

        # Migrate to target node
        try:
            migrate_result = prox.nodes(original_node).qemu(clone_vmid).migrate.post(
                target=target_node,
                online=0
            )

            if migrate_result:
                migrate_upid = migrate_result.get('data') if isinstance(migrate_result, dict) else migrate_result
                if migrate_upid and wait_migration_func(prox, original_node, migrate_upid):
                    # Assign replica to all machines
                    _assign_replicas(machines, target_node, clone_vmid)
                    console.print(
                        f"[green]Шаблон для {len(machines)} машины(н) с VMID {template_vmid} "
                        f"синхронизирован на ноду {target_node}[/green]"
                    )
                    log_operation(logger, "Template replica created",
                                success=True,
                                template_vmid=template_vmid,
                                clone_vmid=clone_vmid,
                                target_node=target_node,
                                machine_count=len(machines))
                    return True
                else:
                    logger.error(f"Migration of template {clone_vmid} to {target_node} failed or timed out")
            else:
                logger.error(f"Failed to initiate migration of template {clone_vmid} to {target_node}")
        except Exception as e:
            log_error(logger, e, f"Migrate template {clone_vmid} to {target_node}")

        return False

    except Exception as e:
        log_error(logger, e, f"Create template replica {template_vmid} -> {target_node}")
        return False

def _assign_replicas(machines: List[Dict[str, Any]], node: str, vmid: int) -> None:
    """
    Assign replica VMID to all machines for specified node.

    Args:
        machines: List of machines to update
        node: Node where replica exists
        vmid: Replica VMID on that node
    """
    for machine in machines:
        if 'replicas' not in machine:
            machine['replicas'] = {}
        machine['replicas'][node] = vmid
        logger.debug(f"Assigned replica {vmid} on {node} to machine {machine.get('name')}")
def sync_templates(prox, stand: Dict[str, Any], nodes: List[str]) -> bool:
    """
    Sync templates to all nodes, ensure replicas exist where needed.

    This function groups machines by their template VMID, then ensures each template
    has replicas on all required nodes. It creates clones, converts them to templates,
    migrates to target nodes, and updates machine configurations accordingly.

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

        updated = False

        # Group machines by template to avoid redundant operations
        template_groups = _group_machines_by_template(stand)
        if not template_groups:
            logger.warning("No valid machines with template_vmid found in stand")
            return False

        # Process each template group
        for template_vmid, machines in template_groups.items():
            logger.info(f"Processing template {template_vmid} used by {len(machines)} machines")

            # Get original node for this template
            original_machine = machines[0]
            original_node = original_machine.get('template_node')
            if not original_node:
                logger.error(f"Machine {original_machine.get('name', 'unknown')} missing template_node")
                continue

            # Sync template to each target node
            for node in nodes:
                if node == original_node:
                    continue  # Skip original node

                logger.debug(f"Checking template {template_vmid} replica on node {node}")

                # Check if replica already exists and is valid
                replica_vmid = _check_existing_replica(machines, node)
                if replica_vmid and _verify_template_exists(prox, node, replica_vmid):
                    logger.debug(f"Valid template {replica_vmid} replica exists on {node}")
                    continue

                # Replica invalid or missing, create new one
                if replica_vmid:
                    _remove_invalid_replica(machines, node)

                logger.info(f"Creating template {template_vmid} replica on {node}")
                if _create_template_replica(prox, original_node, template_vmid, node, machines):
                    updated = True
                    log_operation(logger, "Template synchronized",
                                success=True,
                                template_vmid=template_vmid,
                                target_node=node,
                                machine_count=len(machines))
                else:
                    logger.error(f"Failed to create template replica {template_vmid} on {node}")

        logger.info(f"Template synchronization {'completed with updates' if updated else 'completed - no changes needed'}")
        return updated

def _check_existing_replica(machines: List[Dict[str, Any]], node: str) -> Optional[int]:
    """
    Check if any machine in the group has a recorded replica on the target node.

    Args:
        machines: List of machines using the same template
        node: Target node to check

    Returns:
        Replica VMID if found, None otherwise
    """
    for machine in machines:
        replicas = machine.get('replicas', {})
        if node in replicas:
            return int(replicas[node])
    return None

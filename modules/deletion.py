#!/usr/bin/env python3
"""
Deletion module for Lazy Teacher.
Provides optimized functions for deleting stands and users.
"""

import glob
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set
import logging

from . import shared
from .connections import get_proxmox_connection
from .tasks import wait_for_task as wait_task_func
from .network import reload_network as reload_net_func
from .logger import get_logger, log_operation, log_error, OperationTimer
from rich.table import Table

logger = get_logger(__name__)

def _normalize_user(user: str) -> str:
    """Normalize user format, ensuring @pve domain."""
    if not user:
        raise ValueError("User cannot be empty")
    if '@' not in user:
        user += '@pve'
    return user

def _get_user_lists() -> List[Tuple[str, str]]:
    """Get list of available user list files."""
    pattern = str(shared.CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    return [(Path(file).stem.replace('_list', ''), file) for file in files]

def _load_user_list(name: str) -> Optional[List[str]]:
    """Load user list from YAML file."""
    file_path = shared.CONFIG_DIR / f"{name}_list.yaml"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        users = data.get('users', [])
        return users if isinstance(users, list) else []
    except FileNotFoundError:
        logger.warning(f"User list {name} not found")
        return None
    except Exception as e:
        log_error(logger, e, f"Load user list {name}")
        return None

def _select_user_list() -> Optional[Tuple[str, str, List[str]]]:
    """Select a user list interactively."""
    user_lists = _get_user_lists()
    if not user_lists:
        shared.console.print("[yellow]Нет списков пользователей.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return None

    table = Table(title="Выбор списка пользователей")
    table.add_column("№", style="cyan", justify="center")
    table.add_column("Имя списка", style="green")
    table.add_column("Пользователей", style="magenta", justify="center")

    for i, (name, file_path) in enumerate(user_lists, 1):
        try:
            users = _load_user_list(name) or []
            table.add_row(str(i), name, str(len(users)))
        except Exception:
            table.add_row(str(i), name, "Ошибка")

    shared.console.print(table)

    try:
        choice = int(input("Выберите номер списка: ")) - 1
        if 0 <= choice < len(user_lists):
            name, file_path = user_lists[choice]
            users = _load_user_list(name)
            if users is None:
                shared.console.print(f"[red]Ошибка загрузки списка '{name}'.[/red]")
                return None
            shared.console.print(f"[green]Выбран список: {name} ({len(users)} пользователей)[/green]")
            return name, file_path, users
        else:
            shared.console.print("[red]Недопустимый номер.[/red]")
            return None
    except ValueError:
        shared.console.print("[red]Введите число.[/red]")
        return None

def _validate_user_exists(prox, user: str) -> bool:
    """Validate if user exists in Proxmox."""
    try:
        users = prox.access.users.get()
        return any(u['userid'] == user for u in users)
    except Exception as e:
        log_error(logger, e, f"Validate user {user} existence")
        return False

def _validate_pool_exists(prox, pool_name: str) -> bool:
    """Validate if pool exists in Proxmox."""
    try:
        pools = prox.pools.get()
        return any(p['poolid'] == pool_name for p in pools)
    except Exception as e:
        log_error(logger, e, f"Validate pool {pool_name} existence")
        return False

def _get_pool_members(prox, pool_name: str) -> Optional[List[Dict[str, Any]]]:
    """Get VM members from pool."""
    try:
        pool_data = prox.pools(pool_name).get()
        return pool_data.get('members', [])
    except Exception as e:
        log_error(logger, e, f"Get pool {pool_name} members")
        return None

def _collect_bridges_to_delete(prox, members: List[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    """Collect bridges that need to be deleted after VM removal."""
    bridges_to_delete = set()

    for member in members:
        vmid = member.get('vmid')
        member_node = member.get('node')
        if not vmid or not member_node:
            continue

        try:
            vm_config = prox.nodes(member_node).qemu(vmid).config.get()
            for key, value in vm_config.items():
                if key.startswith('net') and 'bridge=' in str(value):
                    bridge_part = str(value).split('bridge=')[1].split(',')[0]
                    if bridge_part.startswith('vmbr') and bridge_part[4:].isdigit():
                        num = int(bridge_part[4:])
                        if 1000 <= num <= 1999:  # User-created bridges range
                            bridges_to_delete.add((bridge_part, member_node))
        except Exception as e:
            logger.warning(f"Failed to check bridges for VM {vmid}: {e}")

    return bridges_to_delete

def _delete_snapshots_from_vms(prox, members: List[Dict[str, Any]]) -> None:
    """Delete snapshots from VMs before VM deletion."""
    for member in members:
        vmid = member.get('vmid')
        member_node = member.get('node')
        if not vmid or not member_node:
            continue

        try:
            snapshots = prox.nodes(member_node).qemu(vmid).snapshot.get()
            for snapshot in snapshots:
                snap_name = snapshot.get('name')
                if snap_name == 'start':  # Delete only 'start' snapshot
                    try:
                        task_id = prox.nodes(member_node).qemu(vmid).snapshot(snap_name).delete()
                        if task_id and wait_task_func(prox, member_node, task_id):
                            logger.info(f"Snapshot '{snap_name}' deleted from VM {vmid}")
                        else:
                            logger.warning(f"Failed to delete snapshot '{snap_name}' from VM {vmid}: task failed")
                    except Exception as e:
                        logger.warning(f"Failed to delete snapshot '{snap_name}' from VM {vmid}: {e}")
        except Exception as e:
            logger.warning(f"Failed to get snapshots for VM {vmid}: {e}")

def _delete_vms_from_pool(prox, members: List[Dict[str, Any]]) -> List[int]:
    """Delete VMs from pool and return successfully deleted VMIDs."""
    deleted_vmids = []
    nodes = [n['node'] for n in prox.nodes.get()]

    for member in members:
        vmid = member.get('vmid')
        if not vmid:
            continue

        for node_name in nodes:
            try:
                vms = prox.nodes(node_name).qemu.get()
                if any(vm['vmid'] == vmid for vm in vms):
                    upid = prox.nodes(node_name).qemu(vmid).delete(purge=1)
                    if wait_task_func(prox, node_name, upid):
                        deleted_vmids.append(vmid)
                        logger.info(f"VM {vmid} deleted from node {node_name}")
                    else:
                        logger.error(f"Failed to delete VM {vmid} from node {node_name}")
                    break
            except Exception as e:
                log_error(logger, e, f"Delete VM {vmid}")

    return deleted_vmids

def _delete_pool_and_user(prox, pool_name: str, user: str) -> Tuple[bool, bool]:
    """Delete pool and user, return success status."""
    pool_deleted = user_deleted = False

    try:
        prox.pools(pool_name).delete()
        pool_deleted = True
        logger.info(f"Pool {pool_name} deleted")
    except Exception as e:
        log_error(logger, e, f"Delete pool {pool_name}")

    try:
        prox.access.users(user).delete()
        user_deleted = True
        logger.info(f"User {user} deleted")
    except Exception as e:
        log_error(logger, e, f"Delete user {user}")

    return pool_deleted, user_deleted

def _delete_bridges_and_reload_network(prox, bridges_to_delete: Set[Tuple[str, str]],
                                      nodes_in_use: Set[str]) -> None:
    """Delete collected bridges and reload network on used nodes."""
    # Delete bridges
    for bridge_name, bridge_node in bridges_to_delete:
        try:
            prox.nodes(bridge_node).network.delete(bridge_name)
            logger.info(f"Bridge {bridge_name} deleted from node {bridge_node}")
        except Exception as e:
            log_error(logger, e, f"Delete bridge {bridge_name} on {bridge_node}")

    # Reload network on all used nodes
    for node_name in nodes_in_use:
        try:
            reload_net_func(prox, node_name)
            logger.info(f"Network reloaded on node {node_name}")
        except Exception as e:
            log_error(logger, e, f"Reload network on {node_name}")

def delete_user_stand() -> Optional[str]:
    """Delete stand of a user with interactive input."""
    with OperationTimer(logger, "Delete user stand"):
        try:
            user_input = input("Введите пользователя (например user1@pve): ").strip()
            if not user_input:
                shared.console.print("[yellow]Имя пользователя не может быть пустым.[/yellow]")
                return None

            user = _normalize_user(user_input)

            with shared.console.status(f"[bold yellow]Удаление стенда {user}...[/bold yellow]",
                                     spinner="dots") as status:
                success = delete_user_stand_logic(user)

            if success:
                shared.console.print(f"[red]Стенд {user} удален[/red]")
                log_operation(logger, "Stand deleted", success=True, user=user)
                return user
            else:
                shared.console.print(f"[red]Не удалось удалить стенд {user}[/red]")
                return None

        except Exception as e:
            shared.console.print(f"[red]Ошибка выполнения: {e}[/red]")
            log_error(logger, e, "Delete user stand")
            return None

def delete_user_stand_logic(user: str) -> bool:
    """
    Execute stand deletion logic for a user.

    Returns True if deletion was successful, False otherwise.
    """
    logger.info(f"Starting stand deletion for user: {user}")

    try:
        # Get Proxmox connection
        prox = get_proxmox_connection()
    except Exception as e:
        log_error(logger, e, f"Connect to Proxmox for user {user}")
        return False

    # Validate user exists
    if not _validate_user_exists(prox, user):
        shared.console.print(f"[red]Пользователь {user} не найден.[/red]")
        input("Нажмите Enter для продолжения...")
        return False

    pool_name = user.split('@')[0]

    # Validate pool exists
    if not _validate_pool_exists(prox, pool_name):
        shared.console.print(f"[red]Пул {pool_name} не найден.[/red]")
        input("Нажмите Enter для продолжения...")
        return False

    # Get pool members (VMs)
    members = _get_pool_members(prox, pool_name)
    if members is None:
        shared.console.print("[red]Ошибка получения членов пула.[/red]")
        return False

    if not members:
        shared.console.print("[yellow]В пуле нет VM.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return False

    # Get nodes in use from members
    nodes_in_use = {member.get('node') for member in members if member.get('node')}
    if not nodes_in_use:
        shared.console.print("[yellow]Не найдены ноды для обработки.[/yellow]")
        return False

    logger.info(f"Found {len(members)} VMs to delete on nodes: {nodes_in_use}")

    # Collect bridges to delete before VM removal
    bridges_to_delete = _collect_bridges_to_delete(prox, members)

    # Delete snapshots from VMs
    _delete_snapshots_from_vms(prox, members)

    # Delete VMs
    deleted_vmids = _delete_vms_from_pool(prox, members)
    if not deleted_vmids:
        logger.warning(f"No VMs were successfully deleted for user {user}")

    # Delete pool and user
    pool_deleted, user_deleted = _delete_pool_and_user(prox, pool_name, user)

    # Delete bridges and reload network
    _delete_bridges_and_reload_network(prox, bridges_to_delete, nodes_in_use)

    success = len(deleted_vmids) > 0 or pool_deleted or user_deleted
    log_operation(logger, "User stand deletion completed",
                 success=success, user=user, pool_name=pool_name,
                 vms_deleted=len(deleted_vmids), bridges_deleted=len(bridges_to_delete),
                 nodes_reloaded=len(nodes_in_use))

    return success

def delete_all_user_stands() -> None:
    """Delete stands of all users in a selected list."""
    with OperationTimer(logger, "Delete all user stands"):
        # Select user list
        selection = _select_user_list()
        if not selection:
            return

        list_name, file_path, users = selection
        logger.info(f"Starting deletion of {len(users)} user stands from list '{list_name}'")

        deleted_count = 0
        failed_users = []

        # Process each user
        for user in users:
            try:
                normalized_user = _normalize_user(user)
                display_name = normalized_user.split('@')[0] + "@pve"

                with shared.console.status(f"[bold yellow]Удаление стенда {display_name}...[/bold yellow]",
                                         spinner="dots") as status:
                    success = delete_user_stand_logic(normalized_user)

                if success:
                    shared.console.print(f"[red]Стенд {display_name} удален[/red]")
                    deleted_count += 1
                else:
                    shared.console.print(f"[red]Не удалось удалить стенд {display_name}[/red]")
                    failed_users.append(user)

            except Exception as e:
                log_error(logger, e, f"Delete stand for {user}")
                failed_users.append(user)
                shared.console.print(f"[red]Ошибка при удалении {user}: {e}[/red]")

        # Final network reload on all nodes
        try:
            prox = get_proxmox_connection()
            nodes_data = prox.nodes.get()
            nodes = [n['node'] for n in nodes_data]

            logger.info(f"Performing final network reload on {len(nodes)} nodes")
            for node_name in nodes:
                try:
                    reload_net_func(prox, node_name)
                    logger.debug(f"Final network reload completed on {node_name}")
                except Exception as e:
                    logger.warning(f"Final network reload failed on {node_name}: {e}")

        except Exception as e:
            log_error(logger, e, "Final network reload")

        # Summary
        if failed_users:
            shared.console.print(f"[yellow]Удаление завершено: {deleted_count}/{len(users)} стендов удалено[/yellow]")
            shared.console.print(f"[red]Не удалось удалить пользователей: {', '.join(failed_users)}[/red]")
        else:
            shared.console.print(f"[green]Удаление всех стендов завершено успешно ({deleted_count} стендов)[/green]")

        log_operation(logger, "Bulk stand deletion completed",
                     success=True, total_users=len(users),
                     deleted_count=deleted_count, failed_count=len(failed_users))

        input("Нажмите Enter для продолжения...")

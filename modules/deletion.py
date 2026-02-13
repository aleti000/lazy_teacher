#!/usr/bin/env python3
"""
Deletion module for Lazy Teacher.
Provides functions for deleting stands and users.
Updated to work with groups system.

Deletion logic:
1. Find user pool
2. Find VMs in pool
3. Determine VM network interfaces (except vmbr0)
4. Check if VMs are running - prompt to stop and wait via task
5. Delete network interfaces (with node specification!)
6. Reload network
7. Delete VMs
8. Delete pool
9. Delete user
"""

import glob
import yaml
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set
import logging

from . import shared
from .connections import get_proxmox_connection
from .tasks import wait_for_task as wait_task_func
from .network import reload_network as reload_net_func
from .groups import remove_user_from_group, find_user_group, delete_group
from .logger import get_logger, log_operation, log_error, OperationTimer

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
        print("[!] Нет списков пользователей.")
        input("Нажмите Enter для продолжения...")
        return None

    print("\nВыбор списка пользователей:")
    print("-" * 50)
    print(f"{'№':<5} {'Имя списка':<25} {'Пользователей':<15}")
    print("-" * 50)

    for i, (name, file_path) in enumerate(user_lists, 1):
        try:
            users = _load_user_list(name) or []
            print(f"{i:<5} {name:<25} {len(users):<15}")
        except Exception:
            print(f"{i:<5} {name:<25} {'Ошибка':<15}")

    print()

    try:
        choice = int(input("Выберите номер списка: ")) - 1
        if 0 <= choice < len(user_lists):
            name, file_path = user_lists[choice]
            users = _load_user_list(name)
            if users is None:
                print(f"[!] Ошибка загрузки списка '{name}'.")
                return None
            print(f"[+] Выбран список: {name} ({len(users)} пользователей)")
            return name, file_path, users
        else:
            print("[!] Недопустимый номер.")
            return None
    except ValueError:
        print("[!] Введите число.")
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


def _check_running_vms(prox, members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Check which VMs are running and return list of running VMs."""
    running_vms = []
    
    for member in members:
        vmid = member.get('vmid')
        node = member.get('node')
        if not vmid or not node:
            continue
        
        try:
            vm_status = prox.nodes(node).qemu(vmid).status.current.get()
            if vm_status.get('status') == 'running':
                running_vms.append({
                    'vmid': vmid,
                    'node': node,
                    'name': member.get('name', 'N/A')
                })
        except Exception as e:
            logger.warning(f"Failed to check status for VM {vmid}: {e}")
    
    return running_vms


def _stop_vms(prox, vms_to_stop: List[Dict[str, Any]], auto_confirm: bool = False) -> bool:
    """
    Stop running VMs with user confirmation.
    Returns True if all VMs were stopped successfully.
    """
    if not vms_to_stop:
        return True
    
    print(f"\n[!] Найдены запущенные ВМ:")
    for vm in vms_to_stop:
        print(f"    - VM {vm['vmid']} ({vm['name']}) на ноде {vm['node']}")
    
    if not auto_confirm:
        confirm = input("\nВыключить эти ВМ? (y/n): ").strip().lower()
        if confirm != 'y':
            print("[!] Удаление отменено. ВМ должны быть выключены перед удалением.")
            return False
    
    print("\n[*] Выключение ВМ...")
    
    all_stopped = True
    for vm in vms_to_stop:
        vmid = vm['vmid']
        node = vm['node']
        
        try:
            print(f"  [*] Выключение VM {vmid} на ноде {node}...")
            upid = prox.nodes(node).qemu(vmid).status.stop.post()
            
            # Wait for stop task
            print(f"      Ожидание завершения...")
            if wait_task_func(prox, node, upid):
                # Additional wait to ensure VM is fully stopped
                for _ in range(30):
                    vm_status = prox.nodes(node).qemu(vmid).status.current.get()
                    if vm_status.get('status') == 'stopped':
                        print(f"  [+] VM {vmid} выключена")
                        break
                    time.sleep(1)
                else:
                    print(f"  [!] VM {vmid} не выключилась в течение 30 секунд")
                    all_stopped = False
            else:
                print(f"  [!] Ошибка при выключении VM {vmid}")
                all_stopped = False
                
        except Exception as e:
            print(f"  [!] Ошибка выключения VM {vmid}: {e}")
            log_error(logger, e, f"Stop VM {vmid}")
            all_stopped = False
    
    return all_stopped


def _collect_bridges_to_delete(prox, members: List[Dict[str, Any]]) -> Set[Tuple[str, str]]:
    """
    Collect bridges that need to be deleted after VM removal.
    Excludes vmbr0 and standard bridges (numbered < 1000).
    Returns set of (bridge_name, node_name) tuples.
    """
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
                    
                    # Skip vmbr0
                    if bridge_part == 'vmbr0':
                        continue
                    
                    # Only collect custom bridges (vmbr1000-1999)
                    if bridge_part.startswith('vmbr') and bridge_part[4:].isdigit():
                        num = int(bridge_part[4:])
                        if 1000 <= num <= 1999:
                            bridges_to_delete.add((bridge_part, member_node))
                            logger.debug(f"Collected bridge {bridge_part} on node {member_node} from VM {vmid}")
        except Exception as e:
            logger.warning(f"Failed to check bridges for VM {vmid}: {e}")

    return bridges_to_delete


def _delete_bridges(prox, bridges_to_delete: Set[Tuple[str, str]]) -> int:
    """
    Delete network bridges.
    Returns count of successfully deleted bridges.
    """
    deleted_count = 0
    
    for bridge_name, bridge_node in bridges_to_delete:
        try:
            print(f"  [*] Удаление моста {bridge_name} на ноде {bridge_node}...")
            prox.nodes(bridge_node).network.delete(bridge_name)
            print(f"  [+] Мост {bridge_name} удален с ноды {bridge_node}")
            logger.info(f"Bridge {bridge_name} deleted from node {bridge_node}")
            deleted_count += 1
        except Exception as e:
            print(f"  [!] Ошибка удаления моста {bridge_name} на {bridge_node}: {e}")
            log_error(logger, e, f"Delete bridge {bridge_name} on {bridge_node}")
    
    return deleted_count


def _reload_network_on_nodes(prox, nodes: Set[str]) -> None:
    """Reload network configuration on specified nodes."""
    for node_name in nodes:
        try:
            print(f"  [*] Обновление сети на ноде {node_name}...")
            reload_net_func(prox, node_name)
            print(f"  [+] Сеть на ноде {node_name} обновлена")
            logger.info(f"Network reloaded on node {node_name}")
        except Exception as e:
            print(f"  [!] Ошибка обновления сети на {node_name}: {e}")
            log_error(logger, e, f"Reload network on {node_name}")


def _delete_vms_from_pool(prox, members: List[Dict[str, Any]]) -> List[int]:
    """Delete VMs from pool and return successfully deleted VMIDs."""
    deleted_vmids = []

    for member in members:
        vmid = member.get('vmid')
        node = member.get('node')
        if not vmid or not node:
            continue

        try:
            print(f"  [*] Удаление VM {vmid} на ноде {node}...")
            upid = prox.nodes(node).qemu(vmid).delete(purge=1)
            
            if wait_task_func(prox, node, upid):
                print(f"  [+] VM {vmid} удалена")
                deleted_vmids.append(vmid)
                logger.info(f"VM {vmid} deleted from node {node}")
            else:
                print(f"  [!] Ошибка удаления VM {vmid}")
                logger.error(f"Failed to delete VM {vmid} from node {node}")
        except Exception as e:
            print(f"  [!] Ошибка удаления VM {vmid}: {e}")
            log_error(logger, e, f"Delete VM {vmid}")

    return deleted_vmids


def _delete_pool_and_user(prox, pool_name: str, user: str) -> Tuple[bool, bool]:
    """Delete pool and user, return success status."""
    pool_deleted = user_deleted = False

    try:
        prox.pools(pool_name).delete()
        print(f"  [+] Пул {pool_name} удален")
        pool_deleted = True
        logger.info(f"Pool {pool_name} deleted")
    except Exception as e:
        print(f"  [!] Ошибка удаления пула {pool_name}: {e}")
        log_error(logger, e, f"Delete pool {pool_name}")

    try:
        prox.access.users(user).delete()
        print(f"  [+] Пользователь {user} удален")
        user_deleted = True
        logger.info(f"User {user} deleted")
    except Exception as e:
        print(f"  [!] Ошибка удаления пользователя {user}: {e}")
        log_error(logger, e, f"Delete user {user}")

    return pool_deleted, user_deleted


def delete_user_stand() -> Optional[str]:
    """Delete stand of a user with interactive input."""
    with OperationTimer(logger, "Delete user stand"):
        try:
            user_input = input("Введите пользователя (например user1@pve): ").strip()
            if not user_input:
                print("[!] Имя пользователя не может быть пустым.")
                return None

            user = _normalize_user(user_input)

            print(f"\n[*] Удаление стенда {user}...")
            success = delete_user_stand_logic(user)

            if success:
                print(f"\n[+] Стенд {user} успешно удален")
                log_operation(logger, "Stand deleted", success=True, user=user)
                return user
            else:
                print(f"\n[!] Не удалось удалить стенд {user}")
                return None

        except Exception as e:
            print(f"[!] Ошибка выполнения: {e}")
            log_error(logger, e, "Delete user stand")
            return None


def delete_user_stand_logic(prox=None, pool_name: str = None, user: str = None, auto_stop: bool = False) -> bool:
    """
    Execute stand deletion logic for a user.
    
    Deletion order:
    1. Find user pool
    2. Find VMs in pool
    3. Determine VM network interfaces (except vmbr0)
    4. Check if VMs are running - prompt to stop and wait via task
    5. Delete network interfaces (with node specification!)
    6. Reload network
    7. Delete VMs
    8. Delete pool
    9. Delete user
    
    Can be called with either prox and pool_name, or just user string.
    auto_stop: if True, automatically stop running VMs without prompting
    """
    # Handle different call signatures
    if prox is None and user is not None:
        user = _normalize_user(user)
        pool_name = user.split('@')[0]
        try:
            prox = get_proxmox_connection()
        except Exception as e:
            print(f"[!] Ошибка подключения к Proxmox: {e}")
            log_error(logger, e, f"Connect to Proxmox for user {user}")
            return False
    elif isinstance(prox, str) and pool_name is None:
        user = _normalize_user(prox)
        pool_name = user.split('@')[0]
        try:
            prox = get_proxmox_connection()
        except Exception as e:
            print(f"[!] Ошибка подключения к Proxmox: {e}")
            log_error(logger, e, f"Connect to Proxmox for user {user}")
            return False
    elif user is None:
        user = f"{pool_name}@pve"
    
    logger.info(f"Starting stand deletion for user: {user}")
    print(f"\n[*] Удаление стенда пользователя: {user}")
    
    # Step 1: Validate user exists
    print("\n[1/9] Проверка пользователя...")
    if not _validate_user_exists(prox, user):
        print(f"[!] Пользователь {user} не найден.")
        return False

    # Step 2: Validate pool exists
    print("[2/9] Проверка пула...")
    if not _validate_pool_exists(prox, pool_name):
        print(f"[!] Пул {pool_name} не найден.")
        return False

    # Step 3: Get pool members
    print("[3/9] Получение списка ВМ...")
    members = _get_pool_members(prox, pool_name)
    if members is None:
        print("[!] Ошибка получения членов пула.")
        return False

    if not members:
        print("[*] В пуле нет VM. Удаление только пользователя и пула.")
        _delete_pool_and_user(prox, pool_name, user)
        group_name = find_user_group(user)
        if group_name:
            remove_user_from_group(group_name, user)
        return True

    nodes_in_use = {member.get('node') for member in members if member.get('node')}
    if not nodes_in_use:
        print("[!] Не найдены ноды для обработки.")
        return False

    print(f"    Найдено {len(members)} ВМ на нодах: {', '.join(nodes_in_use)}")
    logger.info(f"Found {len(members)} VMs to delete on nodes: {nodes_in_use}")

    # Step 4: Collect bridges BEFORE any changes
    print("[4/9] Сбор информации о сетевых интерфейсах...")
    bridges_to_delete = _collect_bridges_to_delete(prox, members)
    if bridges_to_delete:
        print(f"    Найдено сетевых мостов для удаления: {len(bridges_to_delete)}")
        for bridge, node in bridges_to_delete:
            print(f"      - {bridge} на ноде {node}")

    # Step 5: Check for running VMs and stop them
    print("[5/9] Проверка запущенных ВМ...")
    running_vms = _check_running_vms(prox, members)
    
    if running_vms:
        if not _stop_vms(prox, running_vms, auto_confirm=auto_stop):
            print("[!] Удаление отменено.")
            return False
    else:
        print("    Все ВМ выключены")

    # Step 6: Delete bridges
    print("[6/9] Удаление сетевых мостов...")
    if bridges_to_delete:
        deleted_bridges = _delete_bridges(prox, bridges_to_delete)
        print(f"    Удалено мостов: {deleted_bridges}/{len(bridges_to_delete)}")
    else:
        print("    Нет мостов для удаления")

    # Step 7: Reload network on all affected nodes
    print("[7/9] Обновление конфигурации сети...")
    _reload_network_on_nodes(prox, nodes_in_use)

    # Step 8: Delete VMs
    print("[8/9] Удаление виртуальных машин...")
    deleted_vmids = _delete_vms_from_pool(prox, members)
    print(f"    Удалено ВМ: {len(deleted_vmids)}/{len(members)}")
    
    if not deleted_vmids:
        logger.warning(f"No VMs were successfully deleted for user {user}")

    # Step 9: Delete pool and user
    print("[9/9] Удаление пула и пользователя...")
    pool_deleted, user_deleted = _delete_pool_and_user(prox, pool_name, user)

    # Remove from group
    group_name = find_user_group(user)
    if group_name:
        remove_user_from_group(group_name, user)
        logger.info(f"Removed {user} from group {group_name}")

    success = len(deleted_vmids) > 0 or pool_deleted or user_deleted
    log_operation(logger, "User stand deletion completed",
                 success=success, user=user, pool_name=pool_name,
                 vms_deleted=len(deleted_vmids), bridges_deleted=len(bridges_to_delete),
                 nodes_reloaded=len(nodes_in_use))

    return success


def delete_all_user_stands() -> None:
    """Delete stands of all users in a selected list."""
    with OperationTimer(logger, "Delete all user stands"):
        selection = _select_user_list()
        if not selection:
            return

        list_name, file_path, users = selection
        logger.info(f"Starting deletion of {len(users)} user stands from list '{list_name}'")

        deleted_count = 0
        failed_users = []

        for user in users:
            try:
                normalized_user = _normalize_user(user)
                display_name = normalized_user.split('@')[0] + "@pve"

                print(f"\n{'='*50}")
                print(f"[*] Удаление стенда {display_name}...")
                print('='*50)
                
                # auto_stop=True for bulk deletion
                success = delete_user_stand_logic(normalized_user, auto_stop=True)

                if success:
                    deleted_count += 1
                else:
                    failed_users.append(user)

            except Exception as e:
                log_error(logger, e, f"Delete stand for {user}")
                failed_users.append(user)
                print(f"[!] Ошибка при удалении {user}: {e}")

        # Summary
        print("\n" + "=" * 50)
        print("  РЕЗУЛЬТАТЫ УДАЛЕНИЯ")
        print("=" * 50)
        if failed_users:
            print(f"\n[*] Удаление завершено: {deleted_count}/{len(users)} стендов удалено")
            print(f"[!] Не удалось удалить: {', '.join(failed_users)}")
        else:
            print(f"\n[+] Удаление всех стендов завершено успешно ({deleted_count} стендов)")

        log_operation(logger, "Bulk stand deletion completed",
                     success=True, total_users=len(users),
                     deleted_count=deleted_count, failed_count=len(failed_users))

        input("\nНажмите Enter для продолжения...")
#!/usr/bin/env python3
"""
Stand Management module for Lazy Teacher.
Provides functions for managing existing stands.
"""

import time
from typing import List, Dict, Any, Optional

from . import shared
from .connections import get_proxmox_connection
from .groups import get_groups, get_group, get_group_users
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)


def _select_group() -> Optional[str]:
    """Select a group from available groups."""
    groups = get_groups()
    
    if not groups:
        print("[!] Нет доступных групп.")
        return None
    
    print("\nДоступные группы:")
    print("-" * 50)
    
    group_names = list(groups.keys())
    for i, name in enumerate(group_names, 1):
        users = groups[name].get('users', [])
        print(f"  [{i}] {name} ({len(users)} пользователей)")
    print(f"  [0] Отмена")
    print()
    
    try:
        choice = int(input("Выберите группу: "))
        if choice == 0:
            return None
        if 1 <= choice <= len(group_names):
            return group_names[choice - 1]
        print("[!] Неверный выбор.")
        return None
    except ValueError:
        print("[!] Введите число.")
        return None


def _get_pool_members(prox, pool_name: str) -> List[Dict[str, Any]]:
    """Get VM members from pool."""
    try:
        pool_data = prox.pools(pool_name).get()
        return pool_data.get('members', [])
    except Exception as e:
        log_error(logger, e, f"Get pool {pool_name} members")
        return []


def start_all_vms(group_name: str = None) -> bool:
    """Start all VMs in a group."""
    with OperationTimer(logger, "Start all VMs"):
        if group_name is None:
            group_name = _select_group()
            if not group_name:
                return False
        
        group = get_group(group_name)
        if not group:
            print(f"[!] Группа {group_name} не найдена.")
            return False
        
        users = group.get('users', [])
        if not users:
            print("[!] В группе нет пользователей.")
            return False
        
        try:
            prox = get_proxmox_connection()
        except Exception as e:
            print(f"[!] {e}")
            return False
        
        print(f"\n[*] Запуск всех VM группы {group_name}...")
        
        started_count = 0
        for user in users:
            pool_name = user.split('@')[0]
            members = _get_pool_members(prox, pool_name)
            
            for member in members:
                vmid = member.get('vmid')
                node = member.get('node')
                
                if vmid and node:
                    try:
                        vm_status = prox.nodes(node).qemu(vmid).status.current.get()
                        if vm_status.get('status') != 'running':
                            prox.nodes(node).qemu(vmid).status.start.post()
                            print(f"  [+] VM {vmid} запущена")
                            started_count += 1
                    except Exception as e:
                        log_error(logger, e, f"Start VM {vmid}")
        
        print(f"\n[+] Запущено {started_count} VM")
        log_operation(logger, "Start all VMs", success=True, 
                     group=group_name, started=started_count)
        return True


def stop_all_vms(group_name: str = None) -> bool:
    """Stop all VMs in a group."""
    with OperationTimer(logger, "Stop all VMs"):
        if group_name is None:
            group_name = _select_group()
            if not group_name:
                return False
        
        group = get_group(group_name)
        if not group:
            print(f"[!] Группа {group_name} не найдена.")
            return False
        
        users = group.get('users', [])
        if not users:
            print("[!] В группе нет пользователей.")
            return False
        
        try:
            prox = get_proxmox_connection()
        except Exception as e:
            print(f"[!] {e}")
            return False
        
        print(f"\n[*] Остановка всех VM группы {group_name}...")
        
        stopped_count = 0
        for user in users:
            pool_name = user.split('@')[0]
            members = _get_pool_members(prox, pool_name)
            
            for member in members:
                vmid = member.get('vmid')
                node = member.get('node')
                
                if vmid and node:
                    try:
                        vm_status = prox.nodes(node).qemu(vmid).status.current.get()
                        if vm_status.get('status') == 'running':
                            prox.nodes(node).qemu(vmid).status.stop.post()
                            print(f"  [+] VM {vmid} остановлена")
                            stopped_count += 1
                    except Exception as e:
                        log_error(logger, e, f"Stop VM {vmid}")
        
        print(f"\n[+] Остановлено {stopped_count} VM")
        log_operation(logger, "Stop all VMs", success=True,
                     group=group_name, stopped=stopped_count)
        return True


def reset_all_to_snapshot(group_name: str = None, snapshot_name: str = "start") -> bool:
    """Reset all VMs in a group to a snapshot."""
    with OperationTimer(logger, "Reset all to snapshot"):
        if group_name is None:
            group_name = _select_group()
            if not group_name:
                return False
        
        group = get_group(group_name)
        if not group:
            print(f"[!] Группа {group_name} не найдена.")
            return False
        
        users = group.get('users', [])
        if not users:
            print("[!] В группе нет пользователей.")
            return False
        
        try:
            prox = get_proxmox_connection()
        except Exception as e:
            print(f"[!] {e}")
            return False
        
        print(f"\n[*] Сброс всех VM группы {group_name} на snapshot '{snapshot_name}'...")
        
        reset_count = 0
        for user in users:
            pool_name = user.split('@')[0]
            members = _get_pool_members(prox, pool_name)
            
            for member in members:
                vmid = member.get('vmid')
                node = member.get('node')
                
                if vmid and node:
                    try:
                        # Stop if running
                        vm_status = prox.nodes(node).qemu(vmid).status.current.get()
                        if vm_status.get('status') == 'running':
                            prox.nodes(node).qemu(vmid).status.stop.post()
                            
                            # Wait for stop
                            for _ in range(30):
                                status = prox.nodes(node).qemu(vmid).status.current.get()
                                if status.get('status') == 'stopped':
                                    break
                                time.sleep(1)
                        
                        # Rollback to snapshot
                        prox.nodes(node).qemu(vmid).snapshot(snapshot_name).rollback.post()
                        print(f"  [+] VM {vmid} сброшена на '{snapshot_name}'")
                        reset_count += 1
                        
                    except Exception as e:
                        log_error(logger, e, f"Reset VM {vmid}")
        
        print(f"\n[+] Сброшено {reset_count} VM")
        log_operation(logger, "Reset all to snapshot", success=True,
                     group=group_name, snapshot=snapshot_name, reset=reset_count)
        return True


def show_group_status(group_name: str = None) -> None:
    """Show status of all VMs in a group."""
    with OperationTimer(logger, "Show group status"):
        if group_name is None:
            group_name = _select_group()
            if not group_name:
                return
        
        group = get_group(group_name)
        if not group:
            print(f"[!] Группа {group_name} не найдена.")
            return
        
        users = group.get('users', [])
        if not users:
            print("[!] В группе нет пользователей.")
            return
        
        try:
            prox = get_proxmox_connection()
        except Exception as e:
            print(f"[!] {e}")
            return
        
        print(f"\nСтатус VM группы {group_name}:")
        print("-" * 60)
        print(f"{'Пользователь':<20} {'VMID':<8} {'Имя':<20} {'Статус':<10}")
        print("-" * 60)
        
        for user in users:
            pool_name = user.split('@')[0]
            members = _get_pool_members(prox, pool_name)
            
            for member in members:
                vmid = member.get('vmid')
                node = member.get('node')
                vm_name = member.get('name', 'N/A')
                
                if vmid and node:
                    try:
                        vm_status = prox.nodes(node).qemu(vmid).status.current.get()
                        status = vm_status.get('status', 'unknown')
                        status_display = '\033[92mrunning\033[0m' if status == 'running' else '\033[91mstopped\033[0m'
                        print(f"{pool_name:<20} {vmid:<8} {vm_name:<20} {status_display}")
                    except Exception as e:
                        print(f"{pool_name:<20} {vmid:<8} {vm_name:<20} \033[93merror\033[0m")
        
        print("-" * 60)
        input("\nНажмите Enter для продолжения...")


def stand_management_menu():
    """Interactive stand management menu."""
    options = {
        '1': 'Запустить все VM группы',
        '2': 'Остановить все VM группы',
        '3': 'Сбросить все VM на snapshot',
        '4': 'Показать статус VM группы',
        '0': 'Назад'
    }
    
    while True:
        print("\n" + "=" * 50)
        print("  УПРАВЛЕНИЕ СТЕНДАМИ")
        print("=" * 50)
        
        for key, desc in options.items():
            print(f"  [{key}] {desc}")
        print()
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            start_all_vms()
        elif choice == '2':
            stop_all_vms()
        elif choice == '3':
            snapshot_name = input("Имя snapshot (по умолчанию 'start'): ").strip()
            if not snapshot_name:
                snapshot_name = "start"
            reset_all_to_snapshot(snapshot_name=snapshot_name)
        elif choice == '4':
            show_group_status()
        
        if choice != '0':
            input("\nНажмите Enter для продолжения...")
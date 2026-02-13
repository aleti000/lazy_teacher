#!/usr/bin/env python3
"""
Deploy Stand Distributed module for Lazy Teacher.
Deploys stands with even distribution across cluster nodes.
Uses centralized templates.yaml registry for template management.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from . import shared
from .connections import get_proxmox_connection
from .sync_templates import sync_templates
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)


def deploy_stand_distributed(stand_config: Dict = None, users_list: List[str] = None, 
                             clone_type: int = None, return_results: bool = False) -> Optional[List[Dict]]:
    """Deploy stand with even distribution of users across nodes."""
    from .ui_menus import select_stand_config, select_user_list, select_clone_type
    from .deploy_stand_local import deploy_stand_local

    if stand_config is None:
        result = select_stand_config()
        if result is None:
            print("[!] Не выбран стенд.")
            input("Нажмите Enter для продолжения...")
            return None
        stand, stand_file_path = result
    else:
        stand = stand_config
        stand_file_path = None

    if users_list is None:
        users = select_user_list()
        if not users:
            print("[!] Не выбран список пользователей.")
            input("Нажмите Enter для продолжения...")
            return None
    else:
        users = users_list

    if clone_type is None:
        from .ui_menus import select_clone_type
        clone_type = select_clone_type()

    try:
        prox = get_proxmox_connection()
    except Exception as e:
        print(f"[!] {e}")
        input("Нажмите Enter для продолжения...")
        return None

    nodes_data = prox.nodes.get()
    nodes = [n['node'] for n in nodes_data]
    
    if len(nodes) < 2:
        print(f"[!] Кластер содержит только {len(nodes)} ноду. Используйте локальное развертывание.")
        input("Нажмите Enter для продолжения...")
        return None

    print(f"\n[*] Кластер содержит {len(nodes)} нод: {', '.join(nodes)}")
    print(f"[*] Начинаем синхронизацию шаблонов...")
    
    # Sync templates to all nodes
    sync_templates(prox, stand, nodes)

    # Deploy for each user on assigned node
    all_deployment_results = []
    
    for user_index, user in enumerate(users):
        target_node = nodes[user_index % len(nodes)]
        print(f"\n[*] Развертывание для пользователя {user} на ноде {target_node}")

        user_results = deploy_stand_local(
            stand_config=stand,
            users_list=[user],
            target_node=target_node,
            update_stand_file=False,
            clone_type=clone_type
        )
        all_deployment_results.extend(user_results)

    print("\n[+] Распределенное развертывание завершено!")

    # Show results
    if not return_results:
        print("\n" + "=" * 50)
        print("  РЕЗУЛЬТАТЫ РАСПРЕДЕЛЕННОГО РАЗВЕРТЫВАНИЯ")
        print("=" * 50)
        if all_deployment_results:
            print(f"\n{'Пользователь':<20} {'Пароль':<12} {'Нода':<15}")
            print("-" * 47)
            for result in all_deployment_results:
                print(f"{result['user']:<20} {result['password']:<12} {result['node']:<15}")
        else:
            print("\n[!] Нет результатов развертывания.")
        input("\nНажмите Enter для продолжения...")

    return all_deployment_results
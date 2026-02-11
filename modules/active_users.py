#!/usr/bin/env python3
"""
Active Users module for Lazy Teacher.
Provides functions for viewing and managing active users.
"""

from typing import List, Dict, Any, Optional
from .connections import get_proxmox_connection
from .logger import get_logger, OperationTimer

logger = get_logger(__name__)


def get_active_users() -> List[Dict[str, Any]]:
    """Get list of active users from Proxmox."""
    try:
        prox = get_proxmox_connection()
        users = prox.access.users.get()
        return [u for u in users if u.get('enable', 1)]
    except Exception as e:
        logger.error(f"Error getting active users: {e}")
        return []


def get_user_pools(username: str) -> List[Dict[str, Any]]:
    """Get pools for a specific user."""
    try:
        prox = get_proxmox_connection()
        pools = prox.pools.get()
        user_pools = []
        
        for pool in pools:
            pool_id = pool.get('poolid', '')
            if pool_id == username.split('@')[0]:
                pool_data = prox.pools(pool_id).get()
                user_pools.append(pool_data)
        
        return user_pools
    except Exception as e:
        logger.error(f"Error getting pools for {username}: {e}")
        return []


def display_active_users() -> None:
    """Display all active users."""
    with OperationTimer(logger, "Display active users"):
        users = get_active_users()
        
        if not users:
            print("[!] Нет активных пользователей.")
            input("\nНажмите Enter для продолжения...")
            return
        
        print("\nАктивные пользователи:")
        print("-" * 60)
        print(f"{'№':<5} {'Пользователь':<30} {'Группы':<15}")
        print("-" * 60)
        
        for i, user in enumerate(users, 1):
            userid = user.get('userid', 'N/A')
            groups = ', '.join(user.get('groups', [])) or '-'
            print(f"{i:<5} {userid:<30} {groups:<15}")
        
        print("-" * 60)
        print(f"\nВсего: {len(users)} пользователей")
        input("\nНажмите Enter для продолжения...")


def display_user_details(username: str) -> None:
    """Display details for a specific user."""
    with OperationTimer(logger, f"Display user details {username}"):
        try:
            prox = get_proxmox_connection()
            user_data = prox.access.users(username).get()
        except Exception as e:
            print(f"[!] Пользователь {username} не найден: {e}")
            return
        
        print(f"\nДетали пользователя: {username}")
        print("-" * 50)
        
        print(f"  ID: {user_data.get('userid', 'N/A')}")
        print(f"  Включен: {'Да' if user_data.get('enable', 1) else 'Нет'}")
        print(f"  Группы: {', '.join(user_data.get('groups', [])) or '-'}")
        print(f"  Комментарий: {user_data.get('comment', '-')}")
        
        # Get pools
        pool_name = username.split('@')[0]
        try:
            pool_data = prox.pools(pool_name).get()
            members = pool_data.get('members', [])
            
            print(f"\n  Пул: {pool_name}")
            print(f"  VM в пуле: {len(members)}")
            
            if members:
                print("\n  Виртуальные машины:")
                for member in members:
                    vmid = member.get('vmid', 'N/A')
                    vm_name = member.get('name', 'N/A')
                    node = member.get('node', 'N/A')
                    print(f"    - {vmid}: {vm_name} ({node})")
        except Exception:
            print(f"\n  Пул: не найден")
        
        print("-" * 50)
        input("\nНажмите Enter для продолжения...")


def select_user() -> Optional[str]:
    """Select a user from list."""
    users = get_active_users()
    
    if not users:
        print("[!] Нет активных пользователей.")
        return None
    
    print("\nВыберите пользователя:")
    print("-" * 50)
    
    for i, user in enumerate(users, 1):
        userid = user.get('userid', 'N/A')
        print(f"  [{i}] {userid}")
    print(f"  [0] Отмена")
    print()
    
    try:
        choice = int(input("Выбор: "))
        if choice == 0:
            return None
        if 1 <= choice <= len(users):
            return users[choice - 1].get('userid')
        print("[!] Неверный выбор.")
        return None
    except ValueError:
        print("[!] Введите число.")
        return None


def active_users_menu() -> None:
    """Interactive menu for managing active users."""
    options = {
        '1': 'Показать всех активных пользователей',
        '2': 'Показать детали пользователя',
        '0': 'Назад'
    }
    
    while True:
        print("\n" + "=" * 50)
        print("  УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ")
        print("=" * 50)
        
        for key, desc in options.items():
            print(f"  [{key}] {desc}")
        print()
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            display_active_users()
        elif choice == '2':
            username = select_user()
            if username:
                display_user_details(username)
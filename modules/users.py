#!/usr/bin/env python3
"""
Users module for Lazy Teacher.
Provides functions for managing user lists.
"""

import glob
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any

from . import shared
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)


def _get_user_list_files() -> List[tuple]:
    """Get list of user list files."""
    pattern = str(shared.CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    return [(Path(f).stem.replace('_list', ''), f) for f in files]


def display_user_lists() -> None:
    """Display all saved user lists."""
    with OperationTimer(logger, "Display user lists"):
        user_lists = _get_user_list_files()
        
        if not user_lists:
            print("[!] Нет сохраненных списков пользователей.")
            input("\nНажмите Enter для продолжения...")
            return
        
        print("\nСохраненные списки пользователей:")
        print("-" * 50)
        print(f"{'№':<5} {'Имя списка':<25} {'Пользователей':<15}")
        print("-" * 50)
        
        for i, (name, file_path) in enumerate(user_lists, 1):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                users = data.get('users', [])
                print(f"{i:<5} {name:<25} {len(users):<15}")
            except Exception:
                print(f"{i:<5} {name:<25} {'Ошибка':<15}")
        
        print("-" * 50)
        input("\nНажмите Enter для продолжения...")


def input_users_manual() -> Optional[List[str]]:
    """Input users manually."""
    with OperationTimer(logger, "Input users manual"):
        users = []
        
        print("\nВвод пользователей (пустая строка для завершения):")
        print("Формат: user1 или user1@pve")
        print()
        
        while True:
            user = input("Пользователь: ").strip()
            if not user:
                break
            
            if '@' not in user:
                user = f"{user}@pve"
            
            users.append(user)
        
        if not users:
            print("[!] Список пуст.")
            return None
        
        print(f"\nВведено {len(users)} пользователей:")
        for user in users:
            print(f"  - {user}")
        
        save = input("\nСохранить список? (y/n): ").strip().lower()
        
        if save == 'y':
            list_name = input("Имя списка: ").strip()
            if list_name:
                save_user_list(list_name, users)
        
        return users


def import_users() -> Optional[List[str]]:
    """Import users from a text file."""
    with OperationTimer(logger, "Import users"):
        file_path = input("Путь к файлу со списком пользователей: ").strip()
        
        if not file_path:
            print("[!] Путь не указан.")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            users = []
            for line in lines:
                user = line.strip()
                if user and not user.startswith('#'):
                    if '@' not in user:
                        user = f"{user}@pve"
                    users.append(user)
            
            if not users:
                print("[!] Файл не содержит пользователей.")
                return None
            
            print(f"\nИмпортировано {len(users)} пользователей:")
            for user in users[:10]:
                print(f"  - {user}")
            if len(users) > 10:
                print(f"  ... и еще {len(users) - 10}")
            
            save = input("\nСохранить список? (y/n): ").strip().lower()
            
            if save == 'y':
                list_name = input("Имя списка: ").strip()
                if list_name:
                    save_user_list(list_name, users)
            
            return users
            
        except FileNotFoundError:
            print(f"[!] Файл не найден: {file_path}")
            return None
        except Exception as e:
            print(f"[!] Ошибка чтения файла: {e}")
            log_error(logger, e, "Import users")
            return None


def save_user_list(name: str, users: List[str]) -> bool:
    """Save user list to file."""
    file_path = shared.CONFIG_DIR / f"{name}_list.yaml"
    
    try:
        data = {'users': users}
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        print(f"\n[+] Список '{name}' сохранен ({len(users)} пользователей)")
        logger.info(f"Saved user list: {name} ({len(users)} users)")
        return True
    except Exception as e:
        print(f"[!] Ошибка сохранения: {e}")
        log_error(logger, e, f"Save user list {name}")
        return False


def load_user_list(name: str) -> Optional[List[str]]:
    """Load user list from file."""
    file_path = shared.CONFIG_DIR / f"{name}_list.yaml"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return data.get('users', [])
    except FileNotFoundError:
        logger.warning(f"User list {name} not found")
        return None
    except Exception as e:
        log_error(logger, e, f"Load user list {name}")
        return None


def delete_user_list() -> None:
    """Delete a user list file."""
    user_lists = _get_user_list_files()
    
    if not user_lists:
        print("[!] Нет сохраненных списков пользователей.")
        input("\nНажмите Enter для продолжения...")
        return
    
    print("\nУдаление списка пользователей:")
    print("-" * 50)
    
    for i, (name, _) in enumerate(user_lists, 1):
        print(f"  [{i}] {name}")
    print(f"  [0] Отмена")
    print()
    
    try:
        choice = int(input("Выберите список: "))
        if choice == 0:
            return
        if 1 <= choice <= len(user_lists):
            name, file_path = user_lists[choice - 1]
            
            confirm = input(f"Удалить список '{name}'? (y/n): ").strip().lower()
            if confirm == 'y':
                Path(file_path).unlink()
                print(f"\n[+] Список '{name}' удален")
                logger.info(f"Deleted user list: {name}")
        else:
            print("[!] Неверный выбор.")
    except ValueError:
        print("[!] Введите число.")
    
    input("\nНажмите Enter для продолжения...")


def select_user_list() -> Optional[List[str]]:
    """Select a user list interactively."""
    user_lists = _get_user_list_files()
    
    if not user_lists:
        print("[!] Нет сохраненных списков пользователей.")
        return None
    
    print("\nВыберите список пользователей:")
    print("-" * 50)
    
    for i, (name, file_path) in enumerate(user_lists, 1):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            users_count = len(data.get('users', []))
            print(f"  [{i}] {name} ({users_count} польз.)")
        except Exception:
            print(f"  [{i}] {name} (ошибка)")
    
    print(f"  [0] Отмена")
    print()
    
    try:
        choice = int(input("Выбор: "))
        if choice == 0:
            return None
        if 1 <= choice <= len(user_lists):
            name, _ = user_lists[choice - 1]
            return load_user_list(name)
        print("[!] Неверный выбор.")
        return None
    except ValueError:
        print("[!] Введите число.")
        return None
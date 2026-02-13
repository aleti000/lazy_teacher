#!/usr/bin/env python3
"""
UI Menus module for Lazy Teacher.
Provides menu interfaces with ASCII-only interface.
"""

import sys
import glob
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import logging
from . import shared
from .logger import get_logger, OperationTimer

logger = get_logger(__name__)


def clear_screen():
    """Clear the console screen."""
    shared.console.clear()


def print_header(title: str):
    """Print a formatted header."""
    width = 60
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)
    print()


def print_menu(options: Dict[str, str], title: str = None):
    """Print a menu with options."""
    if title:
        print(f"\n{title}")
        print("-" * 40)
    
    for key, desc in options.items():
        if key == '0':
            print(f"  [{key}] {desc}")
        else:
            print(f"  [{key}] {desc}")
    print()


def get_choice(prompt: str = "Выберите действие: ") -> str:
    """Get user choice."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return '0'


def select_from_list(items: List[str], title: str = "Выберите элемент") -> Optional[str]:
    """Select an item from a list."""
    if not items:
        print("[!] Список пуст")
        return None
    
    print(f"\n{title}:")
    print("-" * 40)
    
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {item}")
    print(f"  [0] Отмена")
    print()
    
    try:
        choice = input("Выбор: ").strip()
        if choice == '0':
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            return items[idx]
        print("[!] Неверный выбор")
        return None
    except (ValueError, EOFError, KeyboardInterrupt):
        print("[!] Неверный ввод")
        return None


def show_help(section: str) -> None:
    """Display contextual help for a menu section."""
    clear_screen()
    
    help_text = {
        "main": """
СПРАВКА: Главное меню
=====================

Управление системой развертывания стендов на Proxmox VE.

Опции:
  [1] Создать стенды - развертывание новых стендов для пользователей
  [2] Управление стендами - управление существующими стендами
  [3] Управление конфигурациями - создание и редактирование конфигураций
  [4] Помощь - эта справка
  [0] Выход

Для навигации вводите номер пункта и нажмите Enter.
        """,
        "create_stands": """
СПРАВКА: Создание стендов
=========================

Развертывание виртуальных стендов для пользователей.

Процесс:
  1. Выберите конфигурацию стенда (или создайте новую)
  2. Выберите список пользователей (или введите вручную)
  3. Выберите тип развертывания (если несколько нод)

Группы:
  При развертывании автоматически создается группа {stand}-{list}
        """,
        "manage_stands": """
СПРАВКА: Управление стендами
============================

Управление развернутыми стендами.

Опции:
  - Включить все машины: запуск всех VM стенда/группы
  - Сбросить на "start": откат к snapshot "start"
  - Удалить стенд: полное удаление стенда
        """,
    }

    if section in help_text:
        print(help_text[section])
    else:
        print(f"[!] Справка для раздела '{section}' не найдена.")

    input("\nНажмите Enter для продолжения...")


def select_from_config_files(pattern: str, suffix: str, title: str) -> Optional[Tuple[Any, str]]:
    """Select from configuration files."""
    files = glob.glob(pattern)
    if not files:
        print(f"[!] Нет файлов {suffix}.")
        return None

    items = []
    for file in files:
        item_name = Path(file).stem.replace(suffix, '')
        items.append((item_name, file))

    print(f"\n{title}:")
    print("-" * 40)
    
    for i, (name, _) in enumerate(items, 1):
        print(f"  [{i}] {name}")
    print(f"  [0] Отмена")
    print()
    
    try:
        choice = input("Выбор: ").strip()
        if choice == '0':
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            name, file_path = items[idx]
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            logger.info(f"Selected {suffix}: {name}")
            return data, file_path
        print("[!] Неверный выбор")
        return None
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Error selecting {suffix}: {e}")
        print(f"[!] Ошибка: {e}")
        return None


def select_stand_config() -> Optional[Tuple[Any, str]]:
    """Select stand configuration file."""
    pattern = str(shared.CONFIG_DIR / "*_stand.yaml")
    return select_from_config_files(pattern, '_stand', "Выберите конфигурацию стенда")


def select_user_list() -> Optional[List[str]]:
    """Select user list file."""
    pattern = str(shared.CONFIG_DIR / "*_list.yaml")
    result = select_from_config_files(pattern, '_list', "Выберите список пользователей")
    return result[0].get('users', []) if result else None


def select_clone_type() -> int:
    """Select clone type."""
    print("\nТип клонирования:")
    print("  [1] Полное клонирование (full)")
    print("  [2] Связанное клонирование (linked)")
    print()
    
    choice = get_choice("Выбор: ")
    return 1 if choice == '1' else 0


# ==================== MAIN MENU ====================

def main_menu():
    """Main menu handler."""
    options = {
        '1': 'Создать стенды',
        '2': 'Управление стендами',
        '3': 'Управление конфигурациями',
        '4': 'Дополнительные функции',
        '5': 'Помощь',
        '0': 'Выход'
    }
    
    while True:
        clear_screen()
        print_header("⚡ LAZY TEACHER")
        print(f"  Подключение: {shared.DEFAULT_CONN}")
        print()
        print_menu(options, "Главное меню")
        
        choice = get_choice()
        
        if choice == '0':
            print("\n[+] Выход из программы...")
            sys.exit(0)
        elif choice == '1':
            create_stands_menu()
        elif choice == '2':
            manage_stands_menu()
        elif choice == '3':
            config_menu()
        elif choice == '4':
            extra_functions_menu()
        elif choice == '5':
            show_help("main")


# ==================== CREATE STANDS MENU ====================

def create_stands_menu():
    """Menu for creating stands."""
    from .connections import get_proxmox_connection
    from .groups import create_group, generate_group_name, group_exists
    from .deploy_stand_local import deploy_stand_local
    from .deploy_stand_distributed import deploy_stand_distributed
    
    clear_screen()
    print_header("СОЗДАНИЕ СТЕНДОВ")
    
    # Step 1: Select stand config
    stand_configs = _get_stand_config_choices()
    
    if not stand_configs:
        print("[!] Нет конфигураций стендов")
        create_new = input("Создать новую конфигурацию? (y/n): ").strip().lower()
        if create_new == 'y':
            stand_name = input("Имя стенда: ").strip()
            if stand_name:
                stand = {'machines': []}
                create_stand_config_menu(stand_name, stand)
                if not stand['machines']:
                    return
                stand_file = f"{stand_name}_stand.yaml"
            else:
                return
        else:
            input("\nНажмите Enter для продолжения...")
            return
    else:
        print("Конфигурации стендов:")
        for i, cfg in enumerate(stand_configs, 1):
            print(f"  [{i}] {cfg}")
        print(f"  [{len(stand_configs)+1}] Создать новую конфигурацию")
        print(f"  [0] Отмена")
        print()
        
        choice = get_choice("Выбор: ")
        
        if choice == '0':
            return
        
        try:
            idx = int(choice) - 1
            if idx == len(stand_configs):
                # Create new
                stand_name = input("Имя стенда: ").strip()
                if not stand_name:
                    return
                stand = {'machines': []}
                create_stand_config_menu(stand_name, stand)
                if not stand['machines']:
                    return
                stand_file = f"{stand_name}_stand.yaml"
            elif 0 <= idx < len(stand_configs):
                stand_file = f"{stand_configs[idx]}_stand.yaml"
                stand_path = shared.CONFIG_DIR / stand_file
                with open(stand_path, 'r', encoding='utf-8') as f:
                    stand = yaml.safe_load(f)
            else:
                print("[!] Неверный выбор")
                input("\nНажмите Enter для продолжения...")
                return
        except Exception as e:
            print(f"[!] Ошибка: {e}")
            input("\nНажмите Enter для продолжения...")
            return
    
    # Step 2: Select user list
    user_lists = _get_user_list_choices()
    
    if not user_lists:
        print("\n[!] Нет списков пользователей")
        users = _enter_users_menu()
        if not users:
            return
        user_list_file = "manual"
    else:
        print("\nСписки пользователей:")
        for i, lst in enumerate(user_lists, 1):
            print(f"  [{i}] {lst}")
        print(f"  [{len(user_lists)+1}] Ввести пользователей вручную")
        print(f"  [0] Отмена")
        print()
        
        choice = get_choice("Выбор: ")
        
        if choice == '0':
            return
        
        try:
            idx = int(choice) - 1
            if idx == len(user_lists):
                users = _enter_users_menu()
                if not users:
                    return
                user_list_file = "manual"
            elif 0 <= idx < len(user_lists):
                user_list_file = f"{user_lists[idx]}_list.yaml"
                user_list_path = shared.CONFIG_DIR / user_list_file
                with open(user_list_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    users = data.get('users', [])
            else:
                print("[!] Неверный выбор")
                input("\nНажмите Enter для продолжения...")
                return
        except Exception as e:
            print(f"[!] Ошибка: {e}")
            input("\nНажмите Enter для продолжения...")
            return
    
    # Step 3: Generate group name
    group_name = generate_group_name(stand_file, user_list_file)
    
    if group_exists(group_name):
        print(f"\n[!] Группа '{group_name}' уже существует.")
        overwrite = input("Перезаписать? (y/n): ").strip().lower()
        if overwrite != 'y':
            return
    
    # Step 4: Select clone type
    clone_type = select_clone_type()
    
    # Step 5: Check cluster nodes
    try:
        prox = get_proxmox_connection()
        nodes_data = prox.nodes.get()
        nodes = [n['node'] for n in nodes_data]
    except Exception as e:
        print(f"[!] Ошибка получения списка нод: {e}")
        input("\nНажмите Enter для продолжения...")
        return
    
    if len(nodes) <= 1:
        # Single node
        print(f"\n[*] Кластер содержит 1 ноду. Локальное развертывание...")
        create_group(group_name, stand_file, user_list_file, users)
        deploy_stand_local(stand_config=stand, users_list=users, clone_type=clone_type)
    else:
        # Multiple nodes
        print(f"\nКластер содержит {len(nodes)} нод. Выберите тип развертывания:")
        print("  [1] Равномерное распределение по нодам")
        print("  [2] Развертывание на выбранной ноде")
        print("  [0] Отмена")
        print()
        
        deploy_choice = get_choice("Выбор: ")
        
        if deploy_choice == '0':
            return
        
        create_group(group_name, stand_file, user_list_file, users)
        
        if deploy_choice == '1':
            deploy_stand_distributed(stand_config=stand, users_list=users, clone_type=clone_type)
        elif deploy_choice == '2':
            print("\nДоступные ноды:")
            for i, node in enumerate(nodes, 1):
                print(f"  [{i}] {node}")
            print()
            
            node_choice = get_choice("Выбор ноды: ")
            try:
                node_idx = int(node_choice) - 1
                if 0 <= node_idx < len(nodes):
                    deploy_stand_local(stand_config=stand, users_list=users,
                                      target_node=nodes[node_idx], clone_type=clone_type)
                else:
                    print("[!] Неверный выбор")
            except ValueError:
                print("[!] Неверный ввод")


def _get_stand_config_choices() -> List[str]:
    """Get list of available stand configs."""
    pattern = str(shared.CONFIG_DIR / "*_stand.yaml")
    files = glob.glob(pattern)
    return [Path(f).stem.replace('_stand', '') for f in files]


def _get_user_list_choices() -> List[str]:
    """Get list of available user lists."""
    pattern = str(shared.CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    return [Path(f).stem.replace('_list', '') for f in files]


def _enter_users_menu() -> List[str]:
    """Menu for entering users manually."""
    users = []
    
    print("\nВведите пользователей (пустая строка для завершения):")
    
    while True:
        user = input("Пользователь: ").strip()
        if not user:
            break
        if '@' not in user:
            user = f"{user}@pve"
        users.append(user)
    
    if users:
        print(f"\nВведено {len(users)} пользователей")
        save = input("Сохранить список? (y/n): ").strip().lower()
        
        if save == 'y':
            list_name = input("Имя списка: ").strip()
            if list_name:
                from .users import save_user_list
                save_user_list(list_name, users)
    
    return users


# ==================== MANAGE STANDS MENU ====================

def manage_stands_menu():
    """Menu for managing existing stands."""
    from .groups import get_groups
    
    while True:
        clear_screen()
        print_header("УПРАВЛЕНИЕ СТЕНДАМИ")
        
        groups = get_groups()
        
        if not groups:
            print("[!] Нет развернутых стендов.")
            input("\nНажмите Enter для продолжения...")
            return
        
        print("Группы стендов:")
        items = []
        for i, (group_name, group_data) in enumerate(groups.items(), 1):
            user_count = len(group_data.get('users', []))
            print(f"  [{i}] {group_name} ({user_count} польз.)")
            items.append(group_name)
        print(f"  [0] Назад")
        print()
        
        choice = get_choice("Выбор: ")
        
        if choice == '0':
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                manage_group_menu(items[idx])
            else:
                print("[!] Неверный выбор")
        except ValueError:
            print("[!] Неверный ввод")


def manage_group_menu(group_name: str):
    """Menu for managing a specific group."""
    from .groups import get_group, get_group_users, delete_group, remove_user_from_group
    from .connections import get_proxmox_connection
    
    group = get_group(group_name)
    if not group:
        print(f"[!] Группа {group_name} не найдена")
        return
    
    users = group.get('users', [])
    
    while True:
        clear_screen()
        print_header(f"УПРАВЛЕНИЕ ГРУППОЙ: {group_name}")
        print(f"  Пользователей: {len(users)}")
        print()
        
        options = {
            '1': 'Включить все машины группы',
            '2': 'Сбросить все на snapshot "start"',
            '3': 'Удалить все стенды группы',
            '4': 'Управление отдельными пользователями',
            '0': 'Назад'
        }
        print_menu(options)
        
        choice = get_choice()
        
        if choice == '0':
            return
        
        try:
            prox = get_proxmox_connection()
            
            if choice == '1':
                _start_all_group_vms(prox, users)
            elif choice == '2':
                _reset_all_group_vms(prox, users)
            elif choice == '3':
                confirm = input(f"Удалить все стенды группы {group_name}? (y/n): ").strip().lower()
                if confirm == 'y':
                    _delete_all_group_stands(prox, users, group_name)
                    return
            elif choice == '4':
                manage_group_users_menu(group_name, users)
                
        except Exception as e:
            print(f"[!] Ошибка: {e}")
            input("\nНажмите Enter для продолжения...")


def manage_group_users_menu(group_name: str, users: List[str]):
    """Menu for managing individual users in a group."""
    from .groups import remove_user_from_group
    from .connections import get_proxmox_connection
    
    while True:
        clear_screen()
        print_header(f"ПОЛЬЗОВАТЕЛИ ГРУППЫ: {group_name}")
        
        for i, user in enumerate(users, 1):
            print(f"  [{i}] {user}")
        print(f"  [0] Назад")
        print()
        
        choice = get_choice("Выберите пользователя: ")
        
        if choice == '0':
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(users):
                username = users[idx]
            else:
                print("[!] Неверный выбор")
                continue
        except ValueError:
            print("[!] Неверный ввод")
            continue
        
        # User actions
        print(f"\nДействия для {username}:")
        print("  [1] Включить все машины")
        print("  [2] Сбросить на snapshot 'start'")
        print("  [3] Удалить стенд пользователя")
        print("  [0] Назад")
        print()
        
        action = get_choice("Выбор: ")
        
        if action == '0':
            continue
        
        try:
            prox = get_proxmox_connection()
            
            if action == '1':
                _start_user_vms(prox, username)
            elif action == '2':
                _reset_user_vms(prox, username)
            elif action == '3':
                confirm = input(f"Удалить стенд пользователя {username}? (y/n): ").strip().lower()
                if confirm == 'y':
                    _delete_user_stand(prox, username)
                    remove_user_from_group(group_name, username)
                    users.remove(username)
                    if not users:
                        return
                    
        except Exception as e:
            print(f"[!] Ошибка: {e}")
            input("\nНажмите Enter для продолжения...")


def _start_all_group_vms(prox, users: List[str]):
    """Start all VMs for all users in group."""
    print(f"\n[*] Запуск всех VM группы ({len(users)} пользователей)...")
    
    for user in users:
        _start_user_vms(prox, user)
    
    print("\n[+] Все VM группы запущены")
    input("Нажмите Enter для продолжения...")


def _reset_all_group_vms(prox, users: List[str]):
    """Reset all VMs to 'start' snapshot for all users in group."""
    print(f"\n[*] Сброс всех VM группы на 'start' ({len(users)} пользователей)...")
    
    for user in users:
        _reset_user_vms(prox, user)
    
    print("\n[+] Все VM группы сброшены")
    input("Нажмите Enter для продолжения...")


def _delete_all_group_stands(prox, users: List[str], group_name: str):
    """Delete all stands in group."""
    from .groups import delete_group
    
    print(f"\n[*] Удаление всех стендов группы {group_name}...")
    
    for user in users:
        _delete_user_stand(prox, user)
    
    delete_group(group_name)
    print(f"\n[+] Группа {group_name} удалена")
    input("Нажмите Enter для продолжения...")


def _start_user_vms(prox, username: str):
    """Start all VMs for a user."""
    pool_name = username.split('@')[0]
    
    try:
        pool = prox.pools(pool_name).get()
        members = pool.get('members', [])
        
        for member in members:
            vmid = member.get('vmid')
            node = member.get('node')
            
            if vmid and node:
                try:
                    vm_status = prox.nodes(node).qemu(vmid).status.current.get()
                    if vm_status.get('status') != 'running':
                        prox.nodes(node).qemu(vmid).status.start.post()
                        print(f"  [+] VM {vmid} запущена")
                except Exception as e:
                    logger.error(f"Error starting VM {vmid}: {e}")
                    
    except Exception as e:
        print(f"  [!] Не удалось запустить VM для {username}: {e}")


def _reset_user_vms(prox, username: str):
    """Reset all VMs for a user to 'start' snapshot."""
    pool_name = username.split('@')[0]
    
    try:
        pool = prox.pools(pool_name).get()
        members = pool.get('members', [])
        
        for member in members:
            vmid = member.get('vmid')
            node = member.get('node')
            
            if vmid and node:
                try:
                    vm_status = prox.nodes(node).qemu(vmid).status.current.get()
                    if vm_status.get('status') == 'running':
                        prox.nodes(node).qemu(vmid).status.stop.post()
                        import time
                        for _ in range(30):
                            status = prox.nodes(node).qemu(vmid).status.current.get()
                            if status.get('status') == 'stopped':
                                break
                            time.sleep(1)
                    
                    prox.nodes(node).qemu(vmid).snapshot('start').rollback.post()
                    print(f"  [+] VM {vmid} сброшена на 'start'")
                    
                except Exception as e:
                    logger.error(f"Error resetting VM {vmid}: {e}")
                    
    except Exception as e:
        print(f"  [!] Не удалось сбросить VM для {username}: {e}")


def _delete_user_stand(prox, username: str):
    """Delete all VMs and resources for a user."""
    from .deletion import delete_user_stand_logic
    
    pool_name = username.split('@')[0]
    
    try:
        delete_user_stand_logic(prox, pool_name)
        print(f"  [+] Стенд пользователя {username} удален")
    except Exception as e:
        print(f"  [!] Ошибка удаления стенда {username}: {e}")


# ==================== CONFIG MENU ====================

def config_menu():
    """Configuration management menu."""
    options = {
        '1': 'Конфигурации стендов',
        '2': 'Списки пользователей',
        '3': 'Подключения',
        '0': 'Назад'
    }
    
    while True:
        clear_screen()
        print_header("УПРАВЛЕНИЕ КОНФИГУРАЦИЯМИ")
        print_menu(options)
        
        choice = get_choice()
        
        if choice == '0':
            break
        elif choice == '1':
            stand_config_menu()
        elif choice == '2':
            user_config_menu()
        elif choice == '3':
            connection_menu()


def stand_config_menu():
    """Stand configuration management menu."""
    from .stands import display_list_of_stands, delete_stand_file
    
    options = {
        '1': 'Создать конфигурацию стенда',
        '2': 'Список конфигураций',
        '3': 'Удалить конфигурацию',
        '0': 'Назад'
    }
    
    while True:
        clear_screen()
        print_header("КОНФИГУРАЦИИ СТЕНДОВ")
        print_menu(options)
        
        choice = get_choice()
        
        if choice == '0':
            break
        elif choice == '1':
            stand_name = input("Введите имя стенда: ").strip()
            if stand_name:
                stand = {'machines': []}
                create_stand_config_menu(stand_name, stand)
        elif choice == '2':
            display_list_of_stands()
        elif choice == '3':
            delete_stand_file()


def create_stand_config_menu(stand_name: str, stand: Dict[str, Any]):
    """Menu for creating stand configuration."""
    from .stands import add_vm_to_stand, remove_vm_from_stand, display_stand_vms, save_stand
    
    while True:
        clear_screen()
        print_header(f"СОЗДАНИЕ СТЕНДА: {stand_name}")
        print(f"  Машин в конфигурации: {len(stand.get('machines', []))}")
        print()
        
        options = {
            '1': 'Добавить VM',
            '2': 'Удалить VM из конфигурации',
            '3': 'Просмотреть конфигурацию',
            '4': 'Сохранить и выйти',
            '0': 'Выйти без сохранения'
        }
        print_menu(options)
        
        choice = get_choice()
        
        if choice == '0':
            return
        elif choice == '1':
            add_vm_to_stand(stand, shared.DEFAULT_CONN)
        elif choice == '2':
            remove_vm_from_stand(stand)
        elif choice == '3':
            display_stand_vms(stand)
        elif choice == '4':
            save_stand(stand_name, stand)
            return


def user_config_menu():
    """User list management menu."""
    from .users import input_users_manual, import_users, display_user_lists, delete_user_list
    
    options = {
        '1': 'Импорт пользователей из файла',
        '2': 'Ввод пользователей вручную',
        '3': 'Список сохраненных списков',
        '4': 'Удалить список',
        '0': 'Назад'
    }
    
    while True:
        clear_screen()
        print_header("СПИСКИ ПОЛЬЗОВАТЕЛЕЙ")
        print_menu(options)
        
        choice = get_choice()
        
        if choice == '0':
            break
        elif choice == '1':
            import_users()
        elif choice == '2':
            input_users_manual()
        elif choice == '3':
            display_user_lists()
        elif choice == '4':
            delete_user_list()


def connection_menu():
    """Connection management menu."""
    from .connections import create_connection, delete_connection, display_connections
    
    options = {
        '1': 'Создать новое подключение',
        '2': 'Отобразить все подключения',
        '3': 'Удалить подключение',
        '0': 'Назад'
    }
    
    while True:
        clear_screen()
        print_header("УПРАВЛЕНИЕ ПОДКЛЮЧЕНИЯМИ")
        print_menu(options)
        
        choice = get_choice()
        
        if choice == '0':
            break
        elif choice == '1':
            create_connection()
        elif choice == '2':
            display_connections()
        elif choice == '3':
            delete_connection()


# ==================== LEGACY FUNCTIONS ====================

def config_menu_legacy():
    """Legacy config menu."""
    config_menu()


def stand_menu():
    """Legacy stand menu."""
    stand_config_menu()


def user_menu():
    """Legacy user menu."""
    user_config_menu()


def create_stand_menu(conn_name: Optional[str] = None):
    """Legacy create stand menu."""
    stand_name = input("Введите имя стенда: ").strip()
    if not stand_name:
        return
    stand = {'machines': []}
    create_stand_config_menu(stand_name, stand)


def deploy_stand_menu():
    """Legacy deploy stand menu."""
    create_stands_menu()


def delete_stand_menu():
    """Legacy delete stand menu."""
    manage_stands_menu()


def extra_functions_menu():
    """Menu for additional functions."""
    from .deletion import delete_all_user_stands
    from .connections import get_proxmox_connection

    options = {
        '1': 'Удалить стенды по списку пользователей',
        '2': 'Удалить стенд пользователя вручную',
        '0': 'Назад'
    }

    while True:
        clear_screen()
        print_header("ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ")
        print_menu(options)

        choice = get_choice()

        if choice == '0':
            return
        elif choice == '1':
            print("\n[+] Запуск удаления стендов по списку пользователей...")
            delete_all_user_stands()
            input("\nНажмите Enter для продолжения...")
        elif choice == '2':
            username = input("Введите имя пользователя (например user1@pve): ").strip()
            if username:
                prox = get_proxmox_connection()
                _delete_user_stand(prox, username)
                input("\nНажмите Enter для продолжения...")
        else:
            print("[!] Неверный выбор")

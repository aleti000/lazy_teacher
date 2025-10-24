#!/usr/bin/env python3
"""
UI Menus module for Lazy Teacher.
Provides all menu interfaces for the application.
"""

import sys
import yaml
from pathlib import Path
from . import shared
from rich.panel import Panel

from . import shared
from .connections import create_connection, delete_connection, display_connections
from .users import input_users_manual, import_users, display_user_lists, delete_user_list
from .stands import add_vm_to_stand, remove_vm_from_stand, display_stand_vms, save_stand, delete_stand_file, display_list_of_stands
from .deletion import delete_user_stand, delete_all_user_stands
from .deploy_stand_local import deploy_stand_local
from .deploy_stand_distributed import deploy_stand_distributed

def main_menu():
    """Main menu handler with styled menu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Управление конфигурационными файлами[/green]\n"
            "[green]2. Развернуть стенд[/green]\n"
            "[green]3. Удалить стенд[/green]\n"
            "[red]0. Выход[/red]",
            title="[bold blue]Главное меню[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            shared.console.print("[blue]Выход из программы...[/blue]")
            sys.exit(0)
        elif choice == '1':
            config_menu()
        elif choice == '2':
            deploy_stand_menu()
        elif choice == '3':
            delete_stand_menu()
        else:
            shared.console.print("[red]Недопустимый выбор. Попробуйте еще раз.[/red]")

def config_menu():
    """Configuration management menu with styled menu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Управление подключениями[/green]\n"
            "[green]2. Управление пользователями[/green]\n"
            "[green]3. Управление стендами[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Меню конфигурации[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            connection_menu()
        elif choice == '2':
            user_menu()
        elif choice == '3':
            stand_menu()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

def connection_menu():
    """Connection management submenu with styled menu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Создать новое подключение[/green]\n"
            "[green]2. Отобразить все подключения[/green]\n"
            "[green]3. Удалить подключение[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Управление подключениями[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            create_connection()
        elif choice == '2':
            display_connections()
        elif choice == '3':
            delete_connection()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

def user_menu():
    """User management menu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Ввести пользователей вручную[/green]\n"
            "[green]2. Импорт пользователей из списка[/green]\n"
            "[green]3. Отобразить списки пользователей[/green]\n"
            "[green]4. Удалить список пользователей[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Управление пользователями[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            input_users_manual()
        elif choice == '2':
            import_users()
        elif choice == '3':
            display_user_lists()
        elif choice == '4':
            delete_user_list()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

def stand_menu():
    """Stand management menu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Создать стенд[/green]\n"
            "[green]2. Вывести список стендов[/green]\n"
            "[green]3. Удалить стенд[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Управление стендами[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            print(f"DEBUG: stand_menu DEFAULT_CONN = {shared.DEFAULT_CONN}")
            create_stand_menu(shared.DEFAULT_CONN)
        elif choice == '2':
            display_list_of_stands()
        elif choice == '3':
            delete_stand_file()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

def create_stand_menu(conn_name=None):
    """Create stand submenu."""
    stand_name = input("Введите имя стенда: ").strip()
    if not stand_name:
        return

    stand = {'machines': []}
    # Use provided connection name or DEFAULT_CONN
    if conn_name is None:
        conn_name = shared.DEFAULT_CONN

    print(f"DEBUG: conn_name = {conn_name}, DEFAULT_CONN = {shared.DEFAULT_CONN}")

    if not conn_name:
        print("Нет активного подключения.")
        return

    while True:
        shared.console.clear()
        print("Создание стенда:", stand_name)
        print("1. Создать VM")
        print("2. Удалить VM из стенда")
        print("3. Отобразить список VM")
        print("4. Сохранить стенд")
        print("0. Назад")

        choice = input("Выберите: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            add_vm_to_stand(stand, conn_name)
        elif choice == '2':
            remove_vm_from_stand(stand)
        elif choice == '3':
            display_stand_vms(stand)
        elif choice == '4':
            save_stand(stand_name, stand)
            break
        else:
            print("Недопустимый выбор.")

def deploy_stand_menu():
    """Deploy stand submenu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Локальная развертка ВМ[/green]\n"
            "[green]2. Равномерное распределение машин между нодами[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Развернуть стенд[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            deploy_stand_local()
        elif choice == '2':
            deploy_stand_distributed()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

def delete_stand_menu():
    """Delete stand submenu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Удалить стенд пользователя[/green]\n"
            "[green]2. Удалить все стенды из списка пользователей[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Удалить стенд[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            delete_user_stand()
        elif choice == '2':
            delete_all_user_stands()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

def select_clone_type():
    """Select clone type."""
    print("Выберите тип клонирования:")
    print("1. Полное клонирование (full)")
    print("2. Связанное клонирование (linked)")

    choice = input("Выбор: ").strip()
    return 1 if choice == '1' else 0

def select_stand_config():
    """Select stand configuration file."""
    import glob
    pattern = str(shared.CONFIG_DIR / "*_stand.yaml")
    files = glob.glob(pattern)
    if not files:
        print("Нет конфигураций стендов.")
        return None

    print("Выберите конфигурацию стенда:")
    stands = []
    for file in files:
        stand_name = Path(file).stem.replace('_stand', '')
        stands.append((stand_name, file))

    for i, (name, _) in enumerate(stands, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Номер: ")) - 1
        if 0 <= choice < len(stands):
            name, file = stands[choice]
            with open(file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except (ValueError, FileNotFoundError):
        pass
    return None

def select_user_list():
    """Select user list file."""
    import glob
    pattern = str(shared.CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    if not files:
        print("Нет списков пользователей.")
        return None

    print("Выберите список пользователей:")
    lists = []
    for file in files:
        list_name = Path(file).stem.replace('_list', '')
        lists.append((list_name, file))

    for i, (name, _) in enumerate(lists, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Номер: ")) - 1
        if 0 <= choice < len(lists):
            name, file = lists[choice]
            with open(file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            return data.get('users', [])
    except (ValueError, FileNotFoundError):
        pass
    return None

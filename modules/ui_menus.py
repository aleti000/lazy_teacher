#!/usr/bin/env python3
"""
UI Menus module for Lazy Teacher.
Provides optimized menu interfaces for the application.
"""

import sys
import glob
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Callable
import logging
from . import shared
from .logger import get_logger, OperationTimer
from rich.panel import Panel
from rich.table import Table

from .connections import create_connection, delete_connection, display_connections
from .users import input_users_manual, import_users, display_user_lists, delete_user_list
from .stands import add_vm_to_stand, remove_vm_from_stand, display_stand_vms, save_stand, delete_stand_file, display_list_of_stands
from .deletion import delete_user_stand, delete_all_user_stands

logger = get_logger(__name__)

def _display_menu(title: str, options: Dict[str, str], border_color: str = "blue") -> Optional[str]:
    """
    Display a standardized menu and get user choice.

    Args:
        title: Menu title
        options: Dict of option -> description
        border_color: Rich border color

    Returns:
        User choice or None if exit/back
    """
    with OperationTimer(logger, f"Display menu: {title}"):
        shared.console.clear()

        # Build menu content
        menu_content = ""
        for key, desc in options.items():
            if key == '0':
                menu_content += f"[red]{key}. {desc}[/red]\n"
            else:
                menu_content += f"[green]{key}. {desc}[/green]\n"

        shared.console.print(
            Panel.fit(
                f"\n{menu_content}",
                title=f"[bold {border_color}]{title}[/bold {border_color}]",
                border_style=border_color
            )
        )
        shared.console.print()

        choice = input("Выберите действие: ").strip()
        logger.debug(f"Menu choice: {choice}", menu=title)
        return choice

def _handle_menu_choice(choice: str, handlers: Dict[str, Callable]) -> bool:
    """
    Handle menu choice with centralized error handling.

    Args:
        choice: User's choice
        handlers: Dict of choice -> handler function

    Returns:
        True if handled, False if invalid choice
    """
    if choice in handlers:
        try:
            if handlers[choice]() is False:  # Allow handlers to return False to indicate no action
                pass
            return True
        except Exception as e:
            logger.error(f"Error in menu handler for choice {choice}", error=str(e))
            shared.console.print(f"[red]Ошибка выполнения действия: {e}[/red]")
            input("Нажмите Enter для продолжения...")
            return True
    else:
        shared.console.print("[red]Недопустимый выбор. Попробуйте еще раз.[/red]")
        return False

def select_from_config_files(pattern: str, suffix: str, title: str) -> Optional[Tuple[Any, str]]:
    """
    Generic function to select from configuration files.

    Args:
        pattern: Glob pattern to find files
        suffix: Suffix to remove from filename for display
        title: Title for selection menu

    Returns:
        Tuple of (data, file_path) or None
    """
    with OperationTimer(logger, f"Select from {pattern}"):
        files = glob.glob(pattern)
        if not files:
            shared.console.print(f"[red]Нет {suffix.lower()}.[/red]")
            logger.info(f"No {suffix.lower()} files found")
            return None

        shared.console.print(f"Выберите {suffix.lower()}:")
        items = []

        for file in files:
            item_name = Path(file).stem.replace(suffix, '')
            items.append((item_name, file))

        for i, (name, _) in enumerate(items, 1):
            shared.console.print(f"{i}. {name}")

        try:
            choice = int(input("Номер: ")) - 1
            if 0 <= choice < len(items):
                name, file_path = items[choice]
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                logger.info(f"Selected {suffix.lower()}: {name} (file: {file_path})")
                return data, file_path
        except (ValueError, FileNotFoundError) as e:
            logger.warning(f"Error selecting {suffix.lower()}", error=str(e))

        shared.console.print("[red]Некорректный выбор.[/red]")
        return None


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
            create_stand_menu(shared.DEFAULT_CONN)
        elif choice == '2':
            display_list_of_stands()
        elif choice == '3':
            delete_stand_file()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

def create_stand_menu(conn_name: Optional[str] = None):
    """Create stand submenu."""
    with OperationTimer(logger, "Create stand menu"):
        logger.info("Starting stand creation")
        stand_name = input("Введите имя стенда: ").strip()
        if not stand_name:
            logger.debug("Stand creation cancelled - no name provided")
            return

        stand = {'machines': []}
        # Use provided connection name or DEFAULT_CONN
        if conn_name is None:
            conn_name = shared.DEFAULT_CONN

        if not conn_name:
            shared.console.print("[red]Нет активного подключения.[/red]")
            logger.warning("No active connection for stand creation")
            return

        exit_menu = False

        def _back():
            nonlocal exit_menu
            exit_menu = True

        def _save():
            nonlocal exit_menu
            save_stand(stand_name, stand)
            logger.info(f"Stand '{stand_name}' created successfully", machine_count=len(stand.get('machines', [])))
            exit_menu = True

        # Menu handlers
        handlers = {
            '0': _back,
            '1': lambda: add_vm_to_stand(stand, conn_name),
            '2': lambda: remove_vm_from_stand(stand),
            '3': lambda: display_stand_vms(stand),
            '4': _save
        }

        while not exit_menu:
            choice = _display_menu(
                f"Создание стенда: {stand_name}",
                {
                    '1': 'Создать VM',
                    '2': 'Удалить VM из стенда',
                    '3': 'Отобразить список VM',
                    '4': 'Сохранить стенд',
                    '0': 'Назад'
                }
            )

            if choice in handlers:
                handlers[choice]()
            else:
                shared.console.print("[red]Недопустимый выбор.[/red]")

def deploy_stand_menu():
    """Deploy stand submenu."""
    from .deploy_stand_local import deploy_stand_local
    from .deploy_stand_distributed import deploy_stand_distributed

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

def select_clone_type() -> int:
    """Select clone type."""
    with OperationTimer(logger, "Select clone type"):
        shared.console.print("Выберите тип клонирования:")
        shared.console.print("1. Полное клонирование (full)")
        shared.console.print("2. Связанное клонирование (linked)")

        choice = input("Выбор: ").strip()
        clone_type = 1 if choice == '1' else 0
        logger.info(f"Selected clone type: {'full' if clone_type else 'linked'}")
        return clone_type

def select_stand_config() -> Optional[Tuple[Any, str]]:
    """Select stand configuration file."""
    pattern = str(shared.CONFIG_DIR / "*_stand.yaml")
    return select_from_config_files(pattern, '_stand', "конфигурацию стенда")

def select_user_list() -> Optional[List[str]]:
    """Select user list file."""
    pattern = str(shared.CONFIG_DIR / "*_list.yaml")
    result = select_from_config_files(pattern, '_list', "список пользователей")
    return result[0].get('users', []) if result else None

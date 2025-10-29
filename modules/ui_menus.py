#!/usr/bin/env python3
"""
UI Menus mo_ule for Lazy Teacher.
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
import questionary

from .connections import create_connection, delete_connection, display_connections
from .users import input_users_manual, import_users, display_user_lists, delete_user_list
from .stands import add_vm_to_stand, remove_vm_from_stand, display_stand_vms, save_stand, delete_stand_file, display_list_of_stands
from .deletion import delete_user_stand, delete_all_user_stands
from .active_users import manage_active_users
from .stand_management import manage_stands

logger = get_logger(__name__)

def show_help(section: str) -> None:
    """Display contextual help for a menu section."""
    shared.console.clear()

    help_text = {
        "main": """
[bold blue]Справка: Главное меню[/bold blue]

Управление системой развертывания стендов на Proxmox VE.

[bold green]Опции:[/bold green]
- [cyan]Управление конфигурационными файлами[/cyan]: настройка подключений, пользователей, стендов
- [cyan]Управление стендами[/cyan]: развертывание, управление, удаление стендов
- [cyan]Управление активными пользователями[/cyan]: мониторинг и управление VMs активных пользователей
- [cyan]Помощь[/cyan]: эта справка
- [cyan]Выход[/cyan]: выход из программы

Для навигации используйте стрелки, для выбора - Enter.
        """,
        "stands": """
[bold blue]Справка: Управление стендами[/bold blue]

Развертывание и управление виртуальными стендами на Proxmox VE.

[bold green]Опции:[/bold green]
- [cyan]Развернуть стенд[/cyan]: развертывание стенда в кластере
  - Выберите конфигурацию стенда из сохраненных
  - Укажите список пользователей для развертывания
  - Выберите тип развертывания (локальная/распределенная)
  - Система создаст пользователей, пулы, VM, сети автоматически

- [cyan]Удалить стенд[/cyan]: удаление развернутых стендов
  - Удалите стенд конкретного пользователя
  - Или удалите все стенды для группы пользователей

[bold blue]Создание стенда:[/bold blue]
1. Выберите "Создать стенд" в меню управления стендами
2. Введите имя стенда
3. Дизайн конфигурации VM:
   - Выберите шаблон для клонирования
   - Настройте устройства (linux/ecorouter)
   - Добавьте сетевые интерфейсы (bridge:.vlan или **bridge)
   - Принесите bridge будут автоматически созданы в кластере

[bold blue]Bridge (сетевые мосты):[/bold blue]
- **bridge: конкретный bridge по имени (например, **vmbr0)
- bridge: bridge по alias с автоматическим созданием
- bridge.vlan: bridge с VLAN поддержкой
- Система управляет нумерацией bridge автоматически

[bold blue]Развертывание:[/bold blue]
- Для каждого пользователя создается пул VM с полными правами
- VM клонируются из выбранных шаблонов
- Применяются сетевые конфигурации с созданными bridge
- Создаются snapshot "start" для последующего отката

[bold cyan]Советы:[/bold cyan]
- Перед развертыванием убедитесь в наличии шаблонов
- Bridge создаются автоматически для изоляции пользователей
- Выход из создания стенда сохраняет его без развертывания
        """,
    }

    if section in help_text:
        shared.console.print(help_text[section])
    else:
        shared.console.print(f"[yellow]Справка для раздела '{section}' не найдена.[/yellow]")

    input("\nНажмите Enter для продолжения...")
    return

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
        logger.debug(f"Menu choice: {choice} for menu: {title}")
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
            logger.error(f"Error in menu handler for choice {choice}: {e}")
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
            logger.warning(f"Error selecting {suffix.lower()}: {e}")

        shared.console.print("[red]Некорректный выбор.[/red]")
        return None


def main_menu():
    """Main menu handler with questionary menu."""
    choices = [
        "Управление конфигурационными файлами",
        "Управление стендами",
        "Управление активными пользователями",
        "Помощь",
        "Выход"
    ]
    while True:
        shared.console.clear()
        choice = questionary.select("Главное меню", choices=choices).ask()
        if choice == "Выход":
            shared.console.print("[blue]Выход из программы...[/blue]")
            sys.exit(0)
        elif choice == "Управление конфигурационными файлами":
            config_menu()
        elif choice == "Управление стендами":
            manage_stands()
        elif choice == "Управление активными пользователями":
            manage_active_users()
        elif choice == "Помощь":
            show_help("main")

def config_menu():
    """Configuration management menu with questionary."""
    choices = [
        "Управление подключениями",
        "Управление пользователями",
        "Управление стендами",
        "Назад"
    ]
    while True:
        shared.console.clear()
        choice = questionary.select("Меню конфигурации", choices=choices).ask()
        if choice == "Назад":
            break
        elif choice == "Управление подключениями":
            connection_menu()
        elif choice == "Управление пользователями":
            user_menu()
        elif choice == "Управление стендами":
            stand_menu()

def connection_menu():
    """Connection management submenu with questionary."""
    choices = [
        "Создать новое подключение",
        "Отобразить все подключения",
        "Удалить подключение",
        "Назад"
    ]
    while True:
        shared.console.clear()
        choice = questionary.select("Управление подключениями", choices=choices).ask()
        if choice == "Назад":
            break
        elif choice == "Создать новое подключение":
            create_connection()
        elif choice == "Отобразить все подключения":
            display_connections()
        elif choice == "Удалить подключение":
            delete_connection()

def user_menu():
    """User management menu with questionary."""
    choices = [
        "Ввести пользователей вручную",
        "Импорт пользователей из списка",
        "Отобразить списки пользователей",
        "Удалить список пользователей",
        "Назад"
    ]
    while True:
        shared.console.clear()
        choice = questionary.select("Управление пользователями", choices=choices).ask()
        if choice == "Назад":
            break
        elif choice == "Ввести пользователей вручную":
            input_users_manual()
        elif choice == "Импорт пользователей из списка":
            import_users()
        elif choice == "Отобразить списки пользователей":
            display_user_lists()
        elif choice == "Удалить список пользователей":
            delete_user_list()

def stand_menu():
    """Stand management menu with questionary."""
    choices = [
        "Создать стенд",
        "Вывести список стендов",
        "Удалить стенд",
        "Помощь",
        "Назад"
    ]
    while True:
        shared.console.clear()
        choice = questionary.select("Управление стендами", choices=choices).ask()
        if choice == "Назад":
            break
        elif choice == "Создать стенд":
            create_stand_menu(shared.DEFAULT_CONN)
        elif choice == "Вывести список стендов":
            display_list_of_stands()
        elif choice == "Удалить стенд":
            delete_stand_file()
        elif choice == "Помощь":
            # Use the show_help from stand_management since it's detailed
            from .stand_management import show_help
            show_help("stands")

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
            logger.info(f"Stand '{stand_name}' created successfully with {len(stand.get('machines', []))} machines")
            exit_menu = True

        # Menu handlers
        handlers = {
            '0': _back,
            '1': lambda: add_vm_to_stand(stand, conn_name),
            '2': lambda: remove_vm_from_stand(stand),
            '3': lambda: display_stand_vms(stand),
            '4': _save
        }

        choices = [
            "Создать VM",
            "Удалить VM из стенда",
            "Отобразить список VM",
            "Сохранить стенд",
            "Назад"
        ]
        indices = ['1', '2', '3', '4', '0']
        while not exit_menu:
            shared.console.clear()
            choice = questionary.select(f"Создание стенда: {stand_name}", choices=choices).ask()
            choice = indices[choices.index(choice)]
            if choice in handlers:
                handlers[choice]()
            else:
                shared.console.print("[red]Недопустимый выбор.[/red]")

def deploy_stand_menu():
    """Deploy stand submenu with questionary."""
    from .deploy_stand_local import deploy_stand_local
    from .deploy_stand_distributed import deploy_stand_distributed

    choices = [
        "Локальная развертка ВМ",
        "Равномерное распределение машин между нодами",
        "Назад"
    ]
    while True:
        shared.console.clear()
        choice = questionary.select("Развернуть стенд", choices=choices).ask()
        if choice == "Назад":
            break
        elif choice == "Локальная развертка ВМ":
            deploy_stand_local()
        elif choice == "Равномерное распределение машин между нодами":
            deploy_stand_distributed()

def delete_stand_menu():
    """Delete stand submenu with questionary."""
    choices = [
        "Удалить стенд пользователя",
        "Удалить все стенды из списка пользователей",
        "Назад"
    ]
    while True:
        shared.console.clear()
        choice = questionary.select("Удалить стенд", choices=choices).ask()
        if choice == "Назад":
            break
        elif choice == "Удалить стенд пользователя":
            delete_user_stand()
        elif choice == "Удалить все стенды из списка пользователей":
            delete_all_user_stands()

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

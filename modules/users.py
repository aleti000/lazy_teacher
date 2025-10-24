#!/usr/bin/env python3
"""
Users module for Lazy Teacher.
Provides optimized functions for managing user lists.
"""

import glob
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import logging
from . import shared
from .logger import get_logger, log_operation, log_error, OperationTimer
from rich.table import Table

logger = get_logger(__name__)

def _normalize_user(user: str) -> str:
    """Normalize user format, ensuring @pve domain."""
    if '@' not in user:
        user += '@pve'
    return user

def _load_user_list(list_name: str) -> Optional[List[str]]:
    """Load user list from YAML file."""
    file_path = shared.CONFIG_DIR / f"{list_name}_list.yaml"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        users = data.get('users', [])
        logger.debug(f"Loaded {len(users)} users from {list_name}")
        return users if isinstance(users, list) else []
    except FileNotFoundError:
        logger.debug(f"User list {list_name} not found")
        return None
    except Exception as e:
        log_error(logger, e, f"Load user list {list_name}")
        return None

def _save_user_list(list_name: str, users: List[str]) -> bool:
    """Save user list to YAML file."""
    file_path = shared.CONFIG_DIR / f"{list_name}_list.yaml"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump({'users': users}, f, default_flow_style=False)
        logger.debug(f"Saved {len(users)} users to {list_name}")
        return True
    except Exception as e:
        log_error(logger, e, f"Save user list {list_name}")
        return False

def _get_user_lists() -> List[Tuple[str, str]]:
    """Get list of available user lists with their file paths."""
    pattern = str(shared.CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    return [(Path(file).stem.replace('_list', ''), file) for file in files]

def input_users_manual() -> Optional[str]:
    """Manually input list of users with validation."""
    with OperationTimer(logger, "Manual user input"):
        list_name = input("Введите имя списка пользователей: ").strip()
        if not list_name:
            logger.debug("Manual input cancelled - no list name")
            return None

        # Check if list already exists
        if _load_user_list(list_name) is not None:
            shared.console.print(f"[yellow]Список '{list_name}' уже существует и будет перезаписан.[/yellow]")

        users = []
        shared.console.print("Введите пользователей (оставьте пустым для завершения):")

        while True:
            user_input = input("Пользователь: ").strip()
            if not user_input:
                break

            normalized_user = _normalize_user(user_input)
            users.append(normalized_user)
            logger.debug(f"Added user: {normalized_user}")

        if not users:
            shared.console.print("[yellow]Список пустой.[/yellow]")
            logger.info("No users entered - cancelled")
            return None

        if _save_user_list(list_name, users):
            shared.console.print(f"[green]Список пользователя '{list_name}' сохранен ({len(users)} пользователей).[/green]")
            log_operation(logger, "Created user list", success=True, list_name=list_name, user_count=len(users))
            return list_name
        else:
            shared.console.print("[red]Ошибка сохранения списка.[/red]")
            return None

def import_users() -> Optional[str]:
    """Import users from external file with validation."""
    with OperationTimer(logger, "Import users"):
        file_path = input("Введите путь к файлу списка пользователей: ").strip()
        if not file_path.strip():
            shared.console.print("[red]Путь не указан.[/red]")
            return None

        list_name = input("Введите имя нового списка: ").strip()
        if not list_name:
            logger.debug("Import cancelled - no list name")
            return None

        # Check if list already exists
        if _load_user_list(list_name) is not None:
            response = input(f"Список '{list_name}' уже существует. Перезаписать? (y/n): ").strip().lower()
            if response != 'y':
                logger.debug(f"Import cancelled - list {list_name} already exists")
                return None

        try:
            source_path = Path(file_path)
            if not source_path.exists():
                shared.console.print(f"[red]Файл '{file_path}' не найден.[/red]")
                return None

            with open(source_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            users = []
            for line_num, line in enumerate(lines, 1):
                user_raw = line.strip()
                if user_raw:
                    normalized_user = _normalize_user(user_raw)
                    users.append(normalized_user)
                    logger.debug(f"Imported user {line_num}: {normalized_user}")

            if not users:
                shared.console.print("[yellow]Файл не содержит допустимых пользователей.[/yellow]")
                return None

            if _save_user_list(list_name, users):
                shared.console.print(f"[green]Импорт завершен: '{list_name}' ({len(users)} пользователей из {source_path}).[/green]")
                log_operation(logger, "Imported user list", success=True, list_name=list_name, source_file=str(source_path), user_count=len(users))
                return list_name
            else:
                shared.console.print("[red]Ошибка сохранения импортированного списка.[/red]")
                return None

        except Exception as e:
            shared.console.print(f"[red]Ошибка импорта: {e}[/red]")
            log_error(logger, e, f"Import from {file_path}")
            return None

def display_user_lists() -> None:
    """Display all user lists in formatted tables."""
    with OperationTimer(logger, "Display user lists"):
        user_lists = _get_user_lists()

        if not user_lists:
            shared.console.print("[yellow]Нет списков пользователей.[/yellow]")
            input("Нажмите Enter для продолжения...")
            return

        logger.info(f"Displaying {len(user_lists)} user lists")

        for list_name, file_path in user_lists:
            shared.console.print(f"[bold blue]Список: {list_name}[/bold blue]")

            try:
                users = _load_user_list(list_name)
                if users:
                    table = Table(title="Пользователи", box=None)
                    table.add_column("№", style="magenta", justify="center")
                    table.add_column("Пользователь", style="cyan")
                    for idx, user in enumerate(users, 1):
                        table.add_row(str(idx), user)
                    shared.console.print(table)
                else:
                    shared.console.print("[dim]  Список пуст.[/dim]")
            except Exception as e:
                shared.console.print(f"[red]  Ошибка чтения: {e}[/red]")
                log_error(logger, e, f"Display user list {list_name}")

        input("Нажмите Enter для продолжения...")

def delete_user_list() -> Optional[str]:
    """Delete a user list with confirmation."""
    with OperationTimer(logger, "Delete user list"):
        user_lists = _get_user_lists()

        if not user_lists:
            shared.console.print("[yellow]Нет списков для удаления.[/yellow]")
            return None

        # Display available lists
        table = Table(title="Удаление списка пользователей", box=None)
        table.add_column("№", style="magenta", justify="center")
        table.add_column("Имя списка", style="cyan")
        table.add_column("Количество пользователей", style="green", justify="center")

        list_data = []
        for name, file_path in user_lists:
            try:
                users = _load_user_list(name) or []
                list_data.append((name, file_path, len(users)))
                table.add_row(str(len(list_data)), name, str(len(users)))
            except Exception as e:
                list_data.append((name, file_path, 0))
                table.add_row(str(len(list_data)), name, "Ошибка")
                log_error(logger, e, f"Check user list {name}")

        shared.console.print(table)

        try:
            choice = int(input("Выберите номер для удаления (0 для отмены): ")) - 1
            if choice == -1:  # 0 input becomes -1 after -1
                logger.debug("Delete cancelled by user")
                return None
            elif 0 <= choice < len(list_data):
                name, file_path, user_count = list_data[choice]

                # Confirmation
                confirm = input(f"Удалить список '{name}' с {user_count} пользователями? (y/n): ").strip().lower()
                if confirm != 'y':
                    logger.debug(f"Delete cancelled for list {name}")
                    return None

                try:
                    Path(file_path).unlink()
                    shared.console.print(f"[green]Список '{name}' удален.[/green]")
                    log_operation(logger, "Deleted user list", success=True, list_name=name, user_count=user_count)
                    return name
                except Exception as e:
                    shared.console.print(f"[red]Ошибка удаления файла: {e}[/red]")
                    log_error(logger, e, f"Delete user list file {file_path}")
                    return None
            else:
                shared.console.print("[red]Недопустимый номер.[/red]")
                return None
        except ValueError:
            shared.console.print("[red]Введите число.[/red]")
            return None

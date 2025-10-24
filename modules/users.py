#!/usr/bin/env python3
"""
Users module for Lazy Teacher.
Provides functions for managing user lists.
"""

import yaml
from pathlib import Path
from . import shared
from rich.table import Table

def input_users_manual():
    """Manually input list of users."""
    list_name = input("Введите имя списка пользователей: ").strip()
    if not list_name:
        return

    users = []
    print("Введите пользователей (оставьте пустым для завершения):")
    while True:
        user = input("Пользователь: ").strip()
        if not user:
            break
        if '@' not in user:
            user += '@pve'
        users.append(user)
        shared.logger.debug(f"Добавлен пользователь: {user}")

    if not users:
        print("Список пустой.")
        return

    file_path = shared.CONFIG_DIR / f"{list_name}_list.yaml"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump({'users': users}, f, default_flow_style=False)
        print(f"Список сохранен в {file_path}")
        shared.logger.info(f"Создан список пользователей: {list_name}")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        shared.logger.error(f"Ошибка сохранения списка {list_name}: {e}")

def import_users():
    """Import users from file."""
    # Placeholder: assume user inputs file path or use hardcoded
    # In real impl, prompt for file path
    file_path = input("Введите путь к файлу списка пользователей: ").strip()
    if not file_path:
        print("Путь не указан.")
        return

    list_name = input("Введите имя нового списка: ").strip()
    if not list_name:
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        users = []
        for line in lines:
            user = line.strip()
            if user:
                if '@' not in user:
                    user += '@pve'
                users.append(user)
        shared.logger.debug(f"Импортировано пользователей: {len(users)}")

        out_file = shared.CONFIG_DIR / f"{list_name}_list.yaml"
        with open(out_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump({'users': users}, f, default_flow_style=False)
        print(f"Импорт завершен в {out_file}")
        shared.logger.info(f"Импортирован список: {list_name}")
    except Exception as e:
        print(f"Ошибка импорта: {e}")
        shared.logger.error(f"Ошибка импорта из {file_path}: {e}")

def display_user_lists():
    """Display all user lists in tables."""
    import glob
    pattern = str(shared.CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    if not files:
        shared.console.print("[yellow]Нет списков пользователей.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return

    for file in files:
        list_name = Path(file).stem.replace('_list', '')
        shared.console.print(f"[bold blue]Список: {list_name}[/bold blue]")
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                users = data.get('users', [])
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

    input("Нажмите Enter для продолжения...")

def delete_user_list():
    """Delete a user list."""
    import glob
    pattern = str(shared.CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    if not files:
        shared.console.print("[yellow]Нет списков для удаления.[/yellow]")
        return

    lists = []
    for file in files:
        list_name = Path(file).stem.replace('_list', '')
        lists.append((list_name, file))

    table = Table(title="[bold red]Существующие списки пользователей[/bold red]", box=None)
    table.add_column("№", style="magenta", justify="center")
    table.add_column("Имя списка", style="cyan")
    for i, (name, _) in enumerate(lists, 1):
        table.add_row(str(i), name)
    shared.console.print(table)

    try:
        choice = int(input("Выберите номер для удаления: ")) - 1
        if 0 <= choice < len(lists):
            name, file = lists[choice]
            import os
            os.remove(file)
            shared.console.print(f"[green]Список '{name}' удален.[/green]")
            shared.logger.info(f"Удален список пользователей: {name}")
        else:
            shared.console.print("[red]Недопустимый номер.[/red]")
    except ValueError:
        shared.console.print("[red]Введите число.[/red]")

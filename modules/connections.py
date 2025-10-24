#!/usr/bin/env python3
"""
Connections module for Lazy Teacher.
Provides functions for managing Proxmox connections.
"""

import yaml
import proxmoxer
from pathlib import Path
from . import shared
from rich.table import Table

def create_connection():
    """Create a new Proxmox connection."""
    name = input("Введите имя подключения: ").strip()
    if not name:
        print("Имя не может быть пустым.")
        return

    host = input("Введите адрес хоста (IP или домен): ").strip()
    port = input("Введите порт (по умолчанию 8006): ").strip()
    port = port if port else '8006'

    # Validation TODO: check IP format
    if ':' in host:
        host, port = host.split(':', 1)
    host = host.strip()
    port = port.strip()

    auth_type = input("ВЫберете тип аутентификации (1 - token, 2 - пароль): ").strip()
    token = ''
    login = ''
    password = ''

    if auth_type == '1':
        token = input("Введите API token: ").strip()
    elif auth_type == '2':
        login = input("Введите логин: ").strip()
        if '@' not in login:
            login += '@pam'
        password = input("Введите пароль: ").strip()
    else:
        print("Недопустимый выбор.")
        return

    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'
    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
    except Exception as e:
        print(f"Ошибка чтения существующей конфигурации: {e}")
        shared.logger.error(f"Ошибка чтения {config_file}: {e}")
        return

    data[name] = {
        'host': host,
        'port': port,
        'token': token if auth_type == '1' else '',
        'login': login if auth_type == '2' else '',
        'password': password if auth_type == '2' else ''
    }

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
        print("Подключение сохранено.")
        shared.logger.info(f"Создано подключение: {name}")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        shared.logger.error(f"Ошибка сохранения подключения {name}: {e}")

def delete_connection():
    """Delete a connection."""
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        shared.console.print("[red]Нет сохраненных подключений.[/red]")
        return

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        shared.console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        shared.logger.error(f"Ошибка чтения {config_file}: {e}")
        return

    if not data:
        shared.console.print("[red]Нет подключений.[/red]")
        return

    table = Table(title="[bold red]Существующие подключения[/bold red]", box=None)
    table.add_column("№", style="magenta", justify="center")
    table.add_column("Имя", style="cyan")
    names = list(data.keys())
    for i, name in enumerate(names, 1):
        table.add_row(str(i), name)
    shared.console.print(table)

    try:
        choice = int(input("Выберите номер для удаления: ")) - 1
        if 0 <= choice < len(names):
            deleted = names[choice]
            del data[deleted]
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            shared.console.print(f"[green]Подключение '{deleted}' удалено.[/green]")
            shared.logger.info(f"Удалено подключение: {deleted}")
        else:
            shared.console.print("[red]Недопустимый номер.[/red]")
    except ValueError:
        shared.console.print("[red]Введите число.[/red]")

def display_connections():
    """Display all saved connections using Rich table."""
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        shared.console.print("[red]Нет сохраненных подключений.[/red]")
        return

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        shared.console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        return

    if not data:
        shared.console.print("[red]Нет подключений.[/red]")
        return

    table = Table(title="Сохраненные подключения", box=None)
    table.add_column("Имя", style="cyan", no_wrap=True)
    table.add_column("Хост", style="green")
    table.add_column("Порт", style="magenta")
    table.add_column("Аутентификация", style="yellow")

    for name, conn in data.items():
        auth = "Token" if conn.get('token') else "Пароль"
        table.add_row(name, conn.get('host', ''), str(conn.get('port', '')), auth)

    shared.console.print(table)
    input("Нажмите Enter для продолжения...")

def test_connection(config_data, conn_name):
    """Test connection to Proxmox server."""
    try:
        if config_data.get('token'):
            proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                token_name=config_data['token'],
                token_value=config_data['token'],
                verify_ssl=False,
                timeout=10
            )
        else:
            proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                user=config_data.get('login'),
                password=config_data.get('password'),
                verify_ssl=False,
                timeout=10
            )
        return True, "Подключение успешно"
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            return False, "Ошибка: Превышено время ожидания подключения"
        elif "unauthorized" in error_msg or "authentication" in error_msg:
            return False, "Ошибка: Неправильные учетные данные"
        elif "connection" in error_msg or "network" in error_msg:
            return False, "Ошибка: Не удается подключиться к серверу"
        elif "certificate" in error_msg:
            return False, "Ошибка: Проблема с SSL сертификатом"
        else:
            return False, f"Ошибка подключения: {e}"

def select_default_connection():
    """Select default connection at startup."""
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        shared.console.print("[red]Ошибка: Файл конфигурации не найден.[/red]")
        shared.console.print("[yellow]Создание нового подключения...[/yellow]")
        create_connection()
        return select_default_connection()  # Recurse to select if created

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        shared.console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        shared.logger.error(f"Ошибка чтения конфигурации: {e}")
        return None

    if not data:
        shared.console.print("[red]Ошибка: Нет настроенных подключений.[/red]")
        shared.console.print("[yellow]Создание нового подключения...[/yellow]")
        create_connection()
        return select_default_connection()

    names = list(data.keys())
    shared.console.print("[bold blue]Доступные подключения:[/bold blue]")

    # Test all connections and show their status
    connection_status = {}
    for name in names:
        conn = data[name]
        success, message = test_connection(conn, name)
        connection_status[name] = (success, message)
        status_icon = "✓" if success else "✗"
        shared.console.print(f"  {status_icon} {name} ({conn.get('host')}:{conn.get('port')}) - {message}")

    # Filter available connections
    available_connections = [name for name in names if connection_status[name][0]]

    if not available_connections:
        shared.console.print("[red]Ошибка: Нет доступных подключений.[/red]")
        shared.console.print("[yellow]Проверьте настройки подключений или создайте новое.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return None

    shared.console.print()
    shared.console.print("[green]Доступные для использования:[/green]")
    for i, name in enumerate(available_connections, 1):
        shared.console.print(f"{i}. {name}")

    try:
        choice = int(input("Выберите номер подключения: ")) - 1
        if 0 <= choice < len(available_connections):
            selected = available_connections[choice]
            shared.console.print(f"[green]Выбрано активное подключение: {selected}[/green]")
            return selected
        else:
            shared.console.print("[red]Недопустимый номер.[/red]")
            return select_default_connection()
    except ValueError:
        shared.console.print("[red]Введите число.[/red]")
        return select_default_connection()

def get_proxmox_connection(conn_name=None):
    """
    Get Proxmox API connection object.

    Args:
        conn_name (str, optional): Name of connection from config.
                                  If None, uses shared.DEFAULT_CONN

    Returns:
        proxmoxer.ProxmoxAPI: Connected Proxmox API object

    Raises:
        Exception: If connection fails or config not found
    """
    if conn_name is None:
        conn_name = shared.DEFAULT_CONN

    if not conn_name:
        raise ValueError("Имя подключения не указано")

    # Read config file
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        raise FileNotFoundError("Файл конфигурации не найден")

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data_all = yaml.safe_load(f) or {}
        config_data = config_data_all.get(conn_name)
    except Exception as e:
        raise Exception(f"Ошибка чтения конфигурации: {e}")

    if not config_data:
        raise ValueError(f"Подключение '{conn_name}' не найдено в конфигурации")

    # Create Proxmox API connection
    try:
        if config_data.get('token'):
            prox = proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                token_name=config_data['token'],
                token_value=config_data['token'],
                verify_ssl=False,
                timeout=60
            )
        else:
            prox = proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                user=config_data.get('login'),
                password=config_data.get('password'),
                verify_ssl=False,
                timeout=60
            )
        return prox
    except Exception as e:
        raise Exception(f"Ошибка подключения к Proxmox API: {e}")

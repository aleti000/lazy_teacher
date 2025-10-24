#!/usr/bin/env python3
"""
Connections module for Lazy Teacher.
Provides optimized functions for managing Proxmox connections.
"""

import yaml
import proxmoxer
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging
from . import shared
from .logger import get_logger, log_operation, log_error, OperationTimer
from rich.table import Table

logger = get_logger(__name__)

def _load_config() -> Dict[str, Any]:
    """Load connection configuration from file with error handling."""
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        return {}

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        logger.debug(f"Loaded {len(data)} connections from config file {config_file}")
        return data
    except Exception as e:
        log_error(logger, e, "Load config", config_file=str(config_file))
        shared.console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        return {}

def _save_config(config: Dict[str, Any]) -> bool:
    """Save connection configuration to file."""
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        logger.debug(f"Saved {len(config)} connections to config", config_file=str(config_file))
        return True
    except Exception as e:
        log_error(logger, e, "Save config", config_file=str(config_file))
        shared.console.print(f"[red]Ошибка сохранения конфигурации: {e}[/red]")
        return False

def _create_proxmox_connection(config_data: Dict[str, Any], timeout: int = 60) -> proxmoxer.ProxmoxAPI:
    """
    Create ProxmoxAPI connection object from configuration data.

    Args:
        config_data: Connection configuration dictionary
        timeout: Connection timeout in seconds

    Returns:
        proxmoxer.ProxmoxAPI: Connected Proxmox API instance

    Raises:
        Exception: If connection creation fails
    """
    try:
        if config_data.get('token'):
            prox = proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=config_data['port'],
                token_name=config_data['token'],
                token_value=config_data['token'],
                verify_ssl=False,
                timeout=timeout
            )
        else:
            prox = proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=config_data['port'],
                user=config_data.get('login'),
                password=config_data.get('password'),
                verify_ssl=False,
                timeout=timeout
            )
        return prox
    except Exception as e:
        error_msg = f"Failed to create Proxmox connection to {config_data.get('host', 'unknown')}:{config_data.get('port', 'unknown')}"
        raise Exception(error_msg) from e

def test_connection(config_data: Dict[str, Any], conn_name: str) -> Tuple[bool, str]:
    """
    Test connection to Proxmox server with detailed error reporting.

    Args:
        config_data: Connection configuration data
        conn_name: Name of the connection for logging

    Returns:
        Tuple of (success: bool, message: str)
    """
    with OperationTimer(logger, f"Test connection {conn_name}"):
        try:
            # Use short timeout for testing
            prox = _create_proxmox_connection(config_data, timeout=10)
            # Try to get cluster resources to verify connection
            prox.cluster.resources.get()
            logger.info(f"Connection test successful - conn: {conn_name}, host: {config_data.get('host')}")
            return True, "Подключение успешно"

        except Exception as e:
            error_msg = str(e).lower()

            if "timeout" in error_msg or "time" in error_msg:
                message = "Ошибка: Превышено время ожидания подключения"
            elif "unauthorized" in error_msg or "authentication" in error_msg or "auth" in error_msg:
                message = "Ошибка: Неправильные учетные данные"
            elif "connection" in error_msg or "network" in error_msg or "name resolution" in error_msg:
                message = "Ошибка: Не удается подключиться к серверу"
            elif "certificate" in error_msg or "ssl" in error_msg:
                message = "Ошибка: Проблема с SSL сертификатом"
            else:
                message = f"Ошибка подключения: {str(e)}"

            logger.warning(f"Connection test failed: {message} - conn: {conn_name}, error: {str(e)}")
            return False, message

def create_connection() -> Optional[str]:
    """Create a new Proxmox connection interactively."""
    with OperationTimer(logger, "Create connection"):
        try:
            name = input("Введите имя подключения: ").strip()
            if not name:
                shared.console.print("[red]Имя не может быть пустым.[/red]")
                return None

            host = input("Введите адрес хоста (IP или домен): ").strip()
            port = input("Введите порт (по умолчанию 8006): ").strip()
            port = int(port) if port.isdigit() else 8006

            # Parse host:port format
            if ':' in host:
                host, parsed_port = host.split(':', 1)
                if parsed_port.isdigit():
                    port = int(parsed_port)
            host = host.strip()

            auth_type = input("Выберите тип аутентификации (1 - token, 2 - пароль): ").strip()
            token = login = password = ''

            if auth_type == '1':
                token = input("Введите API token: ").strip()
            elif auth_type == '2':
                login = input("Введите логин: ").strip()
                if '@' not in login:
                    login += '@pam'
                password = input("Введите пароль: ").strip()
            else:
                shared.console.print("[red]Недопустимый выбор.[/red]")
                return None

            # Load existing config
            config = _load_config()

            # Add new connection
            config[name] = {
                'host': host,
                'port': port,
                'token': token if auth_type == '1' else '',
                'login': login if auth_type == '2' else '',
                'password': password if auth_type == '2' else ''
            }

            # Save config
            if _save_config(config):
                shared.console.print("[green]Подключение сохранено.[/green]")
                logger.info(f"Connection created - conn: {name}, host: {host}:{port}")
                return name
            else:
                return None

        except Exception as e:
            shared.console.print(f"[red]Ошибка создания подключения: {e}[/red]")
            log_error(logger, e, "Create connection")
            return None

def delete_connection():
    """Delete a connection."""
    with OperationTimer(logger, "Delete connection"):
        # Load current config
        config = _load_config()
        if not config:
            shared.console.print("[red]Нет сохраненных подключений.[/red]")
            return

        # Display available connections
        table = Table(title="Удаление подключения", box=None)
        table.add_column("№", style="magenta", justify="center")
        table.add_column("Имя", style="cyan")
        table.add_column("Хост", style="green")
        table.add_column("Порт", style="magenta")

        names = list(config.keys())
        for i, name in enumerate(names, 1):
            conn = config[name]
            table.add_row(str(i), name, conn.get('host', ''), str(conn.get('port', '')))

        shared.console.print(table)

        try:
            choice = int(input("Выберите номер для удаления: ")) - 1
            if 0 <= choice < len(names):
                deleted = names[choice]
                del config[deleted]

                if _save_config(config):
                    shared.console.print(f"[green]Подключение '{deleted}' удалено.[/green]")
                    logger.info(f"Connection deleted - conn: {deleted}")
                else:
                    shared.console.print("[red]Ошибка сохранения конфигурации после удаления.[/red]")
            else:
                shared.console.print("[red]Недопустимый номер.[/red]")
        except ValueError:
            shared.console.print("[red]Введите число.[/red]")

def display_connections():
    """Display all saved connections using Rich table."""
    with OperationTimer(logger, "Display connections"):
        connections = _load_config()
        if not connections:
            shared.console.print("[red]Нет сохраненных подключений.[/red]")
            return

        table = Table(title="Сохраненные подключения", box=None)
        table.add_column("Имя", style="cyan", no_wrap=True)
        table.add_column("Хост", style="green")
        table.add_column("Порт", style="magenta")
        table.add_column("Аутентификация", style="yellow")

        for name, conn in connections.items():
            auth = "Token" if conn.get('token') else "Пароль"
            table.add_row(name, conn.get('host', ''), str(conn.get('port', '')), auth)

        shared.console.print(table)
        input("Нажмите Enter для продолжения...")
        logger.debug(f"Displayed {len(connections)} connections")

def select_default_connection() -> Optional[str]:
    """Select default connection at startup with optimized logic."""
    operation = "Select default connection"

    with OperationTimer(logger, operation):
        # Load config
        data = _load_config()
        if not data:
            shared.console.print("[red]Ошибка: Нет настроенных подключений.[/red]")
            shared.console.print("[yellow]Создание нового подключения...[/yellow]")
            create_connection()
            # Retry after creation
            data = _load_config()

        if not data:
            logger.error(f"No connections available - operation: {operation}")
            return None

        names = list(data.keys())
        shared.console.print("[bold blue]Доступные подключения:[/bold blue]")

        # Test all connections and collect status
        connection_tests = {}
        available_connections = []

        for name in names:
            conn = data[name]
            success, message = test_connection(conn, name)
            connection_tests[name] = (success, message)
            status_icon = "✓" if success else "✗"
            shared.console.print(f"  {status_icon} {name} ({conn.get('host')}:{conn.get('port')}) - {message}")

            if success:
                available_connections.append(name)

        if not available_connections:
            shared.console.print("[red]Ошибка: Нет доступных подключений.[/red]")
            shared.console.print("[yellow]Проверьте настройки подключений или создайте новое.[/yellow]")
            input("Нажмите Enter для продолжения...")
            logger.error(f"No connections working - operation: {operation}")
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
                logger.info(f"Default connection selected - conn: {selected}")
                return selected
            else:
                shared.console.print("[red]Недопустимый номер.[/red]")
        except ValueError:
            shared.console.print("[red]Введите число.[/red]")

        # Retry on invalid input
        return select_default_connection()

def get_proxmox_connection(conn_name: Optional[str] = None) -> proxmoxer.ProxmoxAPI:
    """
    Get Proxmox API connection object using optimized config loading.

    Args:
        conn_name: Name of connection from config.
                  If None, uses shared.DEFAULT_CONN

    Returns:
        proxmoxer.ProxmoxAPI: Connected Proxmox API object

    Raises:
        ValueError: If connection name not specified or config issues
        FileNotFoundError: If config file not found
        Exception: If connection creation fails
    """
    if conn_name is None:
        conn_name = shared.DEFAULT_CONN

    if not conn_name:
        raise ValueError("Имя подключения не указано")

    # Load config and get connection data
    config_data = _load_config()
    if not config_data:
        raise FileNotFoundError("Файл конфигурации не найден или пуст")

    connection_config = config_data.get(conn_name)
    if not connection_config:
        available = list(config_data.keys())
        raise ValueError(f"Подключение '{conn_name}' не найдено. Доступные: {available}")

    # Create connection using unified function
    with OperationTimer(logger, f"Get Proxmox connection {conn_name}"):
        try:
            prox = _create_proxmox_connection(connection_config, timeout=60)
            logger.info(f"Proxmox connection established - conn: {conn_name}, host: {connection_config.get('host')}")
            return prox
        except Exception as e:
            log_error(logger, e, f"Get Proxmox connection {conn_name}", host=connection_config.get('host'), port=connection_config.get('port'))
            raise Exception(f"Ошибка подключения к Proxmox API: {e}") from e

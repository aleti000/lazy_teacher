#!/usr/bin/env python3
"""
Select Connection module for Lazy Teacher.
Provides optimized functions for connection selection.
"""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from . import shared
from .logger import get_logger, log_operation, OperationTimer

logger = get_logger(__name__)

def select_connection() -> Optional[str]:
    """
    Interactively select a Proxmox connection from available configurations.

    Displays all available connections in a numbered list and prompts user to choose one.
    Provides validation and error handling.

    Returns:
        Selected connection name if valid choice made, None otherwise
    """
    with OperationTimer(logger, "Select connection"):
        config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'

        # Check if config file exists
        if not config_file.exists():
            shared.console.print("[yellow]Файл конфигурации подключений не найден.[/yellow]")
            logger.warning("Proxmox config file not found", config_file=str(config_file))
            return None

        # Load configuration
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            shared.console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
            log_operation(logger, "Load connection config failed", success=False, error=str(e))
            return None

        # Check if any connections exist
        if not data:
            shared.console.print("[yellow]Нет настроенных подключений.[/yellow]")
            logger.info("No connections configured")
            return None

        # Display available connections
        connections = list(data.keys())
        logger.info(f"Displaying {len(connections)} available connections")

        shared.console.print("[bold blue]Доступные подключения:[/bold blue]")
        for i, name in enumerate(connections, 1):
            # Show connection details if available
            conn_info = data[name]
            host = conn_info.get('host', 'unknown')
            port = conn_info.get('port', 'unknown')
            shared.console.print(f"{i}. {name} (host: {host}:{port})")

        # Get user selection
        try:
            choice_input = input("Выберите номер подключения: ").strip()
            if not choice_input:
                logger.debug("Connection selection cancelled - empty input")
                return None

            choice = int(choice_input) - 1
            if 0 <= choice < len(connections):
                selected = connections[choice]
                shared.console.print(f"[green]Выбрано подключение: {selected}[/green]")
                log_operation(logger, "Connection selected", success=True, connection=selected)
                return selected
            else:
                shared.console.print("[red]Недопустимый номер подключения.[/red]")
                logger.warning(f"Invalid connection choice: {choice + 1} (should be 1-{len(connections)})")
                return None

        except ValueError:
            shared.console.print("[red]Введите корректный номер.[/red]")
            logger.warning("Invalid connection selection - non-numeric input")
            return None

        except EOFError:
            logger.debug("Connection selection interrupted")
            return None

def get_available_connections() -> Dict[str, Dict[str, Any]]:
    """
    Get all available Proxmox connections from configuration.

    Returns:
        Dictionary mapping connection names to their configurations
    """
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'

    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            logger.debug(f"Loaded {len(data)} connections from config")
            return data
        else:
            logger.debug("Connection config file does not exist")
            return {}

    except Exception as e:
        logger.error(f"Failed to load connections config: {e}")
        return {}

def validate_connection_name(name: str) -> bool:
    """
    Validate if a connection name exists in configuration.

    Args:
        name: Connection name to validate

    Returns:
        True if connection exists, False otherwise
    """
    connections = get_available_connections()
    exists = name in connections

    if not exists:
        logger.warning(f"Connection '{name}' not found in configuration")
        available = list(connections.keys())
        logger.info(f"Available connections: {available}")

    return exists

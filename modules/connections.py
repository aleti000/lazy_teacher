#!/usr/bin/env python3
"""
Connections module for Lazy Teacher.
Provides functions for managing Proxmox connections.
"""

import yaml
import proxmoxer
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging
from . import shared
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)


def _load_config() -> Dict[str, Any]:
    """Load connection configuration from file."""
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        return {}

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        logger.debug(f"Loaded {len(data)} connections from config file")
        return data
    except Exception as e:
        log_error(logger, e, "Load config")
        shared.console.print(f"[!] Ошибка чтения конфигурации: {e}")
        return {}


def _save_config(config: Dict[str, Any]) -> bool:
    """Save connection configuration to file."""
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        logger.debug(f"Saved {len(config)} connections to config file")
        return True
    except Exception as e:
        log_error(logger, e, "Save config")
        shared.console.print(f"[!] Ошибка сохранения конфигурации: {e}")
        return False


def _create_proxmox_connection(config_data: Dict[str, Any], timeout: int = 60) -> proxmoxer.ProxmoxAPI:
    """Create ProxmoxAPI connection object from configuration data."""
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
    """Test connection to Proxmox server."""
    with OperationTimer(logger, f"Test connection {conn_name}"):
        try:
            prox = _create_proxmox_connection(config_data, timeout=10)
            prox.cluster.resources.get()
            logger.info(f"Connection test successful - conn: {conn_name}")
            return True, "Подключение успешно"

        except Exception as e:
            error_msg = str(e).lower()

            if "timeout" in error_msg or "time" in error_msg:
                message = "Ошибка: Превышено время ожидания подключения"
            elif "unauthorized" in error_msg or "authentication" in error_msg:
                message = "Ошибка: Неправильные учетные данные"
            elif "connection" in error_msg or "network" in error_msg:
                message = "Ошибка: Не удается подключиться к серверу"
            elif "certificate" in error_msg or "ssl" in error_msg:
                message = "Ошибка: Проблема с SSL сертификатом"
            else:
                message = f"Ошибка подключения: {str(e)}"

            logger.warning(f"Connection test failed: {message}")
            return False, message


def create_connection() -> Optional[str]:
    """Create a new Proxmox connection interactively."""
    with OperationTimer(logger, "Create connection"):
        try:
            name = input("Введите имя подключения: ").strip()
            if not name:
                print("[!] Имя не может быть пустым.")
                return None

            host = input("Введите адрес хоста (IP или домен): ").strip()
            port = input("Введите порт (по умолчанию 8006): ").strip()
            port = int(port) if port.isdigit() else 8006

            if ':' in host:
                host, parsed_port = host.split(':', 1)
                if parsed_port.isdigit():
                    port = int(parsed_port)
            host = host.strip()

            print("\nТип аутентификации:")
            print("  [1] API Token")
            print("  [2] Логин/пароль")
            auth_type = input("Выбор: ").strip()
            
            token = login = password = ''

            if auth_type == '1':
                token = input("Введите API token: ").strip()
            elif auth_type == '2':
                login = input("Введите логин: ").strip()
                if '@' not in login:
                    login += '@pam'
                password = input("Введите пароль: ").strip()
            else:
                print("[!] Недопустимый выбор.")
                return None

            config = _load_config()

            config[name] = {
                'host': host,
                'port': port,
                'token': token if auth_type == '1' else '',
                'login': login if auth_type == '2' else '',
                'password': password if auth_type == '2' else ''
            }

            if _save_config(config):
                print(f"[+] Подключение '{name}' сохранено.")
                logger.info(f"Connection created - conn: {name}, host: {host}:{port}")
                return name
            else:
                return None

        except Exception as e:
            print(f"[!] Ошибка создания подключения: {e}")
            log_error(logger, e, "Create connection")
            return None


def delete_connection():
    """Delete a connection."""
    with OperationTimer(logger, "Delete connection"):
        config = _load_config()
        if not config:
            print("[!] Нет сохраненных подключений.")
            return

        print("\nУдаление подключения:")
        print("-" * 40)
        
        names = list(config.keys())
        for i, name in enumerate(names, 1):
            conn = config[name]
            print(f"  [{i}] {name} ({conn.get('host')}:{conn.get('port')})")
        print(f"  [0] Отмена")
        print()

        try:
            choice = int(input("Выберите номер для удаления: ")) - 1
            if 0 <= choice < len(names):
                deleted = names[choice]
                del config[deleted]

                if _save_config(config):
                    print(f"[+] Подключение '{deleted}' удалено.")
                    logger.info(f"Connection deleted - conn: {deleted}")
                else:
                    print("[!] Ошибка сохранения конфигурации.")
            else:
                print("[!] Недопустимый номер.")
        except ValueError:
            print("[!] Введите число.")


def display_connections():
    """Display all saved connections."""
    with OperationTimer(logger, "Display connections"):
        connections = _load_config()
        if not connections:
            print("[!] Нет сохраненных подключений.")
            return

        print("\nСохраненные подключения:")
        print("-" * 60)
        print(f"{'Имя':<20} {'Хост':<20} {'Порт':<8} {'Аутентификация':<12}")
        print("-" * 60)
        
        for name, conn in connections.items():
            auth = "Token" if conn.get('token') else "Пароль"
            print(f"{name:<20} {conn.get('host', ''):<20} {str(conn.get('port', '')):<8} {auth:<12}")
        
        print("-" * 60)
        input("\nНажмите Enter для продолжения...")
        logger.debug(f"Displayed {len(connections)} connections")


def select_default_connection() -> Optional[str]:
    """Select default connection at startup."""
    operation = "Select default connection"

    with OperationTimer(logger, operation):
        data = _load_config()
        if not data:
            shared.console.print("[!] Нет настроенных подключений.")
            shared.console.print("[*] Создание нового подключения...")
            create_connection()
            data = _load_config()

        if not data:
            logger.error(f"No connections available")
            return None

        names = list(data.keys())
        print("\nДоступные подключения:")
        print("-" * 40)

        # Test all connections
        available_connections = []
        for name in names:
            conn = data[name]
            success, message = test_connection(conn, name)
            status = "[+]" if success else "[!]"
            print(f"  {status} {name} ({conn.get('host')}:{conn.get('port')}) - {message}")
            if success:
                available_connections.append(name)

        if not available_connections:
            print("\n[!] Нет доступных подключений.")
            print("[*] Проверьте настройки или создайте новое подключение.")
            input("Нажмите Enter для продолжения...")
            return None

        print(f"\n[+] Доступно для использования: {len(available_connections)}")
        for i, name in enumerate(available_connections, 1):
            print(f"  [{i}] {name}")

        try:
            choice = int(input("\nВыберите номер подключения: ")) - 1
            if 0 <= choice < len(available_connections):
                selected = available_connections[choice]
                print(f"[+] Выбрано активное подключение: {selected}")
                logger.info(f"Default connection selected - conn: {selected}")
                return selected
            else:
                print("[!] Недопустимый номер.")
        except ValueError:
            print("[!] Введите число.")

        return select_default_connection()


def get_proxmox_connection(conn_name: Optional[str] = None) -> proxmoxer.ProxmoxAPI:
    """Get Proxmox API connection object."""
    if conn_name is None:
        conn_name = shared.DEFAULT_CONN

    if not conn_name:
        raise ValueError("Имя подключения не указано")

    config_data = _load_config()
    if not config_data:
        raise FileNotFoundError("Файл конфигурации не найден или пуст")

    connection_config = config_data.get(conn_name)
    if not connection_config:
        available = list(config_data.keys())
        raise ValueError(f"Подключение '{conn_name}' не найдено. Доступные: {available}")

    with OperationTimer(logger, f"Get Proxmox connection {conn_name}"):
        try:
            prox = _create_proxmox_connection(connection_config, timeout=60)
            logger.info(f"Proxmox connection established - conn: {conn_name}")
            return prox
        except Exception as e:
            log_error(logger, e, f"Get Proxmox connection {conn_name}")
            raise Exception(f"Ошибка подключения к Proxmox API: {e}") from e
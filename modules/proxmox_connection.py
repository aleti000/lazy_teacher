#!/usr/bin/env python3
"""
Proxmox connection module for Lazy Teacher.
Provides centralized connection management to Proxmox servers.
"""

import yaml
import proxmoxer
from pathlib import Path
from . import shared

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

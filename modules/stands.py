#!/usr/bin/env python3
"""
Stands module for Lazy Teacher.
Provides functions for managing stands.
"""

import yaml
from pathlib import Path
from . import shared
from rich.table import Table

def add_vm_to_stand(stand, conn_name):
    """Add VM to stand."""
    config_file = shared.CONFIG_DIR / 'proxmox_config.yaml'

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
        config = config_data.get(conn_name)
        if not config:
            shared.console.print(f"[red]Ошибка: Подключение '{conn_name}' не найдено в конфигурации.[/red]")
            return
    except Exception as e:
        shared.console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        shared.logger.error(f"Ошибка чтения конфигурации: {e}")
        return

    # Test connection first
    success, message = shared.test_connection(config, conn_name)
    if not success:
        shared.console.print(f"[red]Ошибка подключения к '{conn_name}': {message}[/red]")
        shared.console.print("[yellow]Проверьте настройки подключения.[/yellow]")
        return

    # Connect to Proxmox
    try:
        if config.get('token'):
            proxi = proxmoxer.ProxmoxAPI(
                config['host'],
                port=int(config['port']),
                token_name=config['token'],
                token_value=config['token'],
                verify_ssl=False,
                timeout=30
            )
        else:
            proxi = proxmoxer.ProxmoxAPI(
                config['host'],
                port=int(config['port']),
                user=config.get('login'),
                password=config.get('password'),
                verify_ssl=False,
                timeout=30
            )
    except Exception as e:
        shared.console.print(f"[red]Ошибка подключения к Proxmox API: {e}[/red]")
        shared.logger.error(f"Не удалось подключиться к Proxmox API: {e}")
        return

    # Get nodes with better error handling
    try:
        nodes = proxi.nodes.get()
        node_names = [node['node'] for node in nodes]
        if not node_names:
            shared.console.print("[red]Ошибка: Не найдено доступных нод на сервере.[/red]")
            return
        shared.logger.debug(f"Найдены ноды: {node_names}")
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            shared.console.print("[red]Ошибка: Превышено время ожидания при получении списка нод.[/red]")
        elif "permission" in error_msg or "unauthorized" in error_msg:
            shared.console.print("[red]Ошибка: Недостаточно прав для получения списка нод.[/red]")
        else:
            shared.console.print(f"[red]Ошибка получения списка нод: {e}[/red]")
        shared.logger.error(f"Ошибка получения нод: {e}")
        return

    print("Доступные шаблоны:")
    templates = []
    idx = 1
    for node in node_names:
        try:
            vms = proxi.nodes(node).qemu.get()
            for vm in vms:
                if vm.get('template') == 1:
                    templates.append((node, vm['name'], vm['vmid']))
                    print(f"{idx}. {node} {vm['name']} {vm['vmid']}")
                    idx += 1
        except Exception as e:
            shared.logger.warning(f"Ошибка получения VM на {node}: {e}")

    if not templates:
        print("Нет шаблонов.")
        return

    try:
        tmpl_choice = int(input("Выберите шаблон: ")) - 1
        if not (0 <= tmpl_choice < len(templates)):
            print("Недопустимый выбор.")
            return
    except ValueError:
        print("Введите число.")
        return

    template_node, vm_name, vmid = templates[tmpl_choice]
    shared.logger.debug(f"Выбран шаблон: {template_node}:{vm_name}:{vmid}")

    device_type_options = ["linux", "ecorouter"]
    print("Тип машины:")
    for i, opt in enumerate(device_type_options, 1):
        print(f"{i}. {opt}")

    try:
        dt_choice = int(input("Выберите: ")) - 1
        device_type = device_type_options[dt_choice]
    except (ValueError, IndexError):
        print("Недопустимый.")
        return

    name = input("Имя VM: ").strip()

    networks = []
    # Для ecorouter автоматически добавляем management порт
    if device_type == "ecorouter":
        networks.append({'bridge': '**vmbr0', 'comment': '# mngmnt port'})
        print("Автоматически добавлен management порт: **vmbr0**")

    while True:
        net = input("Имя сети (empty to end): ").strip()
        if not net:
            break
        networks.append({'bridge': net})

    vm = {
        'device_type': device_type,
        'name': name,
        'template_node': template_node,
        'template_vmid': vmid,
        'networks': networks
    }
    stand['machines'].append(vm)
    shared.logger.info(f"Добавлена VM: {name}")

def remove_vm_from_stand(stand):
    """Remove VM from stand."""
    display_stand_vms(stand)
    if not stand['machines']:
        return

    vm_names = [vm['name'] for vm in stand['machines']]
    print("Выберите VM для удаления:")
    for i, name in enumerate(vm_names, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Номер: ")) - 1
        if 0 <= choice < len(vm_names):
            removed = stand['machines'].pop(choice)
            print(f"Удалена VM: {removed['name']}")
            shared.logger.info(f"Удалена VM: {removed['name']}")
    except ValueError:
        print("Введите число.")

def display_stand_vms(stand):
    """Display current stand VMs."""
    if not stand['machines']:
        print("Пусто.")
        return
    for vm in stand['machines']:
        networks_info = []
        for n in vm['networks']:
            bridge = n['bridge']
            if 'comment' in n:
                networks_info.append(f"{bridge} {n['comment']}")
            else:
                networks_info.append(bridge)
        print(f"Тип: {vm['device_type']}, Имя: {vm['name']}, Шаблон: {vm['template_node']}:{vm['template_vmid']}, Сети: {networks_info}")

def save_stand(name, stand):
    """Save stand to yaml."""
    file_path = shared.CONFIG_DIR / f"{name}_stand.yaml"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(stand, f, default_flow_style=False)
        print(f"Стенд сохранен в {file_path}")
        shared.logger.info(f"Сохранен стенд: {name}")
    except Exception as e:
        print(f"Ошибка: {e}")
        shared.logger.error(f"Ошибка сохранения стенда {name}: {e}")

def delete_stand_file():
    """Delete a stand file."""
    import glob
    pattern = str(shared.CONFIG_DIR / "*_stand.yaml")
    files = glob.glob(pattern)
    if not files:
        print("Нет стендов для удаления.")
        input("Нажмите Enter для продолжения...")
        return

    stands = []
    for file in files:
        stand_name = Path(file).stem.replace('_stand', '')
        stands.append((stand_name, file))

    print("Существующие стенды:")
    for i, (name, _) in enumerate(stands, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Выберите номер для удаления: ")) - 1
        if 0 <= choice < len(stands):
            name, file = stands[choice]
            import os
            os.remove(file)
            print("Стенд удален.")
            shared.logger.info(f"Удален стенд: {name}")
        else:
            print("Недопустимый номер.")
    except ValueError:
        print("Введите число.")

def display_list_of_stands():
    """Display list of saved stands."""
    import glob
    pattern = str(shared.CONFIG_DIR / "*_stand.yaml")
    files = glob.glob(pattern)
    if not files:
        print("Нет сохраненных стендов.")
        input("Нажмите Enter для продолжения...")
        return

    print("Список стендов:")
    for name in files:
        stand_name = Path(name).stem.replace('_stand', '')
        print(f"- {stand_name}")

    input("Нажмите Enter для продолжения...")

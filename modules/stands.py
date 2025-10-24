#!/usr/bin/env python3
"""
Stands module for Lazy Teacher.
Provides optimized functions for managing stands.
"""

import glob
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from . import shared
from .connections import get_proxmox_connection
from .logger import get_logger, log_operation, log_error, OperationTimer
from rich.table import Table

logger = get_logger(__name__)

def _get_stand_files() -> List[Tuple[str, str]]:
    """Get list of stand files with their names."""
    pattern = str(shared.CONFIG_DIR / "*_stand.yaml")
    files = glob.glob(pattern)
    return [(Path(file).stem.replace('_stand', ''), file) for file in files]

def _load_stand(name: str) -> Optional[Dict[str, Any]]:
    """Load stand configuration from YAML file."""
    file_path = shared.CONFIG_DIR / f"{name}_stand.yaml"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        logger.debug(f"Loaded stand {name} with {len(data.get('machines', []))} VMs")
        return data
    except FileNotFoundError:
        logger.debug(f"Stand file {name} not found")
        return None
    except Exception as e:
        log_error(logger, e, f"Load stand {name}")
        return None

def _save_stand(name: str, stand: Dict[str, Any]) -> bool:
    """Save stand configuration to YAML file."""
    file_path = shared.CONFIG_DIR / f"{name}_stand.yaml"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(stand, f, default_flow_style=False)
        logger.debug(f"Saved stand {name} with {len(stand.get('machines', []))} VMs")
        return True
    except Exception as e:
        log_error(logger, e, f"Save stand {name}")
        return False

def _get_available_templates(proxi) -> List[Tuple[str, str, int]]:
    """
    Get available VM templates from all nodes.

    Args:
        proxi: Proxmox API connection object

    Returns:
        List of (node_name, vm_name, vmid) tuples for templates
    """
    templates = []
    try:
        nodes = proxi.nodes.get()
        node_names = [node['node'] for node in nodes]
        logger.debug(f"Found nodes: {node_names}")

        for node_name in node_names:
            try:
                vms = proxi.nodes(node_name).qemu.get()
                for vm in vms:
                    if vm.get('template') == 1:
                        templates.append((node_name, vm['name'], vm['vmid']))
            except Exception as e:
                logger.warning(f"Failed to get VMs from node {node_name}: {e}")

    except Exception as e:
        log_error(logger, e, "Get available templates")
        return []

    return templates

def _select_from_options(options: List[str], prompt: str, title: str) -> Optional[str]:
    """Helper to select from list of options."""
    if not options:
        shared.console.print(f"[red]Нет доступных {title}.[/red]")
        return None

    shared.console.print(f"{prompt}:")
    for i, option in enumerate(options, 1):
        shared.console.print(f"{i}. {option}")

    try:
        choice = int(input("Выберите: ")) - 1
        if 0 <= choice < len(options):
            return options[choice]
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")
            return None
    except ValueError:
        shared.console.print("[red]Введите число.[/red]")
        return None

def add_vm_to_stand(stand: Dict[str, Any], conn_name: str) -> None:
    """Add VM to stand with optimized connection and template selection."""
    with OperationTimer(logger, f"Add VM to stand {conn_name}"):
        logger.info("Starting VM addition to stand")

        try:
            # Get Proxmox connection using optimized connections module
            proxi = get_proxmox_connection(conn_name)
        except Exception as e:
            shared.console.print(f"[red]Ошибка подключения к Proxmox: {e}[/red]")
            return

        # Get available templates
        templates = _get_available_templates(proxi)
        if not templates:
            shared.console.print("[red]Нет доступных шаблонов.[/red]")
            return

        # Display templates for selection
        shared.console.print("Доступные шаблоны:")
        for i, (node_name, vm_name, vmid) in enumerate(templates, 1):
            shared.console.print(f"{i}. {node_name} - {vm_name} (VMID: {vmid})")

        try:
            tmpl_choice = int(input("Выберите шаблон: ")) - 1
            if not (0 <= tmpl_choice < len(templates)):
                shared.console.print("[red]Недопустимый выбор.[/red]")
                return
        except ValueError:
            shared.console.print("[red]Введите число.[/red]")
            return

        template_node, vm_name, vmid = templates[tmpl_choice]
        logger.info(f"Selected template: {template_node}:{vm_name}:{vmid}")

        # Select device type
        device_type_options = ["linux", "ecorouter"]
        device_type = _select_from_options(device_type_options, "Тип машины", "типы машин")
        if not device_type:
            return

        # Get VM name
        vm_name = input("Имя VM: ").strip()
        if not vm_name:
            shared.console.print("[yellow]Имя VM не может быть пустым.[/yellow]")
            return

        # Configure networks
        networks = []
        if device_type == "ecorouter":
            networks.append({'bridge': '**vmbr0', 'comment': '# mngmnt port'})
            shared.console.print("[green]Автоматически добавлен management порт: **vmbr0**[/green]")

        shared.console.print("Добавьте сетевые интерфейсы (оставьте пустым для завершения):")
        while True:
            net = input("Имя сети: ").strip()
            if not net:
                break
            networks.append({'bridge': net})

        if not networks:
            shared.console.print("[yellow]VM должна иметь хотя бы один сетевой интерфейс.[/yellow]")
            return

        # Create VM configuration
        vm_config = {
            'device_type': device_type,
            'name': vm_name,
            'template_node': template_node,
            'template_vmid': vmid,
            'networks': networks
        }

        stand['machines'].append(vm_config)
        log_operation(logger, "VM added to stand", success=True, vm_name=vm_name, device_type=device_type, template=f"{template_node}:{vmid}")
        shared.console.print(f"[green]VM '{vm_name}' добавлена в стенд.[/green]")

def remove_vm_from_stand(stand: Dict[str, Any]) -> None:
    """Remove VM from stand with confirmation."""
    with OperationTimer(logger, "Remove VM from stand"):
        display_stand_vms(stand)

        if not stand['machines']:
            shared.console.print("[yellow]Стенд пуст.[/yellow]")
            return

        vm_names = [vm['name'] for vm in stand['machines']]
        shared.console.print("Выберите VM для удаления:")
        for i, name in enumerate(vm_names, 1):
            shared.console.print(f"{i}. {name}")

        try:
            choice = int(input("Номер: ")) - 1
            if 0 <= choice < len(vm_names):
                removed_vm = stand['machines'].pop(choice)
                shared.console.print(f"[green]Удалена VM: {removed_vm['name']}[/green]")
                log_operation(logger, "VM removed from stand", success=True, vm_name=removed_vm['name'])
            else:
                shared.console.print("[red]Недопустимый номер.[/red]")
        except ValueError:
            shared.console.print("[red]Введите число.[/red]")

def display_stand_vms(stand: Dict[str, Any]) -> None:
    """Display current stand VMs in formatted table."""
    with OperationTimer(logger, "Display stand VMs"):
        machines = stand.get('machines', [])
        if not machines:
            shared.console.print("[yellow]Стенд пуст.[/yellow]")
            return

        table = Table(title="Виртуальные машины в стенде")
        table.add_column("№", style="cyan", justify="center")
        table.add_column("Имя", style="green")
        table.add_column("Тип", style="magenta")
        table.add_column("Шаблон", style="blue")
        table.add_column("Сетевые интерфейсы", style="yellow")

        for i, vm in enumerate(machines, 1):
            networks_info = []
            for network in vm.get('networks', []):
                bridge = network.get('bridge', '')
                comment = network.get('comment', '')
                if comment:
                    networks_info.append(f"{bridge} {comment}")
                else:
                    networks_info.append(bridge)

            table.add_row(
                str(i),
                vm.get('name', ''),
                vm.get('device_type', ''),
                f"{vm.get('template_node', '')}:{vm.get('template_vmid', '')}",
                ", ".join(networks_info)
            )

        shared.console.print(table)
        logger.debug(f"Displayed {len(machines)} VMs in stand")

def save_stand(name: str, stand: Dict[str, Any]) -> None:
    """Save stand to YAML file with validation."""
    with OperationTimer(logger, f"Save stand {name}"):
        if not name.strip():
            shared.console.print("[red]Имя стенда не может быть пустым.[/red]")
            return

        if not stand.get('machines'):
            shared.console.print("[yellow]В стенде нет VM для сохранения.[/yellow]")
            return

        if _save_stand(name, stand):
            shared.console.print(f"[green]Стенд '{name}' сохранен ({len(stand['machines'])} VM).[/green]")
            log_operation(logger, "Stand saved", success=True, stand_name=name, vm_count=len(stand['machines']))
        else:
            shared.console.print("[red]Ошибка сохранения стенда.[/red]")

def delete_stand_file() -> Optional[str]:
    """Delete a stand file with confirmation."""
    with OperationTimer(logger, "Delete stand file"):
        stand_files = _get_stand_files()

        if not stand_files:
            shared.console.print("[yellow]Нет стендов для удаления.[/yellow]")
            input("Нажмите Enter для продолжения...")
            return None

        # Display available stands
        table = Table(title="Удаление стенда")
        table.add_column("№", style="cyan", justify="center")
        table.add_column("Имя стенда", style="green")
        table.add_column("Файл", style="blue")

        for i, (name, file_path) in enumerate(stand_files, 1):
            table.add_row(str(i), name, Path(file_path).name)

        shared.console.print(table)

        try:
            choice = int(input("Выберите номер для удаления (0 для отмены): ")) - 1
            if choice == -1:  # 0 input becomes -1
                logger.debug("Stand deletion cancelled by user")
                return None
            elif 0 <= choice < len(stand_files):
                name, file_path = stand_files[choice]

                # Confirmation
                confirm = input(f"Удалить стенд '{name}'? (y/n): ").strip().lower()
                if confirm != 'y':
                    logger.debug(f"Deletion cancelled for stand {name}")
                    return None

                try:
                    Path(file_path).unlink()
                    shared.console.print(f"[green]Стенд '{name}' удален.[/green]")
                    log_operation(logger, "Stand deleted", success=True, stand_name=name)
                    return name
                except Exception as e:
                    shared.console.print(f"[red]Ошибка удаления файла: {e}[/red]")
                    log_error(logger, e, f"Delete stand file {file_path}")
                    return None
            else:
                shared.console.print("[red]Недопустимый номер.[/red]")
                return None
        except ValueError:
            shared.console.print("[red]Введите число.[/red]")
            return None

def display_list_of_stands() -> None:
    """Display list of saved stands with details."""
    with OperationTimer(logger, "Display list of stands"):
        stand_files = _get_stand_files()

        if not stand_files:
            shared.console.print("[yellow]Нет сохраненных стендов.[/yellow]")
            input("Нажмите Enter для продолжения...")
            return

        # Display in table format
        table = Table(title="Сохраненные стенды")
        table.add_column("№", style="cyan", justify="center")
        table.add_column("Имя стенда", style="green")
        table.add_column("Количество VM", style="magenta", justify="center")

        total_vms = 0
        for i, (name, file_path) in enumerate(stand_files, 1):
            try:
                stand_data = _load_stand(name)
                vm_count = len(stand_data.get('machines', [])) if stand_data else 0
                total_vms += vm_count
                table.add_row(str(i), name, str(vm_count))
            except Exception as e:
                table.add_row(str(i), name, "Ошибка")
                log_error(logger, e, f"Check stand {name}")

        shared.console.print(table)
        logger.info(f"Displayed {len(stand_files)} stands with {total_vms} total VMs")

        input("Нажмите Enter для продолжения...")

#!/usr/bin/env python3
"""
Stands module for Lazy Teacher.
Provides functions for managing stand configurations.
"""

import glob
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from . import shared
from .connections import get_proxmox_connection
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)


def _get_stand_files() -> List[Tuple[str, str]]:
    """Get list of stand configuration files."""
    pattern = str(shared.CONFIG_DIR / "*_stand.yaml")
    files = glob.glob(pattern)
    return [(Path(f).stem.replace('_stand', ''), f) for f in files]


def display_list_of_stands() -> None:
    """Display list of all stand configurations."""
    with OperationTimer(logger, "Display stands"):
        stand_files = _get_stand_files()
        
        if not stand_files:
            print("[!] Нет конфигураций стендов.")
            input("\nНажмите Enter для продолжения...")
            return
        
        print("\nКонфигурации стендов:")
        print("-" * 60)
        print(f"{'№':<5} {'Имя':<25} {'Машин':<10} {'Сетей':<10}")
        print("-" * 60)
        
        for i, (name, file_path) in enumerate(stand_files, 1):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                machines = data.get('machines', [])
                networks = set()
                for m in machines:
                    for n in m.get('networks', []):
                        networks.add(n.get('bridge', ''))
                
                print(f"{i:<5} {name:<25} {len(machines):<10} {len(networks):<10}")
            except Exception as e:
                print(f"{i:<5} {name:<25} {'Ошибка':<10}")
        
        print("-" * 60)
        input("\nНажмите Enter для продолжения...")


def display_stand_vms(stand: Dict[str, Any]) -> None:
    """Display VMs in a stand configuration."""
    machines = stand.get('machines', [])
    
    if not machines:
        print("[!] В конфигурации нет машин.")
        return
    
    print("\nМашины в конфигурации:")
    print("-" * 80)
    print(f"{'№':<5} {'Имя':<20} {'Template':<12} {'Node':<15} {'Тип':<12} {'Сетей':<8}")
    print("-" * 80)
    
    for i, machine in enumerate(machines, 1):
        name = machine.get('name', 'N/A')
        template = machine.get('template_vmid', 'N/A')
        node = machine.get('template_node', 'N/A')
        device_type = machine.get('device_type', 'linux')
        networks = len(machine.get('networks', []))
        
        print(f"{i:<5} {name:<20} {str(template):<12} {node:<15} {device_type:<12} {networks:<8}")
    
    print("-" * 80)
    input("\nНажмите Enter для продолжения...")


def add_vm_to_stand(stand: Dict[str, Any], conn_name: str = None) -> None:
    """Add a VM to stand configuration."""
    with OperationTimer(logger, "Add VM to stand"):
        try:
            prox = get_proxmox_connection(conn_name)
        except Exception as e:
            print(f"[!] {e}")
            return
        
        # Get available nodes
        nodes_data = prox.nodes.get()
        nodes = [n['node'] for n in nodes_data]
        
        print("\nДоступные ноды:")
        for i, node in enumerate(nodes, 1):
            print(f"  [{i}] {node}")
        
        try:
            node_choice = int(input("Выберите ноду: ")) - 1
            if not (0 <= node_choice < len(nodes)):
                print("[!] Неверный выбор.")
                return
            selected_node = nodes[node_choice]
        except ValueError:
            print("[!] Введите число.")
            return
        
        # Get VMs on selected node
        vms = prox.nodes(selected_node).qemu.get()
        templates = [vm for vm in vms if vm.get('template')]
        
        if not templates:
            print("[!] На ноде нет шаблонов.")
            return
        
        print(f"\nШаблоны на ноде {selected_node}:")
        print("-" * 60)
        print(f"{'№':<5} {'VMID':<10} {'Имя':<40}")
        print("-" * 60)
        
        for i, vm in enumerate(templates, 1):
            print(f"{i:<5} {vm['vmid']:<10} {vm.get('name', 'N/A'):<40}")
        
        print()
        
        try:
            template_choice = int(input("Выберите шаблон: ")) - 1
            if not (0 <= template_choice < len(templates)):
                print("[!] Неверный выбор.")
                return
            selected_template = templates[template_choice]
        except ValueError:
            print("[!] Введите число.")
            return
        
        vm_name = input("Имя VM (оставьте пустым для имени шаблона): ").strip()
        if not vm_name:
            vm_name = selected_template.get('name', 'vm')
        
        # Auto-detect device type from template name
        template_name = selected_template.get('name', '').lower()
        device_type = 'ecorouter' if template_name.startswith('eco-') else 'linux'
        print(f"    Тип машины: {device_type}")
        
        # Get networks
        networks = []
        print("\nДобавление сетей (пустая строка для завершения):")
        
        while True:
            bridge = input("Bridge (например lan или lan.100): ").strip()
            if not bridge:
                break
            networks.append({'bridge': bridge})
        
        if not networks:
            networks = [{'bridge': 'lan'}]
        
        # Add machine to stand
        machine = {
            'name': vm_name,
            'template_vmid': selected_template['vmid'],
            'template_node': selected_node,
            'networks': networks,
            'device_type': device_type
        }
        
        stand.setdefault('machines', []).append(machine)
        print(f"\n[+] Машина '{vm_name}' добавлена в конфигурацию (тип: {device_type})")
        logger.info(f"Added VM {vm_name} to stand config (type: {device_type})")


def remove_vm_from_stand(stand: Dict[str, Any]) -> None:
    """Remove a VM from stand configuration."""
    machines = stand.get('machines', [])
    
    if not machines:
        print("[!] В конфигурации нет машин.")
        return
    
    print("\nМашины в конфигурации:")
    for i, machine in enumerate(machines, 1):
        print(f"  [{i}] {machine.get('name', 'N/A')}")
    print(f"  [0] Отмена")
    
    try:
        choice = int(input("Выберите машину для удаления: "))
        if choice == 0:
            return
        if 1 <= choice <= len(machines):
            removed = machines.pop(choice - 1)
            print(f"\n[+] Машина '{removed.get('name')}' удалена")
            logger.info(f"Removed VM {removed.get('name')} from stand config")
        else:
            print("[!] Неверный выбор.")
    except ValueError:
        print("[!] Введите число.")


def save_stand(stand_name: str, stand: Dict[str, Any]) -> bool:
    """Save stand configuration to file."""
    file_path = shared.CONFIG_DIR / f"{stand_name}_stand.yaml"
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(stand, f, default_flow_style=False, allow_unicode=True)
        print(f"\n[+] Конфигурация '{stand_name}' сохранена")
        logger.info(f"Saved stand config: {stand_name}")
        return True
    except Exception as e:
        print(f"[!] Ошибка сохранения: {e}")
        log_error(logger, e, f"Save stand {stand_name}")
        return False


def load_stand(stand_name: str) -> Optional[Dict[str, Any]]:
    """Load stand configuration from file."""
    file_path = shared.CONFIG_DIR / f"{stand_name}_stand.yaml"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"Stand config {stand_name} not found")
        return None
    except Exception as e:
        log_error(logger, e, f"Load stand {stand_name}")
        return None


def delete_stand_file() -> None:
    """Delete a stand configuration file."""
    stand_files = _get_stand_files()
    
    if not stand_files:
        print("[!] Нет конфигураций стендов.")
        input("\nНажмите Enter для продолжения...")
        return
    
    print("\nУдаление конфигурации стенда:")
    print("-" * 50)
    
    for i, (name, _) in enumerate(stand_files, 1):
        print(f"  [{i}] {name}")
    print(f"  [0] Отмена")
    print()
    
    try:
        choice = int(input("Выберите конфигурацию: "))
        if choice == 0:
            return
        if 1 <= choice <= len(stand_files):
            name, file_path = stand_files[choice - 1]
            
            confirm = input(f"Удалить конфигурацию '{name}'? (y/n): ").strip().lower()
            if confirm == 'y':
                Path(file_path).unlink()
                print(f"\n[+] Конфигурация '{name}' удалена")
                logger.info(f"Deleted stand config: {name}")
        else:
            print("[!] Неверный выбор.")
    except ValueError:
        print("[!] Введите число.")
    
    input("\nНажмите Enter для продолжения...")



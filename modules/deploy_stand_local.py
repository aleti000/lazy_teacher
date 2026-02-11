#!/usr/bin/env python3
"""
Deploy Stand Local module for Lazy Teacher.
Deploys stands on a single node with group and template registry integration.
"""

import random
import string
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from . import shared
from .connections import get_proxmox_connection
from .network import reload_network as reload_net_func
from .tasks import wait_for_clone_task, wait_for_snapshot_task
from .sync_templates import get_template_vmid_for_node
from .logger import get_logger, log_operation, log_error, OperationTimer

logger = get_logger(__name__)


def generate_password() -> str:
    """Generate 8-digit random password."""
    return ''.join(random.choices(string.digits, k=8))


def get_next_vmid(proxmox) -> Optional[int]:
    """Get next free VMID."""
    try:
        return int(proxmox.cluster.nextid.get())
    except Exception as e:
        logger.error(f"Error getting next VMID: {e}")
        return None


def get_next_bridge_number(proxmox, node: str) -> int:
    """Find next available bridge number."""
    try:
        networks = proxmox.nodes(node).network.get()
        existing_bridges = set()

        for net in networks:
            iface = net.get('iface', '')
            if iface.startswith('vmbr'):
                try:
                    num = int(iface[4:])
                    existing_bridges.add(num)
                except ValueError:
                    continue

        num = 1000
        while num in existing_bridges:
            num += 1

        return num
    except Exception as e:
        logger.error(f"Error getting bridge numbers for node {node}: {e}")
        return 1000


def create_bridges(stand: Dict, proxmox, node: str) -> Dict:
    """Analyze network configurations and create bridges.
    
    If any network uses VLAN (e.g., hq.200), the bridge MUST be vlan_aware=1
    to allow both tagged (with VLAN) and untagged (without VLAN) traffic.
    """
    bridge_number = get_next_bridge_number(proxmox, node)
    bridge_configs = {}

    machines = stand.get('machines', [])
    for machine in machines:
        networks = machine.get('networks', [])
        for network in networks:
            bridge = network['bridge']
            
            if bridge.startswith('**'):
                continue
            
            if '.' in bridge:
                alias = bridge.split('.')[0]
                vlan_id = bridge.split('.')[1]
                if alias not in bridge_configs:
                    bridge_configs[alias] = {
                        'vmbr_name': f"vmbr{bridge_number}",
                        'vlans': set(),
                        'has_vlan': True
                    }
                    bridge_number += 1
                else:
                    # Mark as having VLAN even if initially created without
                    bridge_configs[alias]['has_vlan'] = True
                bridge_configs[alias]['vlans'].add(int(vlan_id))
            else:
                alias = bridge
                if alias not in bridge_configs:
                    bridge_configs[alias] = {
                        'vmbr_name': f"vmbr{bridge_number}",
                        'vlans': set(),
                        'has_vlan': False
                    }
                    bridge_number += 1

    for alias, config in bridge_configs.items():
        try:
            bridge_params = {
                'iface': config['vmbr_name'],
                'type': 'bridge',
                'autostart': 1
            }
            proxmox.nodes(node).network.post(**bridge_params)
            
            # Enable vlan_aware if any network uses VLAN for this alias
            # This allows both tagged and untagged traffic on the same bridge
            if config['has_vlan']:
                try:
                    proxmox.nodes(node).network(config['vmbr_name']).put(
                        type='bridge',
                        bridge_vlan_aware=1
                    )
                    logger.info(f"Enabled VLAN-aware for {config['vmbr_name']} (alias: {alias})")
                except Exception as e:
                    logger.error(f"Failed to enable VLAN-aware for {config['vmbr_name']}: {e}")
                    
            logger.info(f"Created bridge {config['vmbr_name']} on {node}")
        except Exception as e:
            logger.error(f"Error creating bridge {config['vmbr_name']}: {e}")

    return bridge_configs


def create_user(proxmox, username: str, password: str) -> bool:
    """Create Proxmox user."""
    try:
        proxmox.access.users.post(
            userid=username,
            password=password,
        )
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" in error_msg:
            logger.info(f"User {username} already exists")
            return True
        logger.error(f"Error creating user {username}: {e}")
        return False


def create_pool(proxmox, pool_name: str) -> bool:
    """Create Proxmox pool."""
    try:
        proxmox.pools.post(poolid=pool_name)
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" in error_msg:
            logger.info(f"Pool {pool_name} already exists")
            return True
        logger.error(f"Error creating pool {pool_name}: {e}")
        return False


def assign_pool_permissions(proxmox, pool_name: str, username: str) -> bool:
    """Assign permissions to user for pool."""
    try:
        proxmox.access.acl.put(
            path=f"/pool/{pool_name}",
            users=username,
            roles="PVEVMUser"
        )
        return True
    except Exception as e:
        logger.error(f"Error assigning pool permissions: {e}")
        return False


def clone_vm(proxmox, node: str, template_vmid: int, new_vmid: int, 
             vm_name: str, full_clone: int, pool_name: str) -> Optional[str]:
    """Clone VM from template."""
    try:
        result = proxmox.nodes(node).qemu(template_vmid).clone.post(
            newid=new_vmid,
            name=vm_name,
            full=full_clone,
            pool=pool_name
        )
        return result
    except Exception as e:
        logger.error(f"Error cloning VM {vm_name}: {e}")
        return None


def configure_vm_network(proxmox, node: str, vmid: int, networks: List,
                        bridge_configs: Dict, machine_name: str, device_type: str):
    """Configure VM network interfaces.
    
    For ecorouter devices:
        - net0 = vmbr0 + link_down (management port, not used in labs)
        - net1+ = interfaces from configuration
    
    For linux devices:
        - net0+ = interfaces from configuration
    """
    import secrets
    
    net_configs = {}

    if device_type == 'ecorouter':
        # Generate MAC address for ecorouter (1C:87:76:40:XX:XX)
        mac = [0x1C, 0x87, 0x76, 0x40]
        mac.extend(secrets.randbelow(256) for _ in range(2))
        mac_addr = ':'.join(f'{b:02x}' for b in mac)
        
        # net0 = vmbr0 + link_down (management port)
        net_configs['net0'] = f"model=vmxnet3,bridge=vmbr0,macaddr={mac_addr},link_down=1"
        
        # net1+ = interfaces from configuration
        for i, network in enumerate(networks, start=1):
            bridge = network['bridge']
            net_key = f"net{i}"
            
            # Generate unique MAC for each interface
            mac = [0x1C, 0x87, 0x76, 0x40]
            mac.extend(secrets.randbelow(256) for _ in range(2))
            mac_addr = ':'.join(f'{b:02x}' for b in mac)
            
            if bridge.startswith('**'):
                # Static bridge (e.g., **vmbr0)
                bridge_name = bridge.strip('*')
                net_config = f"model=vmxnet3,bridge={bridge_name},macaddr={mac_addr}"
            else:
                alias = bridge.split('.')[0]
                vmbr_name = bridge_configs[alias]['vmbr_name']
                
                if '.' in bridge:
                    vlan_id = bridge.split('.')[1]
                    net_config = f"model=vmxnet3,bridge={vmbr_name},tag={vlan_id},macaddr={mac_addr}"
                else:
                    net_config = f"model=vmxnet3,bridge={vmbr_name},macaddr={mac_addr}"
            
            net_configs[net_key] = net_config
    else:
        # Linux devices - standard configuration
        for i, network in enumerate(networks):
            bridge = network['bridge']
            net_key = f"net{i}"

            if bridge.startswith('**'):
                bridge_name = bridge.strip('*')
                net_config = f"model=virtio,bridge={bridge_name}"
            else:
                alias = bridge.split('.')[0]
                vmbr_name = bridge_configs[alias]['vmbr_name']

                if '.' in bridge:
                    vlan_id = bridge.split('.')[1]
                    net_config = f"model=virtio,bridge={vmbr_name},tag={vlan_id}"
                else:
                    net_config = f"model=virtio,bridge={vmbr_name}"

            net_configs[net_key] = net_config

    for net_key, net_config in net_configs.items():
        try:
            proxmox.nodes(node).qemu(vmid).config.put(**{net_key: net_config})
        except Exception as e:
            logger.error(f"Error configuring {net_key} for VM {vmid}: {e}")


def assign_vm_permissions(proxmox, vmid: int, username: str) -> bool:
    """Assign permissions to user for VM."""
    try:
        proxmox.access.acl.put(
            path=f"/vms/{vmid}",
            users=username,
            roles="PVEVMUser"
        )
        return True
    except Exception as e:
        logger.error(f"Error assigning VM permissions: {e}")
        return False


def create_vm_snapshot(proxmox, node: str, vmid: int, snapname: str = "start") -> Optional[str]:
    """Create snapshot for VM."""
    try:
        result = proxmox.nodes(node).qemu(vmid).snapshot.post(snapname=snapname)
        return result
    except Exception as e:
        logger.error(f"Error creating snapshot '{snapname}' for VM {vmid}: {e}")
        return None


def deploy_stand_local(stand_config: Dict = None, users_list: List[str] = None, 
                       target_node: str = None, update_stand_file: bool = True, 
                       clone_type: int = None) -> List[Dict]:
    """Deploy stand locally - main implementation."""
    from .ui_menus import select_stand_config, select_user_list, select_clone_type

    if stand_config is None:
        result = select_stand_config()
        if result is None:
            print("[!] Не выбран стенд.")
            return []
        stand, stand_file_path = result
        if clone_type is None:
            clone_type = select_clone_type()
    else:
        stand = stand_config

    if users_list is None:
        users = select_user_list()
        if not users:
            print("[!] Не выбран список пользователей.")
            return []
    else:
        users = users_list

    try:
        prox = get_proxmox_connection()
    except Exception as e:
        print(f"[!] {e}")
        input("Нажмите Enter для продолжения...")
        return []

    nodes_data = prox.nodes.get()
    nodes = [n['node'] for n in nodes_data]
    
    if target_node and target_node in nodes:
        node = target_node
    else:
        if stand.get('machines'):
            node = stand['machines'][0].get('template_node', nodes[0])
        else:
            node = nodes[0]
        
        if node not in nodes:
            node = nodes[0]

    deployment_results = []
    
    for user in users:
        username = f"{user.split('@')[0]}@pve"
        password = generate_password()
        pool_name = user.split('@')[0]

        print(f"\n[*] Создание стенда {username}...")

        # Create unique bridges for this user
        user_bridge_configs = create_bridges(stand, prox, node)

        # Create user
        if not create_user(prox, username, password):
            print(f"  [!] Ошибка создания пользователя {username}")
            continue

        # Create pool
        if not create_pool(prox, pool_name):
            print(f"  [!] Ошибка создания пула {pool_name}")
            continue

        # Assign pool permissions
        if not assign_pool_permissions(prox, pool_name, username):
            print(f"  [!] Ошибка назначения прав на пул {pool_name}")
            continue

        # Deploy VMs
        for machine in stand.get('machines', []):
            new_vmid = get_next_vmid(prox)
            if not new_vmid:
                continue

            vm_name = machine['name']
            template_vmid = machine.get('template_vmid')
            template_node = machine.get('template_node', node)
            
            actual_template_vmid = get_template_vmid_for_node(
                stand, machine, node, prox
            )
            
            if not actual_template_vmid:
                actual_template_vmid = template_vmid

            result = clone_vm(prox, node, actual_template_vmid, new_vmid, 
                            vm_name, clone_type, pool_name)
            if not result:
                print(f"  [!] Ошибка клонирования VM {vm_name}")
                continue

            # Always wait for clone to complete before proceeding
            wait_for_clone_task(prox, node, result)

            configure_vm_network(prox, node, new_vmid, machine.get('networks', []),
                               user_bridge_configs, vm_name, machine.get('device_type', 'linux'))

            assign_vm_permissions(prox, new_vmid, username)

            snap_result = create_vm_snapshot(prox, node, new_vmid)
            if snap_result:
                wait_for_snapshot_task(prox, node, snap_result)

        print(f"  [+] Стенд {username} создан")

        deployment_results.append({
            'user': pool_name,
            'password': password,
            'node': node
        })

    # Reload network
    reload_net_func(prox, node)

    # Show results if interactive
    if stand_config is None:
        print("\n" + "=" * 50)
        print("  РЕЗУЛЬТАТЫ РАЗВЕРТЫВАНИЯ")
        print("=" * 50)
        if deployment_results:
            print(f"\n{'Пользователь':<20} {'Пароль':<12} {'Нода':<15}")
            print("-" * 47)
            for result in deployment_results:
                print(f"{result['user']:<20} {result['password']:<12} {result['node']:<15}")
        else:
            print("\n[!] Нет результатов развертывания.")
        input("\nНажмите Enter для продолжения...")

    return deployment_results
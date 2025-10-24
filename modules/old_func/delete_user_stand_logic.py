from . import shared
from .connections import get_proxmox_connection
from .wait_for_task import wait_for_task as wait_task_func
from .reload_network import reload_network as reload_net_func

from modules import *

# Make shared constants available
logger = shared.logger

def delete_user_stand_logic(user):
    """Logic to delete stand of a user."""
    # Get Proxmox connection
    try:
        prox = get_proxmox_connection()
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return

    # Check if user exists
    try:
        users = prox.access.users.get()
        user_exists = any(u['userid'] == user for u in users)
        if not user_exists:
            print(f"Пользователь {user} не найден.")
            input("Нажмите Enter для продолжения...")
            return
    except Exception as e:
        print(f"Ошибка проверки пользователя: {e}")
        return

    pool_name = user.split('@')[0]

    # Check if pool exists
    try:
        pools = prox.pools.get()
        pool_exists = any(p['poolid'] == pool_name for p in pools)
        if not pool_exists:
            print(f"Пул {pool_name} не найден.")
            input("Нажмите Enter для продолжения...")
            return
    except Exception as e:
        print(f"Ошибка проверки пула: {e}")
        return

    # Get VM members from pool
    try:
        pool_data = prox.pools(pool_name).get()
        members = pool_data.get('members', [])
        if not members:
            print("В пуле нет VM.")
            input("Нажмите Enter для продолжения...")
            return
    except (KeyError, IndexError):
        print("Пул не найден или недоступен.")
        input("Нажмите Enter для продолжения...")
        return
    except Exception as e:
        print(f"Ошибка получения ВМ пула: {e}")
        input("Нажмите Enter для продолжения...")
        return

    # Get all unique nodes from pool members
    nodes_in_use = set()
    for member in members:
        if 'node' in member:
            nodes_in_use.add(member['node'])
    if not nodes_in_use:
        print("Не найдены ноды для перезагрузки сети.")
        return

    # Collect bridges from VM configs before deleting
    bridges_to_delete = set()
    for member in members:
        vmid = member['vmid']
        member_node = member['node']
        try:
            vm_config = prox.nodes(member_node).qemu(vmid).config.get()
            for key, value in vm_config.items():
                if key.startswith('net') and 'bridge=' in value:
                    bridge_part = value.split('bridge=')[1].split(',')[0]
                    if bridge_part.startswith('vmbr') and bridge_part.split('vmbr')[1].isdigit():
                        num = int(bridge_part.split('vmbr')[1])
                        if 1000 <= num <= 1999:
                            bridges_to_delete.add((bridge_part, member_node))
        except Exception as e:
            print(f"Ошибка получения конфигурации VM {vmid}: {e}")

    # Get nodes again (may have changed)
    nodes_data = prox.nodes.get()
    nodes = [n['node'] for n in nodes_data]

    # Delete VMs
    deleted_vmids = []
    for member in members:
        vmid = member['vmid']
        for node_name in nodes:
            try:
                vms = prox.nodes(node_name).qemu.get()
                if any(vm['vmid'] == vmid for vm in vms):
                    upid = prox.nodes(node_name).qemu(vmid).delete(purge=1)
                    if wait_task_func(prox, node_name, upid):
                        deleted_vmids.append(vmid)
                    break
            except Exception as e:
                logger.error(f"Ошибка удаления ВМ {vmid}: {e}")

    # Delete pool
    try:
        prox.pools(pool_name).delete()
    except Exception as e:
        logger.error(f"Ошибка удаления пула: {e}")

    # Delete user
    try:
        prox.access.users(user).delete()
    except Exception as e:
        logger.error(f"Ошибка удаления пользователя: {e}")

    # Delete bridges on their respective nodes
    for bridge_name, bridge_node in bridges_to_delete:
        try:
            prox.nodes(bridge_node).network.delete(bridge_name)
        except Exception as e:
            logger.error(f"Ошибка удаления bridge {bridge_name} на ноде {bridge_node}: {e}")

    # Reload network on all nodes that were in use
    try:
        for node_name in nodes_in_use:
            reload_net_func(prox, node_name)
    except Exception as e:
        shared.logger.error(f"Ошибка перезагрузки сети: {e}")

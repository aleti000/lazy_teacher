import yaml
from pathlib import Path
from . import shared
from .connections import get_proxmox_connection
from .network import reload_network as reload_net_func
from .tasks import wait_for_clone_task as wait_clone_func, wait_for_task

from modules import *

# Make shared constants available
CONFIG_DIR = shared.CONFIG_DIR
logger = shared.logger
def deploy_stand_local(stand_config=None, users_list=None, target_node=None, update_stand_file=True, clone_type=None):
    """Deploy stand locally - main implementation."""
    import random
    import string

    def generate_password():
        """Generate 8-digit random password."""
        return ''.join(random.choices(string.digits, k=8))

    def get_next_vmid(proxmox):
        """Get next free VMID."""
        try:
            nextid = proxmox.cluster.nextid.get()
            return nextid
        except Exception as e:
            print(f"Ошибка получения следующего VMID: {e}")
            return None

    # Use provided configs if available, otherwise select interactively
    if stand_config is None:
        stand, _ = select_stand_config()
        if clone_type is None:
            clone_type = select_clone_type()
    else:
        stand = stand_config

    if users_list is None:
        users = select_user_list()
    else:
        users = users_list

    def get_next_bridge_number(proxmox, node):
        """Найти следующий свободный номер bridge"""
        try:
            networks = proxmox.nodes(node).network.get()
            existing_bridges = set()

            for net in networks:
                iface = net.get('iface', '')
                if iface.startswith('vmbr'):
                    try:
                        num_str = iface[4:]  # vmbr1000 -> 1000
                        num = int(num_str)
                        existing_bridges.add(num)
                    except ValueError as e:
                        logger.warning(f"Не удалось распарсить номер bridge из интерфейса '{iface}': {e}")

            # Найти минимальный свободный номер >= 1000
            num = 1000
            while num in existing_bridges:
                num += 1

            return num
        except Exception as e:
            print(f"КРИТИЧЕСКАЯ ОШИБКА получения номеров bridge: {e}")
            logger.error(f"Ошибка в get_next_bridge_number для ноды {node}: {e}")
            return 1000  # fallback

    def create_bridges(stand, proxmox, node):
        """Analyze network configurations, create bridge mapping and immediately create bridges."""
        bridge_number = get_next_bridge_number(proxmox, node)
        bridge_configs = {}

        machines = stand.get('machines', [])
        for machine in machines:
            networks = machine.get('networks', [])
            for network in networks:
                # Извлекаем bridge имя, игнорируя комментарии
                bridge = network['bridge']
                if bridge.startswith('**'):
                    continue
                elif '.' in bridge:
                    # Есть VLAN
                    alias = bridge.split('.')[0]
                    vlan_id = bridge.split('.')[1]
                    if alias not in bridge_configs:
                        bridge_configs[alias] = {
                            'vlan_aware': True,
                            'vmbr_name': f"vmbr{bridge_number}",
                            'vlans': set()
                        }
                        bridge_number += 1
                    else:
                        # If adding vlan to existing, ensure vlan_aware is True
                        if not bridge_configs[alias]['vlan_aware']:
                            bridge_configs[alias]['vlan_aware'] = True
                    bridge_configs[alias]['vlans'].add(int(vlan_id))
                else:
                    # Просто alias без VLAN
                    alias = bridge
                    if alias not in bridge_configs:
                        bridge_configs[alias] = {
                            'vlan_aware': False,
                            'vmbr_name': f"vmbr{bridge_number}",
                            'vlans': set()
                        }
                        bridge_number += 1

        # Now create the bridges
        for alias, config in bridge_configs.items():
            try:
                # Параметры для создания bridge
                bridge_params = {
                    'iface': config['vmbr_name'],
                    'type': 'bridge',
                    'autostart': 1
                }
                # Создание bridge
                proxmox.nodes(node).network.post(**bridge_params)
                # If vlan-aware, set it
                if config['vlan_aware']:
                    try:
                        proxmox.nodes(node).network(config['vmbr_name']).put(
                            type='bridge',
                            bridge_vlan_aware=1
                        )
                    except Exception as e:
                        logger.error(f"Не удалось включить VLAN-aware для bridge {config['vmbr_name']}: {e}")
            except Exception as e:
                logger.error(f"Ошибка создания bridge {config['vmbr_name']}: {e}")
        return bridge_configs

    def create_user(proxmox, username, password):
        """Create Proxmox user."""
        try:
            proxmox.access.users.post(
                userid=username,
                password=password,
            )
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg or "user already exists" in error_msg:
                logger.info(f"Пользователь {username} уже существует")
                return True
            logger.error(f"Ошибка создания пользователя {username}: {e}")
            return False

    def create_pool(proxmox, pool_name):
        """Create Proxmox pool."""
        try:
            proxmox.pools.post(poolid=pool_name)
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg or "pool already exists" in error_msg:
                logger.info(f"Пул {pool_name} уже существует")
                return True
            logger.error(f"Ошибка создания пула {pool_name}: {e}")
            return False

    def assign_pool_permissions(proxmox, pool_name, username):
        """Assign permissions to user for pool."""
        try:
            proxmox.access.acl.put(
                path=f"/pool/{pool_name}",
                users=username,
                roles="PVEVMUser"
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка назначения прав на пул: {e}")
            return False

    def clone_vm(proxmox, node, template_vmid, new_vmid, vm_name, full_clone, pool_name):
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
            logger.error(f"Ошибка клонирования VM {vm_name}: {e}")
            return None

    def configure_vm_network(proxmox, node, vmid, networks, bridge_configs, machine_name, device_type):
        """Configure VM network interfaces."""
        net_configs = {}

        for i, network in enumerate(networks):
            # Извлекаем bridge имя, игнорируя комментарии
            bridge = network['bridge']
            net_key = f"net{i}"

            if bridge.startswith('**'):
                # Конкретный bridge
                bridge_name = bridge.strip('*')
                net_config = f"model=virtio,bridge={bridge_name}"
            else:
                # Alias bridge
                alias = bridge.split('.')[0]
                vmbr_name = bridge_configs[alias]['vmbr_name']

                if '.' in bridge:
                    # С VLAN
                    vlan_id = bridge.split('.')[1]
                    net_config = f"model=virtio,bridge={vmbr_name},tag={vlan_id}"
                else:
                    # Без VLAN
                    net_config = f"model=virtio,bridge={vmbr_name}"

            # Специальная обработка для ecorouter
            if device_type == 'ecorouter':
                if i == 0:
                    # Первый интерфейс для ecorouter
                    net_config = f"model=vmxnet3,bridge={bridge_name if bridge.startswith('**') else vmbr_name}"
                    if '.' in bridge:
                        vlan_id = bridge.split('.')[1]
                        net_config += f",tag={vlan_id}"
                    net_config += ",link_down=1"
                    # Генерация MAC адреса
                    import secrets
                    mac = [0x1C, 0x87, 0x76, 0x40]  # Ecorouter OUI prefix
                    mac.extend(secrets.randbelow(256) for _ in range(2))  # Случайные 2 байта
                    mac_addr = ':'.join(f'{b:02x}' for b in mac)
                    net_config += f",macaddr={mac_addr}"
                else:
                    net_config = f"model=vmxnet3,bridge={bridge_name if bridge.startswith('**') else vmbr_name}"
                    if '.' in bridge:
                        vlan_id = bridge.split('.')[1]
                        net_config += f",tag={vlan_id}"
                    import secrets
                    mac = [0x1C, 0x87, 0x76, 0x40]  # Ecorouter OUI prefix
                    mac.extend(secrets.randbelow(256) for _ in range(2))  # Случайные 2 байта
                    mac_addr = ':'.join(f'{b:02x}' for b in mac)
                    net_config += f",macaddr={mac_addr}"

            net_configs[net_key] = net_config

        # Применение сетевых конфигураций
        for net_key, net_config in net_configs.items():
            try:
                proxmox.nodes(node).qemu(vmid).config.put(**{net_key: net_config})
            except Exception as e:
                logger.error(f"Ошибка настройки сети {net_key} для VM {vmid}: {e}")

    def assign_vm_permissions(proxmox, vmid, username):
        """Assign permissions to user for VM."""
        try:
            proxmox.access.acl.put(
                path=f"/vms/{vmid}",
                users=username,
                roles="PVEVMUser"
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка назначения прав на VM: {e}")
            return False

    def create_vm_snapshot(proxmox, node, vmid, snapname="start"):
        """Create snapshot for VM with given name."""
        try:
            result = proxmox.nodes(node).qemu(vmid).snapshot.post(
                snapname=snapname
            )
            return result
        except Exception as e:
            logger.error(f"Ошибка создания snapshot '{snapname}' для VM {vmid}: {e}")
            return None

    # Main deployment logic
    if not stand:
        shared.console.print("[red]Не выбран стенд.[/red]")
        return []

    if not users:
        shared.console.print("[red]Не выбран список пользователей.[/red]")
        return []

    # clone_type is now selected or passed as param

    # Get Proxmox connection
    try:
        prox = get_proxmox_connection()
    except Exception as e:
        shared.console.print(f"[red]{e}[/red]")
        input("Нажмите Enter для продолжения...")
        return []

    # Get nodes
    nodes_data = prox.nodes.get()
    nodes = [n['node'] for n in nodes_data]
    # For deployment, use target_node if specified, else template node from stand
    node = target_node
    if not node:
        node = stand['machines'][0]['template_node'] if stand['machines'] else nodes[0]
    if node not in nodes:
        node = nodes[0]
        logger.warning(f"Target/template node {node} not in nodes, using {node}")

    # Deploy for each user
    deployment_results = []
    user_index = 0
    for user in users:
        username = f"{user.split('@')[0]}@pve"
        password = generate_password()
        pool_name = user.split('@')[0]

        with shared.console.status(f"[bold blue]Создание стенда {username}...[/bold blue]", spinner="dots") as status:
            # Create unique bridges for this user for network isolation
            user_bridge_configs = create_bridges(stand, prox, node)

            # Create user
            if not create_user(prox, username, password):
                shared.console.print(f"[red]Ошибка создания пользователя {username}[/red]")
                continue

            # Create pool
            if not create_pool(prox, pool_name):
                shared.console.print(f"[red]Ошибка создания пула {pool_name}[/red]")
                continue

            # Assign pool permissions
            if not assign_pool_permissions(prox, pool_name, username):
                shared.console.print(f"[red]Ошибка назначения прав на пул {pool_name}[/red]")
                continue

            # Deploy VMs
            for machine in stand['machines']:
                new_vmid = get_next_vmid(prox)
                if not new_vmid:
                    continue

                # Clone VM
                vm_name = machine['name']  # Use machine name, assume templates on node for local
                template_vmid = machine.get('replicas', {}).get(target_node if target_node else node, machine['template_vmid'])

                # Sync guarantees the template exists, remove redundant check

                result = clone_vm(prox, node, template_vmid, new_vmid, vm_name, clone_type, pool_name)
                if not result:
                    shared.console.print(f"[red]Ошибка клонирования VM {vm_name}[/red]")
                    continue

                # Wait for clone to complete only for distributed deployment
                if target_node:
                    wait_clone_func(prox, node, result)

                # Configure networks
                configure_vm_network(prox, node, new_vmid, machine['networks'],
                                   user_bridge_configs, vm_name, machine['device_type'])

                # Assign VM permissions
                assign_vm_permissions(prox, new_vmid, username)

                # Create snapshot
                snap_result = create_vm_snapshot(prox, node, new_vmid)
                if snap_result:
                    wait_for_task(prox, node, snap_result, "snapshot")

        shared.console.print(f"[green]Стенд {username} создан[/green]")

        deployment_results.append({
            'user': pool_name,
            'password': password,
            'node': node
        })
        user_index += 1

    # Reload network
    reload_net_func(prox, node)

    if stand_config is None:
        shared.console.print("\n[bold green]Результаты развертывания:[/bold green]")
        if deployment_results:
            from rich.table import Table
            table = Table(title="Развернутые стенды", show_header=True, header_style="bold magenta")
            table.add_column("Пользователь", style="cyan", justify="center", no_wrap=True)
            table.add_column("Пароль", style="green", justify="center", no_wrap=True)
            table.add_column("Нода", style="yellow", justify="center", no_wrap=True)
            for result in deployment_results:
                table.add_row(result['user'], result['password'], result['node'])
            shared.console.print(table)
        else:
            shared.console.print("[red]Нет результатов развертывания.[/red]")
        input("Нажмите Enter для продолжения...")

    return deployment_results

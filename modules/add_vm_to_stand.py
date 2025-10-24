from .shared import *
from .test_connection import test_connection as test_conn_func

from modules import *
def add_vm_to_stand(stand, conn_name):
    """Add VM to stand."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
        config = config_data.get(conn_name)
        if not config:
            console.print(f"[red]Ошибка: Подключение '{conn_name}' не найдено в конфигурации.[/red]")
            return
    except Exception as e:
        console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        logger.error(f"Ошибка чтения конфигурации: {e}")
        return

    # Test connection first
    success, message = test_conn_func(config, conn_name)
    if not success:
        console.print(f"[red]Ошибка подключения к '{conn_name}': {message}[/red]")
        console.print("[yellow]Проверьте настройки подключения.[/yellow]")
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
        console.print(f"[red]Ошибка подключения к Proxmox API: {e}[/red]")
        logger.error(f"Не удалось подключиться к Proxmox API: {e}")
        return

    # Get nodes with better error handling
    try:
        nodes = proxi.nodes.get()
        node_names = [node['node'] for node in nodes]
        if not node_names:
            console.print("[red]Ошибка: Не найдено доступных нод на сервере.[/red]")
            return
        logger.debug(f"Найдены ноды: {node_names}")
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            console.print("[red]Ошибка: Превышено время ожидания при получении списка нод.[/red]")
        elif "permission" in error_msg or "unauthorized" in error_msg:
            console.print("[red]Ошибка: Недостаточно прав для получения списка нод.[/red]")
        else:
            console.print(f"[red]Ошибка получения списка нод: {e}[/red]")
        logger.error(f"Ошибка получения нод: {e}")
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
            logger.warning(f"Ошибка получения VM на {node}: {e}")

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
    logger.debug(f"Выбран шаблон: {template_node}:{vm_name}:{vmid}")

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
    logger.info(f"Добавлена VM: {name}")

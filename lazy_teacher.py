#!/usr/bin/env python3
"""
Lazy Teacher - CLI tool for deploying VM stands on Proxmox for students.
Automates virtual machine setup via Proxmox API using proxmoxer and YAML configs.
"""

import os
import sys
import yaml
import logging
import warnings
import time
from pathlib import Path
import proxmoxer
from functools import wraps
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

warnings.filterwarnings("ignore", message=".*Unverified HTTPS request.*")

# Setup logger
logging.basicConfig(
    filename='lazy_teacher.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize console
console = Console()

# Constants
CONFIG_DIR = Path('config')
CONFIG_DIR.mkdir(exist_ok=True)

BRIDGE_PREFIX = 'vmbr'
PVE_REALM = '@pve'
VLAN_SEPARATOR = '.'
STATIC_PREFIX = '**'
BACK_OPTION = '0'

DEFAULT_CONN = None

def print_header():
    """Print styled header with current connections and nodes."""
    if DEFAULT_CONN:
        title = f"LAZY TEACHER [active: {DEFAULT_CONN}]"
        header_text_content = f"Автоматизация от {title}"
    else:
        title = "LAZY TEACHER"
        header_text_content = "Автоматизация от LAZY TEACHER"
    header_text = Text(header_text_content, style="bold bright_blue", justify="center")
    console.print(Panel(header_text, title="[bold red]LAZY TEACHER[/bold red]"))

    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            if data:
                table = Table(title="Активные соединения", box=None)
                table.add_column("Имя", style="cyan", no_wrap=True)
                table.add_column("Хост:Порт", style="green")
                table.add_column("Доступные ноды", style="yellow")
                table.add_column("Статус", style="red")
                for name, conn in data.items():
                    host_port = f"{conn['host']}:{conn.get('port', '8006')}"
                    nodes = "Недоступно"

                    try:
                        if conn.get('token'):
                            proxi = proxmoxer.ProxmoxAPI(
                                conn['host'],
                                port=int(conn['port']),
                                token_name=conn['token'],
                                token_value=conn['token'],
                                verify_ssl=False
                            )
                        else:
                            proxi = proxmoxer.ProxmoxAPI(
                                conn['host'],
                                port=int(conn['port']),
                                user=conn.get('login'),
                                password=conn.get('password'),
                                verify_ssl=False
                            )
                        nodelist = proxi.nodes.get()
                        nodes = ', '.join([n['node'] for n in nodelist]) if nodelist else "Нет"

                        if name == DEFAULT_CONN:
                            connection_status = "[green]✓ активен[/green]"
                        else:
                            connection_status = "[red]✗ не активен[/red]"
                    except Exception as e:
                        logger.error(f"Ошибка получения нод для {name}: {e}")
                        if name == DEFAULT_CONN:
                            connection_status = "[red]✗ активен (ошибка)[/red]"
                        else:
                            connection_status = "[red]✗ не активен[/red]"

                    table.add_row(name, host_port, nodes, connection_status)
                console.print(table)
        except Exception as e:
            logger.error(f"Ошибка чтения конфига для заголовка: {e}")
            console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")

def main_menu():
    """Main menu handler with styled menu."""
    while True:
        console.clear()
        print_header()
        console.print()
        console.print(Panel.fit(
            "\n[green]1. Управление конфигурационными файлами[/green]\n"
            "[green]2. Развернуть стенд[/green]\n"
            "[green]3. Удалить стенд[/green]\n"
            "[red]0. Выход[/red]",
            title="[bold blue]Главное меню[/bold blue]",
            border_style="blue"
        ))
        console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            console.print("[blue]Выход из программы...[/blue]")
            sys.exit(0)
        elif choice == '1':
            config_menu()
        elif choice == '2':
            deploy_stand_menu()
        elif choice == '3':
            delete_stand_menu()
        else:
            console.print("[red]Недопустимый выбор. Попробуйте еще раз.[/red]")

def config_menu():
    """Configuration management menu with styled menu."""
    while True:
        console.clear()
        print_header()
        console.print()
        console.print(Panel.fit(
            "\n[green]1. Управление подключениями[/green]\n"
            "[green]2. Управление пользователями[/green]\n"
            "[green]3. Управление стендами[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Меню конфигурации[/bold blue]",
            border_style="blue"
        ))
        console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            connection_menu()
        elif choice == '2':
            user_menu()
        elif choice == '3':
            stand_menu()
        else:
            console.print("[red]Недопустимый выбор.[/red]")

def connection_menu():
    """Connection management submenu with styled menu."""
    while True:
        console.clear()
        print_header()
        console.print()
        console.print(Panel.fit(
            "\n[green]1. Создать новое подключение[/green]\n"
            "[green]2. Отобразить все подключения[/green]\n"
            "[green]3. Удалить подключение[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Управление подключениями[/bold blue]",
            border_style="blue"
        ))
        console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            create_connection()
        elif choice == '2':
            display_connections()
        elif choice == '3':
            delete_connection()
        else:
            console.print("[red]Недопустимый выбор.[/red]")

def display_connections():
    """Display all saved connections using Rich table."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        console.print("[red]Нет сохраненных подключений.[/red]")
        return

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        return

    if not data:
        console.print("[red]Нет подключений.[/red]")
        return

    table = Table(title="Сохраненные подключения", box=None)
    table.add_column("Имя", style="cyan", no_wrap=True)
    table.add_column("Хост", style="green")
    table.add_column("Порт", style="magenta")
    table.add_column("Аутентификация", style="yellow")

    for name, conn in data.items():
        auth = "Token" if conn.get('token') else "Пароль"
        table.add_row(name, conn.get('host', ''), str(conn.get('port', '')), auth)

    console.print(table)
    input("Нажмите Enter для продолжения...")

def create_connection():
    """Create a new Proxmox connection."""
    name = input("Введите имя подключения: ").strip()
    if not name:
        print("Имя не может быть пустым.")
        return

    host = input("Введите адрес хоста (IP или домен): ").strip()
    port = input("Введите порт (по умолчанию 8006): ").strip()
    port = port if port else '8006'

    # Validation TODO: check IP format
    if ':' in host:
        host, port = host.split(':', 1)
    host = host.strip()
    port = port.strip()

    auth_type = input("ВЫберете тип аутентификации (1 - token, 2 - пароль): ").strip()
    token = ''
    login = ''
    password = ''

    if auth_type == '1':
        token = input("Введите API token: ").strip()
    elif auth_type == '2':
        login = input("Введите логин: ").strip()
        if '@' not in login:
            login += '@pam'
        password = input("Введите пароль: ").strip()
    else:
        print("Недопустимый выбор.")
        return

    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
    except Exception as e:
        print(f"Ошибка чтения существующей конфигурации: {e}")
        logger.error(f"Ошибка чтения {config_file}: {e}")
        return

    data[name] = {
        'host': host,
        'port': port,
        'token': token if auth_type == '1' else '',
        'login': login if auth_type == '2' else '',
        'password': password if auth_type == '2' else ''
    }

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
        print("Подключение сохранено.")
        logger.info(f"Создано подключение: {name}")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        logger.error(f"Ошибка сохранения подключения {name}: {e}")

def delete_connection():
    """Delete a connection."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        console.print("[red]Нет сохраненных подключений.[/red]")
        return

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        logger.error(f"Ошибка чтения {config_file}: {e}")
        return

    if not data:
        console.print("[red]Нет подключений.[/red]")
        return

    table = Table(title="[bold red]Существующие подключения[/bold red]", box=None)
    table.add_column("№", style="magenta", justify="center")
    table.add_column("Имя", style="cyan")
    names = list(data.keys())
    for i, name in enumerate(names, 1):
        table.add_row(str(i), name)
    console.print(table)

    try:
        choice = int(input("Выберите номер для удаления: ")) - 1
        if 0 <= choice < len(names):
            deleted = names[choice]
            del data[deleted]
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            console.print(f"[green]Подключение '{deleted}' удалено.[/green]")
            logger.info(f"Удалено подключение: {deleted}")
        else:
            console.print("[red]Недопустимый номер.[/red]")
    except ValueError:
        console.print("[red]Введите число.[/red]")

def user_menu():
    """User management menu."""
    while True:
        console.clear()
        print_header()
        console.print()
        console.print(Panel.fit(
            "\n[green]1. Ввести пользователей вручную[/green]\n"
            "[green]2. Импорт пользователей из списка[/green]\n"
            "[green]3. Отобразить списки пользователей[/green]\n"
            "[green]4. Удалить список пользователей[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Управление пользователями[/bold blue]",
            border_style="blue"
        ))
        console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            input_users_manual()
        elif choice == '2':
            import_users()
        elif choice == '3':
            display_user_lists()
        elif choice == '4':
            delete_user_list()
        else:
            console.print("[red]Недопустимый выбор.[/red]")

def input_users_manual():
    """Manually input list of users."""
    list_name = input("Введите имя списка пользователей: ").strip()
    if not list_name:
        return

    users = []
    print("Введите пользователей (оставьте пустым для завершения):")
    while True:
        user = input("Пользователь: ").strip()
        if not user:
            break
        if '@' not in user:
            user += '@pve'
        users.append(user)
        logger.debug(f"Добавлен пользователь: {user}")

    if not users:
        print("Список пустой.")
        return

    file_path = CONFIG_DIR / f"{list_name}_list.yaml"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump({'users': users}, f, default_flow_style=False)
        print(f"Список сохранен в {file_path}")
        logger.info(f"Создан список пользователей: {list_name}")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        logger.error(f"Ошибка сохранения списка {list_name}: {e}")

def import_users():
    """Import users from file."""
    # Placeholder: assume user inputs file path or use hardcoded
    # In real impl, prompt for file path
    file_path = input("Введите путь к файлу списка пользователей: ").strip()
    if not file_path:
        print("Путь не указан.")
        return

    list_name = input("Введите имя нового списка: ").strip()
    if not list_name:
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        users = []
        for line in lines:
            user = line.strip()
            if user:
                if '@' not in user:
                    user += '@pve'
                users.append(user)
        logger.debug(f"Импортировано пользователей: {len(users)}")

        out_file = CONFIG_DIR / f"{list_name}_list.yaml"
        with open(out_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump({'users': users}, f, default_flow_style=False)
        print(f"Импорт завершен в {out_file}")
        logger.info(f"Импортирован список: {list_name}")
    except Exception as e:
        print(f"Ошибка импорта: {e}")
        logger.error(f"Ошибка импорта из {file_path}: {e}")

def display_user_lists():
    """Display all user lists in tables."""
    import glob
    pattern = str(CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    if not files:
        console.print("[yellow]Нет списков пользователей.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return

    for file in files:
        list_name = Path(file).stem.replace('_list', '')
        console.print(f"[bold blue]Список: {list_name}[/bold blue]")
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                users = data.get('users', [])
                if users:
                    table = Table(title="Пользователи", box=None)
                    table.add_column("№", style="magenta", justify="center")
                    table.add_column("Пользователь", style="cyan")
                    for idx, user in enumerate(users, 1):
                        table.add_row(str(idx), user)
                    console.print(table)
                else:
                    console.print("[dim]  Список пуст.[/dim]")
        except Exception as e:
            console.print(f"[red]  Ошибка чтения: {e}[/red]")

    input("Нажмите Enter для продолжения...")

def delete_user_list():
    """Delete a user list."""
    import glob
    pattern = str(CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    if not files:
        console.print("[yellow]Нет списков для удаления.[/yellow]")
        return

    lists = []
    for file in files:
        list_name = Path(file).stem.replace('_list', '')
        lists.append((list_name, file))

    table = Table(title="[bold red]Существующие списки пользователей[/bold red]", box=None)
    table.add_column("№", style="magenta", justify="center")
    table.add_column("Имя списка", style="cyan")
    for i, (name, _) in enumerate(lists, 1):
        table.add_row(str(i), name)
    console.print(table)

    try:
        choice = int(input("Выберите номер для удаления: ")) - 1
        if 0 <= choice < len(lists):
            name, file = lists[choice]
            os.remove(file)
            console.print(f"[green]Список '{name}' удален.[/green]")
            logger.info(f"Удален список пользователей: {name}")
        else:
            console.print("[red]Недопустимый номер.[/red]")
    except ValueError:
        console.print("[red]Введите число.[/red]")

def stand_menu():
    """Stand management menu."""
    while True:
        console.clear()
        print_header()
        console.print()
        console.print(Panel.fit(
            "\n[green]1. Создать стенд[/green]\n"
            "[green]2. Вывести список стендов[/green]\n"
            "[green]3. Удалить стенд[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Управление стендами[/bold blue]",
            border_style="blue"
        ))
        console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            create_stand_menu()
        elif choice == '2':
            display_list_of_stands()
        elif choice == '3':
            delete_stand_file()
        else:
            console.print("[red]Недопустимый выбор.[/red]")

def create_stand_menu():
    """Create stand submenu."""
    stand_name = input("Введите имя стенда: ").strip()
    if not stand_name:
        return

    stand = {'machines': []}
    # Use the first (or only) connection from config
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        print("Нет подключений.")
        return
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Ошибка чтения конфигурации: {e}")
        return
    if not config_data:
        print("Нет подключений.")
        return
    conn_name = DEFAULT_CONN

    while True:
        os.system('clear')
        print_header()
        print("Создание стенда:", stand_name)
        print("1. Создать VM")
        print("2. Удалить VM из стенда")
        print("3. Отобразить список VM")
        print("4. Сохранить стенд")
        print("0. Назад")

        choice = input("Выберите: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            add_vm_to_stand(stand, conn_name)
        elif choice == '2':
            remove_vm_from_stand(stand)
        elif choice == '3':
            display_stand_vms(stand)
        elif choice == '4':
            save_stand(stand_name, stand)
            break
        else:
            print("Недопустимый выбор.")

def select_connection():
    """Select a Proxmox connection."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        print("Нет подключений.")
        return None

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

    if not data:
        print("Нет подключений.")
        return None

    print("Выберите подключение:")
    names = list(data.keys())
    for i, name in enumerate(names, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Номер: ")) - 1
        if 0 <= choice < len(names):
            return names[choice]
        else:
            print("Недопустимый.")
    except ValueError:
        print("Введите число.")

    return None

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
    success, message = test_connection(config, conn_name)
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
            logger.info(f"Удалена VM: {removed['name']}")
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
    file_path = CONFIG_DIR / f"{name}_stand.yaml"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(stand, f, default_flow_style=False)
        print(f"Стенд сохранен в {file_path}")
        logger.info(f"Сохранен стенд: {name}")
    except Exception as e:
        print(f"Ошибка: {e}")
        logger.error(f"Ошибка сохранения стенда {name}: {e}")

def wait_for_clone_task(proxmox, node, task_id, timeout=600):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = proxmox.nodes(node).tasks(task_id).status.get()
            if status['status'] == 'stopped':
                if status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    raise Exception(f"Clone failed: {status.get('exitstatus')}")
        except Exception as e:
            raise Exception(f"Error checking clone task: {e}")
        time.sleep(2)
    raise TimeoutError("Timeout waiting for clone task to complete")

def wait_for_template_task(proxmox, node, task_id, timeout=600):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = proxmox.nodes(node).tasks(task_id).status.get()
            if status['status'] == 'stopped':
                if status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    raise Exception(f"Template creation failed: {status.get('exitstatus')}")
        except Exception as e:
            raise Exception(f"Error checking template task: {e}")
        time.sleep(2)
    raise TimeoutError("Timeout waiting for template creation task to complete")

def wait_for_migration_task(proxmox, node, task_id, timeout=1200):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = proxmox.nodes(node).tasks(task_id).status.get()
            if status['status'] == 'stopped':
                if status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    raise Exception(f"Migration failed: {status.get('exitstatus')}")
        except Exception as e:
            raise Exception(f"Error checking migration task: {e}")
        time.sleep(5)
    raise TimeoutError("Timeout waiting for migration task to complete")

def sync_templates(prox, stand, nodes):
    """Sync templates to all nodes, update replicas in stand."""
    import random
    import string
    from collections import defaultdict

    updated = False
    # Group machines by template_vmid to avoid redundant clones
    template_groups = defaultdict(list)
    for machine in stand.get('machines', []):
        template_groups[machine['template_vmid']].append(machine)

    # For each unique template_vmid, sync to all nodes
    for template_vmid, machines in template_groups.items():
        # Use original_node from first machine in group (they should be the same)
        original_machine = machines[0]
        original_node = original_machine['template_node']

        for node in nodes:
            if node == original_node:
                continue  # No need for replica on original

            # Check if any machine in group already has replica on this node
            replica_exists = any(node in machine.get('replicas', {}) for machine in machines)
            if replica_exists:
                # Even if config says replica exists, verify it's actually present and is a template
                if 'replicas' in machines[0]:
                    candidate_vmid = machines[0]['replicas'].get(node)
                    if candidate_vmid:
                        try:
                            vms_on_node = prox.nodes(node).qemu.get()
                            template_present = any(vm['vmid'] == candidate_vmid and vm.get('template') == 1 for vm in vms_on_node)
                            if template_present:
                                continue  # Actually exists, skip
                        except Exception:
                            pass
                # If replica not found or error, remove invalid entry and proceed to create new
                for machine in machines:
                    if 'replicas' in machine and node in machine['replicas']:
                        del machine['replicas'][node]

            # Create full clone on original node once per template_vmid per node
            clone_vmid = prox.cluster.nextid.get()
            # Use template_vmid in name for uniqueness, keep simple no special chars
            safe_name = f"tpl{node[:5]}{template_vmid}"
            clone_task_id = prox.nodes(original_node).qemu(template_vmid).clone.post(
                newid=clone_vmid,
                name=safe_name,
                full=1
            )

            # Wait for clone to complete
            try:
                wait_for_clone_task(prox, original_node, clone_task_id)
            except Exception as e:
                logger.error(f"Ошибка ожидания клонирования для шаблона {template_vmid}: {e}")
                continue

            # Convert to template
            template_task_id = prox.nodes(original_node).qemu(clone_vmid).template.post()
            wait_for_template_task(prox, original_node, template_task_id)

            # Migrate to target node
            migrate_result = prox.nodes(original_node).qemu(clone_vmid).migrate.post(
                target=node,
                online=0
            )

            if migrate_result:
                try:
                    migrate_upid = migrate_result['data']
                except TypeError:
                    migrate_upid = migrate_result
                if migrate_upid and wait_for_migration_task(prox, original_node, migrate_upid):
                    # Migration completed, assign replica to all machines using this template
                    for machine in machines:
                        if 'replicas' not in machine:
                            machine['replicas'] = {}
                        machine['replicas'][node] = clone_vmid
                    console.print(f"[green]Шаблон для {len(machines)} машины(н) с template_vmid {template_vmid} синхронизирован на ноду {node}[/green]")
                    updated = True
                else:
                    logger.error(f"Миграция шаблона для template_vmid {template_vmid} на {node} не удалась")
            else:
                logger.error(f"Не удалось инициировать миграцию шаблона для template_vmid {template_vmid} на {node}")

    return updated

def reload_network(proxmox, node):
    """Reload network configuration."""
    try:
        proxmox.nodes(node).network.put()
    except Exception as e:
        logger.error(f"Ошибка перезагрузки сети на ноде {node}: {e}")

def deploy_stand_local(stand_config=None, users_list=None, target_node=None, update_stand_file=True):
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
        def select_stand_config():
            """Select stand configuration file."""
            import glob
            pattern = str(CONFIG_DIR / "*_stand.yaml")
            files = glob.glob(pattern)
            if not files:
                print("Нет конфигураций стендов.")
                return None

            print("Выберите конфигурацию стенда:")
            stands = []
            for file in files:
                stand_name = Path(file).stem.replace('_stand', '')
                stands.append((stand_name, file))

            for i, (name, _) in enumerate(stands, 1):
                print(f"{i}. {name}")

            try:
                choice = int(input("Номер: ")) - 1
                if 0 <= choice < len(stands):
                    name, file = stands[choice]
                    with open(file, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f)
            except (ValueError, FileNotFoundError):
                pass
            return None
        stand = select_stand_config()
    else:
        stand = stand_config

    if users_list is None:
        def select_user_list():
            """Select user list file."""
            import glob
            pattern = str(CONFIG_DIR / "*_list.yaml")
            files = glob.glob(pattern)
            if not files:
                print("Нет списков пользователей.")
                return None

            print("Выберите список пользователей:")
            lists = []
            for file in files:
                list_name = Path(file).stem.replace('_list', '')
                lists.append((list_name, file))

            for i, (name, _) in enumerate(lists, 1):
                print(f"{i}. {name}")

            try:
                choice = int(input("Номер: ")) - 1
                if 0 <= choice < len(lists):
                    name, file = lists[choice]
                    with open(file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f) or {}
                    return data.get('users', [])
            except (ValueError, FileNotFoundError):
                pass
            return None
        users = select_user_list()
    else:
        users = users_list

    def select_clone_type():
        """Select clone type."""
        print("Выберите тип клонирования:")
        print("1. Полное клонирование (full)")
        print("2. Связанное клонирование (linked)")

        choice = input("Выбор: ").strip()
        return 1 if choice == '1' else 0

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
            logger.error(f"Ошибка создания пользователя {username}: {e}")
            return False

    def create_pool(proxmox, pool_name):
        """Create Proxmox pool."""
        try:
            proxmox.pools.post(poolid=pool_name)
            return True
        except Exception as e:
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

    # Main deployment logic
    if not stand:
        console.print("[red]Не выбран стенд.[/red]")
        return []

    if not users:
        console.print("[red]Не выбран список пользователей.[/red]")
        return []

    clone_type = 1  # Default to full clone, or could pass as param

    # Get connection config
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data_all = yaml.safe_load(f) or {}
        config_data = config_data_all.get(DEFAULT_CONN)
        if not config_data:
            console.print(f"[red]Ошибка: Подключение '{DEFAULT_CONN}' не найдено в конфигурации.[/red]")
            input("Нажмите Enter для продолжения...")
            return []
    except Exception as e:
        console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        logger.error(f"Ошибка чтения конфигурации: {e}")
        input("Нажмите Enter для продолжения...")
        return []

    # Test connection before proceeding
    success, message = test_connection(config_data, DEFAULT_CONN)
    if not success:
        console.print(f"[red]Ошибка подключения к '{DEFAULT_CONN}': {message}[/red]")
        console.print("[yellow]Проверьте настройки подключения.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return []

    # Connect to Proxmox
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
    except Exception as e:
        console.print(f"[red]Ошибка подключения к Proxmox API: {e}[/red]")
        logger.error(f"Не удалось подключиться к Proxmox API: {e}")
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

        with console.status(f"[bold blue]Создание стенда {username}...[/bold blue]", spinner="dots") as status:
            # Create unique bridges for this user for network isolation
            user_bridge_configs = create_bridges(stand, prox, node)

            # Create user
            if not create_user(prox, username, password):
                continue

            # Create pool
            if not create_pool(prox, pool_name):
                continue

            # Assign pool permissions
            if not assign_pool_permissions(prox, pool_name, username):
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

                if not clone_vm(prox, node, template_vmid, new_vmid, vm_name, clone_type, pool_name):
                    continue

                # Configure networks
                configure_vm_network(prox, node, new_vmid, machine['networks'],
                                   user_bridge_configs, vm_name, machine['device_type'])

                # Assign VM permissions
                assign_vm_permissions(prox, new_vmid, username)

        console.print(f"[green]Стенд {username} создан[/green]")

        deployment_results.append({
            'user': pool_name,
            'password': password,
            'node': node
        })
        user_index += 1

    # Reload network
    reload_network(prox, node)

    return deployment_results

def deploy_stand_distributed():
    """Deploy stand with even distribution of users across nodes."""
    import glob
    import random
    import string

    def select_stand_config():
        """Select stand configuration file."""
        pattern = str(CONFIG_DIR / "*_stand.yaml")
        files = glob.glob(pattern)
        if not files:
            print("Нет конфигураций стендов.")
            return None

        print("Выберите конфигурацию стенда:")
        stands = []
        for file in files:
            stand_name = Path(file).stem.replace('_stand', '')
            stands.append((stand_name, file))

        for i, (name, _) in enumerate(stands, 1):
            print(f"{i}. {name}")

        try:
            choice = int(input("Номер: ")) - 1
            if 0 <= choice < len(stands):
                name, file = stands[choice]
                with open(file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f), file  # Return stand and file path for saving
        except (ValueError, FileNotFoundError):
            pass
        return None, None

    def select_user_list():
        """Select user list file."""
        pattern = str(CONFIG_DIR / "*_list.yaml")
        files = glob.glob(pattern)
        if not files:
            print("Нет списков пользователей.")
            return None

        print("Выберите список пользователей:")
        lists = []
        for file in files:
            list_name = Path(file).stem.replace('_list', '')
            lists.append((list_name, file))

        for i, (name, _) in enumerate(lists, 1):
            print(f"{i}. {name}")

        try:
            choice = int(input("Номер: ")) - 1
            if 0 <= choice < len(lists):
                name, file = lists[choice]
                with open(file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                return data.get('users', [])
        except (ValueError, FileNotFoundError):
            pass
        return None

    stand, stand_file_path = select_stand_config()
    if not stand:
        input("Нажмите Enter для продолжения...")
        return

    users = select_user_list()
    if not users:
        input("Нажмите Enter для продолжения...")
        return

    # Get connection config
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data_all = yaml.safe_load(f) or {}
        config_data = config_data_all.get(DEFAULT_CONN)
        if not config_data:
            console.print(f"[red]Ошибка: Подключение '{DEFAULT_CONN}' не найдено в конфигурации.[/red]")
            input("Нажмите Enter для продолжения...")
            return
    except Exception as e:
        console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        logger.error(f"Ошибка чтения конфигурации: {e}")
        input("Нажмите Enter для продолжения...")
        return

    # Test connection before proceeding
    success, message = test_connection(config_data, DEFAULT_CONN)
    if not success:
        console.print(f"[red]Ошибка подключения к '{DEFAULT_CONN}': {message}[/red]")
        console.print("[yellow]Проверьте настройки подключения.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return

    # Connect to Proxmox
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
    except Exception as e:
        console.print(f"[red]Ошибка подключения к Proxmox API: {e}[/red]")
        logger.error(f"Не удалось подключиться к Proxmox API: {e}")
        input("Нажмите Enter для продолжения...")
        return

    # Get nodes
    nodes_data = prox.nodes.get()
    nodes = [n['node'] for n in nodes_data]
    if len(nodes) < 2:
        console.print(f"[red]Не хватает нод для распределения. Доступно: {len(nodes)}[/red]")
        input("Нажмите Enter для продолжения...")
        return

    console.print(f"[blue]Начинаем синхронизацию шаблонов для {len(nodes)} нод...[/blue]")
    # Sync templates to all nodes
    updated = sync_templates(prox, stand, nodes)
    if updated:
        # Save updated stand with replicas
        try:
            with open(stand_file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(stand, f, default_flow_style=False)
            console.print("[green]Стенд обновлен с информацией о репликах шаблонов.[/green]")
        except Exception as e:
            logger.error(f"Ошибка сохранения обновленного стенда: {e}")
            console.print(f"[red]Не удалось сохранить обновленный стенд: {e}[/red]")

    # Now deploy for each user on assigned node
    all_deployment_results = []
    for user_index, user in enumerate(users):
        target_node = nodes[user_index % len(nodes)]
        console.print(f"[cyan]Развертывание для пользователя {user} на ноде {target_node}[/cyan]")

        # Deploy stand for this user on target_node and collect results
        user_results = deploy_stand_local(
            stand_config=stand,
            users_list=[user],
            target_node=target_node,
            update_stand_file=False
        )
        all_deployment_results.extend(user_results)

    console.print("[green]Распределенное развертывание завершено![/green]")
    print("\nОбщие результаты развертывания:")
    print("Распределение пользователей по нодам:")
    for result in all_deployment_results:
        print(f"Пользователь: {result['user']}, Пароль: {result['password']}, Нода: {result['node']}")

    input("Нажмите Enter для продолжения...")

def deploy_stand_menu():
    """Deploy stand submenu."""
    while True:
        console.clear()
        print_header()
        console.print()
        console.print(Panel.fit(
            "\n[green]1. Локальная развертка ВМ[/green]\n"
            "[green]2. Равномерное распределение машин между нодами[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Развернуть стенд[/bold blue]",
            border_style="blue"
        ))
        console.print()

        choice = input("Выберите: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            deploy_stand_local()
        elif choice == '2':
            deploy_stand_distributed()
        else:
            console.print("[red]Недопустимый выбор.[/red]")

def delete_stand_menu():
    """Delete stand submenu."""
    while True:
        console.clear()
        print_header()
        console.print()
        console.print(Panel.fit(
            "\n[green]1. Удалить стенд пользователя[/green]\n"
            "[green]2. Удалить все стенды из списка пользователей[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Удалить стенд[/bold blue]",
            border_style="blue"
        ))
        console.print()

        choice = input("Выберите: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            delete_user_stand()
        elif choice == '2':
            delete_all_user_stands()
        else:
            console.print("[red]Недопустимый выбор.[/red]")

def delete_stand_file():
    """Delete a stand file."""
    import glob
    pattern = str(CONFIG_DIR / "*_stand.yaml")
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
            os.remove(file)
            print("Стенд удален.")
            logger.info(f"Удален стенд: {name}")
        else:
            print("Недопустимый номер.")
    except ValueError:
        print("Введите число.")

def display_list_of_stands():
    """Display list of saved stands."""
    import glob
    pattern = str(CONFIG_DIR / "*_stand.yaml")
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

def test_connection(config_data, conn_name):
    """Test connection to Proxmox server."""
    try:
        if config_data.get('token'):
            proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                token_name=config_data['token'],
                token_value=config_data['token'],
                verify_ssl=False,
                timeout=10
            )
        else:
            proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                user=config_data.get('login'),
                password=config_data.get('password'),
                verify_ssl=False,
                timeout=10
            )
        return True, "Подключение успешно"
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            return False, "Ошибка: Превышено время ожидания подключения"
        elif "unauthorized" in error_msg or "authentication" in error_msg:
            return False, "Ошибка: Неправильные учетные данные"
        elif "connection" in error_msg or "network" in error_msg:
            return False, "Ошибка: Не удается подключиться к серверу"
        elif "certificate" in error_msg:
            return False, "Ошибка: Проблема с SSL сертификатом"
        else:
            return False, f"Ошибка подключения: {e}"

def select_default_connection():
    """Select default connection at startup."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        console.print("[red]Ошибка: Файл конфигурации не найден.[/red]")
        console.print("[yellow]Создание нового подключения...[/yellow]")
        create_connection()
        return select_default_connection()  # Recurse to select if created

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        logger.error(f"Ошибка чтения конфигурации: {e}")
        return None

    if not data:
        console.print("[red]Ошибка: Нет настроенных подключений.[/red]")
        console.print("[yellow]Создание нового подключения...[/yellow]")
        create_connection()
        return select_default_connection()

    names = list(data.keys())
    console.print("[bold blue]Доступные подключения:[/bold blue]")

    # Test all connections and show their status
    connection_status = {}
    for name in names:
        conn = data[name]
        success, message = test_connection(conn, name)
        connection_status[name] = (success, message)
        status_icon = "✓" if success else "✗"
        console.print(f"  {status_icon} {name} ({conn.get('host')}:{conn.get('port')}) - {message}")

    # Filter available connections
    available_connections = [name for name in names if connection_status[name][0]]

    if not available_connections:
        console.print("[red]Ошибка: Нет доступных подключений.[/red]")
        console.print("[yellow]Проверьте настройки подключений или создайте новое.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return None

    console.print()
    console.print("[green]Доступные для использования:[/green]")
    for i, name in enumerate(available_connections, 1):
        console.print(f"{i}. {name}")

    try:
        choice = int(input("Выберите номер подключения: ")) - 1
        if 0 <= choice < len(available_connections):
            selected = available_connections[choice]
            console.print(f"[green]Выбрано активное подключение: {selected}[/green]")
            return selected
        else:
            console.print("[red]Недопустимый номер.[/red]")
            return select_default_connection()
    except ValueError:
        console.print("[red]Введите число.[/red]")
        return select_default_connection()

def delete_user_stand():
    """Delete stand of a user."""
    user = input("Введите пользователя (например user1@pve): ").strip()
    if '@' not in user:
        user += '@pve'
    with console.status(f"[bold yellow]Удаление стенда {user}...[/bold yellow]", spinner="dots") as status:
        delete_user_stand_logic(user)
    console.print(f"[red]Стенд {user} удален[/red]")

def wait_for_task(proxmox, node, task_id, timeout=300):
    """
    Ожидает завершения задачи Proxmox.
    Возвращает True при успехе, False при ошибке или таймауте.
    """
    import time
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            task_status = proxmox.nodes(node).tasks(task_id).status.get()
            if task_status['status'] == 'stopped':
                if task_status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    print(f"Task failed: {task_status.get('exitstatus')}")
                    return False
        except Exception as e:
            print(f"Error checking task status: {e}")
            return False
        time.sleep(2)
    print("Timeout waiting for task to complete")
    return False

def delete_user_stand_logic(user):
    """Logic to delete stand of a user."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f).get(DEFAULT_CONN)
    except Exception as e:
        print(f"Ошибка настройки подключения: {e}")
        return

    try:
        if config_data['token']:
            prox = proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                token_name=config_data['token'],
                token_value=config_data['token'],
                verify_ssl=False
            )
        else:
            prox = proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                user=config_data.get('login'),
                password=config_data.get('password'),
                verify_ssl=False
            )
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
                    if wait_for_task(prox, node_name, upid):
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
            reload_network(prox, node_name)
    except Exception as e:
        logger.error(f"Ошибка перезагрузки сети: {e}")

  

def delete_all_user_stands():
    """Delete stands of all users in a list."""
    import glob
    pattern = str(CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    if not files:
        print("Нет списков пользователей.")
        input("Нажмите Enter для продолжения...")
        return

    lists = []
    for file in files:
        list_name = Path(file).stem.replace('_list', '')
        lists.append((list_name, file))

    print("Выберите список пользователей:")
    for i, (name, _) in enumerate(lists, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Номер: ")) - 1
        if 0 <= choice < len(lists):
            name, file = lists[choice]
            print(f"Выбран список: {name}")
        else:
            print("Недопустимый номер.")
            input("Нажмите Enter для продолжения...")
            return
    except ValueError:
        print("Введите число.")
        input("Нажмите Enter для продолжения...")
        return

    try:
        with open(file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        users = data.get('users', [])
    except Exception as e:
        print(f"Ошибка чтения списка: {e}")
        input("Нажмите Enter для продолжения...")
        return

    for user in users:
        username = f"{user.split('@')[0]}@pve"
        with console.status(f"[bold yellow]Удаление стенда {username}...[/bold yellow]", spinner="dots") as status:
            delete_user_stand_logic(user)
        console.print(f"[red]Стенд {username} удален[/red]")

    # Final network reload after all deletions
    try:
        config_file = CONFIG_DIR / 'proxmox_config.yaml'
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f).get(DEFAULT_CONN)
        if config_data['token']:
            proxmox = proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                token_name=config_data['token'],
                token_value=config_data['token'],
                verify_ssl=False
            )
        else:
            proxmox = proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                user=config_data.get('login'),
                password=config_data.get('password'),
                verify_ssl=False
            )
        nodes_data = proxmox.nodes.get()
        nodes = [n['node'] for n in nodes_data]
        # Reload network on all available nodes
        for node_name in nodes:
            reload_network(proxmox, node_name)
    except Exception as e:
        print(f"Ошибка перезагрузки сети: {e}")

    print("Удаление всех стендов завершено.")

if __name__ == "__main__":
    DEFAULT_CONN = select_default_connection()
    main_menu()

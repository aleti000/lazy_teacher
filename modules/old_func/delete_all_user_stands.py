import yaml
from pathlib import Path
from . import shared
from .connections import get_proxmox_connection
from .delete_user_stand_logic import delete_user_stand_logic as delete_logic_func
from .reload_network import reload_network as reload_net_func

from modules import *

# Make shared constants available
CONFIG_DIR = shared.CONFIG_DIR
console = shared.console
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
            delete_logic_func(user)
        console.print(f"[red]Стенд {username} удален[/red]")

    # Final network reload after all deletions
    try:
        proxmox = get_proxmox_connection()
        nodes_data = proxmox.nodes.get()
        nodes = [n['node'] for n in nodes_data]
        # Reload network on all available nodes
        for node_name in nodes:
            reload_net_func(proxmox, node_name)
    except Exception as e:
        print(f"Ошибка перезагрузки сети: {e}")

    print("Удаление всех стендов завершено.")

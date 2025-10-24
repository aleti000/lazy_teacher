from .shared import *

from modules import *
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


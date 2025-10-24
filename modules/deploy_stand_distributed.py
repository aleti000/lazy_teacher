import yaml
import yaml
import yaml
from pathlib import Path
from . import shared
from .connections import get_proxmox_connection
from .sync_templates import sync_templates as sync_templates_func
from .tasks import wait_for_clone_task as wait_clone_func

from .ui_menus import select_stand_config, select_user_list, select_clone_type
from modules import *

# Make shared constants available
CONFIG_DIR = shared.CONFIG_DIR
DEFAULT_CONN = shared.DEFAULT_CONN
console = shared.console
logger = shared.logger
def deploy_stand_distributed():
    """Deploy stand with even distribution of users across nodes."""
    import glob
    import random
    import string

    stand, stand_file_path = select_stand_config()
    if not stand:
        input("Нажмите Enter для продолжения...")
        return

    users = select_user_list()
    if not users:
        input("Нажмите Enter для продолжения...")
        return

    clone_type = select_clone_type()

    # Get Proxmox connection
    try:
        prox = get_proxmox_connection()
    except Exception as e:
        shared.console.print(f"[red]{e}[/red]")
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
    updated = sync_templates_func(prox, stand, nodes)
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
        from .deploy_stand_local import deploy_stand_local as deploy_local_func
        user_results = deploy_local_func(
            stand_config=stand,
            users_list=[user],
            target_node=target_node,
            update_stand_file=False,
            clone_type=clone_type
        )
        all_deployment_results.extend(user_results)

    console.print("[green]Распределенное развертывание завершено![/green]")

    console.print("\n[bold green]Общие результаты развертывания:[/bold green]")
    if all_deployment_results:
        from rich.table import Table
        table = Table(title="Распределение пользователей по нодам", show_header=True, header_style="bold magenta")
        table.add_column("Пользователь", style="cyan", justify="center", no_wrap=True)
        table.add_column("Пароль", style="green", justify="center", no_wrap=True)
        table.add_column("Нода", style="yellow", justify="center", no_wrap=True)
        for result in all_deployment_results:
            table.add_row(result['user'], result['password'], result['node'])
        console.print(table)
    else:
        console.print("[red]Нет результатов развертывания.[/red]")
    input("Нажмите Enter для продолжения...")

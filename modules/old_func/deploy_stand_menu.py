from . import shared
from .deploy_stand_local import deploy_stand_local as deploy_local_func
from .deploy_stand_distributed import deploy_stand_distributed as deploy_distributed_func

from modules import *

def deploy_stand_menu():
    """Deploy stand submenu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Локальная развертка ВМ[/green]\n"
            "[green]2. Равномерное распределение машин между нодами[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Развернуть стенд[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            deploy_local_func()
        elif choice == '2':
            deploy_distributed_func()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

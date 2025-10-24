import sys
from . import shared
from .config_menu import config_menu
from .deploy_stand_menu import deploy_stand_menu as deploy_menu_func
from .delete_stand_menu import delete_stand_menu as delete_menu_func

from modules import *

def main_menu():
    """Main menu handler with styled menu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Управление конфигурационными файлами[/green]\n"
            "[green]2. Развернуть стенд[/green]\n"
            "[green]3. Удалить стенд[/green]\n"
            "[red]0. Выход[/red]",
            title="[bold blue]Главное меню[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            shared.console.print("[blue]Выход из программы...[/blue]")
            sys.exit(0)
        elif choice == '1':
            config_menu()
        elif choice == '2':
            deploy_menu_func()
        elif choice == '3':
            delete_menu_func()
        else:
            shared.console.print("[red]Недопустимый выбор. Попробуйте еще раз.[/red]")

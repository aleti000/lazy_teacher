from . import shared
from rich.panel import Panel

from modules import *

def stand_menu():
    """Stand management menu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Создать стенд[/green]\n"
            "[green]2. Вывести список стендов[/green]\n"
            "[green]3. Удалить стенд[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Управление стендами[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите действие: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            print(f"DEBUG: stand_menu DEFAULT_CONN = {shared.DEFAULT_CONN}")
            create_stand_menu(shared.DEFAULT_CONN)
        elif choice == '2':
            display_list_of_stands()
        elif choice == '3':
            delete_stand_file()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

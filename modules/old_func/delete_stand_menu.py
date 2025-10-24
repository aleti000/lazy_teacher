from . import shared
from .delete_user_stand import delete_user_stand as delete_user_func
from .delete_all_user_stands import delete_all_user_stands as delete_all_func

from modules import *

def delete_stand_menu():
    """Delete stand submenu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Удалить стенд пользователя[/green]\n"
            "[green]2. Удалить все стенды из списка пользователей[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Удалить стенд[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

        choice = input("Выберите: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            delete_user_func()
        elif choice == '2':
            delete_all_func()
        else:
            shared.console.print("[red]Недопустимый выбор.[/red]")

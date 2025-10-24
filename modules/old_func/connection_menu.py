from .shared import *

from modules import *

from .create_connection import create_connection
from .display_connections import display_connections
from .delete_connection import delete_connection
def connection_menu():
    """Connection management submenu with styled menu."""
    while True:
        console.clear()
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

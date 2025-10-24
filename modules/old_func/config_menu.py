from . import shared

from modules import *

def config_menu():
    """Configuration management menu with styled menu."""
    while True:
        shared.console.clear()
        shared.console.print(shared.Panel.fit(
            "\n[green]1. Управление подключениями[/green]\n"
            "[green]2. Управление пользователями[/green]\n"
            "[green]3. Управление стендами[/green]\n"
            "[red]0. Назад[/red]",
            title="[bold blue]Меню конфигурации[/bold blue]",
            border_style="blue"
        ))
        shared.console.print()

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
            shared.console.print("[red]Недопустимый выбор.[/red]")

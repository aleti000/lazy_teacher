from .shared import *

from modules import *

from .input_users_manual import input_users_manual
from .import_users import import_users
from .display_user_lists import display_user_lists
from .delete_user_list import delete_user_list
def user_menu():
    """User management menu."""
    while True:
        console.clear()
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

from . import shared
from .delete_user_stand_logic import delete_user_stand_logic as delete_logic_func

from modules import *

def delete_user_stand():
    """Delete stand of a user."""
    user = input("Введите пользователя (например user1@pve): ").strip()
    if '@' not in user:
        user += '@pve'
    with shared.console.status(f"[bold yellow]Удаление стенда {user}...[/bold yellow]", spinner="dots") as status:
        delete_logic_func(user)
    shared.console.print(f"[red]Стенд {user} удален[/red]")

from .shared import *

from modules import *
def display_user_lists():
    """Display all user lists in tables."""
    import glob
    pattern = str(CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    if not files:
        console.print("[yellow]Нет списков пользователей.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return

    for file in files:
        list_name = Path(file).stem.replace('_list', '')
        console.print(f"[bold blue]Список: {list_name}[/bold blue]")
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                users = data.get('users', [])
                if users:
                    table = Table(title="Пользователи", box=None)
                    table.add_column("№", style="magenta", justify="center")
                    table.add_column("Пользователь", style="cyan")
                    for idx, user in enumerate(users, 1):
                        table.add_row(str(idx), user)
                    console.print(table)
                else:
                    console.print("[dim]  Список пуст.[/dim]")
        except Exception as e:
            console.print(f"[red]  Ошибка чтения: {e}[/red]")

    input("Нажмите Enter для продолжения...")


from .shared import *

from modules import *
def delete_user_list():
    """Delete a user list."""
    import glob
    pattern = str(CONFIG_DIR / "*_list.yaml")
    files = glob.glob(pattern)
    if not files:
        console.print("[yellow]Нет списков для удаления.[/yellow]")
        return

    lists = []
    for file in files:
        list_name = Path(file).stem.replace('_list', '')
        lists.append((list_name, file))

    table = Table(title="[bold red]Существующие списки пользователей[/bold red]", box=None)
    table.add_column("№", style="magenta", justify="center")
    table.add_column("Имя списка", style="cyan")
    for i, (name, _) in enumerate(lists, 1):
        table.add_row(str(i), name)
    console.print(table)

    try:
        choice = int(input("Выберите номер для удаления: ")) - 1
        if 0 <= choice < len(lists):
            name, file = lists[choice]
            os.remove(file)
            console.print(f"[green]Список '{name}' удален.[/green]")
            logger.info(f"Удален список пользователей: {name}")
        else:
            console.print("[red]Недопустимый номер.[/red]")
    except ValueError:
        console.print("[red]Введите число.[/red]")


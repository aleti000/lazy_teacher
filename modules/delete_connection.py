from .shared import *

from modules import *
def delete_connection():
    """Delete a connection."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        console.print("[red]Нет сохраненных подключений.[/red]")
        return

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        logger.error(f"Ошибка чтения {config_file}: {e}")
        return

    if not data:
        console.print("[red]Нет подключений.[/red]")
        return

    table = Table(title="[bold red]Существующие подключения[/bold red]", box=None)
    table.add_column("№", style="magenta", justify="center")
    table.add_column("Имя", style="cyan")
    names = list(data.keys())
    for i, name in enumerate(names, 1):
        table.add_row(str(i), name)
    console.print(table)

    try:
        choice = int(input("Выберите номер для удаления: ")) - 1
        if 0 <= choice < len(names):
            deleted = names[choice]
            del data[deleted]
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            console.print(f"[green]Подключение '{deleted}' удалено.[/green]")
            logger.info(f"Удалено подключение: {deleted}")
        else:
            console.print("[red]Недопустимый номер.[/red]")
    except ValueError:
        console.print("[red]Введите число.[/red]")


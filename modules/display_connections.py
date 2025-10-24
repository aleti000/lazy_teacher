from .shared import *

from modules import *
def display_connections():
    """Display all saved connections using Rich table."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        console.print("[red]Нет сохраненных подключений.[/red]")
        return

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        return

    if not data:
        console.print("[red]Нет подключений.[/red]")
        return

    table = Table(title="Сохраненные подключения", box=None)
    table.add_column("Имя", style="cyan", no_wrap=True)
    table.add_column("Хост", style="green")
    table.add_column("Порт", style="magenta")
    table.add_column("Аутентификация", style="yellow")

    for name, conn in data.items():
        auth = "Token" if conn.get('token') else "Пароль"
        table.add_row(name, conn.get('host', ''), str(conn.get('port', '')), auth)

    console.print(table)
    input("Нажмите Enter для продолжения...")


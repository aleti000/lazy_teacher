from .shared import *

from modules import *
def select_default_connection():
    """Select default connection at startup."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        console.print("[red]Ошибка: Файл конфигурации не найден.[/red]")
        console.print("[yellow]Создание нового подключения...[/yellow]")
        create_connection()
        return select_default_connection()  # Recurse to select if created

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
        logger.error(f"Ошибка чтения конфигурации: {e}")
        return None

    if not data:
        console.print("[red]Ошибка: Нет настроенных подключений.[/red]")
        console.print("[yellow]Создание нового подключения...[/yellow]")
        create_connection()
        return select_default_connection()

    names = list(data.keys())
    console.print("[bold blue]Доступные подключения:[/bold blue]")

    # Test all connections and show their status
    connection_status = {}
    for name in names:
        conn = data[name]
        success, message = test_connection(conn, name)
        connection_status[name] = (success, message)
        status_icon = "✓" if success else "✗"
        console.print(f"  {status_icon} {name} ({conn.get('host')}:{conn.get('port')}) - {message}")

    # Filter available connections
    available_connections = [name for name in names if connection_status[name][0]]

    if not available_connections:
        console.print("[red]Ошибка: Нет доступных подключений.[/red]")
        console.print("[yellow]Проверьте настройки подключений или создайте новое.[/yellow]")
        input("Нажмите Enter для продолжения...")
        return None

    console.print()
    console.print("[green]Доступные для использования:[/green]")
    for i, name in enumerate(available_connections, 1):
        console.print(f"{i}. {name}")

    try:
        choice = int(input("Выберите номер подключения: ")) - 1
        if 0 <= choice < len(available_connections):
            selected = available_connections[choice]
            console.print(f"[green]Выбрано активное подключение: {selected}[/green]")
            return selected
        else:
            console.print("[red]Недопустимый номер.[/red]")
            return select_default_connection()
    except ValueError:
        console.print("[red]Введите число.[/red]")
        return select_default_connection()


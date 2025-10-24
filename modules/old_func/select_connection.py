from .shared import *

from modules import *
def select_connection():
    """Select a Proxmox connection."""
    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    if not config_file.exists():
        print("Нет подключений.")
        return None

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

    if not data:
        print("Нет подключений.")
        return None

    print("Выберите подключение:")
    names = list(data.keys())
    for i, name in enumerate(names, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Номер: ")) - 1
        if 0 <= choice < len(names):
            return names[choice]
        else:
            print("Недопустимый.")
    except ValueError:
        print("Введите число.")

    return None


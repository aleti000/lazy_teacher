from .shared import *

from modules import *
def import_users():
    """Import users from file."""
    # Placeholder: assume user inputs file path or use hardcoded
    # In real impl, prompt for file path
    file_path = input("Введите путь к файлу списка пользователей: ").strip()
    if not file_path:
        print("Путь не указан.")
        return

    list_name = input("Введите имя нового списка: ").strip()
    if not list_name:
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        users = []
        for line in lines:
            user = line.strip()
            if user:
                if '@' not in user:
                    user += '@pve'
                users.append(user)
        logger.debug(f"Импортировано пользователей: {len(users)}")

        out_file = CONFIG_DIR / f"{list_name}_list.yaml"
        with open(out_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump({'users': users}, f, default_flow_style=False)
        print(f"Импорт завершен в {out_file}")
        logger.info(f"Импортирован список: {list_name}")
    except Exception as e:
        print(f"Ошибка импорта: {e}")
        logger.error(f"Ошибка импорта из {file_path}: {e}")


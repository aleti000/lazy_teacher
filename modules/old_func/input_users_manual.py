from .shared import *

from modules import *
def input_users_manual():
    """Manually input list of users."""
    list_name = input("Введите имя списка пользователей: ").strip()
    if not list_name:
        return

    users = []
    print("Введите пользователей (оставьте пустым для завершения):")
    while True:
        user = input("Пользователь: ").strip()
        if not user:
            break
        if '@' not in user:
            user += '@pve'
        users.append(user)
        logger.debug(f"Добавлен пользователь: {user}")

    if not users:
        print("Список пустой.")
        return

    file_path = CONFIG_DIR / f"{list_name}_list.yaml"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump({'users': users}, f, default_flow_style=False)
        print(f"Список сохранен в {file_path}")
        logger.info(f"Создан список пользователей: {list_name}")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        logger.error(f"Ошибка сохранения списка {list_name}: {e}")


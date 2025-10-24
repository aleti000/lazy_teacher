from .shared import *

from modules import *
def create_connection():
    """Create a new Proxmox connection."""
    name = input("Введите имя подключения: ").strip()
    if not name:
        print("Имя не может быть пустым.")
        return

    host = input("Введите адрес хоста (IP или домен): ").strip()
    port = input("Введите порт (по умолчанию 8006): ").strip()
    port = port if port else '8006'

    # Validation TODO: check IP format
    if ':' in host:
        host, port = host.split(':', 1)
    host = host.strip()
    port = port.strip()

    auth_type = input("ВЫберете тип аутентификации (1 - token, 2 - пароль): ").strip()
    token = ''
    login = ''
    password = ''

    if auth_type == '1':
        token = input("Введите API token: ").strip()
    elif auth_type == '2':
        login = input("Введите логин: ").strip()
        if '@' not in login:
            login += '@pam'
        password = input("Введите пароль: ").strip()
    else:
        print("Недопустимый выбор.")
        return

    config_file = CONFIG_DIR / 'proxmox_config.yaml'
    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
    except Exception as e:
        print(f"Ошибка чтения существующей конфигурации: {e}")
        logger.error(f"Ошибка чтения {config_file}: {e}")
        return

    data[name] = {
        'host': host,
        'port': port,
        'token': token if auth_type == '1' else '',
        'login': login if auth_type == '2' else '',
        'password': password if auth_type == '2' else ''
    }

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
        print("Подключение сохранено.")
        logger.info(f"Создано подключение: {name}")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        logger.error(f"Ошибка сохранения подключения {name}: {e}")


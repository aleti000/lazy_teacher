from .shared import *

from modules import *
def save_stand(name, stand):
    """Save stand to yaml."""
    file_path = CONFIG_DIR / f"{name}_stand.yaml"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(stand, f, default_flow_style=False)
        print(f"Стенд сохранен в {file_path}")
        logger.info(f"Сохранен стенд: {name}")
    except Exception as e:
        print(f"Ошибка: {e}")
        logger.error(f"Ошибка сохранения стенда {name}: {e}")


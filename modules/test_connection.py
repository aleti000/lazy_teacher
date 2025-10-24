from .shared import *

from modules import *
def test_connection(config_data, conn_name):
    """Test connection to Proxmox server."""
    try:
        if config_data.get('token'):
            proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                token_name=config_data['token'],
                token_value=config_data['token'],
                verify_ssl=False,
                timeout=10
            )
        else:
            proxmoxer.ProxmoxAPI(
                config_data['host'],
                port=int(config_data['port']),
                user=config_data.get('login'),
                password=config_data.get('password'),
                verify_ssl=False,
                timeout=10
            )
        return True, "Подключение успешно"
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            return False, "Ошибка: Превышено время ожидания подключения"
        elif "unauthorized" in error_msg or "authentication" in error_msg:
            return False, "Ошибка: Неправильные учетные данные"
        elif "connection" in error_msg or "network" in error_msg:
            return False, "Ошибка: Не удается подключиться к серверу"
        elif "certificate" in error_msg:
            return False, "Ошибка: Проблема с SSL сертификатом"
        else:
            return False, f"Ошибка подключения: {e}"


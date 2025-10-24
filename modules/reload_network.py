from .shared import *

from modules import *
def reload_network(proxmox, node):
    """Reload network configuration."""
    try:
        proxmox.nodes(node).network.put()
    except Exception as e:
        logger.error(f"Ошибка перезагрузки сети на ноде {node}: {e}")


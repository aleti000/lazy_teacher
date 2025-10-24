from .shared import *

from modules import *
def wait_for_task(proxmox, node, task_id, timeout=300):
    """
    Ожидает завершения задачи Proxmox.
    Возвращает True при успехе, False при ошибке или таймауте.
    """
    import time
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            task_status = proxmox.nodes(node).tasks(task_id).status.get()
            if task_status['status'] == 'stopped':
                if task_status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    print(f"Task failed: {task_status.get('exitstatus')}")
                    return False
        except Exception as e:
            print(f"Error checking task status: {e}")
            return False
        time.sleep(2)
    print("Timeout waiting for task to complete")
    return False


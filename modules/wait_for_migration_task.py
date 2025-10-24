from .shared import *

from modules import *
def wait_for_migration_task(proxmox, node, task_id, timeout=1200):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = proxmox.nodes(node).tasks(task_id).status.get()
            if status['status'] == 'stopped':
                if status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    raise Exception(f"Migration failed: {status.get('exitstatus')}")
        except Exception as e:
            raise Exception(f"Error checking migration task: {e}")
        time.sleep(5)
    raise TimeoutError("Timeout waiting for migration task to complete")


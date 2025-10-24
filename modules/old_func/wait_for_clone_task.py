from .shared import *

from modules import *
def wait_for_clone_task(proxmox, node, task_id, timeout=600):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = proxmox.nodes(node).tasks(task_id).status.get()
            if status['status'] == 'stopped':
                if status.get('exitstatus', '').startswith('OK'):
                    return True
                else:
                    raise Exception(f"Clone failed: {status.get('exitstatus')}")
        except Exception as e:
            raise Exception(f"Error checking clone task: {e}")
        time.sleep(2)
    raise TimeoutError("Timeout waiting for clone task to complete")


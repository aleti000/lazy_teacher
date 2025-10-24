from .shared import *

from modules import *

from .display_stand_vms import display_stand_vms
def remove_vm_from_stand(stand):
    """Remove VM from stand."""
    display_stand_vms(stand)
    if not stand['machines']:
        return

    vm_names = [vm['name'] for vm in stand['machines']]
    print("Выберите VM для удаления:")
    for i, name in enumerate(vm_names, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Номер: ")) - 1
        if 0 <= choice < len(vm_names):
            removed = stand['machines'].pop(choice)
            print(f"Удалена VM: {removed['name']}")
            logger.info(f"Удалена VM: {removed['name']}")
    except ValueError:
        print("Введите число.")

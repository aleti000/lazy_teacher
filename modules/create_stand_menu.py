import os
from . import shared

from modules import *

from .add_vm_to_stand import add_vm_to_stand
from .remove_vm_from_stand import remove_vm_from_stand
from .display_stand_vms import display_stand_vms
from .save_stand import save_stand
def create_stand_menu(conn_name=None):
    """Create stand submenu."""
    stand_name = input("Введите имя стенда: ").strip()
    if not stand_name:
        return

    stand = {'machines': []}
    # Use provided connection name or DEFAULT_CONN
    if conn_name is None:
        conn_name = shared.DEFAULT_CONN

    print(f"DEBUG: conn_name = {conn_name}, DEFAULT_CONN = {shared.DEFAULT_CONN}")

    if not conn_name:
        print("Нет активного подключения.")
        return

    while True:
        os.system('clear')
        print("Создание стенда:", stand_name)
        print("1. Создать VM")
        print("2. Удалить VM из стенда")
        print("3. Отобразить список VM")
        print("4. Сохранить стенд")
        print("0. Назад")

        choice = input("Выберите: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            add_vm_to_stand(stand, conn_name)
        elif choice == '2':
            remove_vm_from_stand(stand)
        elif choice == '3':
            display_stand_vms(stand)
        elif choice == '4':
            save_stand(stand_name, stand)
            break
        else:
            print("Недопустимый выбор.")

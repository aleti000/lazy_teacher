
# Import all functions to make them available in the namespace
from .ui_menus import main_menu, config_menu, connection_menu, user_menu, stand_menu, create_stand_menu, deploy_stand_menu, delete_stand_menu, select_clone_type, select_stand_config, select_user_list
from .connections import create_connection, delete_connection, display_connections, test_connection, select_default_connection, get_proxmox_connection
from .users import input_users_manual, import_users, display_user_lists, delete_user_list
from .stands import add_vm_to_stand, remove_vm_from_stand, display_stand_vms, save_stand, delete_stand_file, display_list_of_stands
from .deletion import delete_user_stand, delete_user_stand_logic, delete_all_user_stands
from .tasks import wait_for_clone_task, wait_for_template_task, wait_for_migration_task, wait_for_task
from .sync_templates import sync_templates
from .network import reload_network
from .deploy_stand_local import deploy_stand_local
from .deploy_stand_distributed import deploy_stand_distributed

#!/usr/bin/env python3
"""
Lazy Teacher Modules Package.
All functions are exported for easy access.
"""

# UI Menus
from .ui_menus import (
    main_menu, config_menu, connection_menu, user_menu, stand_menu,
    create_stand_menu, deploy_stand_menu, delete_stand_menu,
    select_clone_type, select_stand_config, select_user_list,
    create_stands_menu, manage_stands_menu, stand_config_menu,
    user_config_menu, create_stand_config_menu
)

# Connections
from .connections import (
    create_connection, delete_connection, display_connections,
    test_connection, select_default_connection, get_proxmox_connection
)

# Active Users
from .active_users import active_users_menu, display_active_users, select_user

# Stand Management
from .stand_management import stand_management_menu, start_all_vms, stop_all_vms, reset_all_to_snapshot, show_group_status

# Users
from .users import (
    input_users_manual, import_users, display_user_lists, delete_user_list
)

# Stands
from .stands import (
    add_vm_to_stand, remove_vm_from_stand, display_stand_vms,
    save_stand, delete_stand_file, display_list_of_stands
)

# Deletion
from .deletion import (
    delete_user_stand, delete_user_stand_logic, delete_all_user_stands
)

# Tasks
from .tasks import (
    wait_for_clone_task, wait_for_template_task, wait_for_migration_task, wait_for_task
)

# Sync Templates
from .sync_templates import sync_templates, get_template_vmid_for_node

# Network
from .network import reload_network

# Deploy
from .deploy_stand_local import deploy_stand_local
from .deploy_stand_distributed import deploy_stand_distributed

# Templates Registry (new)
from .templates import (
    get_template_registry, save_template_registry,
    get_replica_vmid, get_source_node, register_template,
    register_replica, remove_replica, get_all_nodes_with_template,
    verify_template_on_node, ensure_template_on_node
)

# Groups (new)
from .groups import (
    get_groups, save_groups, create_group, get_group,
    group_exists, delete_group, get_group_users,
    add_user_to_group, remove_user_from_group,
    get_groups_list, get_groups_with_users,
    find_user_group, generate_group_name
)
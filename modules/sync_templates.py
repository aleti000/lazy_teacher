
from . import shared
from .wait_for_clone_task import wait_for_clone_task as wait_clone_func
from .wait_for_template_task import wait_for_template_task as wait_template_func
from .wait_for_migration_task import wait_for_migration_task as wait_migration_func

from modules import *

# Make shared constants available
console = shared.console
logger = shared.logger
def sync_templates(prox, stand, nodes):
    """Sync templates to all nodes, update replicas in stand."""
    import random
    import string
    from collections import defaultdict

    updated = False
    # Group machines by template_vmid to avoid redundant clones
    template_groups = defaultdict(list)
    for machine in stand.get('machines', []):
        template_groups[machine['template_vmid']].append(machine)

    # For each unique template_vmid, sync to all nodes
    for template_vmid, machines in template_groups.items():
        # Use original_node from first machine in group (they should be the same)
        original_machine = machines[0]
        original_node = original_machine['template_node']

        for node in nodes:
            if node == original_node:
                continue  # No need for replica on original

            # Check if any machine in group already has replica on this node
            replica_exists = any(node in machine.get('replicas', {}) for machine in machines)
            if replica_exists:
                # Even if config says replica exists, verify it's actually present and is a template
                if 'replicas' in machines[0]:
                    candidate_vmid = machines[0]['replicas'].get(node)
                    if candidate_vmid:
                        try:
                            vms_on_node = prox.nodes(node).qemu.get()
                            template_present = any(vm['vmid'] == int(candidate_vmid) and vm.get('template') == 1 for vm in vms_on_node)
                            if template_present:
                                continue  # Actually exists, skip
                        except (Exception, ValueError):
                            pass
                # If replica not found or error, remove invalid entry and proceed to create new
                for machine in machines:
                    if 'replicas' in machine and node in machine['replicas']:
                        del machine['replicas'][node]

            # Create full clone on original node once per template_vmid per node
            clone_vmid = prox.cluster.nextid.get()
            # Use template_vmid in name for uniqueness, keep simple no special chars
            safe_name = f"tpl-{original_node}-{template_vmid}"
            clone_task_id = prox.nodes(original_node).qemu(template_vmid).clone.post(
                newid=clone_vmid,
                name=safe_name,
                full=1
            )

            # Wait for clone to complete
            try:
                wait_clone_func(prox, original_node, clone_task_id)
            except Exception as e:
                logger.error(f"Ошибка ожидания клонирования для шаблона {template_vmid}: {e}")
                continue

            # Convert to template
            template_task_id = prox.nodes(original_node).qemu(clone_vmid).template.post()
            wait_template_func(prox, original_node, template_task_id)

            # Migrate to target node
            migrate_result = prox.nodes(original_node).qemu(clone_vmid).migrate.post(
                target=node,
                online=0
            )

            if migrate_result:
                try:
                    migrate_upid = migrate_result['data']
                except TypeError:
                    migrate_upid = migrate_result
                if migrate_upid and wait_migration_func(prox, original_node, migrate_upid):
                    # Migration completed, assign replica to all machines using this template
                    for machine in machines:
                        if 'replicas' not in machine:
                            machine['replicas'] = {}
                        machine['replicas'][node] = clone_vmid
                    console.print(f"[green]Шаблон для {len(machines)} машины(н) с template_vmid {template_vmid} синхронизирован на ноду {node}[/green]")
                    updated = True
                else:
                    logger.error(f"Миграция шаблона для template_vmid {template_vmid} на {node} не удалась")
            else:
                logger.error(f"Не удалось инициировать миграцию шаблона для template_vmid {template_vmid} на {node}")

    return updated

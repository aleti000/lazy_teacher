#!/usr/bin/env python3
"""
Active Users Management module for Lazy Teacher.
Provides functions for displaying and managing active users with their VM pools.
"""

import questionary
from typing import List, Dict, Any, Optional
from . import shared
from .connections import get_proxmox_connection
from .logger import get_logger, OperationTimer
from rich.console import Console

logger = get_logger(__name__)
console = Console()

def _get_vm_status(prox: Any, node: str, vmid: int) -> str:
    """Get VM status from specific node."""
    try:
        vm = prox.nodes(node).qemu(vmid).status.current.get()
        return vm.get('status', 'unknown')
    except Exception as e:
        logger.warning(f"Failed to get status for VM {vmid} on node {node}: {e}")
        return 'error'

def get_active_users_data(prox: Any) -> List[Dict[str, Any]]:
    """
    Get data about active users and their VM pools status.

    Args:
        prox: Proxmox API connection object

    Returns:
        List of dictionaries with pool status information
    """
    active_users = []

    try:
        # Get all pools
        pools = prox.pools.get()
        logger.info(f"Found {len(pools)} pools")

        for pool in pools:
            pool_id = pool['poolid']
            logger.debug(f"Processing pool: {pool_id}")

            try:
                # Get pool details with members
                pool_details = prox.pools(pool_id).get()
                members = pool_details.get('members', [])

                if not members:
                    logger.debug(f"Pool {pool_id} has no members, skipping")
                    continue

                # Count VM statuses
                total_vms = 0
                running_vms = 0

                for member in members:
                    if member['type'] == 'qemu':
                        total_vms += 1
                        status = _get_vm_status(prox, member['node'], member['vmid'])
                        if status == 'running':
                            running_vms += 1
                        logger.debug(f"VM {member['vmid']} on {member['node']}: {status}")

                if running_vms > 0:  # Only include pools with running VMs
                    color = 'green' if running_vms == total_vms else 'yellow'
                    active_users.append({
                        'pool_name': pool_id,
                        'total_vms': total_vms,
                        'running_vms': running_vms,
                        'color': color
                    })
                    logger.info(f"Active pool {pool_id}: {running_vms}/{total_vms} VMs running")

            except Exception as e:
                logger.error(f"Error processing pool {pool_id}: {e}")
                continue

    except Exception as e:
        logger.error(f"Failed to get pools: {e}")
        shared.console.print(f"[red]Ошибка получения пулов: {e}[/red]")
        return []

    # Sort by activity status: full running first (green), then partial (yellow)
    active_users.sort(key=lambda x: (x['color'] == 'yellow', x['pool_name']))

    return active_users

def stop_all_vms_in_pool(prox: Any, pool_name: str) -> bool:
    """
    Stop all running VMs in a specific pool.

    Args:
        prox: Proxmox API connection object
        pool_name: Name of the pool to stop VMs in

    Returns:
        True if all stop operations initiated successfully, False otherwise
    """
    from .tasks import wait_for_task

    logger.info(f"Starting stop operation for pool: {pool_name}")
    shared.console.print(f"[cyan]Останавливаем все VM в пуле '{pool_name}'...[/cyan]")

    try:
        pool_details = prox.pools(pool_name).get()
        members = pool_details.get('members', [])
        stop_tasks = []

        for member in members:
            if member['type'] == 'qemu':
                node = member['node']
                vmid = member['vmid']
                status = _get_vm_status(prox, node, vmid)

                if status == 'running':
                    logger.info(f"Stopping VM {vmid} on node {node}")
                    try:
                        result = prox.nodes(node).qemu(vmid).status.stop.post()
                        stop_tasks.append((node, result))
                        shared.console.print(f" - [yellow]✓ Отправлен сигнал остановки VM {vmid} на ноде {node}[/yellow]")
                    except Exception as e:
                        logger.error(f"Failed to stop VM {vmid}: {e}")
                        shared.console.print(f" - [red]✗ Ошибка остановки VM {vmid} на ноде {node}: {e}[/red]")
                else:
                    shared.console.print(f" - [dim]VM {vmid} на ноде {node} уже остановлена (статус: {status})[/dim]")

        # Wait for stop tasks to complete
        if stop_tasks:
            shared.console.print("[cyan]Ожидание завершения операций остановки...[/cyan]")
            for node, task_id in stop_tasks:
                try:
                    wait_for_task(prox, node, task_id)
                    shared.console.print(f" - [green]✓ Операция на ноде {node} завершена[/green]")
                except Exception as e:
                    logger.error(f"Stop task wait failed on node {node}: {e}")
                    shared.console.print(f" - [red]✗ Ошибка ожидания завершения на ноде {node}: {e}[/red]")

        shared.console.print(f"[green]Операция остановки для пула '{pool_name}' завершена[/green]")
        return True

    except Exception as e:
        logger.error(f"Error stopping VMs in pool {pool_name}: {e}")
        shared.console.print(f"[red]Ошибка остановки VM в пуле '{pool_name}': {e}[/red]")
        return False

def manage_active_users():
    """Main function for managing active users - displays menu and handles selection."""
    with OperationTimer(logger, "Manage active users"):
        shared.console.clear()

        try:
            # Get Proxmox connection
            prox = get_proxmox_connection()
        except Exception as e:
            shared.console.print(f"[red]Ошибка подключения к Proxmox: {e}[/red]")
            input("Нажмите Enter для продолжения...")
            return

        while True:
            # Get current active users data
            active_users = get_active_users_data(prox)

            if not active_users:
                shared.console.print("[yellow]Нет активных пользователей с запущенными VM.[/yellow]")
                shared.console.print()
                if questionary.select("Действия:", ["Обновить", "Назад"]).ask() == "Назад":
                    break
                continue

            # Prepare choices for menu
            choices = []
            choice_to_pool = {}
            indicators = {'green': '●', 'yellow': '○'}

            for user in active_users:
                pool_name = user['pool_name']
                total = user['total_vms']
                running = user['running_vms']
                indicator = indicators[user['color']]

                # Format: "● username (running/total)" or "○ username (running/total)"
                choice_text = f"{indicator} {pool_name} ({running}/{total})"
                choices.append(choice_text)
                choice_to_pool[choice_text] = pool_name

            choices.append("Назад")

            # Show menu
            shared.console.clear()
            shared.console.print("[bold blue]Активные пользователи[/bold blue]")
            shared.console.print("[green]● Все VM запущены  [yellow]○ Частично запущены[/yellow]")
            shared.console.print()

            selected = questionary.select("Выберите пользователя для управления:", choices).ask()

            if selected == "Назад":
                break

            # Get pool name from the mapping
            pool_name = choice_to_pool[selected]

            # Confirm stop operation
            confirm = questionary.confirm(
                f"Остановить ВСЕ VMs в пуле '{pool_name}'?",
                default=False
            ).ask()

            if confirm:
                success = stop_all_vms_in_pool(prox, pool_name)
                if success:
                    shared.console.print(f"[green]Операция для пула '{pool_name}' завершена успешно.[/green]")
                else:
                    shared.console.print(f"[red]Операция для пула '{pool_name}' завершилась с ошибками.[/red]")
            else:
                shared.console.print("[dim]Операция отменена.[/dim]")

            # Continue showing menu after operation
            input("\nНажмите Enter для продолжения...")

        logger.info("Finished managing active users")

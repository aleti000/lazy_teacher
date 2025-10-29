#!/usr/bin/env python3
"""
Stand Management module for Lazy Teacher.
Provides unified management for stand deployment and deletion.
"""

import questionary
from . import shared
from .connections import get_proxmox_connection
from .logger import get_logger, OperationTimer
def show_help(section="stands"):
    """Display contextual help for stand management."""
    from . import shared
    shared.console.clear()

    help_text = """
[bold blue]Справка: Управление стендами[/bold blue]

Развертывание и управление виртуальными стендами на Proxmox VE.

[bold green]Опции:[/bold green]
- [cyan]Развернуть стенд[/cyan]: развертывание стенда в кластере
  - Выберите конфигурацию стенда из сохраненных
  - Укажите список пользователей для развертывания
  - Выберите тип развертывания (локальная/распределенная)
  - Система создаст пользователей, пулы, VM, сети автоматически

- [cyan]Удалить стенд[/cyan]: удаление развернутых стендов
  - Удалите стенд конкретного пользователя
  - Или удалите все стенды для группы пользователей

[bold blue]Создание стенда:[/bold blue]
1. Выберите "Создать стенд" в меню управления стендами (через конфигурацию)
2. Введите имя стенда
3. Дизайн конфигурации VM:
   - Выберите шаблон для клонирования
   - Настройте устройства (linux/ecorouter)
   - Добавьте сетевые интерфейсы (bridge:.vlan или **bridge)

[bold blue]Bridge (сетевые мосты):[/bold blue]
- **bridge: конкретный bridge по имени (например, **vmbr0)
- bridge: bridge по alias с автоматическим созданием
- bridge.vlan: bridge с VLAN поддержкой
- Система управляет нумерацией bridge автоматически и создает их в кластере

[bold blue]Развертывание:[/bold blue]
- Для каждого пользователя создается пул VM с полными правами
- VM клонируются из выбранных шаблонов
- Применяются сетевые конфигурации с созданными bridge
- Создаются snapshot "start" для последующего отката

[bold cyan]Советы:[/bold cyan]
- Перед развертыванием убедитесь в наличии шаблонов
- Bridge создаются автоматически для изоляции пользователей
- Выход из создания стенда сохраняет его без развертывания
        """

    shared.console.print(help_text)
    input("\nНажмите Enter для продолжения...")
    return

logger = get_logger(__name__)

def manage_stands():
    """Unified function for managing stands - deployment and deletion."""
    with OperationTimer(logger, "Manage stands"):
        while True:
            shared.console.clear()
            choices = [
                "Развернуть стенд",
                "Удалить стенд",
                "Помощь",
                "Назад"
            ]

            choice = questionary.select("Управление стендами", choices=choices).ask()

            if choice == "Назад":
                break
            elif choice == "Развернуть стенд":
                deploy_stand_menu()
            elif choice == "Удалить стенд":
                delete_stand_menu()
            elif choice == "Помощь":
                show_help("stands")

        logger.info("Finished stand management")

def deploy_stand_menu():
    """Interact with deploy options."""
    import modules.ui_menus
    modules.ui_menus.deploy_stand_menu()

def delete_stand_menu():
    """Interact with delete options."""
    import modules.ui_menus
    modules.ui_menus.delete_stand_menu()

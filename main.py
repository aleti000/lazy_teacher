#!/usr/bin/env python3
"""
Lazy Teacher - Main entry point.
Automated management system for Proxmox VE virtual stands.
"""

import sys
import os
from modules import shared
from modules.connections import create_connection, _load_config, test_connection
from modules.ui_menus import main_menu


def clear_screen():
    """Clear the console screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def print_header():
    """Print application header."""
    print()
    print("=" * 50)
    print("  ⚡ LAZY TEACHER - Управление Proxmox стендами")
    print("=" * 50)
    print()


def select_connection_menu():
    """
    Display connection selection menu at startup.
    Shows available connections or prompts to create new one.
    """
    clear_screen()
    print_header()
    
    # Load existing connections
    config = _load_config()
    
    if not config:
        # No connections - prompt to create
        print("[!] Нет настроенных подключений.")
        print()
        
        create_new = input("Создать новое подключение к Proxmox VE? (y/n): ").strip().lower()
        
        if create_new == 'y':
            conn_name = create_connection()
            if conn_name:
                return conn_name
            else:
                print("[!] Не удалось создать подключение.")
                sys.exit(1)
        else:
            print("[!] Без подключения работа невозможна.")
            sys.exit(1)
    
    # Have connections - show selection
    print("Доступные подключения:")
    print("-" * 40)
    
    names = list(config.keys())
    for i, name in enumerate(names, 1):
        conn = config[name]
        print(f"  [{i}] {name} ({conn.get('host')}:{conn.get('port')})")
    print(f"  [{len(names)+1}] Создать новое подключение")
    print(f"  [0] Выход")
    print()
    
    try:
        choice = input("Выберите подключение: ").strip()
        
        if choice == '0':
            sys.exit(0)
        
        idx = int(choice) - 1
        if idx == len(names):
            # Create new
            conn_name = create_connection()
            if conn_name:
                return conn_name
            else:
                return select_connection_menu()
        elif 0 <= idx < len(names):
            selected = names[idx]
            
            # Test connection
            print(f"\n[*] Проверка подключения к {selected}...")
            success, message = test_connection(config[selected], selected)
            
            if success:
                print(f"[+] Подключение к {selected} успешно")
                return selected
            else:
                print(f"[!] {message}")
                retry = input("Попробовать другое подключение? (y/n): ").strip().lower()
                if retry == 'y':
                    return select_connection_menu()
                else:
                    sys.exit(1)
        else:
            print("[!] Неверный выбор")
            return select_connection_menu()
            
    except ValueError:
        print("[!] Введите число")
        return select_connection_menu()
    except (EOFError, KeyboardInterrupt):
        print("\n[!] Отменено")
        sys.exit(1)


def main():
    """Main entry point."""
    # Select connection first
    shared.DEFAULT_CONN = select_connection_menu()
    
    print()
    print(f"[+] Активное подключение: {shared.DEFAULT_CONN}")
    input("Нажмите Enter для продолжения...")
    
    # Enter main menu
    main_menu()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3

import modules

if __name__ == "__main__":
    print(f"DEFAULT_CONN before: {modules.shared.DEFAULT_CONN}")
    modules.shared.DEFAULT_CONN = modules.select_default_connection()
    print(f"DEFAULT_CONN after: {modules.shared.DEFAULT_CONN}")
    modules.main_menu()

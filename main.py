#!/usr/bin/env python3

import modules

if __name__ == "__main__":
    modules.shared.DEFAULT_CONN = modules.select_default_connection()
    modules.main_menu()

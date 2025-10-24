from .shared import *

from modules import *
def display_list_of_stands():
    """Display list of saved stands."""
    import glob
    pattern = str(CONFIG_DIR / "*_stand.yaml")
    files = glob.glob(pattern)
    if not files:
        print("Нет сохраненных стендов.")
        input("Нажмите Enter для продолжения...")
        return

    print("Список стендов:")
    for name in files:
        stand_name = Path(name).stem.replace('_stand', '')
        print(f"- {stand_name}")

    input("Нажмите Enter для продолжения...")


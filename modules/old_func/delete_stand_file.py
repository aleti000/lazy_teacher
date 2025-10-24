from .shared import *

from modules import *
def delete_stand_file():
    """Delete a stand file."""
    import glob
    pattern = str(CONFIG_DIR / "*_stand.yaml")
    files = glob.glob(pattern)
    if not files:
        print("Нет стендов для удаления.")
        input("Нажмите Enter для продолжения...")
        return

    stands = []
    for file in files:
        stand_name = Path(file).stem.replace('_stand', '')
        stands.append((stand_name, file))

    print("Существующие стенды:")
    for i, (name, _) in enumerate(stands, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Выберите номер для удаления: ")) - 1
        if 0 <= choice < len(stands):
            name, file = stands[choice]
            os.remove(file)
            print("Стенд удален.")
            logger.info(f"Удален стенд: {name}")
        else:
            print("Недопустимый номер.")
    except ValueError:
        print("Введите число.")


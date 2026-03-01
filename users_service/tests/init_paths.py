# users_service/tests/init_paths.py
import sys
import pathlib

# Вычисляем пути относительно текущего файла
# Структура: .../smart-budget-backend/users_service/tests/init_paths.py
CURRENT_FILE = pathlib.Path(__file__).resolve()

# Папка 'users_service' (тут лежит папка app)
SERVICE_ROOT = CURRENT_FILE.parent.parent
# Корень проекта (тут лежит папка shared)
PROJECT_ROOT = SERVICE_ROOT.parent

# Добавляем пути в sys.path, если их там нет
# Это позволит делать: from app...
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

# Это позволит делать: from shared...
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

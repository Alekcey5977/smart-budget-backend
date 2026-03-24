import pathlib
import sys

# Вычисляем пути относительно текущего файла
# Структура: .../smart-budget-backend/transaction_service/tests/init_paths.py
CURRENT_FILE = pathlib.Path(__file__).resolve()

# Папка 'transaction_service' (тут лежит папка app)
SERVICE_ROOT = CURRENT_FILE.parent.parent
# Корень проекта (тут лежит папка shared)
PROJECT_ROOT = SERVICE_ROOT.parent

# Добавляем пути в sys.path, если их там нет
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

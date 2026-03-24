"""
Скрипт для генерации тестовых данных для псевдо банка.
Создает данные с правильными хешами счетов.
"""
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Загружаем .env файл
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Секретный ключ для хеширования (берем из .env)
BANK_SECRET_KEY = os.getenv('BANK_SECRET_KEY', 'bank-account-secure-key-2026')


def get_bank_account_hash(account_number: str) -> str:
    """Хеширование номера счета (аналогично users_service/app/auth.py)"""
    secret_key = BANK_SECRET_KEY.encode("utf-8")
    return hmac.new(
        secret_key,
        account_number.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


# Тестовые номера счетов (реальный формат российских счетов)
TEST_ACCOUNTS = [
    {
        "number": "40817810099910004312",
        "name": "Основная карта",
        "bank_id": 1,
        "user_id": 999,
        "balance": "125450.75"
    },
    {
        "number": "40817810099910004313",
        "name": "Накопительная",
        "bank_id": 4,
        "user_id": 999,
        "balance": "50000.00"
    },
    {
        "number": "40817810099910004314",
        "name": "Зарплатная",
        "bank_id": 2,
        "user_id": 998,
        "balance": "78230.50"
    },
    {
        "number": "40817810099910004315",
        "name": "Повседневная",
        "bank_id": 3,
        "user_id": 997,
        "balance": "23100.00"
    },
    # Новые счета
    {
        "number": "40817810099910004316",
        "name": "Кредитная карта",
        "bank_id": 1,
        "user_id": 996,
        "balance": "45000.00"
    },
    {
        "number": "40817810099910004317",
        "name": "Валютный счет",
        "bank_id": 5,
        "user_id": 996,
        "balance": "1500.00"
    },
    {
        "number": "40817810099910004318",
        "name": "Семейная карта",
        "bank_id": 4,
        "user_id": 995,
        "balance": "87500.25"
    },
    {
        "number": "40817810099910004319",
        "name": "Бизнес счет",
        "bank_id": 3,
        "user_id": 995,
        "balance": "250000.00"
    },
    {
        "number": "40817810099910004320",
        "name": "Детская карта",
        "bank_id": 1,
        "user_id": 994,
        "balance": "5000.00"
    },
    {
        "number": "40817810099910004321",
        "name": "Премиум карта",
        "bank_id": 2,
        "user_id": 994,
        "balance": "500000.00"
    }
]


def generate_test_data():
    """Генерация всех тестовых данных"""

    # Категории
    categories = [
        {"id": 1, "name": "Продукты"},
        {"id": 2, "name": "Транспорт"},
        {"id": 3, "name": "Развлечения"},
        {"id": 4, "name": "Здоровье"},
        {"id": 5, "name": "Образование"},
        {"id": 6, "name": "Рестораны"},
        {"id": 7, "name": "Одежда"},
        {"id": 8, "name": "Коммунальные услуги"},
        {"id": 9, "name": "Связь"},
        {"id": 10, "name": "Путешествия"},
        {"id": 11, "name": "Зарплата"},
        {"id": 12, "name": "Подработка"},
        {"id": 13, "name": "Инвестиции"},
        {"id": 14, "name": "Подарки"},
        {"id": 15, "name": "Спорт"}
    ]

    # MCC категории
    mcc_categories = [
        {"mcc": 5411, "name": "Супермаркеты", "category_id": 1},
        {"mcc": 5812, "name": "Рестораны", "category_id": 6},
        {"mcc": 4121, "name": "Такси", "category_id": 2},
        {"mcc": 5541, "name": "Заправки", "category_id": 2},
        {"mcc": 7832, "name": "Кинотеатры", "category_id": 3},
        {"mcc": 8011, "name": "Медицина", "category_id": 4},
        {"mcc": 8220, "name": "Университеты", "category_id": 5},
        {"mcc": 5651, "name": "Одежда", "category_id": 7},
        {"mcc": 4900, "name": "Коммунальные", "category_id": 8},
        {"mcc": 4814, "name": "Мобильная связь", "category_id": 9},
        {"mcc": 4511, "name": "Авиабилеты", "category_id": 10},
        {"mcc": 5941, "name": "Спорттовары", "category_id": 15}
    ]

    # Мерчанты
    merchants = [
        {"id": 1, "name": "Пятёрочка", "inn": "5024045632", "category_id": 1},
        {"id": 2, "name": "Магнит", "inn": "2310031475", "category_id": 1},
        {"id": 3, "name": "Перекрёсток", "inn": "7703270067", "category_id": 1},
        {"id": 4, "name": "Лента", "inn": "7814148471", "category_id": 1},
        {"id": 5, "name": "Яндекс.Такси", "inn": "7704340327", "category_id": 2},
        {"id": 6, "name": "Лукойл", "inn": "7708004767", "category_id": 2},
        {"id": 7, "name": "Газпром", "inn": "7736050003", "category_id": 2},
        {"id": 8, "name": "Макдоналдс", "inn": "7704217160", "category_id": 6},
        {"id": 9, "name": "KFC", "inn": "7703270067", "category_id": 6},
        {"id": 10, "name": "Бургер Кинг", "inn": "7714617793", "category_id": 6},
        {"id": 11, "name": "Додо Пицца", "inn": "5260250585", "category_id": 6},
        {"id": 12, "name": "Кинотеатр Синема Парк", "inn": "7702045093", "category_id": 3},
        {"id": 13, "name": "Спортмастер", "inn": "7707619048", "category_id": 15},
        {"id": 14, "name": "Decathlon", "inn": "7705485928", "category_id": 15},
        {"id": 15, "name": "H&M", "inn": "7706697844", "category_id": 7},
        {"id": 16, "name": "Zara", "inn": "7704821201", "category_id": 7},
        {"id": 17, "name": "Wildberries", "inn": "7721546864", "category_id": 7},
        {"id": 18, "name": "Ozon", "inn": "7704217370", "category_id": 7},
        {"id": 19, "name": "МТС", "inn": "7740000076", "category_id": 9},
        {"id": 20, "name": "Билайн", "inn": "7713076301", "category_id": 9},
        {"id": 21, "name": "Мегафон", "inn": "7812014560", "category_id": 9},
        {"id": 22, "name": "Аэрофлот", "inn": "7712040126", "category_id": 10},
        {"id": 23, "name": "S7 Airlines", "inn": "7312012111", "category_id": 10},
        {"id": 24, "name": "Booking.com", "inn": "NL000000001", "category_id": 10},
        {"id": 25, "name": "ООО РомашкаСофт", "inn": "7701234567", "category_id": 11}
    ]

    # Банки
    banks = [
        {"id": 1, "name": "Сбербанк"},
        {"id": 2, "name": "ВТБ"},
        {"id": 3, "name": "Альфа-Банк"},
        {"id": 4, "name": "Тинькофф"},
        {"id": 5, "name": "Райффайзен"}
    ]

    # Банковские счета с хешами
    bank_accounts = []
    account_id_counter = 1
    for acc in TEST_ACCOUNTS:
        bank_accounts.append({
            "id": account_id_counter,
            "user_id": acc["user_id"],
            "bank_account_hash": get_bank_account_hash(acc["number"]),
            "bank_account_name": acc["name"],
            "bank_id": acc["bank_id"],
            "currency": "RUB",
            "balance": acc["balance"]
        })
        account_id_counter += 1

    # Генерация транзакций
    base_date = datetime(2026, 1, 5, 10, 0, 0)
    transactions = []

    # Транзакции для user_id = 999, account_id = 1
    transactions.extend([
        {
            "user_id": 999,
            "category_id": 11,
            "bank_account_id": 1,
            "amount": "85000.00",
            "type": "income",
            "description": "Зарплата за январь 2026",
            "merchant_id": 25,
            "created_at": base_date.isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 1,
            "bank_account_id": 1,
            "amount": "2450.50",
            "type": "expense",
            "description": "Покупка продуктов",
            "merchant_id": 1,
            "created_at": (base_date + timedelta(days=1, hours=8, minutes=30)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 1,
            "bank_account_id": 1,
            "amount": "1850.00",
            "type": "expense",
            "description": "Покупка продуктов",
            "merchant_id": 2,
            "created_at": (base_date + timedelta(days=2, hours=2, minutes=15)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 2,
            "bank_account_id": 1,
            "amount": "350.00",
            "type": "expense",
            "description": "Поездка на такси",
            "merchant_id": 5,
            "created_at": (base_date + timedelta(days=2, hours=10, minutes=45)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 6,
            "bank_account_id": 1,
            "amount": "1250.00",
            "type": "expense",
            "description": "Обед в ресторане",
            "merchant_id": 8,
            "created_at": (base_date + timedelta(days=3, hours=4)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 2,
            "bank_account_id": 1,
            "amount": "2100.00",
            "type": "expense",
            "description": "Заправка автомобиля",
            "merchant_id": 6,
            "created_at": (base_date + timedelta(days=3, hours=9, minutes=30)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 1,
            "bank_account_id": 1,
            "amount": "3200.75",
            "type": "expense",
            "description": "Покупка продуктов",
            "merchant_id": 3,
            "created_at": (base_date + timedelta(days=4, hours=1)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 3,
            "bank_account_id": 1,
            "amount": "800.00",
            "type": "expense",
            "description": "Билеты в кино",
            "merchant_id": 12,
            "created_at": (base_date + timedelta(days=4, hours=9)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 6,
            "bank_account_id": 1,
            "amount": "2500.00",
            "type": "expense",
            "description": "Ужин в ресторане",
            "merchant_id": 11,
            "created_at": (base_date + timedelta(days=4, hours=11)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 9,
            "bank_account_id": 1,
            "amount": "650.00",
            "type": "expense",
            "description": "Оплата мобильной связи",
            "merchant_id": 19,
            "created_at": (base_date + timedelta(days=5)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 1,
            "bank_account_id": 1,
            "amount": "1950.00",
            "type": "expense",
            "description": "Покупка продуктов",
            "merchant_id": 4,
            "created_at": (base_date + timedelta(days=5, hours=7)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 7,
            "bank_account_id": 1,
            "amount": "4500.00",
            "type": "expense",
            "description": "Покупка одежды",
            "merchant_id": 15,
            "created_at": (base_date + timedelta(days=6, hours=5, minutes=30)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 2,
            "bank_account_id": 1,
            "amount": "450.00",
            "type": "expense",
            "description": "Поездка на такси",
            "merchant_id": 5,
            "created_at": (base_date + timedelta(days=6, hours=12)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 12,
            "bank_account_id": 1,
            "amount": "15000.00",
            "type": "income",
            "description": "Фриланс проект",
            "merchant_id": None,
            "created_at": (base_date + timedelta(days=7, hours=1)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 15,
            "bank_account_id": 1,
            "amount": "3500.00",
            "type": "expense",
            "description": "Спортивная экипировка",
            "merchant_id": 13,
            "created_at": (base_date + timedelta(days=7, hours=3)).isoformat() + "Z"
        }
    ])

    # Транзакции для user_id = 998, account_id = 3
    transactions.extend([
        {
            "user_id": 998,
            "category_id": 11,
            "bank_account_id": 3,
            "amount": "95000.00",
            "type": "income",
            "description": "Зарплата за январь 2026",
            "merchant_id": 25,
            "created_at": base_date.isoformat() + "Z"
        },
        {
            "user_id": 998,
            "category_id": 8,
            "bank_account_id": 3,
            "amount": "4500.00",
            "type": "expense",
            "description": "Коммунальные платежи",
            "merchant_id": None,
            "created_at": (base_date + timedelta(days=1)).isoformat() + "Z"
        },
        {
            "user_id": 998,
            "category_id": 1,
            "bank_account_id": 3,
            "amount": "3200.00",
            "type": "expense",
            "description": "Покупка продуктов",
            "merchant_id": 1,
            "created_at": (base_date + timedelta(days=1, hours=8)).isoformat() + "Z"
        },
        {
            "user_id": 998,
            "category_id": 2,
            "bank_account_id": 3,
            "amount": "2500.00",
            "type": "expense",
            "description": "Заправка",
            "merchant_id": 7,
            "created_at": (base_date + timedelta(days=2)).isoformat() + "Z"
        },
        {
            "user_id": 998,
            "category_id": 6,
            "bank_account_id": 3,
            "amount": "1800.00",
            "type": "expense",
            "description": "Обед",
            "merchant_id": 9,
            "created_at": (base_date + timedelta(days=2, hours=3)).isoformat() + "Z"
        },
        {
            "user_id": 998,
            "category_id": 7,
            "bank_account_id": 3,
            "amount": "8500.00",
            "type": "expense",
            "description": "Онлайн покупка одежды",
            "merchant_id": 17,
            "created_at": (base_date + timedelta(days=3, hours=6)).isoformat() + "Z"
        },
        {
            "user_id": 998,
            "category_id": 1,
            "bank_account_id": 3,
            "amount": "2700.00",
            "type": "expense",
            "description": "Покупка продуктов",
            "merchant_id": 2,
            "created_at": (base_date + timedelta(days=4, hours=9)).isoformat() + "Z"
        },
        {
            "user_id": 998,
            "category_id": 4,
            "bank_account_id": 3,
            "amount": "3500.00",
            "type": "expense",
            "description": "Визит к врачу",
            "merchant_id": None,
            "created_at": (base_date + timedelta(days=5, hours=1)).isoformat() + "Z"
        },
        {
            "user_id": 998,
            "category_id": 9,
            "bank_account_id": 3,
            "amount": "800.00",
            "type": "expense",
            "description": "Оплата интернета",
            "merchant_id": 20,
            "created_at": (base_date + timedelta(days=5, hours=4)).isoformat() + "Z"
        }
    ])

    # Транзакции для user_id = 997, account_id = 4
    transactions.extend([
        {
            "user_id": 997,
            "category_id": 11,
            "bank_account_id": 4,
            "amount": "65000.00",
            "type": "income",
            "description": "Зарплата за январь 2026",
            "merchant_id": 25,
            "created_at": base_date.isoformat() + "Z"
        },
        {
            "user_id": 997,
            "category_id": 1,
            "bank_account_id": 4,
            "amount": "1500.00",
            "type": "expense",
            "description": "Покупка продуктов",
            "merchant_id": 1,
            "created_at": (base_date + timedelta(days=1, hours=7)).isoformat() + "Z"
        },
        {
            "user_id": 997,
            "category_id": 6,
            "bank_account_id": 4,
            "amount": "950.00",
            "type": "expense",
            "description": "Кофе и снеки",
            "merchant_id": 8,
            "created_at": (base_date + timedelta(days=2, hours=2)).isoformat() + "Z"
        },
        {
            "user_id": 997,
            "category_id": 2,
            "bank_account_id": 4,
            "amount": "300.00",
            "type": "expense",
            "description": "Такси",
            "merchant_id": 5,
            "created_at": (base_date + timedelta(days=2, hours=10)).isoformat() + "Z"
        },
        {
            "user_id": 997,
            "category_id": 1,
            "bank_account_id": 4,
            "amount": "2100.00",
            "type": "expense",
            "description": "Покупка продуктов",
            "merchant_id": 3,
            "created_at": (base_date + timedelta(days=3, hours=8, minutes=30)).isoformat() + "Z"
        },
        {
            "user_id": 997,
            "category_id": 7,
            "bank_account_id": 4,
            "amount": "5500.00",
            "type": "expense",
            "description": "Покупка обуви и одежды",
            "merchant_id": 16,
            "created_at": (base_date + timedelta(days=4, hours=4)).isoformat() + "Z"
        },
        {
            "user_id": 997,
            "category_id": 3,
            "bank_account_id": 4,
            "amount": "1200.00",
            "type": "expense",
            "description": "Развлечения",
            "merchant_id": 12,
            "created_at": (base_date + timedelta(days=5, hours=9)).isoformat() + "Z"
        }
    ])

    # Транзакции для user_id = 999, account_id = 2 (накопительная)
    transactions.extend([
        {
            "user_id": 999,
            "category_id": 1,
            "bank_account_id": 2,
            "amount": "1200.00",
            "type": "expense",
            "description": "Покупка продуктов",
            "merchant_id": 1,
            "created_at": (base_date + timedelta(days=1, hours=6)).isoformat() + "Z"
        },
        {
            "user_id": 999,
            "category_id": 13,
            "bank_account_id": 2,
            "amount": "10000.00",
            "type": "income",
            "description": "Дивиденды",
            "merchant_id": None,
            "created_at": (base_date + timedelta(days=5, hours=2)).isoformat() + "Z"
        }
    ])

    # Транзакции для user_id = 996, account_id = 5 (кредитная карта)
    transactions.extend([
        {
            "user_id": 996,
            "category_id": 11,
            "bank_account_id": 5,
            "amount": "75000.00",
            "type": "income",
            "description": "Зарплата за январь 2026",
            "merchant_id": 25,
            "created_at": base_date.isoformat() + "Z"
        },
        {
            "user_id": 996,
            "category_id": 7,
            "bank_account_id": 5,
            "amount": "12500.00",
            "type": "expense",
            "description": "Покупка одежды онлайн",
            "merchant_id": 17,
            "created_at": (base_date + timedelta(days=2, hours=14)).isoformat() + "Z"
        },
        {
            "user_id": 996,
            "category_id": 10,
            "bank_account_id": 5,
            "amount": "35000.00",
            "type": "expense",
            "description": "Авиабилеты в Сочи",
            "merchant_id": 22,
            "created_at": (base_date + timedelta(days=3, hours=10)).isoformat() + "Z"
        }
    ])

    # Транзакции для user_id = 996, account_id = 6 (валютный счет)
    transactions.extend([
        {
            "user_id": 996,
            "category_id": 13,
            "bank_account_id": 6,
            "amount": "500.00",
            "type": "income",
            "description": "Пополнение валютного счета",
            "merchant_id": None,
            "created_at": (base_date + timedelta(days=1)).isoformat() + "Z"
        }
    ])

    # Транзакции для user_id = 995, account_id = 7 (семейная карта)
    transactions.extend([
        {
            "user_id": 995,
            "category_id": 11,
            "bank_account_id": 7,
            "amount": "120000.00",
            "type": "income",
            "description": "Зарплата за январь 2026",
            "merchant_id": 25,
            "created_at": base_date.isoformat() + "Z"
        },
        {
            "user_id": 995,
            "category_id": 1,
            "bank_account_id": 7,
            "amount": "8500.00",
            "type": "expense",
            "description": "Большая закупка продуктов",
            "merchant_id": 4,
            "created_at": (base_date + timedelta(days=1, hours=11)).isoformat() + "Z"
        },
        {
            "user_id": 995,
            "category_id": 5,
            "bank_account_id": 7,
            "amount": "15000.00",
            "type": "expense",
            "description": "Оплата курсов",
            "merchant_id": None,
            "created_at": (base_date + timedelta(days=2)).isoformat() + "Z"
        },
        {
            "user_id": 995,
            "category_id": 4,
            "bank_account_id": 7,
            "amount": "4500.00",
            "type": "expense",
            "description": "Аптека",
            "merchant_id": None,
            "created_at": (base_date + timedelta(days=3, hours=16)).isoformat() + "Z"
        }
    ])

    # Транзакции для user_id = 995, account_id = 8 (бизнес счет)
    transactions.extend([
        {
            "user_id": 995,
            "category_id": 12,
            "bank_account_id": 8,
            "amount": "180000.00",
            "type": "income",
            "description": "Оплата от клиента за проект",
            "merchant_id": None,
            "created_at": (base_date + timedelta(days=2)).isoformat() + "Z"
        },
        {
            "user_id": 995,
            "category_id": 9,
            "bank_account_id": 8,
            "amount": "2500.00",
            "type": "expense",
            "description": "Корпоративная связь",
            "merchant_id": 19,
            "created_at": (base_date + timedelta(days=3)).isoformat() + "Z"
        }
    ])

    # Транзакции для user_id = 994, account_id = 9 (детская карта)
    transactions.extend([
        {
            "user_id": 994,
            "category_id": 14,
            "bank_account_id": 9,
            "amount": "5000.00",
            "type": "income",
            "description": "Карманные деньги",
            "merchant_id": None,
            "created_at": base_date.isoformat() + "Z"
        },
        {
            "user_id": 994,
            "category_id": 1,
            "bank_account_id": 9,
            "amount": "350.00",
            "type": "expense",
            "description": "Снеки",
            "merchant_id": 1,
            "created_at": (base_date + timedelta(days=1, hours=15)).isoformat() + "Z"
        },
        {
            "user_id": 994,
            "category_id": 3,
            "bank_account_id": 9,
            "amount": "800.00",
            "type": "expense",
            "description": "Кино с друзьями",
            "merchant_id": 12,
            "created_at": (base_date + timedelta(days=3, hours=18)).isoformat() + "Z"
        }
    ])

    # Транзакции для user_id = 994, account_id = 10 (премиум карта)
    transactions.extend([
        {
            "user_id": 994,
            "category_id": 11,
            "bank_account_id": 10,
            "amount": "350000.00",
            "type": "income",
            "description": "Зарплата за январь 2026",
            "merchant_id": 25,
            "created_at": base_date.isoformat() + "Z"
        },
        {
            "user_id": 994,
            "category_id": 10,
            "bank_account_id": 10,
            "amount": "85000.00",
            "type": "expense",
            "description": "Бронирование отеля",
            "merchant_id": 24,
            "created_at": (base_date + timedelta(days=2, hours=20)).isoformat() + "Z"
        },
        {
            "user_id": 994,
            "category_id": 7,
            "bank_account_id": 10,
            "amount": "45000.00",
            "type": "expense",
            "description": "Премиум одежда",
            "merchant_id": 16,
            "created_at": (base_date + timedelta(days=4, hours=12)).isoformat() + "Z"
        },
        {
            "user_id": 994,
            "category_id": 6,
            "bank_account_id": 10,
            "amount": "12000.00",
            "type": "expense",
            "description": "Ресторан",
            "merchant_id": 11,
            "created_at": (base_date + timedelta(days=5, hours=20)).isoformat() + "Z"
        }
    ])

    return {
        "categories": categories,
        "mcc_categories": mcc_categories,
        "merchants": merchants,
        "banks": banks,
        "bank_accounts": bank_accounts,
        "transactions": transactions
    }


def generate_test_accounts_info():
    """Генерация информации о тестовых номерах счетов для документации"""
    accounts_info = []
    for acc in TEST_ACCOUNTS:
        accounts_info.append({
            "account_number": acc["number"],
            "account_hash": get_bank_account_hash(acc["number"]),
            "account_name": acc["name"],
            "bank_id": acc["bank_id"],
            "user_id": acc["user_id"],
            "balance": acc["balance"]
        })
    return accounts_info


if __name__ == "__main__":
    # Генерируем данные
    test_data = generate_test_data()
    accounts_info = generate_test_accounts_info()

    # Сохраняем в JSON файл
    with open("pseudo_bank_test_data.json", "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)

    # Сохраняем информацию о счетах
    with open("test_accounts_info.md", "w", encoding="utf-8") as f:
        f.write("# Тестовые банковские счета\n\n")
        f.write("Используйте эти номера счетов для тестирования:\n\n")
        for acc in accounts_info:
            f.write(f"## {acc['account_name']}\n")
            f.write(f"- **Номер счета**: `{acc['account_number']}`\n")
            f.write(f"- **User ID**: {acc['user_id']}\n")
            f.write(f"- **Банк ID**: {acc['bank_id']}\n")
            f.write(f"- **Баланс**: {acc['balance']} RUB\n")
            f.write(f"- **Хеш (для внутреннего использования)**: `{acc['account_hash']}`\n\n")

    print("[OK] Testovye dannye uspeshno sgenerirova!")
    print("   - pseudo_bank_test_data.json")
    print("   - test_accounts_info.md")
    print("\nTestovye nomera schetov:")
    for acc in accounts_info:
        print(f"  - {acc['account_number']} ({acc['account_name']})")

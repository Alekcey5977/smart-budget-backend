"""
Скрипт для загрузки тестовых данных в псевдо банк через API.
"""
import json
import sys
import time

import requests

# URL псевдо банка (можно переопределить через аргумент командной строки)
PSEUDO_BANK_URL = "http://localhost:8004"


def load_test_data(base_url: str):
    """Загрузка тестовых данных в псевдо банк"""

    print(f"Loading test data to {base_url}...")
    print("=" * 60)

    # Загружаем JSON файл
    try:
        with open("pseudo_bank_test_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("[ERROR] File pseudo_bank_test_data.json not found!")
        print("Please run generate_pseudo_bank_data.py first.")
        return False

    # Порядок загрузки важен из-за foreign keys
    steps = [
        ("categories", f"{base_url}/pseudo_bank/categories/bulk", "Categories"),
        ("mcc_categories", f"{base_url}/pseudo_bank/mcc_categories/bulk", "MCC Categories"),
        ("merchants", f"{base_url}/pseudo_bank/merchants/bulk", "Merchants"),
        ("banks", f"{base_url}/pseudo_bank/banks/bulk", "Banks"),
        ("bank_accounts", f"{base_url}/pseudo_bank/bank_accounts/bulk", "Bank Accounts"),
        ("transactions", f"{base_url}/pseudo_bank/transactions/bulk", "Transactions"),
    ]

    for data_key, endpoint, name in steps:
        print(f"\n[STEP] Loading {name}...")
        items = data.get(data_key, [])

        if not items:
            print(f"  [SKIP] No {name} to load")
            continue

        try:
            response = requests.post(
                endpoint,
                json=items,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code in [200, 201]:
                result = response.json()
                print(f"  [OK] Loaded {len(items)} {name}")
                if "created" in result:
                    print(f"       Created: {result['created']}")
            else:
                print(f"  [ERROR] Failed to load {name}")
                print(f"          Status: {response.status_code}")
                print(f"          Response: {response.text}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"  [ERROR] Cannot connect to {base_url}")
            print("          Make sure the pseudo-bank service is running")
            return False
        except requests.exceptions.Timeout:
            print(f"  [ERROR] Request timeout for {name}")
            return False
        except Exception as e:
            print(f"  [ERROR] Unexpected error: {str(e)}")
            return False

        time.sleep(0.5)  # Small delay between requests

    print("\n" + "=" * 60)
    print("[SUCCESS] All test data loaded successfully!")
    print("\nTest account numbers:")

    # Показываем тестовые номера счетов
    try:
        with open("test_accounts_info.md", "r", encoding="utf-8") as f:
            lines = f.readlines()
            in_account = False
            for line in lines:
                if line.startswith("## "):
                    in_account = True
                    print(f"\n  {line.strip().replace('## ', '')}")
                elif in_account and "Номер счета" in line:
                    account_num = line.split("`")[1]
                    print(f"    Number: {account_num}")
                    in_account = False
    except Exception:
        pass

    return True


if __name__ == "__main__":
    # Проверяем аргументы командной строки
    base_url = PSEUDO_BANK_URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print("Pseudo Bank Test Data Loader")
    print("=" * 60)
    print(f"Target URL: {base_url}")
    print()

    success = load_test_data(base_url)
    sys.exit(0 if success else 1)

#!/bin/bash
# Script to load test data into pseudo-bank using curl
# Run inside pseudo-bank-service container

set -e

PSEUDO_BANK_URL="http://localhost:8004"
TEST_DATA_DIR="/testData"
DATA_FILE="$TEST_DATA_DIR/pseudo_bank_test_data.json"

echo "Pseudo Bank Test Data Loader (curl version)"
echo "============================================================"
echo "Target URL: $PSEUDO_BANK_URL"
echo ""

load_data() {
    local endpoint=$1
    local data_key=$2
    local name=$3

    echo "[STEP] Loading $name..."

    local tmp_file="/tmp/${data_key}.json"
    
    python3 -c "
import json
with open('$DATA_FILE', 'r') as f:
    data = json.load(f)
items = data.get('$data_key', [])
print(json.dumps(items))
" > "$tmp_file"

    local count=$(python3 -c "
import json
with open('$tmp_file', 'r') as f:
    data = json.load(f)
print(len(data))
")

    if [ "$count" -eq 0 ]; then
        echo "  [SKIP] No $name to load"
        rm -f "$tmp_file"
        return 0
    fi

    # Send bulk POST request
    local response=$(curl -sf -X POST "$endpoint" \
        -H "Content-Type: application/json" \
        -d @$tmp_file \
        --max-time 30 2>/dev/null)

    rm -f "$tmp_file"

    if [ $? -eq 0 ]; then
        echo "  [OK] Loaded $count $name"
        return 0
    else
        echo "  [ERROR] Failed to load $name"
        return 1
    fi
}

load_data "$PSEUDO_BANK_URL/pseudo_bank/categories/bulk" "categories" "Categories" || exit 1
sleep 0.5

load_data "$PSEUDO_BANK_URL/pseudo_bank/mcc_categories/bulk" "mcc_categories" "MCC Categories" || exit 1
sleep 0.5

load_data "$PSEUDO_BANK_URL/pseudo_bank/merchants/bulk" "merchants" "Merchants" || exit 1
sleep 0.5

load_data "$PSEUDO_BANK_URL/pseudo_bank/banks/bulk" "banks" "Banks" || exit 1
sleep 0.5

load_data "$PSEUDO_BANK_URL/pseudo_bank/bank_accounts/bulk" "bank_accounts" "Bank Accounts" || exit 1
sleep 0.5

load_data "$PSEUDO_BANK_URL/pseudo_bank/transactions/bulk" "transactions" "Transactions" || exit 1

echo ""
echo "============================================================"
echo "[SUCCESS] All test data loaded successfully!"
echo ""

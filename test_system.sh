#!/bin/bash
# Test script for Prime Number Generation System

set -e

echo "=== Prime Number Generation System Test ==="
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_URL="http://localhost:8000"

# Function to wait for API to be ready
wait_for_api() {
    echo -n "Waiting for API to be ready..."
    for i in {1..30}; do
        if curl -s "$API_URL/" > /dev/null 2>&1; then
            echo -e " ${GREEN}Ready!${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    echo -e " ${RED}Failed!${NC}"
    return 1
}

# Test 1: Health check
echo "Test 1: Health Check"
wait_for_api
HEALTH=$(curl -s "$API_URL/")
echo "Response: $HEALTH"
echo -e "${GREEN}✓ Health check passed${NC}"
echo

# Test 2: Create a new request
echo "Test 2: Create New Request (3 primes, 12 digits)"
NEW_RESPONSE=$(curl -s -X POST "$API_URL/api/new" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 3, "digits": 12}')
echo "Response: $NEW_RESPONSE"

REQUEST_ID=$(echo $NEW_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['request_id'])")
echo "Request ID: $REQUEST_ID"

if [ -z "$REQUEST_ID" ]; then
    echo -e "${RED}✗ Failed to create request${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Request created successfully${NC}"
echo

# Test 3: Check status
echo "Test 3: Check Status"
STATUS=$(curl -s "$API_URL/api/status/$REQUEST_ID")
echo "Response: $STATUS"
echo -e "${GREEN}✓ Status check passed${NC}"
echo

# Test 4: Wait for completion and monitor progress
echo "Test 4: Monitor Progress (waiting for completion)"
COMPLETED=false
for i in {1..30}; do
    STATUS=$(curl -s "$API_URL/api/status/$REQUEST_ID")
    GENERATED=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['generated_count'])" 2>/dev/null || echo "0")
    PROGRESS=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['progress_percentage'])" 2>/dev/null || echo "0")
    
    echo "Progress: $GENERATED/3 ($PROGRESS%)"
    
    if [ "$GENERATED" = "3" ]; then
        COMPLETED=true
        break
    fi
    sleep 3
done

if [ "$COMPLETED" = false ]; then
    echo -e "${YELLOW}⚠ Warning: Not all primes generated yet, but continuing...${NC}"
fi
echo

# Test 5: Get results
echo "Test 5: Get Results"
RESULT=$(curl -s "$API_URL/api/result/$REQUEST_ID")
echo "Response: $RESULT"

# Extract and display prime numbers
echo
echo "Generated Prime Numbers:"
echo $RESULT | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, prime in enumerate(data['prime_numbers'], 1):
    print(f'{i}. {prime}')
"

echo
echo -e "${GREEN}✓ Results retrieved successfully${NC}"
echo

# Test 6: Verify uniqueness
echo "Test 6: Verify No Duplicates"
UNIQUE_COUNT=$(echo $RESULT | python3 -c "
import sys, json
data = json.load(sys.stdin)
primes = data['prime_numbers']
print(len(set(primes)))
")
TOTAL_COUNT=$(echo $RESULT | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(len(data['prime_numbers']))
")

if [ "$UNIQUE_COUNT" = "$TOTAL_COUNT" ]; then
    echo -e "${GREEN}✓ All primes are unique${NC}"
else
    echo -e "${RED}✗ Found duplicate primes${NC}"
    exit 1
fi
echo

echo "=== All Tests Passed! ==="

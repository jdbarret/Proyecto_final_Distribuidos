#!/bin/bash
# Example usage of the Prime Number Generation API

API_URL="${API_URL:-http://localhost:8000}"

echo "=== Prime Number Generation System - Example Usage ==="
echo "API URL: $API_URL"
echo

# Function to print section header
print_header() {
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
}

# Example 1: Create a request
print_header "Example 1: Create a new request for 5 primes of 12 digits"

echo "Request:"
echo 'POST /api/new {"quantity": 5, "digits": 12}'
echo

RESPONSE=$(curl -s -X POST "$API_URL/api/new" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5, "digits": 12}')

echo "Response:"
echo $RESPONSE | python3 -m json.tool

REQUEST_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['request_id'])")

# Example 2: Check status
print_header "Example 2: Check the status of the request"

echo "Request:"
echo "GET /api/status/$REQUEST_ID"
echo

sleep 2  # Give workers time to process

STATUS=$(curl -s "$API_URL/api/status/$REQUEST_ID")
echo "Response:"
echo $STATUS | python3 -m json.tool

# Example 3: Wait for completion
print_header "Example 3: Monitoring progress until completion"

echo "Polling status every 2 seconds..."
echo

for i in {1..30}; do
    STATUS=$(curl -s "$API_URL/api/status/$REQUEST_ID")
    GENERATED=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['generated_count'])" 2>/dev/null || echo "0")
    QUANTITY=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['quantity'])" 2>/dev/null || echo "5")
    PROGRESS=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['progress_percentage'])" 2>/dev/null || echo "0")
    
    # Progress bar
    BARS=$(printf "%.0f" $(echo "$PROGRESS / 5" | bc -l))
    PROGRESS_BAR=$(printf '%*s' $BARS | tr ' ' '█')
    REMAINING_BAR=$(printf '%*s' $((20 - BARS)) | tr ' ' '░')
    
    echo -ne "\r[$PROGRESS_BAR$REMAINING_BAR] $GENERATED/$QUANTITY ($PROGRESS%)"
    
    if [ "$GENERATED" = "$QUANTITY" ]; then
        echo
        echo "✓ All primes generated!"
        break
    fi
    sleep 2
done
echo

# Example 4: Get results
print_header "Example 4: Retrieve the generated prime numbers"

echo "Request:"
echo "GET /api/result/$REQUEST_ID"
echo

RESULT=$(curl -s "$API_URL/api/result/$REQUEST_ID")
echo "Response:"
echo $RESULT | python3 -m json.tool

echo
echo "Generated Prime Numbers:"
echo $RESULT | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, prime in enumerate(data['prime_numbers'], 1):
    print(f'  {i}. {prime}')
"

# Example 5: Large numbers
print_header "Example 5: Generate a 20-digit prime number"

echo "Request:"
echo 'POST /api/new {"quantity": 1, "digits": 20}'
echo

RESPONSE=$(curl -s -X POST "$API_URL/api/new" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 1, "digits": 20}')

echo "Response:"
echo $RESPONSE | python3 -m json.tool

REQUEST_ID_2=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['request_id'])")

echo
echo "Waiting for generation..."
for i in {1..20}; do
    STATUS=$(curl -s "$API_URL/api/status/$REQUEST_ID_2")
    GENERATED=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['generated_count'])" 2>/dev/null || echo "0")
    
    if [ "$GENERATED" = "1" ]; then
        break
    fi
    echo -n "."
    sleep 1
done
echo

RESULT=$(curl -s "$API_URL/api/result/$REQUEST_ID_2")
echo "20-digit prime:"
echo $RESULT | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data['prime_numbers']:
    print(f\"  {data['prime_numbers'][0]}\")
"

print_header "Examples completed!"

echo "You can now try your own requests using curl:"
echo
echo "  # Create request"
echo '  curl -X POST http://localhost:8000/api/new \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"quantity": 3, "digits": 15}'"'"
echo
echo "  # Check status"
echo '  curl http://localhost:8000/api/status/{request_id}'
echo
echo "  # Get results"
echo '  curl http://localhost:8000/api/result/{request_id}'
echo

#!/bin/bash
set -e

ENV_FILE="../.env"
LOG_FILE="../log/update_data.log"
RESPONSE_FILE="/tmp/update_data_response.txt"

MAX_RETRIES=3
RETRY_DELAY=600
TIMEOUT=60

LOG_DIR=$(dirname "$LOG_FILE")
mkdir -p "$LOG_DIR"
touch "$LOG_FILE"

if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] .env not found at $ENV_FILE" >> "$LOG_FILE"
  exit 1
fi

if [ -z "$APP_IP_ADDRESS" ] || [ -z "$APP_PORT" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] APP_IP_ADDRESS or APP_PORT not set in .env" >> "$LOG_FILE"
  exit 1
fi

if [ -z "$SCHEDULER_API_KEY" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] SCHEDULER_API_KEY not found in .env" >> "$LOG_FILE"
  exit 1
fi

API_URL="http://$APP_IP_ADDRESS:$APP_PORT/api/fin_reports/jobs/fetch_daily_financial_reports"

make_request() {
  curl -s -w "%{http_code}" -o "$RESPONSE_FILE" \
    -X POST "$API_URL" \
    -H "X-API-Key: $SCHEDULER_API_KEY" \
    -H "Content-Type: application/json" \
    --max-time $TIMEOUT
}

log_response() {
  local status=$1
  if [ -f "$RESPONSE_FILE" ] && [ -s "$RESPONSE_FILE" ]; then
    local response_content=$(cat "$RESPONSE_FILE")
    echo "$(date '+%Y-%m-%d %H:%M:%S') [RESPONSE] HTTP $status: $response_content" >> "$LOG_FILE"
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') [RESPONSE] HTTP $status: Empty response" >> "$LOG_FILE"
  fi
}

for ((i=1; i<=MAX_RETRIES; i++)); do
  STATUS=$(make_request)

  log_response "$STATUS"

  if [[ "$STATUS" == 2* ]]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Success (HTTP $STATUS)" >> "$LOG_FILE"
    exit 0
  else
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] Attempt $i failed (HTTP $STATUS)" >> "$LOG_FILE"

    if [[ "$STATUS" =~ ^(408|429|5) ]]; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Retrying in $RETRY_DELAY seconds..." >> "$LOG_FILE"
      sleep $RETRY_DELAY
    else
      echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] Non-retryable status $STATUS" >> "$LOG_FILE"
      exit 1
    fi
  fi
done

echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] All retries failed" >> "$LOG_FILE"
exit 1

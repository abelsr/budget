#!/bin/sh
# Run from cron. The webhook must accept a JSON POST, such as a Discord webhook.
set -eu

DISK_PATH=${DISK_PATH:-/}
DISK_THRESHOLD_PERCENT=${DISK_THRESHOLD_PERCENT:-85}
DISK_ALERT_WEBHOOK=${DISK_ALERT_WEBHOOK:-}

case "$DISK_THRESHOLD_PERCENT" in
  ''|*[!0-9]*)
    echo "DISK_THRESHOLD_PERCENT must be an integer" >&2
    exit 2
    ;;
esac

if [ "$DISK_THRESHOLD_PERCENT" -gt 100 ]; then
  echo "DISK_THRESHOLD_PERCENT must be at most 100" >&2
  exit 2
fi

usage=$(df -P "$DISK_PATH" | awk 'NR == 2 { sub(/%$/, "", $5); print $5 }')
if [ -z "$usage" ]; then
  echo "Could not determine disk usage for $DISK_PATH" >&2
  exit 1
fi

if [ "$usage" -lt "$DISK_THRESHOLD_PERCENT" ]; then
  exit 0
fi

message="Disk usage on $(hostname) is ${usage}% at ${DISK_PATH} (threshold: ${DISK_THRESHOLD_PERCENT}%)."
echo "$message" >&2

if [ -z "$DISK_ALERT_WEBHOOK" ]; then
  echo "DISK_ALERT_WEBHOOK is required when the threshold is exceeded" >&2
  exit 1
fi

payload=$(printf '{"text":"%s"}' "$message")
curl --fail --silent --show-error --max-time 15 \
  -X POST -H 'Content-Type: application/json' -d "$payload" "$DISK_ALERT_WEBHOOK"

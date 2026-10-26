#!/bin/sh
set -e

while true; do
  python manage.py send_expiry_reminders --base-url "${SITE_URL:-http://localhost:8000}" || true
  python manage.py sync_prices --pages "${SYNC_PAGES:-2}" || true
  sleep "${SCHEDULER_INTERVAL:-86400}"
done

#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  python manage.py migrate --noinput
  python manage.py setup_assistant
  python manage.py setup_billing
fi

exec "$@"

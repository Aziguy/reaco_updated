#!/bin/bash

# Install psycopg2-binary
echo "Install psycopg2-binary..."
pip install psycopg2-binary
# Build the project
echo "Building the project..."
python3.9 -m pip install -r requirements.txt

echo "Make Migration..."
python3.9 manage.py makemigrations --noinput
python3.9 manage.py migrate --noinput

echo "Collect Static..."
python3.9 manage.py collectstatic --noinput --clear

echo "Load datas into DB..."
python3.9 manage.py loaddata project_dump.json
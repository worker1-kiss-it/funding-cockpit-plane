#!/bin/bash
set -e

python manage.py wait_for_db $1

python manage.py migrate $1

# Seed funding data (idempotent - skips existing records)
python manage.py seed_funding_data || true
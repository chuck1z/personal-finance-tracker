#!/bin/bash

set -e

# Wait for PostgreSQL to be ready
until pg_isready -h localhost -p 5432 -U $POSTGRES_USER
do
  echo "Waiting for PostgreSQL to start..."
  sleep 2
done

echo "PostgreSQL started. Running database migrations..."

# Navigate to the migrations directory and run the Python migration script
cd /docker-entrypoint-initdb.d/migrations
python migrate.py --initial-setup

echo "Database setup complete."

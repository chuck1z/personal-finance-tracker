# Use a PostgreSQL base image
FROM postgres:13

# Set environment variables for PostgreSQL
ENV POSTGRES_DB=finanalyze
ENV POSTGRES_USER=finanalyze_user
ENV POSTGRES_PASSWORD=finanalyze_password

# Create a directory for our migration script
RUN mkdir -p /docker-entrypoint-initdb.d/migrations

# Copy the migration script and schema.sql to the container
COPY migrate.py /docker-entrypoint-initdb.d/migrations/
COPY schema.sql /docker-entrypoint-initdb.d/migrations/

# Copy a small shell script to execute the Python migration script
# This script will ensure the database is ready before running the migration
COPY init-db.sh /docker-entrypoint-initdb.d/

# Ensure the init-db.sh is executable
RUN chmod +x /docker-entrypoint-initdb.d/init-db.sh


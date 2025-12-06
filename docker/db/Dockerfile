# Multi-architecture PostgreSQL 16 with PostGIS
# Supports both ARM64 and AMD64

FROM postgres:16

# Install PostGIS
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
           postgis \
           postgresql-16-postgis-3 \
    && rm -rf /var/lib/apt/lists/*

# Copy initialization script
COPY init-postgis.sql /docker-entrypoint-initdb.d/
RUN chmod 644 /docker-entrypoint-initdb.d/init-postgis.sql

# The initialization script will be executed automatically
# when the container starts for the first time

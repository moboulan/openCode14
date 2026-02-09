FROM postgres:15-alpine

LABEL maintainer="moboulan"
LABEL description="Incident Platform PostgreSQL database with schema initialization"

# Copy initialization scripts (executed in alphabetical order on first start)
COPY init-db/ /docker-entrypoint-initdb.d/

# Harden: remove unnecessary setuid/setgid binaries
RUN find / -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

EXPOSE 5432

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
	CMD pg_isready -U postgres || exit 1

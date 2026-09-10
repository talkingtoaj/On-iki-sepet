# Build with uv, matching how the project is developed, so the container gets
# exactly the locked dependency set rather than a fresh resolve.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# gettext provides msgfmt, needed to compile the Turkish catalogue.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first, so a code-only change does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev

# Collect static files and compile translations at build time, not at start:
# doing it on boot would repeat the work on every cold start, and a failure
# would surface as a failed request rather than a failed build.
#
# These placeholders satisfy the production settings guards for the duration of
# the build only. Nothing here is baked into the image's runtime config.
RUN DJANGO_ENV=production \
    DJANGO_SECRET_KEY=build-time-only-not-a-real-secret-key-000000000000 \
    DJANGO_ALLOWED_HOSTS=localhost \
    POSTGRES_DB=build POSTGRES_HOST=localhost \
    DJANGO_EMAIL_BACKEND=django.core.mail.backends.dummy.EmailBackend \
    uv run python manage.py collectstatic --noinput \
    && uv run python manage.py compilemessages -l tr

# The entrypoint is copied and made executable while still root, and stays
# root-owned so the unprivileged user cannot rewrite the script it is about to
# execute.
#
# chmod is a separate RUN rather than COPY --chmod on purpose: --chmod requires
# BuildKit, and Cloud Build's gcr.io/cloud-builders/docker runs the legacy
# builder, where it fails the build outright. Docker's COPY does preserve the
# source mode, so this is also insurance against a checkout that has lost the
# executable bit.
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

# Run unprivileged.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

# Cloud Run sets $PORT; default to 8000 for local runs.
CMD ["sh", "-c", "uv run gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 60 --access-logfile -"]

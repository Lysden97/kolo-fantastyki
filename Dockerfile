FROM node:26-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY static ./static
COPY templates ./templates
RUN npm run build:css

FROM python:3.13-slim-bookworm AS builder
WORKDIR /build
COPY requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index /wheels/* && rm -rf /wheels \
    && useradd --create-home --uid 10001 appuser \
    && mkdir /app/staticfiles && chown appuser:appuser /app/staticfiles
COPY --chown=appuser:appuser . .
COPY --from=frontend --chown=appuser:appuser /build/static/css/dist/style.css ./static/css/dist/style.css
RUN chmod +x /app/entrypoint.prod.sh
USER appuser
EXPOSE 8000
CMD ["/app/entrypoint.prod.sh"]

FROM node:22-slim AS admin-ui-builder

WORKDIR /ui/admin

COPY ui/admin/package.json ui/admin/package-lock.json ./
RUN npm ci

COPY ui/admin ./
RUN npm run build


FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHATMOCK_ADMIN_UI_DIST_DIR=/app/ui/admin/dist

WORKDIR /app

COPY pyproject.toml README.md chatmock.py prompt.md prompt_gpt5_codex.md /app/
COPY chatmock /app/chatmock
COPY --from=admin-ui-builder /ui/admin/dist /app/ui/admin/dist
RUN pip install --no-cache-dir .

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && groupadd --system chatmock \
    && useradd --system --gid chatmock --home-dir /app --no-create-home chatmock \
    && mkdir -p /data \
    && chown -R chatmock:chatmock /app /data

USER chatmock

EXPOSE 8000 1455

ENTRYPOINT ["/entrypoint.sh"]
CMD ["serve"]

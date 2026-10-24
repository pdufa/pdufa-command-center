FROM python:3.12-slim
WORKDIR /service
# pg_dump/pg_restore support private, manually authorized database recovery.
# No scheduled job or HTTP backup endpoint is enabled.
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY scripts/export_render_postgres.py ./scripts/export_render_postgres.py
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

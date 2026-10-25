FROM python:3.12-slim
# Cap glibc arena growth and trim released pages on the 512 MiB staging service.
# Does not change worker count, trial contents, or compute plan.
ENV MALLOC_ARENA_MAX=2 MALLOC_TRIM_THRESHOLD_=131072
WORKDIR /service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

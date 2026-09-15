FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY start.py ./
RUN pip install --no-cache-dir .
RUN useradd -r appuser && chown -R appuser:appuser /app
USER appuser
CMD ["python", "start.py"]

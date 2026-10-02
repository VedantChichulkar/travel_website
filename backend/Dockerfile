FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system vayora && adduser --system --ingroup vayora vayora
COPY requirements.txt requirements.private-storage.txt requirements.public-media.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt --requirement requirements.private-storage.txt --requirement requirements.public-media.txt
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
RUN mkdir -p /app/uploads && chown -R vayora:vayora /app

USER vayora
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

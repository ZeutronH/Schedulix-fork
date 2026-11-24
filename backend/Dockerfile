FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
COPY wheels/ /wheels/

RUN python -m pip install \
    --no-index \
    --find-links=/wheels \
    --no-cache-dir \
    -r requirements.txt

COPY . .

RUN mkdir -p media

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
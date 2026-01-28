FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY pactfix/ ./pactfix/

RUN pip install --no-cache-dir -e .

EXPOSE 5000

ENV PORT=5000
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "pactfix.server"]

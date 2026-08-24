FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.4.20 /uv /uvx /bin/

WORKDIR /app

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]

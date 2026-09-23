FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.4.20 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 8000

CMD ["uv", "run", "python", "main.py"]

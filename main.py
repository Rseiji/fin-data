"""Entry-point: starts the FastAPI server and the background scheduler."""
import uvicorn

from src.api.app import app
from src.config.settings import settings
from src.orchestration.scheduler import start_scheduler


def main():
    scheduler = start_scheduler()
    try:
        uvicorn.run(app, host=settings.api_host, port=settings.api_port)
    finally:
        if scheduler:
            scheduler.shutdown()


if __name__ == "__main__":
    main()

"""Entry-point: starts the FastAPI server and the background scheduler."""
import uvicorn

from src.api.app import app
from src.orchestration.scheduler import start_scheduler


def main():
    scheduler = start_scheduler()
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        if scheduler:
            scheduler.shutdown()


if __name__ == "__main__":
    main()

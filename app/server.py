import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from data.database import Database


def create_app():
    # Initialize Database
    Database.init_db()

    app = FastAPI(
        title="LLM Security Gateway Pro",
        description="A robust, middleware-based security layer intercepting requests and responses to mitigate LLM vulnerabilities.",
        version="2.0.0",
        contact={
            "name": "Dhruv Patil",
            "url": "https://github.com/dhruuv-patil",
        },
        license_info={
            "name": "MIT",
        },
    )

    # Register Routes
    app.include_router(router)

    # Serve Static Files
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(static_dir, "index.html"))

    return app

app = create_app()

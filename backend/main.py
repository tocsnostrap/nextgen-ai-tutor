"""
NextGen AI Tutor - Main FastAPI Application
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NextGen AI Tutor Backend...")

    from .core.database import init_db
    from .core.redis import init_redis
    from .models.session import SessionManager
    from .websocket.manager import websocket_manager

    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    try:
        from .core.database import _get_session_local
        session_factory = _get_session_local()
    except Exception as e:
        session_factory = None
        logger.warning(f"Session factory init failed: {e}")

    if session_factory:
        try:
            from .api.v1.endpoints.videos import seed_video_lessons
            async with session_factory() as session:
                try:
                    await seed_video_lessons(session)
                    await session.commit()
                    logger.info("Video lessons seeded")
                except Exception as e:
                    await session.rollback()
                    logger.warning(f"Video lesson seeding skipped: {e}")
        except Exception as e:
            logger.warning(f"Video seeding failed: {e}")

        try:
            from .curriculum_data import seed_curriculum
            async with session_factory() as session:
                try:
                    await seed_curriculum(session)
                    logger.info("Curriculum seeded")
                except Exception as e:
                    await session.rollback()
                    logger.warning(f"Curriculum seeding skipped: {e}")
        except Exception as e:
            logger.warning(f"Curriculum seeding failed: {e}")

    try:
        await init_redis()
        logger.info("Redis initialized")
    except Exception as e:
        logger.warning(f"Redis initialization skipped: {e}")

    await SessionManager.initialize()
    logger.info("Session manager initialized")

    await websocket_manager.initialize()
    logger.info("WebSocket manager initialized")

    yield

    logger.info("Shutting down NextGen AI Tutor Backend...")
    await websocket_manager.cleanup()
    logger.info("Shutdown complete")


app = FastAPI(
    title="NextGen AI Tutor API",
    description="Enterprise-grade AI tutoring platform backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

from .core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

from .api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
videos_dir = os.path.join(frontend_dir, "videos")
assets_dir = os.path.join(frontend_dir, "assets")
os.makedirs(videos_dir, exist_ok=True)
os.makedirs(assets_dir, exist_ok=True)
app.mount("/videos", StaticFiles(directory=videos_dir), name="videos")
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/frontend/{file_path:path}")
async def serve_frontend_file(file_path: str):
    full_path = os.path.join(frontend_dir, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        media_type = "application/javascript" if file_path.endswith(".js") else None
        return FileResponse(full_path, media_type=media_type)
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/sw.js")
async def service_worker():
    sw_path = os.path.join(frontend_dir, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Service worker not found")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "nextgen-ai-tutor",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    demo_path = os.path.join(frontend_dir, "demo.html")
    if os.path.exists(demo_path):
        return FileResponse(demo_path, media_type="text/html")
    return {"message": "Welcome to NextGen AI Tutor API", "version": "1.0.0", "docs": "/docs"}


@app.get("/parent")
async def parent_dashboard():
    parent_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "parent_dashboard.html")
    if os.path.exists(parent_path):
        return FileResponse(parent_path, media_type="text/html")
    return {"error": "Parent dashboard not found"}


@app.get("/demo")
async def demo():
    demo_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "demo.html")
    if os.path.exists(demo_path):
        return FileResponse(demo_path, media_type="text/html")
    return {"error": "Demo not found"}


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    return {
        "user_id": "user_123",
        "email": "student@example.com",
        "role": "student"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "code": 500}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )

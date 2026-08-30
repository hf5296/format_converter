"""
Format Converter - FastAPI Application
A self-hosted file format converter with a beautiful UI
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .routes.convert import router as convert_router

# Application metadata
app = FastAPI(
    title="Format Converter",
    description="A self-hosted file format converter with one-click presets",
    version="1.0.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(convert_router)

# Determine frontend path
# Check multiple locations for flexibility between dev and production
FRONTEND_DIR = None
possible_paths = [
    Path("/app/frontend"),  # Docker container
    Path(__file__).parent.parent.parent / "frontend",  # Local dev (backend/app/main.py -> frontend)
    Path(__file__).parent.parent / "frontend",  # Alternative structure
]

for path in possible_paths:
    if path.exists() and (path / "index.html").exists():
        FRONTEND_DIR = path
        break


# Mount static files if frontend directory exists
if FRONTEND_DIR and FRONTEND_DIR.exists():
    # Mount CSS and JS directories
    if (FRONTEND_DIR / "css").exists():
        app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    if (FRONTEND_DIR / "js").exists():
        app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the frontend index.html."""
        return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api")
async def api_root():
    """API root endpoint with documentation links."""
    return {
        "message": "Format Converter API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "presets": "/api/presets",
            "formats": "/api/formats",
            "convert": "/api/convert",
            "batch_convert": "/api/batch-convert",
            "health": "/api/health"
        }
    }

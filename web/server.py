from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bot.bot import bot
from bot.services.database import db
from web.routes import router

# Get base directory for static files
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "web" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
        await db.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
app.include_router(router)


@app.get("/", response_class=FileResponse)
async def root():
    """Serve index.html for root path"""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return {"error": "index.html not found", "looking_at": str(index_file)}
    return FileResponse(str(index_file), media_type="text/html")

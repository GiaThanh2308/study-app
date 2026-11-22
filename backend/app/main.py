from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pathlib import Path
from app.core.database import DATA_DIR
from app.core.logging_config import setup_logging
from app.api import structure, files, search, chat, hierarchy, catalog, practice, imports, generation
from app.core.settings import LOCAL_ORIGINS

# Cấu hình logging
logger = setup_logging()

Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(title="StudyApp API — Ôn thi THPT Quốc gia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(structure.router, prefix="/api", tags=["structure"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(catalog.router, prefix="/api", tags=["catalog"])
app.include_router(practice.router, prefix="/api", tags=["practice"])
app.include_router(imports.router, prefix="/api", tags=["imports"])
app.include_router(hierarchy.router, prefix="/api", tags=["hierarchy"])
app.include_router(generation.router, prefix="/api", tags=["generation"])


@app.on_event("startup")
def recover_generation_jobs():
    generation.mark_interrupted_jobs()

# Cho phép frontend truy cập trực tiếp file (xem PDF, phát video) qua /data/...
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.get("/")
def root():
    return {"status": "ok", "message": "StudyApp backend đang chạy — Ôn thi THPT Quốc gia"}

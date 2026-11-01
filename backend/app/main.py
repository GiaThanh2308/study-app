from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, engine, DATA_DIR, SessionLocal
from app.core.logging_config import setup_logging
from app.core.seed import seed_database
from app.core.init_hierarchy import seed_hierarchy_data
from app.api import structure, files, search, chat, exams, stats, hierarchy

# Cấu hình logging
logger = setup_logging()

# Tạo bảng nếu chưa có
Base.metadata.create_all(bind=engine)

# Seed dữ liệu mẫu & hệ thống phân cấp
logger.info("Kiểm tra và seed dữ liệu...")
_seed_db = SessionLocal()
try:
    seed_database(_seed_db)
    seed_hierarchy_data(_seed_db)
finally:
    _seed_db.close()

app = FastAPI(title="StudyApp API — Ôn thi THPT Quốc gia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(structure.router, prefix="/api", tags=["structure"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(exams.router, prefix="/api", tags=["exams"])
app.include_router(hierarchy.router, prefix="/api", tags=["hierarchy"])
app.include_router(stats.router, prefix="/api", tags=["stats"])

# Cho phép frontend truy cập trực tiếp file (xem PDF, phát video) qua /data/...
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")


@app.get("/")
def root():
    return {"status": "ok", "message": "StudyApp backend đang chạy — Ôn thi THPT Quốc gia"}

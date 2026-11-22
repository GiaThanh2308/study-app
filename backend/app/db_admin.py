"""Explicit backup, restore, and reset operations for the new local SQLite DB."""

import argparse
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import BACKEND_DIR, DATA_DIR, DB_PATH


SUPPORTED_REVISIONS = {
    "0001_initial",
    "0002_practice_scoring",
    "0003_unique_exam_question_links",
    "0004_ingestion_fingerprints",
    "0005_generation_workflow",
}
HEAD_REVISION = "0005_generation_workflow"
BACKUP_DIR = DATA_DIR / "backups"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_conn = sqlite3.connect(str(source))
    target_conn = sqlite3.connect(str(destination))
    try:
        source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()


def _validate_database(path: Path, *, require_head: bool = False) -> str:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise ValueError(f"Database backup lỗi integrity_check: {result}")
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "alembic_version" not in tables:
            raise ValueError("File này không có alembic_version, không phải backup StudyApp hợp lệ.")
        revision = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        version = revision[0] if revision else None
        if version not in SUPPORTED_REVISIONS:
            raise ValueError(f"Revision backup không tương thích: {version or 'trống'}.")
        if require_head and version != HEAD_REVISION:
            raise ValueError(f"Database chưa ở revision mới nhất: {version}.")
        return version
    finally:
        conn.close()


def _new_backup_path(label: str) -> Path:
    return BACKUP_DIR / f"studyapp-{label}-{_timestamp()}.sqlite3"


def do_backup(output: Path | None) -> Path:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Chưa có database mới để backup: {DB_PATH}")
    destination = output.resolve() if output else _new_backup_path("backup")
    if destination == DB_PATH.resolve():
        raise ValueError("Đường dẫn backup không được trùng với database đang dùng.")
    _sqlite_backup(DB_PATH, destination)
    _validate_database(destination, require_head=True)
    return destination


def do_restore(source: Path, confirmed: bool) -> Path:
    if not confirmed:
        raise ValueError("Restore thay thế database hiện tại. Hãy truyền --yes để xác nhận.")
    source = source.resolve()
    if not source.is_file() or source == DB_PATH.resolve():
        raise ValueError("File backup không tồn tại hoặc trùng database đang chạy.")
    _validate_database(source)
    if DB_PATH.is_file():
        current_backup = _new_backup_path("before-restore")
        _sqlite_backup(DB_PATH, current_backup)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    staging_path = DB_PATH.with_name(f"{DB_PATH.name}.restore-{_timestamp()}")
    try:
        _sqlite_backup(source, staging_path)
        _validate_database(staging_path)
        staging_path.replace(DB_PATH)
    finally:
        staging_path.unlink(missing_ok=True)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
    )
    return DB_PATH


def do_reset(confirmed: bool) -> Path:
    if not confirmed:
        raise ValueError("Reset xóa database mới và nạp seed lại. Hãy truyền --yes để xác nhận.")
    data_root = DATA_DIR.resolve()
    database_path = DB_PATH.resolve()
    if not database_path.is_relative_to(data_root):
        raise ValueError("Từ chối reset: DB_PATH phải nằm trong STUDYAPP_DATA_DIR.")
    if DB_PATH.is_file():
        saved_copy = _new_backup_path("before-reset")
        _sqlite_backup(DB_PATH, saved_copy)
        DB_PATH.unlink()

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "app.seed_data.seed_initial"],
        cwd=BACKEND_DIR,
        check=True,
    )
    return DB_PATH


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Backup/restore/reset StudyApp SQLite database")
    commands = parser.add_subparsers(dest="command", required=True)

    backup_parser = commands.add_parser("backup", help="Tạo backup nhất quán của DB hiện hành")
    backup_parser.add_argument("--output", type=Path, help="Đường dẫn backup; mặc định backend/data/backups")

    restore_parser = commands.add_parser("restore", help="Khôi phục một backup đã kiểm tra")
    restore_parser.add_argument("source", type=Path)
    restore_parser.add_argument("--yes", action="store_true", help="Xác nhận thay thế DB hiện hành")

    reset_parser = commands.add_parser("reset", help="Tạo lại DB rỗng rồi chạy migration và seed")
    reset_parser.add_argument("--yes", action="store_true", help="Xác nhận xóa DB hiện hành sau khi backup")

    args = parser.parse_args()
    if args.command == "backup":
        print(f"Backup đã tạo: {do_backup(args.output)}")
    elif args.command == "restore":
        print(f"Đã restore database: {do_restore(args.source, args.yes)}")
    elif args.command == "reset":
        print(f"Đã tạo lại database: {do_reset(args.yes)}")


if __name__ == "__main__":
    main()

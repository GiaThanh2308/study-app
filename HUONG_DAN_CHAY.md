# Hướng dẫn chạy StudyApp - Giai đoạn 2

## Bước 0 — Chuyển project sang ổ D:
Giải nén file zip, đặt toàn bộ thư mục `StudyApp` vào:
```
D:\StudyApp
```

## Bước 1 — Cài Python (nếu chưa có)
Tải Python 3.11 tại https://www.python.org/downloads/ (nhớ tick "Add Python to PATH" khi cài).

## Bước 2 — Chạy Backend
Mở PowerShell hoặc CMD:
```
cd D:\StudyApp\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Nếu thành công, bạn sẽ thấy dòng: `Uvicorn running on http://127.0.0.1:8000`

Kiểm tra: mở trình duyệt vào http://127.0.0.1:8000 — thấy `{"status":"ok",...}` là backend chạy tốt.
Xem tài liệu API tự động tại: http://127.0.0.1:8000/docs

## Bước 3 — Cài Node.js (nếu chưa có)
Tải bản LTS tại https://nodejs.org/

## Bước 4 — Chạy Frontend
Mở terminal MỚI (giữ nguyên terminal backend đang chạy):
```
cd D:\StudyApp\frontend
npm install
npm run dev
```
Mở trình duyệt vào: http://localhost:5173

## Bước 5 — Dùng thử
1. Vào menu "Môn học"
2. Gõ tên môn (VD: Toán) → bấm "+ Thêm môn"
3. Bấm vào môn vừa tạo → thêm chương → thêm bài học
4. Bấm vào bài học → upload thử 1 file PDF hoặc video

## Lỗi thường gặp
- **"uvicorn: command not found"** → chưa activate venv, chạy lại `venv\Scripts\activate`
- **CORS error trên trình duyệt** → đảm bảo backend chạy ở cổng 8000, frontend ở cổng 5173 đúng như cấu hình
- **Upload file lỗi 413** → file quá lớn, video dài cần config lại giới hạn (sẽ xử lý ở giai đoạn sau khi thêm nén/chunk upload)

## Cấu trúc file đã tạo
```
StudyApp/
├── backend/
│   ├── app/
│   │   ├── main.py           # entry point FastAPI
│   │   ├── core/database.py  # kết nối SQLite
│   │   ├── models/models.py  # 7 bảng: Subject, Chapter, Lesson, Video, Transcript, Document
│   │   ├── models/schemas.py # Pydantic schemas
│   │   └── api/
│   │       ├── structure.py  # CRUD môn/chương/bài + xem cây thư mục
│   │       ├── files.py      # upload video/pdf/transcript
│   │       └── search.py     # tìm kiếm text
│   ├── data/                 # nơi lưu file thật (video, pdf...)
│   └── studyapp.db           # tự tạo khi chạy lần đầu
│
└── frontend/
    └── src/
        ├── App.jsx           # router + layout
        ├── components/Sidebar.jsx
        └── pages/Subjects.jsx # trang chính giai đoạn 2
```

## Tiếp theo
Đây là nền tảng Giai đoạn 2 (quản lý dữ liệu). Các trang Chat AI, Luyện tập, Thống kê hiện là placeholder — sẽ xây ở Giai đoạn 3 trở đi.

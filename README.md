# 🎓 StudyApp — Nền Tảng Hỗ Trợ Học Tập & Ôn Thi Tốt Nghiệp THPT (Toán - Lý - Hóa)

Ứng dụng hỗ trợ học sinh lớp 12 tự học và luyện thi THPT Quốc gia theo cấu trúc chuẩn 3 môn **Toán học**, **Vật lý**, và **Hóa học**. Tích hợp trợ lý **AI tra cứu kiến thức (Smart Precision RAG)**, tự động tìm và phát đúng **phút:giây** của video bài giảng trên YouTube, bóc tách đề thi từ **ảnh chụp mạng xã hội (Facebook/Zalo OCR)**, và hệ thống luyện thi trắc nghiệm kèm bộ đếm tiến độ thông minh.

---

## 📌 1. Các Tính Năng Đột Phá Đã Triển Khai

- 📐 **Cấu trúc chuẩn lớp 12**: Định hình sẵn toàn bộ cây thư mục kiến thức (Môn học ➔ Chương ➔ Bài học) của 3 môn Toán, Lý, Hóa bám sát chương trình THPT.
- 🏛️ **Kho Đề Thi Nguyên Bản 2025 (GDPT 2018) & Định Danh Nguồn Gốc**:
  - Tích hợp đề thi nguyên bản 100% từ các **Sở GD&ĐT** (Hà Nội, Nghệ An, Nam Định, Bắc Ninh...) và các **Trường THPT Chuyên** danh tiếng (Lam Sơn, KHTN...).
  - **Chính sách không Mock / Không Hallucination:** Tuyệt đối cấm AI tự bịa câu hỏi kiểu "Phương án A, Phương án B" hay chắp vá câu hỏi rời rạc.
  - Hiển thị đầy đủ **Huy hiệu xuất xứ**: Tỉnh/Thành phố ra đề, Tên trường/Sở, Năm thi 2025, Chuẩn chương trình mới GDPT 2018 (kèm danh pháp hóa học quốc tế IUPAC mới).
- ❌ **Sổ Lỗi Sai (Mistake Log) & Thống kê Chuyên Sâu**:
  - Giao diện **Sổ lỗi sai (`Mistakes.jsx`)** chuyên biệt: Tự động lưu và phân loại từng câu làm sai của học sinh, so sánh đáp án bạn chọn (đỏ) với đáp án đúng (xanh) kèm lời giải chi tiết và nút "Hỏi AI câu này".
  - Giao diện **Thống kê (`Stats.jsx`)**: Bảng theo dõi điểm số trung bình, điểm kỷ lục, số câu đã làm và tỷ lệ chính xác (%) theo từng môn.
- 🎬 **YouTube Harvester & Zero-Disk Storage**:
  - Không tải file video nặng hàng chục GB về máy tính.
  - Tự động bóc tách phụ đề (transcript) có gắn **mốc thời gian từng giây (timestamp)** từ YouTube.
- 🎯 **Trợ lý AI Định vị Chính xác (Smart Precision RAG)**:
  - Khi học sinh hỏi kiến thức, AI trả lời kèm **Interactive Media Block**: Nhúng trình phát video tự động nhảy đến đúng **phút:giây** mà thầy cô đang giảng đoạn đó!
  - Định vị chính xác số trang tài liệu PDF.
- 📷 **Vision AI & OCR Đề Thi Mạng Xã Hội**:
  - Học sinh có thể tải ảnh chụp đề thi (chụp bằng điện thoại hoặc tải từ nhóm Facebook).
  - AI tự động nhận diện chữ, công thức toán và **bóc tách thành đề trắc nghiệm có thể bấm chọn A-B-C-D và làm bài trực tiếp**.
- 💬 **Chọn Đề Thi Bằng Cách Chat Trực Tiếp Với AI**:
  - Học sinh chỉ cần chat: *"Hôm nay tôi muốn làm 1 đề thi tốt nghiệp"*, *"Cho tôi 1 bài kiểm tra về đạo hàm"*.
  - AI tự động quét ngân hàng đề thi và hiển thị thẻ đề thi với nút **"Vào làm ngay"**.
- 📝 **Hệ thống Luyện thi & Chấm điểm Tự động**:
  - Đồng hồ đếm ngược thời gian làm bài thi.
  - Tự động nộp bài khi hết giờ, chấm điểm thang 10 và hiển thị lời giải chi tiết.
- 📊 **Bộ đếm tiến độ học tập & Sổ lỗi sai**:
  - Trực quan hóa số đề **Đã làm / Còn lại** của từng môn.
  - Tự động lưu lại các câu làm sai để học sinh ôn tập lại lỗ hổng kiến thức.

---

## 🏗️ 2. Kiến Trúc Kỹ Thuật (Tech Stack)

### **Backend (FastAPI - Python 3.10+)**
- **Framework:** FastAPI (RESTful API, Streaming Responses)
- **Database:** SQLite + SQLAlchemy 2.0 ORM
- **Xử lý tài liệu & OCR:**
  - `python-docx` (đọc file Word)
  - `PyPDF2` (đọc file PDF)
  - `Vision Parser & OCR` (bóc tách đề thi từ hình ảnh)
- **YouTube Harvester:** Tự động lấy transcript có timestamp từ YouTube API
- **RAG Engine:** Phân tách text thông minh, tính điểm trọng số và truy xuất tọa độ vị trí
- **AI Local Engine:** Kết nối **Ollama** (`qwen2.5:7b` hoặc `gemma2:2b`) & sẵn sàng mở rộng sang **Gemini API**

### **Frontend (React - SPA)**
- **Bundler:** Vite 5.x
- **Core:** React 18.x
- **Routing:** React Router DOM 6.x
- **UI Components:**
  - Interactive YouTube Player với tham số `?start={giây}`
  - Đồng hồ đếm ngược thi trắc nghiệm
  - Bộ đếm tiến độ Progress Bar

---

## 📂 3. Cấu Trúc Thư Mục Dự Án

```
StudyApp/
├── README.md                      # Tài liệu tổng quan dự án
├── HUONG_DAN_CHAY.md              # Hướng dẫn chi tiết cách chạy app
│
├── backend/
│   ├── requirements.txt           # Danh sách thư viện Python
│   ├── studyapp.db                # Database SQLite
│   ├── app/
│   │   ├── main.py                # Entry point FastAPI, CORS, router setup
│   │   ├── core/
│   │   │   ├── database.py        # Cấu hình engine, session, data directory
│   │   │   ├── logging_config.py  # Hệ thống log chuẩn hóa
│   │   │   └── seed.py            # Dữ liệu preset chuẩn: 3 môn + bài học + đề thi mẫu
│   │   ├── models/
│   │   │   ├── models.py          # ORM Models (Subject, Lesson, Exam, KnowledgeChunk...)
│   │   │   └── schemas.py         # Pydantic schemas
│   │   ├── api/
│   │   │   ├── structure.py       # API Quản lý cây môn học / chương / bài học
│   │   │   ├── files.py           # API Upload PDF, DOCX, Video, Transcript
│   │   │   ├── exams.py           # API Đề thi, nộp bài, tính điểm, bộ đếm
│   │   │   ├── stats.py           # API Thống kê dashboard, sổ lỗi sai
│   │   │   └── chat.py            # API Chat AI định vị video & import ảnh đề thi
│   │   └── ai/
│   │       ├── ollama_client.py   # Client giao tiếp với Ollama (Streaming)
│   │       ├── rag.py             # Smart Precision RAG (YouTube timestamp, PDF page)
│   │       ├── youtube_harvester.py # Module cào transcript YouTube có mốc thời gian
│   │       └── vision_parser.py   # Module OCR đọc ảnh đề thi từ mạng xã hội
│   └── data/                      # Lưu trữ file tài liệu
│
└── frontend/
    └── src/
        ├── App.jsx                # Router điều hướng
        ├── components/
        │   └── Sidebar.jsx        # Thanh menu
        └── pages/
            ├── Dashboard.jsx      # Thống kê & Bộ đếm đề thi
            ├── Subjects.jsx       # Quản lý 3 môn học & tài liệu
            ├── Exams.jsx          # Danh sách đề thi & Bộ đếm
            ├── ExamTake.jsx       # Giao diện thi trắc nghiệm tính giờ & chấm điểm
            ├── Chat.jsx           # Khung chat AI, video player định vị & quét ảnh đề
            ├── Mistakes.jsx       # Sổ lỗi sai (Mistake Log) chi tiết từng câu
            └── Stats.jsx          # Thống kê năng lực chuyên sâu theo từng môn
```

---

## 🚀 4. Hướng Dẫn Khởi Chạy Ứng Dụng

### Bước 1: Chạy Backend (FastAPI)
Mở terminal tại thư mục `backend`:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
> Khi khởi động lần đầu, hệ thống sẽ tự động khởi tạo cơ sở dữ liệu và seed sẵn cấu trúc 3 môn Toán - Lý - Hóa 12 cùng các đề thi mẫu!

### Bước 2: Chạy Frontend (React)
Mở terminal thứ hai tại thư mục `frontend`:
```powershell
npm install
npm run dev
```
Truy cập ứng dụng tại: **[http://localhost:5173](http://localhost:5173)**

---

## 💡 5. Hướng Dẫn Trải Nghiệm Các Tính Năng Mới

1. **Hỏi AI để xem video nhảy đúng phút:giây**:
   - Vào menu **"Chat AI"**.
   - Gõ: *"Giải thích cho tôi chu kỳ dao động của con lắc lò xo"* hoặc bấm vào các nút gợi ý câu hỏi nhanh.
   - AI sẽ trả lời và hiện ngay khung video phát đúng đoạn thầy cô đang giảng công thức đó!
2. **Quét ảnh đề thi chụp trên mạng xã hội**:
   - Trong trang **"Chat AI"**, bấm nút **"📷 Quét ảnh đề thi (FB/Ảnh)"**.
   - Chọn một bức ảnh đề thi chụp bằng điện thoại.
   - Hệ thống sẽ tự động đọc câu hỏi, tạo đề thi trắc nghiệm và chuyển bạn vào làm bài ngay lập tức!
3. **Chat để chọn đề thi**:
   - Gõ: *"Hôm nay tôi muốn làm 1 đề thi tốt nghiệp"* ➔ Thẻ đề thi sẽ xuất hiện kèm nút **"📝 Vào làm ngay"**.

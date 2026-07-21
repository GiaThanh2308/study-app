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

---

# Giai đoạn 3 — AI Engine

Cần cài Ollama (https://ollama.com/download) và tải model:
```
ollama pull qwen2.5:7b
```
(hoặc `qwen2.5:3b` nếu máy yếu — model nhẹ hơn, phù hợp máy không GPU RAM 16GB)

---

# Giai đoạn 4 — RAG (Chat với tài liệu, có trích nguồn)

## Cần thêm 1 model embedding
```
ollama pull nomic-embed-text
```
Model này nhẹ (~270MB), dùng để "hiểu nghĩa" văn bản, khác với model chat (qwen2.5).

## Cài thêm thư viện Python
```
cd D:\StudyApp\backend
venv\Scripts\activate
pip install -r requirements.txt
```
(sẽ cài thêm `pypdf` và `chromadb`)

## Cách dùng
1. Vào "Môn học" → upload 1 file PDF vào bài học nào đó
2. Bấm nút **"Xử lý AI"** cạnh tên file PDF — hệ thống sẽ đọc, chia đoạn, tạo embedding, lưu vào vector database (chạy nền, PDF càng dài càng lâu, vài chục giây tới vài phút)
3. Vào "Chat AI" → tick **"Chat với tài liệu (RAG)"** → chọn tài liệu (hoặc để "Tất cả")
4. Hỏi câu liên quan tới nội dung PDF — AI sẽ trả lời dựa trên tài liệu và show "Nguồn: tên file, trang X"

## Lưu ý
- Vector database lưu ở `backend/vector_store/` — nếu xóa PDF gốc thì nên xóa luôn vector tương ứng (chưa có nút xóa trên UI, có thể yêu cầu bổ sung)
- PDF dạng ảnh scan (không có text thật) sẽ không trích được nội dung — cần OCR, việc này để sau

---

# Bổ sung — Xử lý hình ảnh/đồ thị trong PDF

## Cần thêm model vision
```
ollama pull moondream
```
Model này nhẹ (~1.6GB), chuyên mô tả hình ảnh, phù hợp máy không GPU (dù vẫn chậm hơn model text).

## Cài thêm thư viện
```
cd D:\studyapp\backend
venv\Scripts\activate
pip install -r requirements.txt
```
(sẽ cài thêm `pymupdf`, thay thế `pypdf` để đọc PDF mạnh hơn)

## Cách hoạt động
Khi bấm "Xử lý AI" trên 1 file PDF, hệ thống sẽ:
1. Đọc text từng trang như trước
2. Nếu trang có hình ảnh/đồ thị nhúng, chụp lại cả trang, gửi cho model vision mô tả bằng lời
3. Gộp mô tả đó vào text của trang trước khi tạo embedding

**Kết quả**: khi hỏi về 1 bài có đồ thị, AI sẽ có thêm "mô tả bằng lời" của đồ thị đó làm dữ kiện, dù bản thân model chat không trực tiếp "nhìn" ảnh lúc trả lời.

## Lưu ý quan trọng
- Bước này làm **chậm hơn đáng kể** thời gian xử lý PDF (mỗi trang có hình sẽ tốn thêm vài chục giây gọi model vision) — file nhiều trang có hình sẽ xử lý lâu, cứ để chạy nền
- Chất lượng mô tả phụ thuộc vào model vision nhẹ (moondream) — không hoàn hảo như GPT-4 Vision, có thể mô tả sai chi tiết với đồ thị phức tạp, nên vẫn cần tự kiểm tra lại nếu câu trả lời liên quan tới hình có vẻ không hợp lý
- Nếu chưa cài `moondream`, hệ thống vẫn xử lý PDF bình thường (bỏ qua bước mô tả hình, không báo lỗi)



---

# Bổ sung — Đổi sang model embedding mạnh nhất (qwen3-embedding:8b)

## Cần tải model mới
```
ollama pull qwen3-embedding:8b
```
Model này nặng ~4.7GB (bản Q4), mạnh nhất về hiểu đa ngôn ngữ (bao gồm tiếng Việt) trong các model embedding chạy được qua Ollama tính đến giữa 2026.

## ⚠️ BẮT BUỘC: Xóa vector database cũ trước khi dùng
Vì đổi model embedding, các vector cũ (tạo bằng `nomic-embed-text`) không còn tương thích — dùng lẫn sẽ cho kết quả tìm kiếm sai hoàn toàn. Xóa thư mục:
```
cd D:\studyapp\backend
rmdir /s /q vector_store
```
Sau đó vào "Môn học", bấm **"Xử lý lại"** trên từng file PDF đã xử lý trước đó để tạo lại vector bằng model mới.

## Lưu ý về tốc độ/RAM
- Xử lý hàng loạt (nhiều trang PDF) bằng model 8B sẽ **chậm hơn đáng kể** so với nomic-embed-text — nên cân nhắc dùng máy mạnh hơn để xử lý số lượng lớn tài liệu, rồi copy `vector_store/` + `studyapp.db` + `data/` sang máy yếu hơn để chỉ dùng (hỏi đáp), không xử lý.
- Máy dùng để **hỏi đáp** (không xử lý) vẫn cần cài đúng `qwen3-embedding:8b` này, dù không dùng để xử lý hàng loạt — vì mỗi câu hỏi cũng cần tạo embedding để tìm kiếm, phải cùng model với lúc xử lý dữ liệu.

---

# Giai đoạn 5 — Video Intelligence (Whisper)

## Cần cài ffmpeg (bắt buộc, Whisper dùng để đọc audio từ video)
1. Tải bản "essentials" tại: https://www.gyan.dev/ffmpeg/builds/
2. Giải nén vào ổ D (VD: `D:\ffmpeg`)
3. Thêm `D:\ffmpeg\bin` vào biến môi trường PATH của Windows:
   - Tìm "Environment Variables" trong Windows Search
   - Sửa biến `Path` (phần User hoặc System đều được), thêm dòng mới: `D:\ffmpeg\bin`
   - Mở terminal MỚI, gõ `ffmpeg -version` để kiểm tra đã nhận chưa

## Cài thêm thư viện Python
```
cd D:\studyapp\backend
venv\Scripts\activate
pip install -r requirements.txt
```
(sẽ cài thêm `faster-whisper`)

## ⚠️ Cập nhật database
Model `Video` có thêm cột `rag_status` mới — cần xóa database cũ:
```
del studyapp.db
```
(mất môn/chương/bài đã tạo, cần tạo lại — file vật lý trong `data/` vẫn còn)

## Cách dùng
1. Vào "Môn học" → upload video vào bài học
2. Bấm "Xử lý AI" cạnh video đó → hệ thống chạy Whisper nghe audio, tạo transcript, tạo embedding
3. Vào "Chat AI" → tick RAG mode → hỏi về nội dung video
4. AI trả lời kèm nguồn dạng "🎥 Tên video, phút 03:41" — bấm vào để xem video ngay từ giây đó

## Lưu ý quan trọng về tốc độ
- Model Whisper mặc định đang để `"base"` (nhẹ, cho máy không GPU) — có thể đổi sang `"small"` (chính xác hơn, chậm hơn) trong file `app/ai/video/whisper_transcribe.py`, dòng `WHISPER_MODEL_SIZE`
- Xử lý video CPU khá chậm — 1 video 20 phút có thể mất **10-30 phút xử lý** tùy độ dài và cấu hình máy, khuyến khích xử lý trên máy xịn rồi copy dữ liệu về như đã bàn trước đó
- Nếu dùng máy xịn có GPU, đổi `WHISPER_DEVICE = "cuda"` và `WHISPER_COMPUTE_TYPE = "float16"` trong file trên để tăng tốc đáng kể, đồng thời có thể đổi `WHISPER_MODEL_SIZE = "medium"` hoặc `"large-v3"` cho độ chính xác cao hơn

## Giới hạn hiện tại
- Dropdown "chọn tài liệu cụ thể" trong Chat AI hiện chỉ áp dụng cho PDF, chưa hỗ trợ chọn 1 video cụ thể — để "Tất cả tài liệu đã xử lý" thì AI vẫn tìm được trong cả PDF lẫn video

---

# Giai đoạn 6 — Learning System (Luyện tập, Flashcard, Sổ lỗi sai, Thống kê)

## Không cần cài thêm thư viện gì mới
Chỉ dùng lại đúng các thư viện đã cài từ trước.

## ⚠️ Cập nhật database (bắt buộc)
Thêm 4 bảng mới: Question, Answer, StudyHistory, Flashcard — cần xóa database cũ:
```
cd D:\studyapp\backend
del studyapp.db
```
(mất môn/chương/bài — cần tạo lại; file PDF/video vật lý trong `data/` không mất)

## Các tính năng mới

### 1. Luyện tập (trang có 4 tab)
- **Làm bài**: chọn môn, làm 10 câu random, chấm điểm ngay, hiện giải thích khi sai
- **Thêm câu hỏi**: nhập tay câu hỏi + 4 đáp án, tick đáp án đúng
- **AI tạo câu hỏi**: chọn môn + tài liệu đã xử lý RAG (Giai đoạn 4), AI tự soạn câu hỏi dạng NHÁP — bạn xem lại, bấm "Lưu câu hỏi này" cho từng câu ưng ý mới lưu chính thức (không tự động lưu hết, tránh câu hỏi sai lọt vào)
- **Flashcard**: thêm thẻ, ôn tập theo thuật toán lặp lại ngắt quãng (Spaced Repetition) — thẻ nhớ tốt sẽ giãn cách ngày ôn ra xa dần, thẻ quên sẽ quay lại ôn sớm hơn

### 2. Sổ lỗi sai
Tự động — không cần thao tác thủ công. Câu nào làm sai lần gần nhất sẽ xuất hiện ở đây; làm lại đúng trong "Luyện tập" thì tự biến mất khỏi danh sách.

### 3. Thống kê
Tỉ lệ đúng tổng thể + theo từng môn, dựa trên toàn bộ lịch sử làm bài.

## Lưu ý về AI tạo câu hỏi
- Cần tài liệu đó đã "Xử lý AI" xong (Giai đoạn 4) trước, nếu chưa sẽ báo lỗi
- AI có thể tạo câu hỏi/đáp án sai hoặc không tự nhiên — luôn đọc kỹ trước khi bấm lưu
- Nếu AI trả JSON không đúng định dạng (model yếu đôi khi lỗi format), sẽ báo lỗi "AI trả về định dạng không hợp lệ" — thử lại hoặc giảm số câu hỏi yêu cầu

---

# Bổ sung — Tạo đề thi thử (gộp ngẫu nhiên nhiều file đề)

## Không cần cài thêm gì, không cần xóa database
Chỉ thêm code mới, không đổi cấu trúc bảng.

## Điều kiện để dùng được
1. Có ít nhất 1 file PDF đã upload với loại **"exam"** (đề thi) — hiện tại code upload chỉ hỗ trợ `doc_type="exam"` qua API, giao diện "Môn học" hiện chỉ có nút upload PDF thường (`doc_type="pdf"`). Cần dùng đúng API upload đề thi, hoặc mình bổ sung thêm nút "+ Đề thi" riêng trên giao diện nếu bạn muốn dùng tính năng này (báo mình nếu cần, hiện tại làm được qua http://127.0.0.1:8000/docs thử tay trước)
2. File đề thi đó đã "Xử lý AI" xong (Giai đoạn 4)

## Cách dùng
1. Vào "Luyện tập" → tab "Đề thi thử"
2. Chọn môn, số file đề lấy ngẫu nhiên, số câu mỗi file
3. Bấm "Tạo đề thi thử" — AI đọc từng file, soạn câu hỏi, gộp thành 1 đề — **có thể mất vài phút** vì gọi AI nhiều lần liên tiếp (mỗi file 1 lần gọi)
4. Làm bài như luyện tập bình thường, chấm điểm ngay, câu sai tự động vào "Sổ lỗi sai"

## Lưu ý
- Câu hỏi AI tạo ra được **lưu thẳng vào database** (không phải nháp như "AI tạo câu hỏi" đơn lẻ) — vì đề thi cần tính nhất quán khi làm, không tiện cho xem trước từng câu. Nếu chất lượng không ưng, có thể xóa câu hỏi qua `/practice/questions/{id}` (DELETE) sau

---

# Giai đoạn 7 — AI Tutor (Gia sư chủ động)

## Không cần cài thêm thư viện gì mới

## ⚠️ Cập nhật database (bắt buộc)
Thêm cột `topic` vào bảng Question — cần xóa database cũ:
```
cd D:\studyapp\backend
del studyapp.db
```

## Khác biệt với "Luyện tập" thường
| | Luyện tập / Đề thi thử | AI Gia sư |
|---|---|---|
| Phạm vi câu hỏi | Cả môn học (rộng) | 1 chủ đề cụ thể bạn chọn (hẹp, VD "Este") |
| Biết bạn yếu gì | Không | Có — dựa lịch sử làm bài theo từng chủ đề |
| Giải thích khi sai | Giải thích có sẵn (nếu có) | Có thêm nút "Giải thích sâu hơn" — AI viết giải thích riêng theo đúng lựa chọn sai của bạn |
| Sau khi xong | Không có gì thêm | Gợi ý video liên quan tới đúng chủ đề vừa luyện |

## Cách dùng
1. Vào "Luyện tập" → tab "AI Gia sư"
2. Chọn môn → bấm "Xem chủ đề đang yếu" (chỉ có dữ liệu sau khi bạn đã luyện qua AI Gia sư ít nhất 1 lần với chủ đề đó — lần đầu sẽ trống, đây là hành vi đúng, không phải lỗi)
3. Gõ tên chủ đề cần luyện (VD: "Este", "Đạo hàm hàm hợp") — AI sẽ tìm nội dung liên quan trong TOÀN BỘ tài liệu đã xử lý của môn đó (không giới hạn 1 file như "AI tạo câu hỏi" trước)
4. Làm bài — khi sai, có nút "🎓 Giải thích sâu hơn" để AI viết giải thích riêng dựa đúng vào lựa chọn sai của bạn
5. Làm hết bài → tự động gợi ý video liên quan tới chủ đề đó (nếu có video đã xử lý Whisper chứa nội dung liên quan)

## Lưu ý về độ chính xác "chủ đề đang yếu"
Tính năng này CHỈ theo dõi các câu hỏi được tạo qua chính "AI Gia sư" (có gắn `topic`) — câu hỏi nhập tay hoặc từ "AI tạo câu hỏi"/"Đề thi thử" không có `topic` nên không tính vào thống kê này. Đây là giới hạn thiết kế, không phải lỗi.

---

# Giai đoạn 8 — Analytics (Dashboard hiểu người học)

## Không cần cài thêm gì, không cần xóa database
Chỉ thêm code mới (endpoint + trang), không đổi cấu trúc bảng.

## Trang Dashboard giờ hiển thị
1. **Tổng giờ học (ước tính)** — không phải số chính xác tuyệt đối, mà ước lượng dựa trên các hoạt động (làm bài, chat) gom thành từng phiên học. Nếu bạn mới dùng thử vài phút, số này sẽ rất nhỏ — đây là hành vi đúng, không phải lỗi.
2. **% đúng theo từng môn** — thanh tiến độ trực quan
3. **"AI nhận thấy bạn đang yếu nhất ở..."** — tự động tìm chủ đề có tỉ lệ đúng thấp nhất (trong các chủ đề đã luyện qua "AI Gia sư", cần ít nhất 2 lần làm mới tính), kèm gợi ý video liên quan nếu có

## Vì sao "chưa đủ dữ liệu" khi mới cài đặt
Phần "điểm yếu nhất" chỉ hoạt động sau khi bạn đã dùng "AI Gia sư" (Giai đoạn 7) để luyện ít nhất 1 chủ đề, làm ít nhất 2 câu của chủ đề đó. Nếu bạn chỉ dùng "Luyện tập" thường hoặc "Đề thi thử" (không gắn `topic`), Dashboard sẽ không có dữ liệu để phân tích theo chủ đề — đây là giới hạn thiết kế đã nêu ở Giai đoạn 7.

## Logic có thể tự kiểm tra
- `_estimate_study_hours`: sort mọi timestamp, gom nhóm nếu khoảng cách giữa 2 hoạt động liên tiếp ≤ 10 phút, mỗi phiên tính tối thiểu 1 phút (tránh trường hợp 1 hoạt động đơn lẻ tính ra 0 giờ)
- Chỉ tính chủ đề có ≥ 2 lần làm vào "điểm yếu" — tránh kết luận vội vàng chỉ từ 1 câu sai

---

# Bổ sung — Quét file DOCX (Word)

## Cài thêm thư viện
```
cd D:\studyapp\backend
venv\Scripts\activate
pip install -r requirements.txt
```
(sẽ cài thêm `python-docx`)

## Không cần xóa database
Tính năng này không thêm cột/bảng mới, chỉ thêm code xử lý — chỉ cần khởi động lại backend + frontend.

## Cách dùng
Y hệt PDF — vào "Môn học", nút "+ PDF/DOCX" giờ nhận cả 2 định dạng, bấm "Xử lý AI" như bình thường.

## Khác biệt quan trọng so với PDF
- **Không có "số trang" thật** — Word không lưu cố định số trang trong file (số trang chỉ hiện lúc in/xem), nên trích dẫn DOCX ghi **"Phần X"** (theo thứ tự nội dung xử lý), không phải "Trang X"
- **Xem trước khi trích dẫn**: vì không tính được "trang" để chụp ảnh như PDF, khi bấm vào nguồn DOCX sẽ hiện **thẳng đoạn văn bản** tìm được (dạng chữ), không phải ảnh
- **Chưa xử lý hình ảnh/đồ thị trong DOCX** — khác với PDF đã có bước mô tả hình bằng model vision, DOCX hiện chỉ đọc chữ, bỏ qua hình ảnh nhúng trong file
- Hoạt động bình thường với "AI tạo câu hỏi", "Đề thi thử", "AI Gia sư" — các tính năng này không phân biệt PDF/DOCX, chỉ cần file đã "Xử lý AI" xong

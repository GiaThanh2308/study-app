# Chạy StudyApp cục bộ

Ứng dụng hiện chạy trên máy cá nhân: frontend và backend chỉ bind loopback. Chat và đọc ảnh gửi yêu cầu từ backend tới Gemini API; không cần Ollama hoặc GPU. Để giữ chi phí bằng 0, chỉ dùng quota miễn phí và không bật billing ở tài khoản provider.

## 1. Cấu hình backend

Mở PowerShell:

```powershell
cd D:\studyapp\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m app.seed_data.seed_initial
```

Mở `backend/.env`, nhập Gemini API key tại `GEMINI_API_KEY`. Nếu dùng tìm kiếm web tự động, nhập thêm Tavily free API key tại `TAVILY_API_KEY`; không có key thì tính năng đó chưa khả dụng. Không gửi hoặc commit file `.env`.

Chạy backend:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Kiểm tra `http://127.0.0.1:8000/` và tài liệu API tại `http://127.0.0.1:8000/docs`.

## 2. Chạy frontend

Mở terminal PowerShell thứ hai:

```powershell
cd -d D:\studyapp\frontend
npm install
npm run dev -- --host 127.0.0.1
```

Mở `http://127.0.0.1:5173`.

## Trạng thái database

Database mới ở `backend/data/studyapp.sqlite3`. Lệnh Alembic tạo schema; lệnh seed nạp 3 môn, 42 chủ đề và 3 blueprint phiên bản 1 từ ma trận. Database cũ `backend/studyapp.db` không được import, ghi đè hoặc xóa. App không tự tạo bảng/seed khi khởi động.

Kho đề, bộ lọc, làm bài, chấm điểm, thống kê và sổ lỗi sai hiện dùng schema mới. Bước 7 đã thêm trang **Tìm & nhập đề** ở `/imports`: tìm candidate bằng Tavily Basic miễn phí, dán URL trực tiếp, tải PDF/DOCX/TXT/MD/HTML/JPG/PNG/WebP, hoặc dán nội dung. Nếu Tavily chưa cấu hình/hết quota, dùng URL hoặc file thủ công; app không chuyển sang dịch vụ trả phí.

Mỗi nguồn vào hàng chờ duyệt trước khi xuất bản. File gốc được lưu theo SHA-256, không ghi đè; phần trích xuất là dữ liệu riêng. Đề web không cho sửa câu hỏi trích xuất. Đáp án chỉ được dùng chấm sau khi bạn xác minh. Nguồn trùng byte/nội dung được liên kết với đề có sẵn; đề gần trùng cần bạn xác nhận trước khi lưu thành bản riêng. PDF/DOCX/văn bản được trích xuất cục bộ; ảnh có thể dùng Gemini OCR nếu API key đã cấu hình, nếu không thì lưu ảnh để bạn nhập text thủ công. Đề chưa trích xuất được vẫn có thể lưu như nguồn tham khảo, nhưng không làm được bài tương tác.

### Sinh đề luyện theo ma trận (Bước 8)

Mở **Sinh đề theo ma trận** ở thanh bên hoặc `/generate`. Có hai chế độ: đề đầy đủ theo đúng ma trận môn, hoặc bộ câu hỏi theo phần/chủ đề đã chọn. Việc tạo chạy từng phần và chỉ có tối đa một job đang hoạt động. Hủy có hiệu lực giữa các lần gọi Gemini; nếu API/quota lỗi, phần đã hợp lệ được giữ lại để bạn bấm tiếp tục. StudyApp không tự retry và không đổi sang nhà cung cấp/mô hình khác.

Phân bổ nhận biết/thông hiểu/vận dụng và lớp lấy từ blueprint được lưu trong DB; các lệnh hỏi được chấm điểm có metadata riêng (mỗi ý a–d của câu đúng/sai là một đơn vị). Preset dễ/vừa/khó mặc định 30/50/20 là lựa chọn luyện tập của StudyApp, không phải tỷ lệ của Bộ. Nếu số nguyên không chia hết, app dùng largest remainder theo thứ tự trong blueprint. Với Lý/Hóa, khoảng 10+11 được chia gần đều giữa hai lớp vì ma trận không quy định tỷ lệ riêng cho từng lớp.

Bộ câu hỏi theo chủ đề có thời gian ước tính theo số câu và chuẩn hóa tổng điểm về 10 để kết quả dễ đọc; đề đầy đủ giữ nguyên điểm từng phần trong ma trận.

Đề AI tạo được lưu dạng nháp trong cùng database nhưng không xuất hiện ở kho đề cho tới khi bạn duyệt. Mở phần duyệt để xem và sửa nội dung, key, lời giải; xác nhận từng câu hoặc dùng **Tôi đã xem, xác nhận đáp án cả đề** sau khi rà toàn bộ. Sau đó xuất bản để bắt đầu làm bài; hệ thống tự chấm theo scoring config của đề. Phần đúng/sai của blueprint hiện dùng thang 2025: 1/2/3/4 ý đúng nhận 0,1/0,25/0,5/1 điểm. Key AI chưa xác nhận không thể dùng để làm bài có chấm điểm.

Generation chỉ gửi yêu cầu sinh mới và blueprint tới Gemini Developer API. Dùng API key ở `backend/.env`; để chi phí bằng 0, không bật billing ở project Google và dừng khi hết free quota. Google có thể dùng dữ liệu free-tier để cải thiện sản phẩm theo chính sách hiện hành, nên không nhập nội dung riêng tư. Hạn mức free thay đổi; ứng dụng không đảm bảo số request cố định mỗi ngày.

Tutor (Bước 9) và các trang tài liệu cũ vẫn đang chờ chuyển.

### Chấm phần trắc nghiệm đúng/sai

StudyApp chấm riêng từng câu 4 ý theo cấu trúc tốt nghiệp THPT từ năm 2025: đúng 1 ý = 0,1 điểm; đúng 2 ý = 0,25 điểm; đúng 3 ý = 0,5 điểm; đúng cả 4 ý = 1 điểm. Quy tắc này được Bộ nêu trong đề minh họa/hướng dẫn theo định dạng mới; app sẽ lưu cùng scoring config của mỗi đề để kết quả không phụ thuộc vào mặc định ẩn. Cấu trúc cho các năm sau cần được đối chiếu với công bố mới nhất của Bộ.

Backup thủ công:

```powershell
python -m app.db_admin backup
```

Khôi phục backup sau khi đã tắt backend (sẽ lưu backup tự động của DB hiện hành trước khi thay thế):

```powershell
python -m app.db_admin restore D:\studyapp\backend\data\backups\<ten-file>.sqlite3 --yes
```

Reset DB mới sau khi đã tắt backend (tự backup DB trước khi tạo lại schema và seed):

```powershell
python -m app.db_admin reset --yes
```

## Lỗi cấu hình AI thường gặp

- Chat báo chưa cấu hình: kiểm tra `GEMINI_API_KEY` trong `backend/.env`, sau đó khởi động lại backend.
- Gemini báo giới hạn hoặc quota: đợi quota miễn phí được làm mới; ứng dụng không tự chuyển sang dịch vụ trả phí.
- Tìm kiếm web chưa cấu hình: thêm `TAVILY_API_KEY` hoặc dùng phương án nhập URL/nguồn thủ công khi luồng đó được hoàn thiện.

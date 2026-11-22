# Hướng dẫn cho AI làm việc trên StudyApp

## Phạm vi dự án

- Ứng dụng học tập cá nhân, chạy cục bộ trên Windows.
- Backend dùng Python, FastAPI, SQLAlchemy và Alembic; sinh câu hỏi luyện tập qua Gemini Developer API.
- Frontend dùng npm/Vite (giao diện phát triển thường chạy tại `http://127.0.0.1:5173`); API backend thường chạy tại `http://127.0.0.1:8000`.
- Đề tìm được hoặc do người dùng nhập phải được giữ nguyên nội dung nguồn. Chỉ câu hỏi AI tạo mới được kiểm tra theo ma trận/quy chuẩn; không gắn nhãn đề AI tạo thành đề chính thức.
- Đây là ứng dụng cá nhân và ưu tiên không phát sinh chi phí. Không thêm dịch vụ trả phí, model local nặng, hoặc tự động gửi dữ liệu ra ngoài nếu chưa được người dùng yêu cầu.

## Lệnh thường dùng (PowerShell)

### Backend

```powershell
cd D:\studyapp\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Nếu môi trường ảo chưa tồn tại, tạo và cài dependency theo manifest thực tế của backend (kiểm tra `requirements.txt` hoặc `pyproject.toml` trước khi cài):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Migration Alembic:

```powershell
cd D:\studyapp\backend
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

Chỉ tạo migration sau khi cập nhật model và kiểm tra kỹ migration được sinh. Không sửa/xóa migration đã áp dụng để thay đổi lịch sử schema; tạo migration mới để điều chỉnh.

### Frontend

```powershell
cd D:\studyapp\frontend
npm install
npm run dev
npm run
npm run build
```

Chạy kiểm tra frontend bằng script đã khai báo trong `frontend\package.json` (ví dụ `npm test` hoặc `npm run lint` nếu script đó tồn tại). Không tự giả định một script không có trong manifest.

### Kiểm tra backend

Chạy từ `D:\studyapp\backend`, dùng Python trong virtualenv. Nếu dự án có bộ pytest:

```powershell
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\python.exe -m compileall app
```

Chỉ chạy lệnh test/lint khi phù hợp với phạm vi thay đổi; trước khi kết luận đã kiểm tra, nêu rõ lệnh nào thực sự chạy và kết quả.

## Quy tắc bắt buộc

1. Đọc cấu trúc và các manifest (`requirements.txt`/`pyproject.toml`, `package.json`, cấu hình Alembic, `.env.example`) trước khi thay đổi; tuân theo dependency và scripts đang có.
2. Giữ bí mật trong `.env`; không in, commit, chép vào log hoặc đưa API key/token vào frontend. Chỉ sửa `.env.example` để cập nhật tên biến mẫu, tuyệt đối không điền secret thật.
3. Không đổi nội dung đề nguồn khi nhập hoặc tìm từ Internet. Lưu nguồn/URL và metadata riêng; phát hiện trùng bằng khóa/chuẩn hóa phù hợp, không gộp âm thầm các câu chỉ vì giống văn bản.
4. Câu hỏi AI phải qua xác thực cấu trúc trước khi lưu: nội dung đầy đủ, đáp án hợp lệ, các lựa chọn trắc nghiệm không rỗng/không trùng, định dạng đúng-sai và lệnh hỏi chấm điểm đúng quy chuẩn. Khi một câu sai, không đánh dấu cả phần hoàn tất.
5. Giữ các khái niệm ma trận kiến thức/nhận thức tách biệt với độ khó luyện tập. Độ khó mặc định đã thống nhất là dễ/vừa/khó 30/50/20; tính phân bổ trên lệnh hỏi được chấm điểm nếu đặc tả hiện hành không nói khác.
6. Không log prompt đầy đủ, nội dung cá nhân, API key hoặc headers. Log lỗi cần hữu ích nhưng đã loại bỏ bí mật.
7. Giữ thay đổi nhỏ theo yêu cầu; không thêm dịch vụ trả phí hoặc tự ý gửi thông điệp, deploy, publish hay thay đổi dữ liệu người dùng.
8. Sau thay đổi schema database, dùng migration Alembic. Không sửa database trực tiếp để thay thế migration.
9. Không xóa/ghi đè thay đổi sẵn có của người dùng. Trước khi commit, xem `git status` và chỉ stage đúng file thuộc công việc.
10. Khi báo cáo, phân biệt rõ điều đã xác minh với giả định; nêu giới hạn và lệnh kiểm tra đã chạy.

## Đường dẫn không được tự ý sửa đổi hoặc xóa

- `D:\studyapp\.git\` — metadata và lịch sử Git.
- `D:\studyapp\backend\venv\` — môi trường Python cục bộ.
- `D:\studyapp\frontend\node_modules\` — dependency cài bằng npm.
- `D:\studyapp\backend\.env` và mọi file `.env` — bí mật/cấu hình máy cá nhân.
- File database cục bộ (SQLite hoặc DB khác), thư mục upload/storage/cache và dữ liệu đề/bài làm của người dùng — dữ liệu cá nhân cần bảo toàn.

Các đường dẫn này chỉ được đụng tới khi chính người dùng yêu cầu rõ thao tác cụ thể. Không đưa chúng vào lệnh dọn dẹp/reset tổng quát. Nếu chưa rõ file nào là database hoặc dữ liệu người dùng, dừng thao tác phá hủy và kiểm tra cấu hình trước.

## Quy trình khi nhận việc

1. Xác định yêu cầu và tiêu chí chấp nhận; đọc code/config liên quan.
2. Báo trước kế hoạch ngắn nếu thay đổi nhiều phần; với yêu cầu từng bước, chỉ thực hiện bước người dùng đã duyệt.
3. Thực hiện thay đổi tối thiểu; giữ tương thích API/schema và dữ liệu hiện có.
4. Chạy kiểm tra phù hợp, xem diff và trạng thái Git.
5. Tóm tắt file thay đổi, hành vi, kiểm tra đã chạy và phần còn cần người dùng nghiệm thu.

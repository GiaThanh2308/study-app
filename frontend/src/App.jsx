import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Exams from "./pages/Exams";
import ExamTake from "./pages/ExamTake";
import Mistakes from "./pages/Mistakes";
import Stats from "./pages/Stats";
import Placeholder from "./pages/Placeholder";
import ImportExams from "./pages/ImportExams";
import GenerateExam from "./pages/GenerateExam";

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: "flex" }}>
        <Sidebar />
        <div style={{ flex: 1, overflowY: "auto", height: "100vh" }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/subjects" element={<Placeholder title="Môn học" message="Quản lý curriculum sẽ được chuyển sang schema mới trong Bước 10." />} />
            <Route path="/exams" element={<Exams />} />
            <Route path="/imports" element={<ImportExams />} />
            <Route path="/generate" element={<GenerateExam />} />
            <Route path="/exam-take/:examId/:attemptId" element={<ExamTake />} />
            <Route path="/chat" element={<Placeholder title="Tutor AI" message="Tutor sẽ được nối lại với dữ liệu mới trong Bước 9." />} />
            <Route path="/mistakes" element={<Mistakes />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/settings" element={<Placeholder title="Cài đặt" message="Cài đặt local sẽ được hoàn thiện trong Bước 10." />} />
            <Route path="*" element={<Placeholder title="Không tìm thấy trang" message="Hãy chọn một mục trên thanh điều hướng." />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

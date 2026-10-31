import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Subjects from "./pages/Subjects";
import Exams from "./pages/Exams";
import ExamTake from "./pages/ExamTake";
import Chat from "./pages/Chat";
import Mistakes from "./pages/Mistakes";
import Stats from "./pages/Stats";
import Placeholder from "./pages/Placeholder";

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: "flex" }}>
        <Sidebar />
        <div style={{ flex: 1, overflowY: "auto", height: "100vh" }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/subjects" element={<Subjects />} />
            <Route path="/exams" element={<Exams />} />
            <Route path="/exam-take/:examId/:attemptId" element={<ExamTake />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/mistakes" element={<Mistakes />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/settings" element={<Placeholder title="Cài đặt" />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

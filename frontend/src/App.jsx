import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Subjects from "./pages/Subjects";
import Chat from "./pages/Chat";
import Placeholder from "./pages/Placeholder";

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: "flex" }}>
        <Sidebar />
        <div style={{ flex: 1, overflowY: "auto", height: "100vh" }}>
          <Routes>
            <Route path="/" element={<Placeholder title="Dashboard" />} />
            <Route path="/subjects" element={<Subjects />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/practice" element={<Placeholder title="Luyện tập" />} />
            <Route path="/mistakes" element={<Placeholder title="Sổ lỗi sai" />} />
            <Route path="/stats" element={<Placeholder title="Thống kê" />} />
            <Route path="/settings" element={<Placeholder title="Cài đặt" />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Subjects from "./pages/Subjects";
import Chat from "./pages/Chat";
import Practice from "./pages/Practice";
import Mistakes from "./pages/Mistakes";
import Stats from "./pages/Stats";
import Placeholder from "./pages/Placeholder";

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: "flex", background: "#f7fafc", minHeight: "100vh" }}>
        <Sidebar />
        <div style={{ flex: 1, overflowY: "auto", height: "100vh" }}>
          <div style={{ maxWidth: 1000, margin: "0 auto" }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/subjects" element={<Subjects />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/practice" element={<Practice />} />
              <Route path="/mistakes" element={<Mistakes />} />
              <Route path="/stats" element={<Stats />} />
              <Route path="/settings" element={<Placeholder title="Cài đặt" />} />
            </Routes>
          </div>
        </div>
      </div>
    </BrowserRouter>
  );
}

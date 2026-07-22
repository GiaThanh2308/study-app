import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Subjects from "./pages/Subjects";
import Chat from "./pages/Chat";
import Practice from "./pages/Practice";
import Mistakes from "./pages/Mistakes";

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: "flex", background: "var(--color-bg)", minHeight: "100vh" }}>
        <Sidebar />
        <div style={{ flex: 1, overflowY: "auto", height: "100vh" }}>
          <div style={{ maxWidth: 1000, margin: "0 auto" }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/subjects" element={<Subjects />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/practice" element={<Practice />} />
              <Route path="/mistakes" element={<Mistakes />} />
            </Routes>
          </div>
        </div>
      </div>
    </BrowserRouter>
  );
}

import { useEffect, useRef, useState } from "react";
import api from "../api";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [ollamaOk, setOllamaOk] = useState(true);
  const [ragMode, setRagMode] = useState(false);
  const [ragDocs, setRagDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [expandedSource, setExpandedSource] = useState(null); // key: "msgIndex-sourceIndex"
  const bottomRef = useRef(null);

  useEffect(() => {
    api.get("/chat/history").then((res) => setMessages(res.data));
    api.get("/chat/status").then((res) => setOllamaOk(res.data.ollama_running));
    api.get("/rag/documents").then((res) => setRagDocs(res.data));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userText = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setLoading(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "", sources: [] }]);

    try {
      const url = ragMode
        ? "http://127.0.0.1:8000/api/rag/chat"
        : "http://127.0.0.1:8000/api/chat/send";
      const body = ragMode
        ? { message: userText, document_id: selectedDoc }
        : { message: userText };

      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let raw = "";
      let sources = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        raw += decoder.decode(value, { stream: true });

        // Tách phần __SOURCES__...__END_SOURCES__ nếu có (chỉ xuất hiện ở đầu, chế độ RAG)
        let displayText = raw;
        const sourceMatch = raw.match(/^__SOURCES__(.*?)__END_SOURCES__/s);
        if (sourceMatch) {
          try {
            sources = JSON.parse(sourceMatch[1]);
          } catch {}
          displayText = raw.replace(/^__SOURCES__.*?__END_SOURCES__/s, "");
        }

        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: displayText, sources };
          return updated;
        });
      }
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "⚠️ Lỗi kết nối AI. Kiểm tra Ollama có đang chạy không.",
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", height: "100vh", boxSizing: "border-box" }}>
      <h2>Chat AI</h2>

      {!ollamaOk && (
        <div style={styles.warning}>
          ⚠️ Không kết nối được Ollama. Mở terminal, chạy <code>ollama serve</code> hoặc kiểm tra Ollama đã cài đúng chưa.
        </div>
      )}

      <div style={styles.modeBar}>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
          <input
            type="checkbox"
            checked={ragMode}
            onChange={(e) => setRagMode(e.target.checked)}
          />
          Chat với tài liệu (RAG)
        </label>
        {ragMode && (
          <select
            value={selectedDoc || ""}
            onChange={(e) => setSelectedDoc(e.target.value ? Number(e.target.value) : null)}
            style={{ padding: 6, borderRadius: 6 }}
          >
            <option value="">Tất cả tài liệu đã xử lý</option>
            {ragDocs.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        )}
        {ragMode && ragDocs.length === 0 && (
          <span style={{ fontSize: 13, color: "#c05621" }}>
            Chưa có tài liệu nào được xử lý. Vào "Môn học" → bấm "Xử lý AI" trên 1 file PDF trước.
          </span>
        )}
      </div>

      <div style={styles.chatBox}>
        {messages.length === 0 && (
          <div style={{ color: "#a0aec0" }}>Bắt đầu hỏi AI điều gì đó...</div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={m.role === "user" ? styles.userMsg : styles.aiMsg}>
            <b>{m.role === "user" ? "Bạn" : "AI"}:</b> {m.content || (loading && i === messages.length - 1 ? "..." : "")}
            {m.sources && m.sources.length > 0 && (
              <div style={styles.sourceBox}>
                📚 Nguồn:{" "}
                {m.sources.map((s, si) => {
                  const key = `${i}-${si}`;
                  const isOpen = expandedSource === key;
                  const label =
                    s.type === "video"
                      ? `🎥 ${s.source_name}, phút ${s.timestamp}`
                      : `📄 ${s.source_name}, trang ${s.page}`;
                  return (
                    <button
                      key={si}
                      style={{ ...styles.sourceTag, background: isOpen ? "#bee3f8" : "#ebf8ff" }}
                      onClick={() => setExpandedSource(isOpen ? null : key)}
                      title={s.type === "video" ? "Bấm để xem video từ đúng thời điểm" : "Bấm để xem trang PDF"}
                    >
                      {label} {isOpen ? "▲" : "▼"}
                    </button>
                  );
                })}

                {m.sources.map((s, si) => {
                  const key = `${i}-${si}`;
                  if (expandedSource !== key || !s.file_path) return null;

                  if (s.type === "video") {
                    const url = `http://127.0.0.1:8000/data/${s.file_path}#t=${s.start_seconds}`;
                    return (
                      <div key={`preview-${si}`} style={styles.pdfPreview}>
                        <video src={url} controls style={{ width: "100%" }} />
                      </div>
                    );
                  }
                  const url = `http://127.0.0.1:8000/data/${s.file_path}#page=${s.page}`;
                  return (
                    <div key={`preview-${si}`} style={styles.pdfPreview}>
                      <iframe
                        src={url}
                        title={`${s.source_name} trang ${s.page}`}
                        style={styles.pdfIframe}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Nhập câu hỏi..."
          style={styles.input}
          disabled={loading}
        />
        <button onClick={send} disabled={loading} style={styles.btn}>
          {loading ? "Đang trả lời..." : "Gửi"}
        </button>
      </div>
    </div>
  );
}

const styles = {
  warning: {
    background: "#fffaf0",
    border: "1px solid #f6ad55",
    color: "#c05621",
    padding: 10,
    borderRadius: 6,
    marginBottom: 12,
    fontSize: 14,
  },
  modeBar: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginBottom: 12,
    padding: 10,
    background: "#f7fafc",
    borderRadius: 6,
  },
  sourceBox: {
    marginTop: 6,
    fontSize: 12,
    color: "#2b6cb0",
  },
  sourceTag: {
    background: "#ebf8ff",
    color: "#2b6cb0",
    padding: "2px 8px",
    borderRadius: 4,
    marginRight: 6,
    marginTop: 4,
    display: "inline-block",
    border: "1px solid #bee3f8",
    cursor: "pointer",
    fontSize: 12,
  },
  pdfPreview: {
    marginTop: 8,
    border: "1px solid #cbd5e0",
    borderRadius: 6,
    overflow: "hidden",
  },
  pdfIframe: {
    width: "100%",
    height: 500,
    border: "none",
  },
  chatBox: {
    flex: 1,
    overflowY: "auto",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 18,
    background: "#fff",
    boxShadow: "var(--shadow-sm)",
  },
  userMsg: {
    background: "var(--color-primary)",
    color: "#fff",
    padding: "10px 14px",
    borderRadius: "14px 14px 4px 14px",
    marginBottom: 10,
    maxWidth: "78%",
    marginLeft: "auto",
    lineHeight: 1.5,
  },
  aiMsg: {
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    padding: "10px 14px",
    borderRadius: "14px 14px 14px 4px",
    marginBottom: 10,
    maxWidth: "78%",
    lineHeight: 1.5,
  },
  input: { flex: 1, padding: "11px 14px", border: "1px solid #cbd5e0", borderRadius: 10, fontSize: 14 },
  btn: {
    padding: "11px 20px",
    background: "var(--color-primary)",
    color: "#fff",
    border: "none",
    borderRadius: 10,
    cursor: "pointer",
    fontWeight: 500,
  },
};

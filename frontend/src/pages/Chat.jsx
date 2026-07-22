import { useEffect, useRef, useState } from "react";
import api from "../api";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [ollamaOk, setOllamaOk] = useState(true);
  const [ragMode, setRagMode] = useState(false);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [ragDocs, setRagDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [expandedSource, setExpandedSource] = useState(null); // key: "msgIndex-sourceIndex"
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    api.get("/chat/history").then((res) => setMessages(res.data));
    api.get("/chat/status").then((res) => setOllamaOk(res.data.ollama_running));
    api.get("/subjects").then((res) => setSubjects(res.data));
  }, []);

  // Khi đổi môn học, tải lại danh sách tài liệu đã xử lý CỦA ĐÚNG môn đó, bỏ chọn tài liệu cũ
  useEffect(() => {
    const url = selectedSubject ? `/rag/documents?subject_id=${selectedSubject}` : "/rag/documents";
    api.get(url).then((res) => setRagDocs(res.data));
    setSelectedDoc(null);
  }, [selectedSubject]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userText = input;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setLoading(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "", sources: [] }]);

    try {
      const url = ragMode
        ? "http://127.0.0.1:8000/api/rag/chat"
        : "http://127.0.0.1:8000/api/chat/send";
      const body = ragMode
        ? { message: userText, document_id: selectedDoc, subject_id: selectedDoc ? null : selectedSubject }
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

        // Marker __SOURCES__...__END_SOURCES__ giờ nằm ở CUỐI stream (backend chỉ gửi sau khi
        // biết chắc AI có thực sự dùng được tài liệu để trả lời hay không) — không còn ở đầu nữa.
        let displayText = raw;
        const sourceMatch = raw.match(/__SOURCES__(.*?)__END_SOURCES__/s);
        if (sourceMatch) {
          try {
            sources = JSON.parse(sourceMatch[1]);
          } catch {}
          displayText = raw.replace(/__SOURCES__.*?__END_SOURCES__/s, "");
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

  const handleTextareaInput = (e) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div style={styles.page}>
      {/* Thanh trên: tiêu đề + chế độ RAG */}
      <div style={styles.topBar}>
        <h1 style={styles.title}>Chat AI</h1>

        <div style={styles.modeRow}>
          <label style={styles.ragToggle}>
            <input
              type="checkbox"
              checked={ragMode}
              onChange={(e) => setRagMode(e.target.checked)}
              style={styles.checkbox}
            />
            <span>📎 Chat với tài liệu (RAG)</span>
          </label>

          {ragMode && (
            <div style={styles.subjectChipRow}>
              <button
                style={{ ...styles.subjectChip, ...(selectedSubject === null ? styles.subjectChipActive : {}) }}
                onClick={() => setSelectedSubject(null)}
              >
                Tất cả môn
              </button>
              {subjects.map((s) => (
                <button
                  key={s.id}
                  style={{ ...styles.subjectChip, ...(selectedSubject === s.id ? styles.subjectChipActive : {}) }}
                  onClick={() => setSelectedSubject(s.id)}
                >
                  {s.name}
                </button>
              ))}
            </div>
          )}

          {ragMode && (
            <select
              value={selectedDoc || ""}
              onChange={(e) => setSelectedDoc(e.target.value ? Number(e.target.value) : null)}
              style={styles.select}
            >
              <option value="">
                {selectedSubject ? "Tất cả tài liệu của môn này" : "Tất cả tài liệu đã xử lý"}
              </option>
              {ragDocs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          )}

          {ragMode && ragDocs.length === 0 && (
            <span style={styles.ragHint}>
              Chưa có tài liệu nào được xử lý — vào "Môn học" → bấm "Xử lý AI" trên 1 file PDF trước.
            </span>
          )}
        </div>

        {!ollamaOk && (
          <div style={styles.warning}>
            ⚠️ Không kết nối được Ollama. Mở terminal, chạy <code>ollama serve</code> hoặc kiểm tra
            Ollama đã cài đúng chưa.
          </div>
        )}
      </div>

      {/* Vùng hội thoại */}
      <div style={styles.chatArea}>
        <div style={styles.chatInner}>
          {messages.length === 0 && (
            <div style={styles.emptyState}>
              <div style={{ fontSize: 36, marginBottom: 10 }}>💬</div>
              <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>
                Bắt đầu hỏi AI điều gì đó
              </div>
              <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 18 }}>
                Bật "Chat với tài liệu" nếu muốn AI trả lời dựa trên PDF / video bạn đã xử lý.
              </div>

              <div style={styles.promptChipGrid}>
                {[
                  "Tóm tắt lý thuyết chương này giúp tôi",
                  "Giải thích khái niệm này bằng ví dụ dễ hiểu",
                  "Cho tôi 3 câu hỏi trắc nghiệm để tự kiểm tra",
                  "Giải giúp tôi bài tập khó này",
                ].map((suggestion, idx) => (
                  <button
                    key={idx}
                    style={styles.promptChip}
                    onClick={() => setInput(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => {
            const isUser = m.role === "user";
            const isTyping = loading && i === messages.length - 1 && !m.content;
            return (
              <div key={i} style={{ ...styles.msgRow, justifyContent: isUser ? "flex-end" : "flex-start" }}>
                {!isUser && <div style={styles.avatar}>🤖</div>}

                <div style={{ ...styles.bubble, ...(isUser ? styles.bubbleUser : styles.bubbleAi) }}>
                  {isTyping ? (
                    <span style={styles.typingDots}>
                      <span style={styles.dot} />
                      <span style={{ ...styles.dot, animationDelay: "0.15s" }} />
                      <span style={{ ...styles.dot, animationDelay: "0.3s" }} />
                    </span>
                  ) : (
                    <span style={{ whiteSpace: "pre-wrap" }}>{m.content}</span>
                  )}

                  {m.sources && m.sources.length > 0 && (
                    <div style={styles.sourceBox}>
                      <div style={styles.sourceLabel}>📚 Nguồn</div>
                      <div style={styles.sourceTagRow}>
                        {m.sources.map((s, si) => {
                          const key = `${i}-${si}`;
                          const isOpen = expandedSource === key;
                          const label =
                            s.type === "video"
                              ? `🎥 ${s.source_name}, phút ${s.timestamp}`
                              : s.type === "docx"
                              ? `📝 ${s.source_name}, phần ${s.part}`
                              : `📄 ${s.source_name}, trang ${s.page}`;
                          return (
                            <button
                              key={si}
                              style={{ ...styles.sourceTag, ...(isOpen ? styles.sourceTagOpen : {}) }}
                              onClick={() => setExpandedSource(isOpen ? null : key)}
                              title={
                                s.type === "video"
                                  ? "Bấm để xem video từ đúng thời điểm"
                                  : s.type === "docx"
                                  ? "Bấm để xem đoạn văn bản"
                                  : "Bấm để xem trang PDF"
                              }
                            >
                              {label} {isOpen ? "▲" : "▼"}
                            </button>
                          );
                        })}
                      </div>

                      {m.sources.map((s, si) => {
                        const key = `${i}-${si}`;
                        if (expandedSource !== key) return null;

                        if (s.type === "video") {
                          const url = `http://127.0.0.1:8000/data/${s.file_path}`;
                          return (
                            <div key={`preview-${si}`} style={styles.preview}>
                              <video
                                src={url}
                                controls
                                style={{ width: "100%", display: "block" }}
                                onLoadedMetadata={(e) => {
                                  e.target.currentTime = s.start_seconds;
                                }}
                              />
                            </div>
                          );
                        }
                        if (s.type === "docx") {
                          // DOCX không có "trang" thật để render ảnh xem trước — hiện thẳng đoạn văn bản đã tìm được
                          return (
                            <div key={`preview-${si}`} style={{ ...styles.preview, padding: 14, fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                              {s.snippet}
                            </div>
                          );
                        }
                        if (!s.document_id) return null;
                        const imgUrl = `http://127.0.0.1:8000/api/rag/page-image?document_id=${s.document_id}&page=${s.page}`;
                        return (
                          <div key={`preview-${si}`} style={styles.preview}>
                            <img src={imgUrl} alt={`${s.source_name} trang ${s.page}`} style={{ width: "100%", display: "block" }} />
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {isUser && <div style={{ ...styles.avatar, ...styles.avatarUser }}>🧑</div>}
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Thanh nhập liệu nổi phía dưới */}
      <div style={styles.inputBarWrap}>
        <div style={styles.inputBar}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            placeholder="Nhập câu hỏi... (Enter để gửi, Shift+Enter để xuống dòng)"
            style={styles.textarea}
            rows={1}
            disabled={loading}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            style={{
              ...styles.sendBtn,
              ...(loading || !input.trim() ? styles.sendBtnDisabled : {}),
            }}
          >
            {loading ? "···" : "➤"}
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    boxSizing: "border-box",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    color: "var(--color-text)",
    background: "var(--color-bg)",
  },
  topBar: {
    padding: "24px 32px 16px",
    borderBottom: "1px solid var(--color-border)",
    background: "var(--color-surface)",
  },
  title: { fontSize: 24, fontWeight: 700, margin: "0 0 14px", letterSpacing: "-0.02em" },
  modeRow: { display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" },
  ragToggle: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 13.5,
    fontWeight: 600,
    background: "#eef1ff",
    color: "#4338ca",
    padding: "8px 14px",
    borderRadius: 20,
    cursor: "pointer",
  },
  checkbox: { accentColor: "#4f46e5", width: 15, height: 15, cursor: "pointer" },
  select: {
    padding: "8px 12px",
    borderRadius: 10,
    border: "1px solid #dde1e8",
    fontSize: 13.5,
    background: "var(--color-surface)",
  },
  subjectChipRow: { display: "flex", gap: 6, flexWrap: "wrap" },
  subjectChip: {
    padding: "6px 14px",
    borderRadius: 20,
    border: "1px solid #dde1e8",
    background: "var(--color-surface)",
    color: "var(--color-text-muted)",
    fontSize: 13,
    cursor: "pointer",
    fontWeight: 500,
  },
  subjectChipActive: {
    background: "var(--color-primary)",
    color: "#fff",
    border: "1px solid var(--color-primary)",
  },
  ragHint: { fontSize: 12.5, color: "#b45309" },
  warning: {
    background: "#fef3e2",
    border: "1px solid #f6ad55",
    color: "#b45309",
    padding: "10px 14px",
    borderRadius: 10,
    marginTop: 12,
    fontSize: 13.5,
  },

  chatArea: { flex: 1, overflowY: "auto" },
  chatInner: { maxWidth: 760, margin: "0 auto", padding: "24px 24px 8px" },

  emptyState: { textAlign: "center", padding: "60px 24px" },
  promptChipGrid: {
    display: "flex",
    flexWrap: "wrap",
    gap: 8,
    justifyContent: "center",
    maxWidth: 480,
    margin: "0 auto",
  },
  promptChip: {
    padding: "9px 16px",
    borderRadius: 18,
    border: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    color: "var(--color-text)",
    fontSize: 13,
    cursor: "pointer",
    textAlign: "left",
  },

  msgRow: { display: "flex", alignItems: "flex-end", gap: 10, marginBottom: 18 },
  avatar: {
    width: 30,
    height: 30,
    borderRadius: "50%",
    background: "#eef1ff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 15,
    flexShrink: 0,
  },
  avatarUser: { background: "#e6f6f4" },

  bubble: {
    maxWidth: "72%",
    padding: "12px 16px",
    borderRadius: 16,
    fontSize: 14.5,
    lineHeight: 1.55,
  },
  bubbleUser: {
    background: "#4f46e5",
    color: "#fff",
    borderBottomRightRadius: 4,
  },
  bubbleAi: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    color: "var(--color-text)",
    borderBottomLeftRadius: 4,
    boxShadow: "0 1px 2px rgba(30,36,51,0.04)",
  },

  typingDots: { display: "inline-flex", gap: 4, padding: "2px 0" },
  dot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    background: "#a0a8b8",
    display: "inline-block",
    animation: "studyapp-typing 1s infinite ease-in-out",
  },

  sourceBox: { marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--color-border)" },
  sourceLabel: { fontSize: 11.5, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 6 },
  sourceTagRow: { display: "flex", flexWrap: "wrap", gap: 6 },
  sourceTag: {
    background: "#eef6ff",
    color: "#2563eb",
    padding: "4px 10px",
    borderRadius: 8,
    border: "1px solid #d6e8ff",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 600,
  },
  sourceTagOpen: { background: "#dbeafe" },
  preview: {
    marginTop: 8,
    border: "1px solid #dde1e8",
    borderRadius: 10,
    overflow: "hidden",
  },
  pdfIframe: { width: "100%", height: 460, border: "none", display: "block" },

  inputBarWrap: {
    borderTop: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    padding: "14px 24px 20px",
  },
  inputBar: {
    maxWidth: 760,
    margin: "0 auto",
    display: "flex",
    alignItems: "flex-end",
    gap: 10,
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: 20,
    padding: "8px 8px 8px 18px",
  },
  textarea: {
    flex: 1,
    border: "none",
    background: "transparent",
    outline: "none",
    resize: "none",
    fontSize: 14.5,
    lineHeight: 1.5,
    fontFamily: "inherit",
    padding: "8px 0",
    maxHeight: 160,
    color: "var(--color-text)",
  },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: "50%",
    border: "none",
    background: "#4f46e5",
    color: "#fff",
    fontSize: 15,
    cursor: "pointer",
    flexShrink: 0,
  },
  sendBtnDisabled: { background: "#c7cbe0", cursor: "not-allowed" },
};

// Keyframes cho hiệu ứng "đang gõ" — chèn 1 lần vào document
if (typeof document !== "undefined" && !document.getElementById("studyapp-chat-keyframes")) {
  const styleTag = document.createElement("style");
  styleTag.id = "studyapp-chat-keyframes";
  styleTag.textContent = `
    @keyframes studyapp-typing {
      0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
      30% { opacity: 1; transform: translateY(-3px); }
    }
  `;
  document.head.appendChild(styleTag);
}

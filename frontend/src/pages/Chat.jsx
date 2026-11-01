import { useEffect, useRef, useState } from "react";
import api from "../api";
import { useNavigate } from "react-router-dom";
import MathView from "../components/MathView";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [ollamaOk, setOllamaOk] = useState(true);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState(1);
  const bottomRef = useRef(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/chat/history").then((res) => setMessages(res.data));
    api.get("/chat/status").then((res) => setOllamaOk(res.data.ollama_running));
    api.get("/subjects").then((res) => {
      setSubjects(res.data);
      if (res.data.length > 0) setSelectedSubjectId(res.data[0].id);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (textToSend) => {
    const text = textToSend || input;
    if (!text.trim() || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
      const response = await fetch(`${API_BASE}/chat/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: accumulated };
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

  const startExam = async (examId) => {
    try {
      const res = await api.post(`/exams/${examId}/start`);
      navigate(`/exam-take/${examId}/${res.data.id}`);
    } catch (err) {
      alert("Lỗi khi mở bài thi: " + (err.response?.data?.detail || err.message));
    }
  };

  // Upload ảnh đề thi chụp từ Facebook / điện thoại
  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingImage(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("subject_id", selectedSubjectId);

    try {
      const res = await api.post("/chat/import-exam-image", formData);
      alert(`🎉 ${res.data.message}`);
      startExam(res.data.exam_id);
    } catch (err) {
      alert("Lỗi khi đọc ảnh đề thi: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploadingImage(false);
    }
  };

  // Bóc tách text, thẻ đề thi và media định vị chính xác
  const parseMessageContent = (content) => {
    let cleanText = content;
    let recommendedExams = [];
    let mediaAttachments = [];

    const examMatch = cleanText.match(/<!--EXAM_RECOMMENDATION:(.*?)-->/s);
    if (examMatch) {
      cleanText = cleanText.replace(examMatch[0], "").trim();
      try {
        recommendedExams = JSON.parse(examMatch[1]);
      } catch (e) {}
    }

    const mediaMatch = cleanText.match(/<!--MEDIA_ATTACHMENTS:(.*?)-->/s);
    if (mediaMatch) {
      cleanText = cleanText.replace(mediaMatch[0], "").trim();
      try {
        mediaAttachments = JSON.parse(mediaMatch[1]);
      } catch (e) {}
    }

    return { cleanText, recommendedExams, mediaAttachments };
  };

  const samplePrompts = [
    "Hôm nay tôi muốn làm 1 đề thi tốt nghiệp",
    "Giải thích cho tôi chu kỳ con lắc lò xo",
    "Tôi muốn làm bài kiểm tra về đạo hàm",
    "Chỉ cho tôi công thức este hóa môn Hóa",
  ];

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", height: "100vh", boxSizing: "border-box" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div>
          <h2 style={{ margin: 0 }}>💬 Trợ Lý AI Ôn Thi (YouTube Precision & Vision OCR)</h2>
          <span style={{ fontSize: 13, color: "#718096" }}>
            Tự động tìm kiếm video phát đúng phút:giây & quét ảnh đề thi từ mạng xã hội
          </span>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <select
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(Number(e.target.value))}
            style={{ padding: "8px 10px", borderRadius: 6, border: "1px solid #cbd5e0", fontSize: 13, background: "#fff" }}
            title="Chọn môn học cho ảnh đề thi"
          >
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>Môn: {s.name}</option>
            ))}
          </select>
          <input
            type="file"
            accept="image/*"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={handleImageUpload}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            style={styles.imageBtn}
            disabled={uploadingImage}
          >
            {uploadingImage ? "⏳ Đang quét đề..." : "📷 Quét ảnh đề (FB)"}
          </button>
          <button
            onClick={async () => {
              if (window.confirm("Xóa toàn bộ lịch sử chat?")) {
                await api.delete("/chat/history");
                setMessages([]);
              }
            }}
            style={styles.clearBtn}
          >
            🗑️ Xóa lịch sử
          </button>
        </div>
      </div>

      {!ollamaOk && (
        <div style={styles.warning}>
          ⚠️ Không kết nối được Ollama. Mở terminal và chạy lệnh <code>ollama serve</code> (hoặc <code>ollama run qwen2.5:7b</code>).
        </div>
      )}

      {/* Gợi ý câu hỏi nhanh */}
      <div style={styles.promptPillContainer}>
        <span style={{ fontSize: 13, color: "#718096", alignSelf: "center" }}>Gợi ý:</span>
        {samplePrompts.map((p, idx) => (
          <button key={idx} style={styles.promptPill} onClick={() => send(p)}>
            ✨ {p}
          </button>
        ))}
      </div>

      <div style={styles.chatBox}>
        {messages.length === 0 && (
          <div style={{ color: "#a0aec0", textAlign: "center", marginTop: 40 }}>
            <div style={{ fontSize: 40, marginBottom: 10 }}>🤖</div>
            <b>Bạn cần ôn tập kiến thức hay làm đề thi nào hôm nay?</b>
            <p style={{ fontSize: 14 }}>
              Hỏi bất kỳ kiến thức nào ➔ AI sẽ trả lời và <b>chiếu đúng đoạn video thầy cô giảng bài</b>!<br />
              Hoặc bấm nút <b>"📷 Quét ảnh đề thi"</b> để tải ảnh chụp đề trên Facebook vào làm thử.
            </p>
          </div>
        )}

        {messages.map((m, i) => {
          if (m.role === "user") {
            return (
              <div key={i} style={styles.userMsg}>
                <b>Bạn:</b> <MathView text={m.content} />
              </div>
            );
          }

          const { cleanText, recommendedExams, mediaAttachments } = parseMessageContent(m.content);

          return (
            <div key={i} style={styles.aiMsg}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <span style={{ fontSize: 18 }}>🤖</span>
                <b>Trợ lý AI:</b>
              </div>

              {/* Lời giải thích text */}
              <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                <MathView text={cleanText || (loading && i === messages.length - 1 ? "Đang tra cứu kho kiến thức..." : "")} />
              </div>

              {/* Interactive Video Block: Nhảy đúng phút:giây */}
              {mediaAttachments && mediaAttachments.length > 0 && (
                <div style={styles.mediaContainer}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#975a16", marginBottom: 8 }}>
                    🎬 VIDEO BÀI GIẢNG ĐÚNG ĐOẠN BẠN CẦN XEM:
                  </div>
                  {mediaAttachments.map((media, idx) => {
                    const mins = Math.floor(media.timestamp_start / 60);
                    const secs = media.timestamp_start % 60;
                    const timeStr = `${mins}:${secs.toString().padStart(2, "0")}`;

                    return (
                      <div key={idx} style={styles.mediaCard}>
                        <div style={{ marginBottom: 6, fontWeight: 600 }}>
                          ▶ {media.title} — <span style={{ color: "#c05621" }}>Đoạn {timeStr}</span>
                        </div>
                        {media.type === "youtube" ? (
                          <div style={{ position: "relative", paddingBottom: "56.25%", height: 0, overflow: "hidden", borderRadius: 6 }}>
                            <iframe
                              style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", border: 0 }}
                              src={`https://www.youtube.com/embed/${media.youtube_id}?start=${media.timestamp_start}&autoplay=0`}
                              title={media.title}
                              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                              allowFullScreen
                            />
                          </div>
                        ) : (
                          <div style={{ fontSize: 13, color: "#718096" }}>
                            📄 Vị trí tài liệu: Trang {media.page_number || "1"}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Danh sách đề thi được đề xuất nếu có */}
              {recommendedExams && recommendedExams.length > 0 && (
                <div style={styles.examCardContainer}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#2b6cb0", marginBottom: 8 }}>
                    🎯 ĐỀ THI PHÙ HỢP CHO BẠN:
                  </div>
                  {recommendedExams.map((exam) => (
                    <div key={exam.id} style={styles.examCard}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: 15, color: "#2d3748" }}>
                          {exam.subject_icon} {exam.title}
                        </div>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                          {exam.school_or_dept && <span style={styles.schoolBadge}>🏛️ {exam.school_or_dept}</span>}
                          {exam.province && <span style={styles.provinceBadge}>📍 {exam.province}</span>}
                          {exam.curriculum_standard && <span style={styles.curriculumBadge}>🎯 {exam.curriculum_standard}</span>}
                        </div>
                        <div style={{ fontSize: 13, color: "#718096", marginTop: 4 }}>
                          Môn: {exam.subject_name} · {exam.total_questions} câu · Thời gian: {exam.duration_minutes} phút
                        </div>
                      </div>
                      <button style={styles.startExamBtn} onClick={() => startExam(exam.id)}>
                        📝 Vào làm ngay
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Nhập câu hỏi: 'Hôm nay tôi muốn làm 1 đề thi thử...', 'Tại sao este có nhiệt độ sôi thấp hơn ancol?'..."
          style={styles.input}
          disabled={loading}
        />
        <button onClick={() => send()} disabled={loading} style={styles.btn}>
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
    marginBottom: 8,
    fontSize: 14,
  },
  promptPillContainer: {
    display: "flex",
    gap: 8,
    flexWrap: "wrap",
    marginBottom: 10,
  },
  promptPill: {
    background: "#ebf8ff",
    border: "1px solid #bee3f8",
    color: "#2b6cb0",
    padding: "6px 12px",
    borderRadius: 16,
    fontSize: 13,
    cursor: "pointer",
  },
  chatBox: {
    flex: 1,
    overflowY: "auto",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: 16,
    background: "#f8fafc",
  },
  userMsg: {
    background: "#e2e8f0",
    padding: "10px 14px",
    borderRadius: 8,
    marginBottom: 12,
    alignSelf: "flex-end",
    maxWidth: "80%",
    marginLeft: "auto",
    color: "#1a202c",
  },
  aiMsg: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    padding: "14px 16px",
    borderRadius: 8,
    marginBottom: 14,
    maxWidth: "92%",
    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
  },
  mediaContainer: {
    marginTop: 14,
    padding: 12,
    background: "#fffaf0",
    border: "1px solid #feebc8",
    borderRadius: 8,
  },
  mediaCard: {
    background: "#fff",
    border: "1px solid #fed7d7",
    padding: 10,
    borderRadius: 6,
    marginTop: 6,
  },
  examCardContainer: {
    marginTop: 12,
    padding: 12,
    background: "#edf8ff",
    border: "1px solid #bee3f8",
    borderRadius: 8,
  },
  examCard: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "#fff",
    border: "1px solid #cbd5e0",
    borderRadius: 6,
    padding: "10px 14px",
    marginTop: 6,
  },
  schoolBadge: { background: "#ebf8ff", color: "#2b6cb0", padding: "1px 6px", borderRadius: 4, fontSize: 11, fontWeight: 700, border: "1px solid #bee3f8" },
  provinceBadge: { background: "#feebc8", color: "#c05621", padding: "1px 6px", borderRadius: 4, fontSize: 11, fontWeight: 600, border: "1px solid #fbd38d" },
  curriculumBadge: { background: "#c6f6d5", color: "#22543d", padding: "1px 6px", borderRadius: 4, fontSize: 11, fontWeight: 700, border: "1px solid #9ae6b4" },
  startExamBtn: {
    padding: "8px 16px",
    background: "#38a169",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 13,
  },
  imageBtn: {
    background: "#805ad5",
    color: "#fff",
    border: "none",
    padding: "8px 14px",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
  },
  input: { flex: 1, padding: 12, border: "1px solid #cbd5e0", borderRadius: 6, fontSize: 14 },
  btn: {
    padding: "10px 22px",
    background: "#3182ce",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    fontWeight: 600,
  },
  clearBtn: {
    background: "transparent",
    border: "1px solid #e2e8f0",
    padding: "6px 12px",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 13,
    color: "#718096",
  },
};

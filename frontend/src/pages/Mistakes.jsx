import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import MathView from "../components/MathView";

function answerText(value) {
  if (Array.isArray(value)) return value.map((item) => item === "T" ? "Đúng" : item === "F" ? "Sai" : String(item ?? "—")).join(" · ");
  if (value && typeof value === "object" && Array.isArray(value.accepted)) return value.accepted.join(" hoặc ");
  if (value && typeof value === "object" && value.choice) return String(value.choice);
  if (value && typeof value === "object") return JSON.stringify(value);
  return value === null || value === undefined || value === "" ? "Không trả lời" : String(value);
}

function entries(options) {
  if (Array.isArray(options)) return options.map((value, index) => [String.fromCharCode(65 + index), value]);
  if (options && typeof options === "object") return Object.entries(options).map(([key, value]) => [key.replace(/^option_?/i, "").toUpperCase(), value]);
  return [];
}

export default function Mistakes() {
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => { api.get("/catalog/subjects").then((response) => setSubjects(response.data)).catch(() => setSubjects([])); }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    const query = subjectId ? `?subject_id=${subjectId}` : "";
    api.get(`/stats/mistakes${query}`).then((response) => setItems(response.data)).catch((requestError) => {
      setError(requestError.response?.data?.detail || "Không tải được sổ lỗi sai.");
    }).finally(() => setLoading(false));
  }, [subjectId]);

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <div><h2 style={{ margin: 0 }}>Sổ lỗi sai</h2><p style={styles.muted}>Câu sai hoặc bỏ trống trong các lượt đã nộp.</p></div>
        <button style={styles.button} onClick={() => navigate("/exams")}>Mở kho đề</button>
      </header>
      <label style={styles.filter}>Lọc môn
        <select value={subjectId} onChange={(event) => setSubjectId(event.target.value)} style={styles.select}>
          <option value="">Tất cả môn</option>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
        </select>
      </label>
      {error && <div style={styles.error}>{error}</div>}
      {loading ? <div style={styles.empty}>Đang tải...</div> : items.length === 0 ? <div style={styles.emptyState}><h3>Chưa có lỗi sai</h3><p>Khi bạn nộp một lượt làm, câu chưa đúng sẽ xuất hiện tại đây.</p></div> : <section style={styles.list}>
        {items.map((item) => <article key={item.id} style={styles.card}>
          <div style={styles.badges}><span style={styles.subject}>{item.subject_name}</span><span>{item.exam_title}</span>{item.topic_tag && <span>· {item.topic_tag}</span>}</div>
          <div style={styles.question}><b>Câu {item.question_number}.</b> <MathView text={item.question_text} /></div>
          {entries(item.options).length > 0 && <div style={styles.options}>{entries(item.options).map(([key, value]) => <div key={key} style={styles.option}><b>{key}.</b><MathView text={String(value)} /></div>)}</div>}
          <div style={styles.answerGrid}>
            <div><small>BẠN TRẢ LỜI</small><div style={{ color: "#b91c1c", fontWeight: 700 }}>{answerText(item.selected_answer)}</div></div>
            <div><small>ĐÁP ÁN</small><div style={{ color: "#15803d", fontWeight: 700 }}>{answerText(item.correct_answer)}</div></div>
            <div><small>ĐIỂM CÂU</small><div>{item.score_earned}/{item.max_points ?? "—"}</div></div>
          </div>
          {item.explanation && <div style={styles.explanation}><b>Giải thích:</b><div><MathView text={item.explanation} /></div></div>}
        </article>)}
      </section>}
    </main>
  );
}

const styles = {
  page: { maxWidth: 980, margin: "0 auto", padding: 24, color: "#1f2937" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 18 },
  muted: { color: "#64748b", fontSize: 14, margin: "5px 0 0" },
  button: { border: 0, borderRadius: 8, padding: "10px 14px", background: "#2563eb", color: "white", cursor: "pointer", fontWeight: 700 },
  filter: { display: "flex", alignItems: "center", gap: 10, marginBottom: 16, color: "#475569", fontSize: 14 },
  select: { border: "1px solid #cbd5e1", borderRadius: 7, padding: "8px 10px", background: "white" },
  list: { display: "grid", gap: 12 },
  card: { border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, background: "white" },
  badges: { display: "flex", flexWrap: "wrap", gap: 8, color: "#64748b", fontSize: 13 },
  subject: { color: "#1d4ed8", fontWeight: 700 },
  question: { display: "flex", gap: 6, margin: "14px 0", lineHeight: 1.6 },
  options: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 7 },
  option: { display: "flex", gap: 7, border: "1px solid #f1f5f9", borderRadius: 6, padding: 8 },
  answerGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12, marginTop: 14, padding: 12, background: "#f8fafc", borderRadius: 8 },
  explanation: { marginTop: 12, paddingTop: 12, borderTop: "1px solid #e2e8f0", lineHeight: 1.6 },
  empty: { textAlign: "center", padding: 36, color: "#64748b" },
  emptyState: { textAlign: "center", border: "1px dashed #cbd5e1", borderRadius: 10, padding: 34, color: "#64748b" },
  error: { padding: 12, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, marginBottom: 12 },
};

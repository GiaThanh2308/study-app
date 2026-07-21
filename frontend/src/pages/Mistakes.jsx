import { useEffect, useState } from "react";
import api from "../api";

export default function Mistakes() {
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");
  const [mistakes, setMistakes] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/subjects").then((res) => setSubjects(res.data));
    load();
  }, []);

  const load = async (sid = "") => {
    setLoading(true);
    const url = sid ? `/practice/mistakes?subject_id=${sid}` : "/practice/mistakes";
    const res = await api.get(url);
    setMistakes(res.data);
    setLoading(false);
  };

  const onSubjectChange = (e) => {
    setSubjectId(e.target.value);
    load(e.target.value);
  };

  return (
    <div className="page">
      <h2>Sổ lỗi sai</h2>
      <p style={{ color: "#718096", fontSize: 13 }}>
        Các câu hỏi mà lần làm gần nhất bị sai. Làm lại đúng trong "Luyện tập" sẽ tự động biến mất khỏi danh sách này.
      </p>

      <select value={subjectId} onChange={onSubjectChange} style={styles.select}>
        <option value="">Tất cả môn học</option>
        {subjects.map((s) => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>

      {loading && <p>Đang tải...</p>}
      {!loading && mistakes.length === 0 && (
        <p style={{ color: "#38a169", marginTop: 20 }}>🎉 Không có lỗi sai nào — làm tốt lắm!</p>
      )}

      {mistakes.map((q) => (
        <div key={q.id} style={styles.card}>
          <p style={{ fontWeight: 600 }}>{q.content}</p>
          {q.answers.map((a) => (
            <div key={a.id} style={{ ...styles.answerRow, background: a.is_correct ? "#c6f6d5" : "#fff" }}>
              {a.content} {a.is_correct && "✓ (đáp án đúng)"}
            </div>
          ))}
          {q.explanation && <p style={styles.explanation}>💡 {q.explanation}</p>}
        </div>
      ))}
    </div>
  );
}

const styles = {
  select: { padding: "9px 12px", border: "1px solid #cbd5e0", borderRadius: 8, marginBottom: 16, fontSize: 14 },
  card: {
    border: "1px solid #fed7d7",
    background: "#fff",
    borderRadius: "var(--radius)",
    boxShadow: "var(--shadow-sm)",
    borderLeft: "4px solid var(--color-danger)",
    padding: 18,
    marginBottom: 14,
    maxWidth: 650,
  },
  answerRow: {
    padding: "8px 12px",
    border: "1px solid var(--color-border)",
    borderRadius: 8,
    marginBottom: 5,
    fontSize: 14,
  },
  explanation: { fontSize: 13, color: "var(--color-text-muted)", marginTop: 8 },
};

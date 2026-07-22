import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function Mistakes() {
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");
  const [mistakes, setMistakes] = useState([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

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

  const onSubjectChange = (sid) => {
    setSubjectId(sid);
    load(sid);
  };

  const subjectName = (id) => subjects.find((s) => s.id === id)?.name || "";

  const retryTopic = (topic) => {
    navigate(`/practice?tab=tutor&topic=${encodeURIComponent(topic)}`);
  };

  return (
    <div className="page">
      <h2>Sổ lỗi sai</h2>
      <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>
        Các câu hỏi mà lần làm gần nhất bị sai. Làm lại đúng trong "Luyện tập" sẽ tự động biến mất khỏi danh sách này.
      </p>

      <div style={styles.chipRow}>
        <button
          style={{ ...styles.chip, ...(subjectId === "" ? styles.chipActive : {}) }}
          onClick={() => onSubjectChange("")}
        >
          Tất cả môn học
        </button>
        {subjects.map((s) => (
          <button
            key={s.id}
            style={{ ...styles.chip, ...(subjectId === String(s.id) ? styles.chipActive : {}) }}
            onClick={() => onSubjectChange(String(s.id))}
          >
            {s.name}
          </button>
        ))}
      </div>

      {loading && <p>Đang tải...</p>}

      {!loading && mistakes.length === 0 && (
        <div style={styles.emptyState}>
          <svg width="120" height="120" viewBox="0 0 120 120" style={{ marginBottom: 8 }}>
            <circle cx="60" cy="60" r="56" fill="var(--color-success-light)" />
            <path d="M60 26c-14 0-22 8-22 8v14c0 12 9 22 22 26 13-4 22-14 22-26V34s-8-8-22-8z"
                  fill="var(--color-success)" opacity="0.15" />
            <path d="M44 40h32v10a16 16 0 0 1-32 0V40z" fill="var(--color-success)" />
            <rect x="56" y="60" width="8" height="14" fill="var(--color-success)" />
            <rect x="46" y="74" width="28" height="7" rx="3" fill="var(--color-success)" />
            <path d="M44 42h-8a8 8 0 0 0 8 8" stroke="var(--color-success)" strokeWidth="3" fill="none" />
            <path d="M76 42h8a8 8 0 0 1-8 8" stroke="var(--color-success)" strokeWidth="3" fill="none" />
            <circle cx="60" cy="50" r="3.5" fill="#fff" />
          </svg>
          <div style={{ fontWeight: 700, fontSize: 17 }}>Không có lỗi sai nào!</div>
          <div style={{ fontSize: 13.5, color: "var(--color-text-muted)", marginTop: 4 }}>
            Bạn đang học rất tốt — tiếp tục phát huy nhé! 🎉
          </div>
        </div>
      )}

      {mistakes.map((q) => (
        <div key={q.id} style={styles.card}>
          <div style={styles.cardHeader}>
            {subjectName(q.subject_id) && (
              <span style={styles.subjectTag}>{subjectName(q.subject_id)}</span>
            )}
          </div>
          <p style={{ fontWeight: 600, margin: "6px 0" }}>{q.content}</p>
          {q.answers.map((a) => (
            <div
              key={a.id}
              style={{
                ...styles.answerRow,
                background: a.is_correct ? "var(--color-success-light)" : "var(--color-surface)",
              }}
            >
              {a.content} {a.is_correct && "✓ (đáp án đúng)"}
            </div>
          ))}
          {q.explanation && <p style={styles.explanation}>💡 {q.explanation}</p>}

          {q.topic && (
            <button style={styles.retryBtn} onClick={() => retryTopic(q.topic)}>
              🔁 Làm lại ngay (chủ đề: {q.topic})
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

const styles = {
  chipRow: { display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 18 },
  chip: {
    padding: "7px 16px",
    borderRadius: 20,
    border: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    color: "var(--color-text-muted)",
    fontSize: 13.5,
    fontWeight: 500,
    cursor: "pointer",
  },
  chipActive: {
    background: "var(--color-primary)",
    color: "#fff",
    border: "1px solid var(--color-primary)",
  },
  card: {
    border: "1px solid #fed7d7",
    background: "var(--color-surface)",
    borderRadius: "var(--radius)",
    boxShadow: "var(--shadow-sm)",
    borderLeft: "4px solid var(--color-danger)",
    padding: 18,
    marginBottom: 14,
    maxWidth: 650,
  },
  cardHeader: { display: "flex", gap: 8 },
  subjectTag: {
    fontSize: 11,
    fontWeight: 600,
    padding: "2px 10px",
    borderRadius: 12,
    background: "var(--color-primary-light)",
    color: "var(--color-primary)",
  },
  retryBtn: {
    marginTop: 10,
    padding: "8px 14px",
    borderRadius: 8,
    border: "1px solid var(--color-primary)",
    background: "transparent",
    color: "var(--color-primary)",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
  },
  emptyState: {
    textAlign: "center",
    padding: "50px 20px",
    background: "var(--color-surface)",
    borderRadius: "var(--radius)",
    border: "1px solid var(--color-border)",
    maxWidth: 400,
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

import { useEffect, useState } from "react";
import api from "../api";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [counter, setCounter] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/stats/overview").then((r) => setStats(r.data)).catch(() => {});
    api.get("/exam-counter").then((r) => setCounter(r.data)).catch(() => {});
  }, []);

  if (!stats) return <div style={{ padding: 24 }}>Đang tải...</div>;

  return (
    <div style={{ padding: 24 }}>
      <h2>📊 Dashboard — Ôn thi THPT Quốc gia</h2>

      {/* Thẻ tổng quan */}
      <div style={styles.grid}>
        <StatCard icon="📚" label="Môn học" value={stats.total_subjects} color="#3182ce" />
        <StatCard icon="📖" label="Chương" value={stats.total_chapters} color="#38a169" />
        <StatCard icon="📄" label="Bài học" value={stats.total_lessons} color="#d69e2e" />
        <StatCard icon="🎬" label="Video" value={stats.total_videos} color="#e53e3e" />
        <StatCard icon="📑" label="Tài liệu" value={stats.total_documents} color="#805ad5" />
        <StatCard icon="📝" label="Đề thi" value={stats.total_exams} color="#dd6b20" />
      </div>

      {/* Bộ đếm đề thi */}
      <h3 style={{ marginTop: 28 }}>🎯 Tiến độ ôn thi</h3>
      {counter.length === 0 ? (
        <p style={{ color: "#718096" }}>Chưa có đề thi nào. Vào mục Đề thi để thêm.</p>
      ) : (
        <div style={styles.counterGrid}>
          {counter.map((c) => {
            const pct = c.total_exams > 0 ? Math.round((c.completed_exams / c.total_exams) * 100) : 0;
            return (
              <div key={c.subject_id} style={styles.counterCard}>
                <div style={{ fontSize: 18, fontWeight: 700 }}>
                  {c.subject_icon || "📘"} {c.subject_name}
                </div>
                <div style={{ margin: "10px 0" }}>
                  <div style={styles.progressBg}>
                    <div style={{ ...styles.progressBar, width: `${pct}%` }} />
                  </div>
                </div>
                <div style={{ fontSize: 14, color: "#4a5568" }}>
                  <b>{c.completed_exams}</b> / {c.total_exams} đề đã làm
                  {c.remaining_exams > 0 && (
                    <span style={{ color: "#e53e3e" }}> — còn {c.remaining_exams} đề</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Thống kê theo môn */}
      {stats.subjects.length > 0 && (
        <>
          <h3 style={{ marginTop: 28 }}>📈 Kết quả theo môn</h3>
          <div style={styles.counterGrid}>
            {stats.subjects.map((s) => (
              <div key={s.subject_id} style={styles.subjectStatsCard}>
                <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 8 }}>{s.subject_name}</div>
                <div style={styles.statRow}>
                  <span>Điểm TB:</span>
                  <b style={{ color: s.average_score >= 5 ? "#38a169" : "#e53e3e" }}>
                    {s.average_score !== null ? s.average_score.toFixed(1) : "—"}
                  </b>
                </div>
                <div style={styles.statRow}>
                  <span>Điểm cao nhất:</span>
                  <b>{s.best_score !== null ? s.best_score.toFixed(1) : "—"}</b>
                </div>
                <div style={styles.statRow}>
                  <span>Tỉ lệ đúng:</span>
                  <b>{s.accuracy_percent !== null ? `${s.accuracy_percent}%` : "—"}</b>
                </div>
                <div style={styles.statRow}>
                  <span>Câu đã làm:</span>
                  <span>{s.total_questions_done} ({s.total_correct} đúng)</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Shortcut buttons */}
      <div style={{ display: "flex", gap: 12, marginTop: 28, flexWrap: "wrap" }}>
        <button style={styles.actionBtn} onClick={() => navigate("/exams")}>📝 Làm đề thi</button>
        <button style={styles.actionBtn} onClick={() => navigate("/subjects")}>📚 Quản lý môn học</button>
        <button style={styles.actionBtn} onClick={() => navigate("/chat")}>💬 Hỏi AI</button>
        <button style={styles.actionBtn} onClick={() => navigate("/mistakes")}>❌ Xem lỗi sai</button>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  return (
    <div style={{ ...styles.statCard, borderLeft: `4px solid ${color}` }}>
      <div style={{ fontSize: 24 }}>{icon}</div>
      <div>
        <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
        <div style={{ fontSize: 13, color: "#718096" }}>{label}</div>
      </div>
    </div>
  );
}

const styles = {
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
    gap: 12,
    marginTop: 16,
  },
  statCard: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: "14px 16px",
  },
  counterGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: 12,
    marginTop: 12,
  },
  counterCard: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: 16,
  },
  progressBg: {
    background: "#e2e8f0",
    borderRadius: 6,
    height: 10,
    overflow: "hidden",
  },
  progressBar: {
    background: "linear-gradient(90deg, #38a169, #48bb78)",
    height: "100%",
    borderRadius: 6,
    transition: "width 0.5s ease",
  },
  subjectStatsCard: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: 16,
  },
  statRow: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: 14,
    padding: "3px 0",
    color: "#4a5568",
  },
  actionBtn: {
    padding: "10px 18px",
    background: "#3182ce",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 600,
  },
};

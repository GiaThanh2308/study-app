import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function Stats() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/stats/overview").then((response) => setStats(response.data)).catch((requestError) => {
      setError(requestError.response?.data?.detail || "Không tải được thống kê.");
    });
  }, []);

  if (error) return <div style={styles.page}><div style={styles.error}>{error}</div></div>;
  if (!stats) return <div style={styles.page}>Đang tải thống kê...</div>;

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <div><h2 style={{ margin: 0 }}>Thống kê học tập</h2><p style={styles.muted}>Chỉ tính các lượt làm đã nộp và đề đã xuất bản.</p></div>
        <button style={styles.button} onClick={() => navigate("/exams")}>Mở kho đề</button>
      </header>
      <section style={styles.metrics}>
        <Metric label="Đề trong kho" value={stats.total_exams} />
        <Metric label="Lượt đã hoàn thành" value={`${stats.completed_attempts}/${stats.total_attempts}`} />
        <Metric label="Điểm trung bình" value={stats.overall_average_score === null ? "—" : `${stats.overall_average_score}/10`} />
        <Metric label="Chủ đề" value={stats.total_topics} />
      </section>
      <h3 style={{ margin: "24px 0 12px" }}>Kết quả theo môn</h3>
      <section style={styles.subjects}>
        {stats.subjects.map((subject) => <article key={subject.subject_id} style={styles.card}>
          <h3 style={{ marginTop: 0 }}>{subject.subject_icon} {subject.subject_name}</h3>
          <div style={styles.row}><span>Đề trong kho</span><b>{subject.total_exams}</b></div>
          <div style={styles.row}><span>Lượt hoàn thành</span><b>{subject.completed_exams}</b></div>
          <div style={styles.row}><span>Điểm trung bình / cao nhất</span><b>{subject.average_score ?? "—"} / {subject.best_score ?? "—"}</b></div>
          <div style={styles.row}><span>Tỷ lệ đúng trọn câu</span><b>{subject.accuracy_percent === null ? "—" : `${subject.accuracy_percent}%`}</b></div>
          <div style={styles.row}><span>Câu đúng trọn vẹn</span><b>{subject.total_correct}/{subject.total_questions_done}</b></div>
        </article>)}
      </section>
    </main>
  );
}

function Metric({ label, value }) {
  return <div style={styles.metric}><div style={styles.muted}>{label}</div><strong>{value ?? 0}</strong></div>;
}

const styles = {
  page: { maxWidth: 1050, margin: "0 auto", padding: 24, color: "#1f2937" },
  header: { display: "flex", justifyContent: "space-between", gap: 14, alignItems: "center" },
  muted: { color: "#64748b", margin: "5px 0 0", fontSize: 14 },
  metrics: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))", gap: 12, marginTop: 20 },
  metric: { display: "grid", gap: 10, padding: 16, border: "1px solid #e2e8f0", borderRadius: 10, background: "#f8fafc" },
  subjects: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 12 },
  card: { border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, background: "white" },
  row: { display: "flex", justifyContent: "space-between", gap: 10, padding: "7px 0", borderTop: "1px solid #f1f5f9", fontSize: 14 },
  button: { border: 0, borderRadius: 8, padding: "10px 14px", background: "#2563eb", color: "white", fontWeight: 700, cursor: "pointer" },
  error: { padding: 12, color: "#b91c1c", background: "#fef2f2", borderRadius: 8 },
};

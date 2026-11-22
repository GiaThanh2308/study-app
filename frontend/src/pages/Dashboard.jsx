import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/stats/overview").then((response) => setStats(response.data)).catch((requestError) => {
      setError(requestError.response?.data?.detail || "Không tải được tổng quan học tập.");
    });
  }, []);

  if (error) return <main style={styles.page}><div style={styles.error}>{error}</div></main>;
  if (!stats) return <main style={styles.page}>Đang tải tổng quan...</main>;

  return (
    <main style={styles.page}>
      <h2>StudyApp · Ôn thi THPT 2027</h2>
      <p style={styles.subtitle}>Kho đề, lượt luyện tập và tiến độ của bạn được lưu trong database cục bộ mới.</p>
      <section style={styles.metrics}>
        <Metric label="Môn học" value={stats.total_subjects} />
        <Metric label="Chủ đề trong ma trận" value={stats.total_topics} />
        <Metric label="Đề đã xuất bản" value={stats.total_exams} />
        <Metric label="Lượt đã hoàn thành" value={stats.completed_attempts} />
        <Metric label="Điểm trung bình" value={stats.overall_average_score === null ? "—" : `${stats.overall_average_score}/10`} />
      </section>
      <section style={styles.actions}>
        <button style={styles.primary} onClick={() => navigate("/exams")}>Mở kho đề</button>
        <button style={styles.secondary} onClick={() => navigate("/mistakes")}>Sổ lỗi sai</button>
        <button style={styles.secondary} onClick={() => navigate("/stats")}>Thống kê</button>
      </section>
      <h3 style={{ marginTop: 26 }}>Theo môn</h3>
      <section style={styles.subjects}>
        {stats.subjects.map((subject) => <article key={subject.subject_id} style={styles.card}>
          <h3 style={{ marginTop: 0 }}>{subject.subject_icon} {subject.subject_name}</h3>
          <p style={styles.subtitle}>{subject.total_exams} đề trong kho · {subject.completed_exams} lượt hoàn thành</p>
          <div>Điểm trung bình: <b>{subject.average_score ?? "—"}</b> · cao nhất: <b>{subject.best_score ?? "—"}</b></div>
        </article>)}
      </section>
      {stats.total_exams === 0 && <p style={styles.empty}>Kho đang trống. Tìm đề và nhập đề có sẵn sẽ được nối vào catalog ở Bước 7.</p>}
    </main>
  );
}

function Metric({ label, value }) {
  return <div style={styles.metric}><span>{label}</span><strong>{value ?? 0}</strong></div>;
}

const styles = {
  page: { maxWidth: 1100, margin: "0 auto", padding: 24, color: "#1f2937" },
  subtitle: { color: "#64748b", marginTop: 5 },
  metrics: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(155px,1fr))", gap: 12, marginTop: 20 },
  metric: { display: "grid", gap: 10, padding: 16, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10, color: "#64748b" },
  actions: { display: "flex", flexWrap: "wrap", gap: 10, marginTop: 18 },
  primary: { border: 0, borderRadius: 8, padding: "11px 16px", background: "#2563eb", color: "white", fontWeight: 700, cursor: "pointer" },
  secondary: { border: "1px solid #cbd5e1", borderRadius: 8, padding: "11px 16px", background: "white", color: "#334155", fontWeight: 700, cursor: "pointer" },
  subjects: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 12 },
  card: { border: "1px solid #e2e8f0", borderRadius: 10, padding: 16 },
  empty: { marginTop: 18, padding: 14, borderRadius: 8, background: "#fffbeb", color: "#92400e" },
  error: { padding: 12, background: "#fef2f2", color: "#b91c1c", borderRadius: 8 },
};

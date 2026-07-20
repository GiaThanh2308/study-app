import { useEffect, useState } from "react";
import api from "../api";

export default function Stats() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get("/practice/stats").then((res) => setStats(res.data));
  }, []);

  if (!stats) return <div style={{ padding: 24 }}>Đang tải...</div>;

  return (
    <div style={{ padding: 24 }}>
      <h2>Thống kê</h2>

      <div style={styles.overviewBox}>
        <div style={styles.statNumber}>{stats.total_attempts}</div>
        <div style={{ color: "#718096" }}>lượt làm bài</div>
        {stats.overall_percent !== null && (
          <div style={{ marginTop: 8, fontSize: 16 }}>
            Tỉ lệ đúng tổng thể: <b>{stats.overall_percent}%</b>
          </div>
        )}
      </div>

      <h4 style={{ marginTop: 24 }}>Theo môn học</h4>
      {stats.by_subject.map((s) => (
        <div key={s.subject_id} style={styles.subjectRow}>
          <span style={{ width: 100 }}>{s.subject_name}</span>
          <div style={styles.barBg}>
            {s.percent_correct !== null && (
              <div style={{ ...styles.barFill, width: `${s.percent_correct}%` }} />
            )}
          </div>
          <span style={{ width: 60, textAlign: "right" }}>
            {s.percent_correct !== null ? `${s.percent_correct}%` : "chưa làm"}
          </span>
        </div>
      ))}
    </div>
  );
}

const styles = {
  overviewBox: {
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: 24,
    textAlign: "center",
    maxWidth: 300,
  },
  statNumber: { fontSize: 36, fontWeight: 700, color: "#3182ce" },
  subjectRow: { display: "flex", alignItems: "center", gap: 12, marginBottom: 10, maxWidth: 500 },
  barBg: { flex: 1, height: 10, background: "#e2e8f0", borderRadius: 5, overflow: "hidden" },
  barFill: { height: "100%", background: "#38a169" },
};

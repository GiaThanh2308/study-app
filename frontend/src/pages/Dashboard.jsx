import { useEffect, useState } from "react";
import api from "../api";

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/analytics/overview").then((res) => setData(res.data));
  }, []);

  if (!data) return <div className="page">Đang tải...</div>;

  return (
    <div className="page">
      <h2>Dashboard</h2>

      <div style={styles.hoursBox}>
        <div style={styles.hoursNumber}>{data.total_hours_estimated}</div>
        <div style={{ color: "#718096" }}>giờ học (ước tính)</div>
      </div>

      <h4 style={{ marginTop: 24 }}>Theo môn học</h4>
      {data.by_subject.length === 0 && <p style={{ color: "#718096" }}>Chưa có môn học nào.</p>}
      {data.by_subject.map((s) => (
        <div key={s.subject_id} style={styles.subjectRow}>
          <span style={{ width: 100 }}>{s.subject_name}</span>
          <div style={styles.barBg}>
            {s.percent_correct !== null && (
              <div style={{ ...styles.barFill, width: `${s.percent_correct}%` }} />
            )}
          </div>
          <span style={{ width: 70, textAlign: "right" }}>
            {s.percent_correct !== null ? `${s.percent_correct}%` : "chưa làm"}
          </span>
        </div>
      ))}

      {data.weakest_point && (
        <div style={styles.weakBox}>
          <h4 style={{ marginTop: 0 }}>🎯 AI nhận thấy bạn đang yếu nhất ở:</h4>
          <p style={{ fontSize: 18, fontWeight: 600 }}>
            {data.weakest_point.topic} <span style={{ fontSize: 14, color: "#718096" }}>({data.weakest_point.subject_name})</span>
          </p>
          <p style={{ color: "#c53030" }}>
            Chỉ đúng {data.weakest_point.percent_correct}% ({data.weakest_point.attempts} lần làm)
          </p>
          {data.weakest_point.suggested_video && (
            <p style={{ color: "#2b6cb0" }}>
              🎥 Nên xem lại: {data.weakest_point.suggested_video.source_name}, phút {data.weakest_point.suggested_video.timestamp}
            </p>
          )}
          <p style={{ fontSize: 13, color: "#718096" }}>
            Vào "Luyện tập" → tab "AI Gia sư" → gõ chủ đề này để luyện tập nhắm đúng điểm yếu.
          </p>
        </div>
      )}

      {!data.weakest_point && (
        <p style={{ color: "#718096", marginTop: 20, fontSize: 13 }}>
          Chưa đủ dữ liệu để xác định điểm yếu — hãy luyện tập qua "AI Gia sư" (Luyện tập → tab AI Gia sư) để AI bắt đầu theo dõi theo từng chủ đề cụ thể.
        </p>
      )}
    </div>
  );
}

const styles = {
  hoursBox: {
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    boxShadow: "var(--shadow-sm)",
    padding: 24,
    textAlign: "center",
    maxWidth: 240,
    background: "#fff",
  },
  hoursNumber: { fontSize: 36, fontWeight: 700, color: "var(--color-primary)" },
  subjectRow: { display: "flex", alignItems: "center", gap: 12, marginBottom: 10, maxWidth: 500 },
  barBg: { flex: 1, height: 10, background: "var(--color-border)", borderRadius: 5, overflow: "hidden" },
  barFill: { height: "100%", background: "var(--color-success)" },
  weakBox: {
    marginTop: 24,
    border: "1px solid #fbd38d",
    background: "var(--color-warning-light)",
    borderRadius: "var(--radius)",
    boxShadow: "var(--shadow-sm)",
    padding: 20,
    maxWidth: 500,
  },
};

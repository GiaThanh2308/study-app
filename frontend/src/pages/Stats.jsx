import { useEffect, useState } from "react";
import api from "../api";
import { useNavigate } from "react-router-dom";

export default function Stats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/stats/overview")
      .then((res) => setStats(res.data))
      .catch((err) => console.error("Lỗi tải thống kê:", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 24, textAlign: "center" }}>Đang tải dữ liệu thống kê...</div>;
  if (!stats) return <div style={{ padding: 24 }}>Không có dữ liệu thống kê.</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: "0 0 4px" }}>📊 Thống Kê Học Tập Chuyên Sâu</h2>
          <div style={{ color: "#718096", fontSize: 14 }}>
            Theo dõi năng lực thực tế, điểm số trung bình và tỷ lệ chính xác từng môn học
          </div>
        </div>
        <button onClick={() => navigate("/exams")} style={styles.primaryBtn}>
          📝 Làm thêm đề thi
        </button>
      </div>

      {/* Thẻ chỉ số tổng thể */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <div style={{ fontSize: 13, color: "#718096", fontWeight: 600 }}>TỔNG SỐ LẦN THI</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#2b6cb0", marginTop: 4 }}>
            {stats.completed_attempts} / {stats.total_attempts}
          </div>
          <div style={{ fontSize: 12, color: "#718096", marginTop: 4 }}>Lần hoàn thành</div>
        </div>

        <div style={styles.metricCard}>
          <div style={{ fontSize: 13, color: "#718096", fontWeight: 600 }}>ĐIỂM TRUNG BÌNH TỔNG</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: stats.overall_average_score >= 5 ? "#2f855a" : "#c53030", marginTop: 4 }}>
            {stats.overall_average_score !== null ? stats.overall_average_score.toFixed(1) : "—"}
          </div>
          <div style={{ fontSize: 12, color: "#718096", marginTop: 4 }}>Thang điểm 10</div>
        </div>

        <div style={styles.metricCard}>
          <div style={{ fontSize: 13, color: "#718096", fontWeight: 600 }}>TỔNG SỐ ĐỀ TRONG KHO</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#805ad5", marginTop: 4 }}>
            {stats.total_exams}
          </div>
          <div style={{ fontSize: 12, color: "#718096", marginTop: 4 }}>Đề thi chuẩn 2025</div>
        </div>
      </div>

      {/* Chi tiết theo từng môn học */}
      <h3 style={{ marginTop: 28, marginBottom: 12 }}>📈 Chi Tiết Năng Lực Từng Môn</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {stats.subjects.map((sub) => {
          const completionPct = sub.total_exams > 0 ? Math.round((sub.completed_exams / sub.total_exams) * 100) : 0;
          return (
            <div key={sub.subject_id} style={styles.subjectCard}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#2d3748" }}>
                  📘 {sub.subject_name}
                </div>
                <div style={{ fontSize: 14, color: "#718096" }}>
                  Tiến độ: <b>{sub.completed_exams}</b> / {sub.total_exams} đề ({completionPct}%)
                </div>
              </div>

              {/* Thanh tiến độ */}
              <div style={styles.progressBg}>
                <div style={{ ...styles.progressBar, width: `${completionPct}%` }} />
              </div>

              {/* Bảng các chỉ số môn học */}
              <div style={styles.subStatsGrid}>
                <div style={styles.subStatBox}>
                  <div style={styles.subStatLabel}>Điểm Trung Bình</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: sub.average_score >= 5 ? "#38a169" : "#e53e3e" }}>
                    {sub.average_score !== null ? sub.average_score.toFixed(1) : "Chưa làm"}
                  </div>
                </div>

                <div style={styles.subStatBox}>
                  <div style={styles.subStatLabel}>Điểm Cao Nhất</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#3182ce" }}>
                    {sub.best_score !== null ? sub.best_score.toFixed(1) : "Chưa làm"}
                  </div>
                </div>

                <div style={styles.subStatBox}>
                  <div style={styles.subStatLabel}>Tỷ Lệ Đúng</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#d69e2e" }}>
                    {sub.accuracy_percent !== null ? `${sub.accuracy_percent}%` : "—"}
                  </div>
                </div>

                <div style={styles.subStatBox}>
                  <div style={styles.subStatLabel}>Số Câu Đã Làm</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "#4a5568" }}>
                    {sub.total_questions_done} <span style={{ fontSize: 13, color: "#38a169" }}>({sub.total_correct} đúng)</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles = {
  primaryBtn: {
    padding: "9px 18px",
    background: "#3182ce",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 14,
  },
  metricsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: 16,
    marginTop: 8,
  },
  metricCard: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: 10,
    padding: 18,
    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
  },
  subjectCard: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: 10,
    padding: 20,
    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
  },
  progressBg: {
    background: "#edf2f7",
    height: 8,
    borderRadius: 4,
    overflow: "hidden",
    marginBottom: 16,
  },
  progressBar: {
    background: "linear-gradient(90deg, #3182ce, #38a169)",
    height: "100%",
    borderRadius: 4,
    transition: "width 0.4s ease",
  },
  subStatsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: 12,
  },
  subStatBox: {
    background: "#f7fafc",
    borderRadius: 8,
    padding: "10px 14px",
    border: "1px solid #edf2f7",
  },
  subStatLabel: {
    fontSize: 12,
    color: "#718096",
    marginBottom: 4,
    fontWeight: 500,
  },
};

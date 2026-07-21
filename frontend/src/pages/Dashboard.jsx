import { useEffect, useState } from "react";
import api from "../api";

// ── Cấu hình nhanh — chỉnh 2 dòng này nếu cần ──
const STUDENT_NAME = "Thành";
// Bộ GD-ĐT chưa công bố lịch chính thức kỳ thi THPT 2027 tại thời điểm viết code này.
// Đang để mốc tạm 26/06/2027 08:00 dựa theo thông lệ các năm gần đây — sửa lại khi có lịch chính thức.
const EXAM_DATE = new Date("2027-06-26T08:00:00");

function getGreeting(hour) {
  if (hour < 11) return "Chào buổi sáng";
  if (hour < 13) return "Chào buổi trưa";
  if (hour < 18) return "Chào buổi chiều";
  return "Chào buổi tối";
}

function pad(n) {
  return String(n).padStart(2, "0");
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [now, setNow] = useState(new Date());
  const [sessionStart] = useState(() => new Date());

  useEffect(() => {
    api.get("/analytics/overview").then((res) => setData(res.data));
  }, []);

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const sessionMs = now - sessionStart;
  const sessionH = Math.floor(sessionMs / 3600000);
  const sessionM = Math.floor((sessionMs % 3600000) / 60000);
  const sessionS = Math.floor((sessionMs % 60000) / 1000);

  const examMs = Math.max(0, EXAM_DATE - now);
  const examDays = Math.floor(examMs / 86400000);
  const examH = Math.floor((examMs % 86400000) / 3600000);
  const examM = Math.floor((examMs % 3600000) / 60000);
  const examS = Math.floor((examMs % 60000) / 1000);

  const dateStr = now.toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

  if (!data) return <div style={styles.loading}>Đang tải...</div>;

  return (
    <div style={styles.page}>
      {/* Header chào mừng */}
      <div style={styles.header}>
        <div>
          <div style={styles.eyebrow}>{dateStr}</div>
          <h1 style={styles.greeting}>
            {getGreeting(now.getHours())}, {STUDENT_NAME} 👋
          </h1>
        </div>
      </div>

      {/* Hàng 3 thẻ số liệu chính */}
      <div style={styles.statsGrid}>
        <div style={{ ...styles.statCard, ...styles.timerCard }}>
          <div style={styles.statLabel}>⏱ Thời gian học phiên này</div>
          <div style={styles.timerDigits}>
            {pad(sessionH)}:{pad(sessionM)}:{pad(sessionS)}
          </div>
          <div style={styles.statSub}>Đang đếm từ lúc bạn mở ứng dụng</div>
        </div>

        <div style={{ ...styles.statCard, ...styles.examCard }}>
          <div style={styles.statLabel}>🎯 Đếm ngược kỳ thi THPT 2027</div>
          <div style={styles.examDaysRow}>
            <span style={styles.examDaysNumber}>{examDays}</span>
            <span style={styles.examDaysUnit}>ngày</span>
          </div>
          <div style={styles.examSubDigits}>
            {pad(examH)} giờ : {pad(examM)} phút : {pad(examS)} giây
          </div>
          <div style={styles.statSub}>Mốc dự kiến — cập nhật khi có lịch chính thức</div>
        </div>

        <div style={{ ...styles.statCard, ...styles.hoursCard }}>
          <div style={styles.statLabel}>📚 Tổng giờ học (ước tính)</div>
          <div style={styles.hoursNumber}>{data.total_hours_estimated}</div>
          <div style={styles.statSub}>Tính từ toàn bộ lịch sử học tập</div>
        </div>
      </div>

      {/* Tiến độ theo môn */}
      <div style={styles.sectionCard}>
        <h3 style={styles.sectionTitle}>Theo môn học</h3>
        {data.by_subject.length === 0 && (
          <p style={styles.emptyText}>Chưa có môn học nào — vào "Môn học" để bắt đầu.</p>
        )}
        {data.by_subject.map((s) => (
          <div key={s.subject_id} style={styles.subjectRow}>
            <span style={styles.subjectName}>{s.subject_name}</span>
            <div style={styles.barBg}>
              {s.percent_correct !== null && (
                <div style={{ ...styles.barFill, width: `${s.percent_correct}%` }} />
              )}
            </div>
            <span style={styles.subjectPercent}>
              {s.percent_correct !== null ? `${s.percent_correct}%` : "chưa làm"}
            </span>
          </div>
        ))}
      </div>

      {/* Điểm yếu nhất */}
      {data.weakest_point && (
        <div style={styles.weakBox}>
          <h4 style={styles.weakTitle}>🎓 AI nhận thấy bạn đang yếu nhất ở</h4>
          <p style={styles.weakTopic}>
            {data.weakest_point.topic}
            <span style={styles.weakSubject}> · {data.weakest_point.subject_name}</span>
          </p>
          <p style={styles.weakPercent}>
            Chỉ đúng {data.weakest_point.percent_correct}% ({data.weakest_point.attempts} lần làm)
          </p>
          {data.weakest_point.suggested_video && (
            <p style={styles.weakVideo}>
              🎥 Nên xem lại: {data.weakest_point.suggested_video.source_name}, phút{" "}
              {data.weakest_point.suggested_video.timestamp}
            </p>
          )}
          <p style={styles.weakHint}>
            Vào "Luyện tập" → tab "AI Gia sư" → gõ chủ đề này để luyện tập nhắm đúng điểm yếu.
          </p>
        </div>
      )}

      {!data.weakest_point && (
        <div style={styles.emptyWeakBox}>
          Chưa đủ dữ liệu để xác định điểm yếu — hãy luyện tập qua "AI Gia sư" (Luyện tập → tab AI
          Gia sư) để AI bắt đầu theo dõi theo từng chủ đề cụ thể.
        </div>
      )}
    </div>
  );
}

const NUMERIC_FONT = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

const styles = {
  page: {
    padding: "28px 32px 48px",
    maxWidth: 1040,
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    color: "#1e2433",
  },
  loading: { padding: 24, color: "#8892a6" },
  header: { marginBottom: 24 },
  eyebrow: {
    fontSize: 13,
    color: "#8892a6",
    textTransform: "capitalize",
    marginBottom: 4,
  },
  greeting: { fontSize: 28, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" },

  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: 16,
    marginBottom: 24,
  },
  statCard: {
    borderRadius: 14,
    padding: "20px 22px",
    color: "#fff",
    boxShadow: "0 8px 20px -8px rgba(30,36,51,0.25)",
    display: "flex",
    flexDirection: "column",
  },
  statLabel: { fontSize: 13, opacity: 0.85, marginBottom: 10, fontWeight: 600 },
  statSub: { fontSize: 11.5, opacity: 0.75, marginTop: 8 },

  timerCard: { background: "linear-gradient(135deg, #0d9488, #0f766e)" },
  timerDigits: {
    fontFamily: NUMERIC_FONT,
    fontSize: 34,
    fontWeight: 700,
    letterSpacing: "0.02em",
    fontVariantNumeric: "tabular-nums",
  },

  examCard: { background: "linear-gradient(135deg, #f59e0b, #d97706)" },
  examDaysRow: { display: "flex", alignItems: "baseline", gap: 6 },
  examDaysNumber: {
    fontFamily: NUMERIC_FONT,
    fontSize: 40,
    fontWeight: 800,
    fontVariantNumeric: "tabular-nums",
  },
  examDaysUnit: { fontSize: 15, fontWeight: 600, opacity: 0.9 },
  examSubDigits: {
    fontFamily: NUMERIC_FONT,
    fontSize: 13.5,
    fontVariantNumeric: "tabular-nums",
    marginTop: 4,
    opacity: 0.92,
  },

  hoursCard: { background: "linear-gradient(135deg, #4f46e5, #4338ca)" },
  hoursNumber: {
    fontFamily: NUMERIC_FONT,
    fontSize: 34,
    fontWeight: 700,
    fontVariantNumeric: "tabular-nums",
  },

  sectionCard: {
    background: "#fff",
    border: "1px solid #eceef2",
    borderRadius: 14,
    padding: "20px 22px",
    marginBottom: 20,
    boxShadow: "0 1px 2px rgba(30,36,51,0.04)",
  },
  sectionTitle: { fontSize: 15, fontWeight: 700, margin: "0 0 14px" },
  emptyText: { color: "#8892a6", fontSize: 14 },
  subjectRow: { display: "flex", alignItems: "center", gap: 14, marginBottom: 12 },
  subjectName: { width: 110, fontSize: 14, fontWeight: 600 },
  barBg: { flex: 1, height: 8, background: "#eceef2", borderRadius: 4, overflow: "hidden" },
  barFill: { height: "100%", background: "#0d9488", borderRadius: 4 },
  subjectPercent: { width: 66, textAlign: "right", fontSize: 13, color: "#4b5566" },

  weakBox: {
    border: "1px solid #fde3b0",
    background: "#fffaf0",
    borderRadius: 14,
    padding: "20px 22px",
    maxWidth: 560,
  },
  weakTitle: { margin: "0 0 8px", fontSize: 14.5, fontWeight: 700 },
  weakTopic: { fontSize: 19, fontWeight: 700, margin: "0 0 6px" },
  weakSubject: { fontSize: 13, fontWeight: 500, color: "#8892a6" },
  weakPercent: { color: "#c05621", margin: "0 0 8px", fontSize: 14 },
  weakVideo: { color: "#2b6cb0", margin: "0 0 8px", fontSize: 13.5 },
  weakHint: { fontSize: 12.5, color: "#8892a6", margin: 0 },

  emptyWeakBox: {
    fontSize: 13,
    color: "#8892a6",
    maxWidth: 560,
    lineHeight: 1.6,
  },
};

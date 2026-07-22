import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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

// Đọc/khởi tạo mốc bắt đầu phiên học từ sessionStorage.
// Lý do: nếu để useState(() => new Date()) như trước, mỗi lần rời trang
// Dashboard rồi quay lại, component bị unmount/mount lại từ đầu và mốc
// thời gian bị tạo mới → đồng hồ "Thời gian học phiên này" nhảy về 00:00:00.
// Lưu vào sessionStorage giúp mốc này giữ nguyên trong suốt phiên trình
// duyệt (chỉ mất khi đóng tab/đóng app), bất kể chuyển qua lại giữa các mục.
function getSessionStart() {
  const saved = sessionStorage.getItem("studyapp_session_start");
  if (saved) return new Date(saved);
  const now = new Date();
  sessionStorage.setItem("studyapp_session_start", now.toISOString());
  return now;
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [now, setNow] = useState(new Date());
  const [sessionStart] = useState(getSessionStart);
  const [editingGoal, setEditingGoal] = useState(false);
  const [goalInput, setGoalInput] = useState("");
  // Mục tiêu tuỳ chỉnh lưu ở máy học sinh (backend hiện chưa có API riêng cho việc này)
  const [customGoal, setCustomGoal] = useState(() => {
    const saved = localStorage.getItem("studyapp_daily_goal_minutes");
    return saved ? Number(saved) : null;
  });
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/analytics/overview").then((res) => setData(res.data));
  }, []);

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const saveGoal = () => {
    const n = Number(goalInput);
    if (n > 0) {
      setCustomGoal(n);
      localStorage.setItem("studyapp_daily_goal_minutes", String(n));
    }
    setEditingGoal(false);
  };

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

      {/* Widget "Tiếp tục học" — nổi bật, bấm vào để luyện ngay chủ đề học gần nhất */}
      {data.continue_learning && (
        <button
          style={styles.continueCard}
          onClick={() =>
            navigate(
              `/practice?tab=tutor&topic=${encodeURIComponent(data.continue_learning.topic)}`
            )
          }
        >
          <div style={styles.continueIcon}>▶</div>
          <div style={{ textAlign: "left", flex: 1 }}>
            <div style={styles.continueLabel}>Tiếp tục học</div>
            <div style={styles.continueTopic}>
              {data.continue_learning.topic}
              <span style={styles.continueSubject}> · {data.continue_learning.subject_name}</span>
            </div>
          </div>
          <div style={styles.continueArrow}>→</div>
        </button>
      )}

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

          <div style={styles.goalWrap}>
            <div style={styles.goalLabelRow}>
              <span>Mục tiêu hôm nay</span>
              {editingGoal ? (
                <span style={styles.goalEditRow}>
                  <input
                    autoFocus
                    type="number"
                    min="1"
                    value={goalInput}
                    onChange={(e) => setGoalInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveGoal()}
                    onBlur={saveGoal}
                    style={styles.goalInput}
                  />
                  <span>phút</span>
                </span>
              ) : (
                <span
                  style={styles.goalValueBtn}
                  onClick={() => {
                    setGoalInput(String(customGoal ?? data.daily_goal_minutes));
                    setEditingGoal(true);
                  }}
                  title="Bấm để chỉnh mục tiêu"
                >
                  {data.today_minutes}/{customGoal ?? data.daily_goal_minutes} phút ✎
                </span>
              )}
            </div>
            <div style={styles.goalBarBg}>
              <div
                style={{
                  ...styles.goalBarFill,
                  width: `${Math.min(
                    100,
                    (data.today_minutes / (customGoal ?? data.daily_goal_minutes)) * 100
                  )}%`,
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Tiến độ theo môn — mini biểu đồ cột */}
      <div style={styles.sectionCard}>
        <h3 style={styles.sectionTitle}>Theo môn học</h3>
        {data.by_subject.length === 0 && (
          <button style={styles.chartEmptyState} onClick={() => navigate("/subjects")}>
            <div style={{ fontSize: 30, marginBottom: 8 }}>📊</div>
            <div style={{ fontWeight: 700, fontSize: 14.5, marginBottom: 4 }}>
              Chưa có dữ liệu học tập
            </div>
            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              Bấm vào đây để thêm môn học đầu tiên và bắt đầu luyện tập →
            </div>
          </button>
        )}
        {data.by_subject.length > 0 && (
          <div style={styles.barChartRow}>
            {data.by_subject.map((s) => {
              const pct = s.percent_correct ?? 0;
              const noData = s.percent_correct === null;
              const Wrapper = noData ? "button" : "div";
              return (
                <Wrapper
                  key={s.subject_id}
                  style={{ ...styles.barChartCol, ...(noData ? styles.barChartColClickable : {}) }}
                  onClick={
                    noData
                      ? () => navigate(`/practice?tab=tutor&topic=${encodeURIComponent(s.subject_name)}`)
                      : undefined
                  }
                  title={noData ? `Bấm để luyện tập ${s.subject_name} ngay` : undefined}
                >
                  <div style={styles.barChartValue}>
                    {s.percent_correct !== null ? `${s.percent_correct}%` : "—"}
                  </div>
                  <div style={styles.barChartTrack}>
                    <div
                      style={{
                        ...styles.barChartBar,
                        height: `${Math.max(pct, 3)}%`,
                        background: noData
                          ? "var(--color-border)"
                          : "linear-gradient(180deg, #4f6ef7, #0d9488)",
                      }}
                    />
                  </div>
                  <div style={styles.barChartLabel}>{s.subject_name}</div>
                  {noData && <div style={styles.barChartHint}>Luyện ngay →</div>}
                </Wrapper>
              );
            })}
          </div>
        )}
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
    color: "var(--color-text)",
  },
  loading: { padding: 24, color: "var(--color-text-muted)" },
  header: { marginBottom: 24 },

  continueCard: {
    display: "flex",
    alignItems: "center",
    gap: 16,
    width: "100%",
    textAlign: "left",
    background: "var(--gradient-blue)",
    border: "none",
    borderRadius: 14,
    padding: "18px 22px",
    marginBottom: 20,
    cursor: "pointer",
    boxShadow: "0 8px 20px -8px rgba(79,110,247,0.4)",
  },
  continueIcon: {
    width: 40,
    height: 40,
    borderRadius: "50%",
    background: "rgba(255,255,255,0.2)",
    color: "#fff",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 15,
    flexShrink: 0,
  },
  continueLabel: { fontSize: 12, color: "rgba(255,255,255,0.85)", fontWeight: 600, marginBottom: 2 },
  continueTopic: { fontSize: 17, fontWeight: 700, color: "#fff" },
  continueSubject: { fontSize: 13, fontWeight: 500, color: "rgba(255,255,255,0.8)" },
  continueArrow: { fontSize: 20, color: "#fff", opacity: 0.85 },

  goalWrap: { marginTop: 14 },
  goalLabelRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: 11.5,
    opacity: 0.85,
    marginBottom: 5,
  },
  goalValueBtn: {
    cursor: "pointer",
    borderBottom: "1px dashed rgba(255,255,255,0.6)",
  },
  goalEditRow: { display: "flex", alignItems: "center", gap: 5 },
  goalInput: {
    width: 46,
    padding: "2px 6px",
    borderRadius: 6,
    border: "1px solid rgba(255,255,255,0.4)",
    background: "rgba(255,255,255,0.15)",
    color: "#fff",
    fontSize: 12,
  },
  goalBarBg: {
    height: 6,
    background: "rgba(255,255,255,0.25)",
    borderRadius: 3,
    overflow: "hidden",
  },
  goalBarFill: { height: "100%", background: "#fff", borderRadius: 3 },

  barChartRow: {
    display: "flex",
    gap: 18,
    alignItems: "flex-end",
    height: 160,
    paddingTop: 10,
  },
  barChartCol: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    flex: 1,
    height: "100%",
    border: "none",
    background: "transparent",
    padding: 0,
    font: "inherit",
  },
  barChartColClickable: { cursor: "pointer" },
  barChartHint: {
    fontSize: 10.5,
    color: "var(--color-primary)",
    fontWeight: 600,
    marginTop: 3,
  },
  barChartValue: { fontSize: 12, fontWeight: 700, marginBottom: 6, color: "var(--color-text)" },
  barChartTrack: {
    flex: 1,
    width: 28,
    background: "var(--color-bg)",
    borderRadius: 6,
    display: "flex",
    alignItems: "flex-end",
    overflow: "hidden",
  },
  barChartBar: { width: "100%", borderRadius: "6px 6px 0 0", transition: "height 0.4s ease" },
  barChartLabel: { fontSize: 12, color: "var(--color-text-muted)", marginTop: 8, fontWeight: 600 },
  eyebrow: {
    fontSize: 13,
    color: "var(--color-text-muted)",
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
    background: "var(--color-surface)",
    border: "1px solid #eceef2",
    borderRadius: 14,
    padding: "20px 22px",
    marginBottom: 20,
    boxShadow: "0 1px 2px rgba(30,36,51,0.04)",
  },
  sectionTitle: { fontSize: 15, fontWeight: 700, margin: "0 0 14px" },
  emptyText: { color: "var(--color-text-muted)", fontSize: 14 },
  chartEmptyState: {
    width: "100%",
    textAlign: "center",
    padding: "36px 20px",
    background: "var(--color-bg)",
    border: "1px dashed var(--color-border)",
    borderRadius: 12,
    cursor: "pointer",
    font: "inherit",
    color: "var(--color-text)",
  },
  subjectRow: { display: "flex", alignItems: "center", gap: 14, marginBottom: 12 },
  subjectName: { width: 110, fontSize: 14, fontWeight: 600 },
  barBg: { flex: 1, height: 8, background: "#eceef2", borderRadius: 4, overflow: "hidden" },
  barFill: { height: "100%", background: "#0d9488", borderRadius: 4 },
  subjectPercent: { width: 66, textAlign: "right", fontSize: 13, color: "var(--color-text-muted)" },

  weakBox: {
    border: "1px solid #fde3b0",
    background: "#fffaf0",
    borderRadius: 14,
    padding: "20px 22px",
    maxWidth: 560,
  },
  weakTitle: { margin: "0 0 8px", fontSize: 14.5, fontWeight: 700 },
  weakTopic: { fontSize: 19, fontWeight: 700, margin: "0 0 6px" },
  weakSubject: { fontSize: 13, fontWeight: 500, color: "var(--color-text-muted)" },
  weakPercent: { color: "var(--color-warning)", margin: "0 0 8px", fontSize: 14 },
  weakVideo: { color: "var(--color-primary-dark)", margin: "0 0 8px", fontSize: 13.5 },
  weakHint: { fontSize: 12.5, color: "var(--color-text-muted)", margin: 0 },

  emptyWeakBox: {
    fontSize: 13,
    color: "var(--color-text-muted)",
    maxWidth: 560,
    lineHeight: 1.6,
  },
};




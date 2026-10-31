import { useEffect, useState } from "react";
import api from "../api";
import { useNavigate } from "react-router-dom";
import MathView from "../components/MathView";

export default function Mistakes() {
  const [mistakes, setMistakes] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/subjects").then((res) => setSubjects(res.data));
    loadMistakes();
  }, []);

  const loadMistakes = (subjectId = null) => {
    setLoading(true);
    const url = subjectId ? `/stats/mistakes?subject_id=${subjectId}` : "/stats/mistakes";
    api.get(url)
      .then((res) => setMistakes(res.data))
      .catch((err) => console.error("Lỗi tải sổ lỗi sai:", err))
      .finally(() => setLoading(false));
  };

  const handleFilter = (subjectId) => {
    setSelectedSubject(subjectId);
    loadMistakes(subjectId);
  };

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
        <div>
          <h2 style={{ margin: "0 0 4px" }}>❌ Sổ Lỗi Sai (Mistake Log)</h2>
          <div style={{ color: "#718096", fontSize: 14 }}>
            Tổng hợp toàn bộ câu hỏi bạn đã làm sai để ôn tập lại kiến thức trọng tâm
          </div>
        </div>
        <button
          onClick={() => navigate("/exams")}
          style={styles.primaryBtn}
        >
          📝 Làm đề luyện tập
        </button>
      </div>

      {/* Bộ lọc môn học */}
      <div style={styles.filterRow}>
        <button
          onClick={() => handleFilter(null)}
          style={{
            ...styles.filterBtn,
            background: selectedSubject === null ? "#3182ce" : "#edf2f7",
            color: selectedSubject === null ? "#fff" : "#2d3748",
          }}
        >
          Tất cả môn ({mistakes.length})
        </button>
        {subjects.map((s) => (
          <button
            key={s.id}
            onClick={() => handleFilter(s.id)}
            style={{
              ...styles.filterBtn,
              background: selectedSubject === s.id ? "#3182ce" : "#edf2f7",
              color: selectedSubject === s.id ? "#fff" : "#2d3748",
            }}
          >
            {s.name}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#718096" }}>Đang tải dữ liệu lỗi sai...</div>
      ) : mistakes.length === 0 ? (
        <div style={styles.emptyBox}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🎉</div>
          <h3>Không có lỗi sai nào!</h3>
          <p style={{ color: "#718096" }}>
            {selectedSubject ? "Bạn chưa làm sai câu nào ở môn học này." : "Bạn chưa làm sai câu nào hoặc chưa hoàn thành bài thi nào."}
          </p>
          <button onClick={() => navigate("/exams")} style={styles.primaryBtn}>
            Vào phòng thi làm bài ngay
          </button>
        </div>
      ) : (
        <div style={{ marginTop: 16 }}>
          {mistakes.map((m, idx) => (
            <div key={m.answer_id || idx} style={styles.card}>
              <div style={styles.cardHeader}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <span style={styles.subjectBadge}>📘 {m.subject_name || "Môn học"}</span>
                  <span style={styles.examTitle}>Đề: {m.exam_title}</span>
                  {m.topic_tag && <span style={styles.tagBadge}>🏷️ {m.topic_tag}</span>}
                </div>
                <button
                  onClick={() => navigate("/chat")}
                  style={styles.askAiBtn}
                  title="Nhờ AI giải thích chi tiết câu này"
                >
                  💬 Hỏi AI câu này
                </button>
              </div>

              {/* Nội dung câu hỏi */}
              <div style={styles.questionText}>
                <b>Câu {m.question_number}:</b> <MathView text={m.question_text} />
              </div>

              {/* Các phương án lựa chọn (Phần I hoặc II/III) */}
              {m.option_a || m.option_b ? (
                <div style={styles.optionsGrid}>
                  {["A", "B", "C", "D"].map((opt) => {
                    const optText = m[`option_${opt.toLowerCase()}`];
                    if (!optText) return null;
                    const isSelected = m.selected_answer === opt;
                    const isCorrect = m.correct_answer === opt;

                    let border = "#e2e8f0";
                    let bg = "#fff";
                    if (isSelected && !isCorrect) {
                      border = "#f56565";
                      bg = "#fff5f5";
                    } else if (isCorrect) {
                      border = "#48bb78";
                      bg = "#f0fff4";
                    }

                    return (
                      <div key={opt} style={{ ...styles.optionItem, borderColor: border, background: bg }}>
                        <span style={{ fontWeight: 700, width: 24 }}>{opt}.</span>
                        <span style={{ flex: 1 }}>
                          <MathView text={optText} />
                        </span>
                        {isSelected && !isCorrect && (
                          <span style={{ color: "#e53e3e", fontWeight: 700, fontSize: 13 }}>❌ Bạn đã chọn</span>
                        )}
                        {isCorrect && (
                          <span style={{ color: "#38a169", fontWeight: 700, fontSize: 13 }}>✅ Đáp án đúng</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ background: "#f8fafc", padding: "10px 14px", borderRadius: 8, marginBottom: 12, border: "1px solid #e2e8f0" }}>
                  <div style={{ color: "#dc2626", marginBottom: 4 }}>
                    ❌ <b>Bạn đã điền:</b> {m.selected_answer || "Chưa điền đáp án"}
                  </div>
                  <div style={{ color: "#16a34a", fontWeight: 700 }}>
                    ✅ <b>Đáp án chuẩn:</b> {m.correct_answer}
                  </div>
                </div>
              )}

              {/* Lời giải chi tiết */}
              {m.explanation && (
                <div style={styles.explanationBox}>
                  <b>💡 Lời giải / Phân tích chi tiết:</b>
                  <div style={{ marginTop: 4, color: "#4a5568", lineHeight: 1.5 }}>
                    <MathView text={m.explanation} />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
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
  filterRow: {
    display: "flex",
    gap: 8,
    margin: "18px 0 10px",
    flexWrap: "wrap",
  },
  filterBtn: {
    padding: "6px 14px",
    border: "none",
    borderRadius: 20,
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
  },
  emptyBox: {
    background: "#fff",
    border: "1px dashed #cbd5e0",
    borderRadius: 12,
    padding: 48,
    textAlign: "center",
    marginTop: 24,
  },
  card: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: 18,
    marginBottom: 16,
    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
    paddingBottom: 8,
    borderBottom: "1px solid #edf2f7",
  },
  subjectBadge: {
    background: "#ebf8ff",
    color: "#2b6cb0",
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 12,
    fontWeight: 700,
  },
  examTitle: {
    color: "#718096",
    fontSize: 13,
  },
  tagBadge: {
    background: "#edf2f7",
    color: "#4a5568",
    padding: "2px 8px",
    borderRadius: 4,
    fontSize: 12,
  },
  askAiBtn: {
    padding: "4px 10px",
    background: "#edf2f7",
    border: "1px solid #cbd5e0",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 600,
    color: "#2b6cb0",
  },
  questionText: {
    fontSize: 15,
    color: "#2d3748",
    lineHeight: 1.5,
    marginBottom: 12,
  },
  optionsGrid: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
    marginBottom: 12,
  },
  optionItem: {
    display: "flex",
    alignItems: "center",
    padding: "8px 12px",
    borderRadius: 6,
    border: "1px solid",
    fontSize: 14,
  },
  explanationBox: {
    background: "#fffaf0",
    borderLeft: "4px solid #dd6b20",
    borderRadius: 4,
    padding: "10px 14px",
    fontSize: 14,
  },
};

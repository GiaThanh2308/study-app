import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api";
import MathView from "../components/MathView";

export default function ExamTake() {
  const { examId, attemptId } = useParams();
  const navigate = useNavigate();

  const [exam, setExam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  // answers: { [questionId]: "A" | "T,F,T,F" | "12.5" }
  const [answers, setAnswers] = useState({});
  const [flagged, setFlagged] = useState({}); // { [questionId]: boolean }
  const [timeLeft, setTimeLeft] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  // Modal & Toast states
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: "", message: "", action: null });
  const [toast, setToast] = useState(null);

  const storageKey = `studyapp_exam_${examId}_attempt_${attemptId}`;

  // Tải dữ liệu đề thi & khôi phục bài làm
  const fetchExamData = () => {
    setLoading(true);
    setLoadError(null);
    api.get(`/exams/${examId}`)
      .then((res) => {
        setExam(res.data);
        
        // Kiểm tra xem có bản nháp tự động lưu trong localStorage không
        const savedDraft = localStorage.getItem(storageKey);
        if (savedDraft) {
          try {
            const parsed = JSON.parse(savedDraft);
            setAnswers(parsed.answers || {});
            setFlagged(parsed.flagged || {});
            setTimeLeft(parsed.timeLeft > 0 ? parsed.timeLeft : res.data.duration_minutes * 60);
            showToast("💾 Đã khôi phục các câu trả lời bạn đã chọn trước đó!", "info");
          } catch (e) {
            setTimeLeft(res.data.duration_minutes * 60);
          }
        } else {
          setTimeLeft(res.data.duration_minutes * 60);
        }
      })
      .catch((err) => {
        setLoadError(err.response?.data?.detail || "Không thể tải đề thi. Vui lòng kiểm tra lại kết nối máy chủ.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchExamData();
  }, [examId]);

  // Tự động lưu bài làm vào localStorage
  useEffect(() => {
    if (!result && exam && Object.keys(answers).length > 0) {
      localStorage.setItem(storageKey, JSON.stringify({ answers, flagged, timeLeft }));
    }
  }, [answers, flagged, timeLeft, result, exam]);

  // Bộ đếm ngược thời gian
  useEffect(() => {
    if (result || timeLeft <= 0 || loading || loadError) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          handleAutoSubmitOnTimeout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft, result, loading, loadError]);

  const showToast = (message, type = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Chọn đáp án trắc nghiệm Phần I (A, B, C, D)
  const handleSelectOption = (questionId, option) => {
    if (result) return;
    setAnswers((prev) => ({ ...prev, [questionId]: option }));
  };

  // Chọn Đúng / Sai từng ý Phần II (a, b, c, d)
  const handleToggleTrueFalse = (questionId, statementIdx, value) => {
    if (result) return;
    const current = (answers[questionId] || "_,_,_,_").split(",");
    while (current.length < 4) current.push("_");
    current[statementIdx] = value; // "T" hoặc "F"
    setAnswers((prev) => ({ ...prev, [questionId]: current.join(",") }));
  };

  // Nhập đáp án trả lời ngắn Phần III
  const handleShortAnswerChange = (questionId, value) => {
    if (result) return;
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  // Đánh dấu câu phân vân (Flag)
  const toggleFlag = (questionId) => {
    setFlagged((prev) => ({ ...prev, [questionId]: !prev[questionId] }));
  };

  // Tự động nộp bài khi hết giờ
  const handleAutoSubmitOnTimeout = () => {
    showToast("⏰ Đã hết thời gian làm bài! Hệ thống đang tự động nộp bài thi...", "warning");
    doSubmitPayload();
  };

  // Bấm nút nộp bài chủ động
  const confirmAndSubmit = () => {
    if (result) return;
    const answeredCount = Object.keys(answers).filter((k) => answers[k] && !answers[k].includes("_")).length;
    const totalQ = exam?.questions?.length || 0;

    setConfirmModal({
      isOpen: true,
      title: "Xác nhận nộp bài thi",
      message: `Bạn đã làm ${answeredCount}/${totalQ} câu hỏi. Bạn có chắc chắn muốn nộp bài để xem điểm và lời giải chi tiết không?`,
      confirmText: "Nộp bài ngay",
      confirmColor: "#10b981",
      action: doSubmitPayload,
    });
  };

  const doSubmitPayload = async () => {
    setIsSubmitting(true);
    setConfirmModal({ isOpen: false, title: "", message: "", action: null });
    try {
      const payloadAnswers = exam.questions.map((q) => ({
        question_id: q.id,
        selected_answer: answers[q.id] || null,
      }));

      const res = await api.post(`/attempts/${attemptId}/submit`, {
        exam_id: Number(examId),
        answers: payloadAnswers,
      });

      setResult(res.data);
      localStorage.removeItem(storageKey); // Xóa bản nháp sau khi đã nộp thành công
      showToast("🎉 Nộp bài thành công! Xem điểm và phân tích bên dưới.", "success");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      showToast("Lỗi khi nộp bài: " + (err.response?.data?.detail || err.message), "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Xử lý khi bấm nút Thoát
  const handleExit = () => {
    if (result) {
      navigate("/exams");
      return;
    }
    setConfirmModal({
      isOpen: true,
      title: "Rời khỏi phòng thi?",
      message: "Bài thi chưa được nộp. Tiến độ làm bài của bạn đã được tự động lưu tạm trên máy. Bạn có chắc chắn muốn thoát?",
      confirmText: "Thoát ra",
      confirmColor: "#ef4444",
      action: () => navigate("/exams"),
    });
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Cuộn mượt đến câu hỏi
  const scrollToQuestion = (qId) => {
    const el = document.getElementById(`q-${qId}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  // 1. Giao diện Loading Skeleton
  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.skeletonHeader} />
        <div style={{ display: "flex", gap: 24, marginTop: 20 }}>
          <div style={{ flex: 1 }}>
            {[1, 2, 3].map((n) => (
              <div key={n} style={styles.skeletonCard}>
                <div style={styles.skeletonLineShort} />
                <div style={styles.skeletonLineFull} />
                <div style={styles.skeletonLineFull} />
              </div>
            ))}
          </div>
          <div style={styles.skeletonSidebar} />
        </div>
      </div>
    );
  }

  // 2. Giao diện Báo Lỗi có nút Thử lại
  if (loadError) {
    return (
      <div style={{ padding: 40, textAlign: "center", maxWidth: 500, margin: "60px auto", background: "#fff", borderRadius: 12, border: "1px solid #fee2e2" }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>⚠️</div>
        <h3 style={{ color: "#b91c1c" }}>Không thể tải đề thi</h3>
        <p style={{ color: "#6b7280", margin: "10px 0 20px" }}>{loadError}</p>
        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <button style={styles.btnSecondary} onClick={() => navigate("/exams")}>← Quay lại Kho đề</button>
          <button style={styles.btnPrimary} onClick={fetchExamData}>🔄 Thử lại ngay</button>
        </div>
      </div>
    );
  }

  const answeredCount = exam.questions.filter((q) => {
    const a = answers[q.id];
    return a && (q.question_type !== "true_false" || !a.includes("_"));
  }).length;

  return (
    <div style={styles.container}>
      {/* Toast Notification */}
      {toast && (
        <div style={{ ...styles.toast, background: toast.type === "success" ? "#065f46" : toast.type === "error" ? "#991b1b" : "#1e40af" }}>
          {toast.message}
        </div>
      )}

      {/* Custom Confirmation Modal */}
      {confirmModal.isOpen && (
        <div style={styles.modalBackdrop}>
          <div style={styles.modalBox}>
            <h3 style={{ margin: "0 0 10px", fontSize: 18, color: "#1f2937" }}>{confirmModal.title}</h3>
            <p style={{ color: "#4b5563", fontSize: 14, lineHeight: 1.5, margin: "0 0 20px" }}>{confirmModal.message}</p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button style={styles.btnSecondary} onClick={() => setConfirmModal({ isOpen: false, title: "", message: "", action: null })}>
                Hủy bỏ
              </button>
              <button style={{ ...styles.btnPrimary, background: confirmModal.confirmColor }} onClick={confirmModal.action}>
                {confirmModal.confirmText}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header đề thi */}
      <div style={styles.header}>
        <div>
          <button style={styles.backBtn} onClick={handleExit}>
            ← Thoát phòng thi
          </button>
          <h2 style={{ margin: "6px 0 4px", fontSize: 20, color: "#111827" }}>
            <MathView text={exam.title} />
          </h2>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
            {exam.school_or_dept && <span style={styles.badgeSchool}>🏛️ {exam.school_or_dept}</span>}
            {exam.province && <span style={styles.badgeProvince}>📍 {exam.province}</span>}
            <span style={styles.badgeStandard}>🎯 Chuẩn cấu trúc 2025 (GDPT 2018)</span>
            <span style={{ fontSize: 13, color: "#6b7280", marginLeft: 4 }}>
              · {exam.total_questions} câu · {exam.duration_minutes} phút
            </span>
          </div>
        </div>

        {/* Khối hiển thị kết quả hoặc đếm ngược */}
        {result ? (
          <div style={styles.resultBox}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#065f46", textTransform: "uppercase" }}>KẾT QUẢ BÀI THI</div>
            <div style={{ fontSize: 28, fontWeight: 900, color: "#059669" }}>{result.score} / 10</div>
            <div style={{ fontSize: 12, color: "#047857" }}>Đúng {result.total_correct}/{result.total_questions} câu</div>
          </div>
        ) : (
          <div style={{ ...styles.timerBox, borderColor: timeLeft < 300 ? "#fca5a5" : "#bfdbfe" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#6b7280" }}>THỜI GIAN CÒN LẠI</div>
            <div style={{ fontSize: 26, fontWeight: 800, color: timeLeft < 300 ? "#dc2626" : "#1d4ed8" }}>
              ⏳ {formatTime(timeLeft)}
            </div>
          </div>
        )}
      </div>

      {/* Thông báo hoàn thành sau khi nộp */}
      {result && (
        <div style={styles.completedBanner}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
            <div>
              <h3 style={{ margin: "0 0 4px", color: "#065f46" }}>🎉 Chúc mừng bạn đã hoàn thành bài thi!</h3>
              <p style={{ margin: 0, fontSize: 14, color: "#047857" }}>
                Điểm số đã được ghi nhận vào Dashboard và các câu trả lời chưa đúng đã được tự động lưu vào Sổ lỗi sai để bạn rèn luyện lại.
              </p>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button style={styles.btnSecondary} onClick={() => navigate("/mistakes")}>❌ Xem Sổ lỗi sai</button>
              <button style={styles.btnPrimary} onClick={() => navigate("/dashboard")}>📊 Về Dashboard</button>
            </div>
          </div>
        </div>
      )}

      {/* Main Body: Danh sách câu hỏi (Trái) & Bảng điều hướng câu hỏi (Phải) */}
      <div style={styles.bodyLayout}>
        {/* Cột trái: Các câu hỏi */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {exam.questions.map((q, idx) => {
            const qType = q.question_type || "multiple_choice";
            const userAns = answers[q.id];
            const isFlagged = Boolean(flagged[q.id]);
            const isSubmitted = Boolean(result);

            return (
              <div
                key={q.id}
                id={`q-${q.id}`}
                style={{
                  ...styles.questionCard,
                  borderColor: isSubmitted
                    ? (qType === "multiple_choice" && userAns === q.correct_answer ? "#10b981" : "#e5e7eb")
                    : isFlagged ? "#f59e0b" : "#e5e7eb",
                }}
              >
                {/* Header câu hỏi */}
                <div style={styles.qHeader}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span style={styles.qNumber}>Câu {q.question_number}</span>
                    <span style={styles.qTypeBadge}>
                      {qType === "multiple_choice" ? "Phần I: 4 Lựa chọn" : qType === "true_false" ? "Phần II: Đúng / Sai" : "Phần III: Trả lời ngắn"}
                    </span>
                    {q.topic_tag && <span style={styles.tagTopic}>{q.topic_tag}</span>}
                  </div>
                  {!isSubmitted && (
                    <button
                      onClick={() => toggleFlag(q.id)}
                      style={{ ...styles.flagBtn, background: isFlagged ? "#fef3c7" : "transparent", color: isFlagged ? "#d97706" : "#9ca3af" }}
                      title="Đánh dấu câu phân vân để xem lại sau"
                    >
                      {isFlagged ? "⭐ Đang phân vân" : "☆ Đánh dấu"}
                    </button>
                  )}
                </div>

                {/* Nội dung đề bài */}
                <div style={styles.qText}>
                  <MathView text={q.question_text} />
                </div>

                {/* 1. DẠNG TRẮC NGHIỆM 4 LỰA CHỌN (PHẦN I) */}
                {qType === "multiple_choice" && (
                  <div style={styles.optionsList}>
                    {["A", "B", "C", "D"].map((opt) => {
                      const optText = q[`option_${opt.toLowerCase()}`];
                      const isPicked = userAns === opt;
                      const isRight = isSubmitted && q.correct_answer === opt;

                      let bg = "#f9fafb";
                      let border = "#e5e7eb";
                      if (isPicked) { bg = "#eff6ff"; border = "#3b82f6"; }
                      if (isSubmitted) {
                        if (isRight) { bg = "#ecfdf5"; border = "#10b981"; }
                        else if (isPicked && !isRight) { bg = "#fef2f2"; border = "#ef4444"; }
                      }

                      return (
                        <div
                          key={opt}
                          onClick={() => handleSelectOption(q.id, opt)}
                          style={{ ...styles.optionCard, background: bg, borderColor: border, cursor: isSubmitted ? "default" : "pointer" }}
                        >
                          <span style={styles.optLetter}>{opt}.</span>
                          <span style={{ flex: 1 }}>
                            <MathView text={optText} />
                          </span>
                          {isSubmitted && isRight && <span style={styles.tagCorrect}>✅ Đáp án đúng</span>}
                          {isSubmitted && isPicked && !isRight && <span style={styles.tagWrong}>❌ Bạn đã chọn</span>}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* 2. DẠNG TRẮC NGHIỆM ĐÚNG / SAI 4 Ý (PHẦN II) */}
                {qType === "true_false" && (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 8, fontStyle: "italic" }}>
                      Thí sinh chọn Đúng hoặc Sai cho mỗi ý a), b), c), d):
                    </div>
                    {["a", "b", "c", "d"].map((subKey, subIdx) => {
                      const stmtText = q[`option_${subKey}`];
                      const userChoices = (userAns || "_,_,_,_").split(",");
                      const myChoice = userChoices[subIdx]; // "T" hoặc "F" hoặc "_"
                      const correctChoices = (q.correct_answer || "").split(",");
                      const rightChoice = correctChoices[subIdx];

                      return (
                        <div key={subKey} style={styles.tfRow}>
                          <div style={{ flex: 1, paddingRight: 12 }}>
                            <b>{subKey})</b> <MathView text={stmtText} />
                          </div>
                          <div style={{ display: "flex", gap: 6 }}>
                            <button
                              disabled={isSubmitted}
                              onClick={() => handleToggleTrueFalse(q.id, subIdx, "T")}
                              style={{
                                ...styles.tfBtn,
                                background: myChoice === "T" ? (isSubmitted ? (rightChoice === "T" ? "#10b981" : "#ef4444") : "#3b82f6") : "#f3f4f6",
                                color: myChoice === "T" ? "#fff" : "#374151",
                              }}
                            >
                              Đúng
                            </button>
                            <button
                              disabled={isSubmitted}
                              onClick={() => handleToggleTrueFalse(q.id, subIdx, "F")}
                              style={{
                                ...styles.tfBtn,
                                background: myChoice === "F" ? (isSubmitted ? (rightChoice === "F" ? "#10b981" : "#ef4444") : "#3b82f6") : "#f3f4f6",
                                color: myChoice === "F" ? "#fff" : "#374151",
                              }}
                            >
                              Sai
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* 3. DẠNG TRẢ LỜI NGẮN (PHẦN III) */}
                {qType === "short_answer" && (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 6 }}>
                      Điền đáp số số học (nguyên hoặc số thập phân/phân số):
                    </div>
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <input
                        type="text"
                        disabled={isSubmitted}
                        value={userAns || ""}
                        onChange={(e) => handleShortAnswerChange(q.id, e.target.value)}
                        placeholder="Nhập kết quả (VD: 10, 0.4, 73.6)..."
                        style={styles.shortInput}
                      />
                      {isSubmitted && (
                        <div style={{ fontSize: 14 }}>
                          {userAns?.trim() === q.correct_answer?.trim() ? (
                            <span style={{ color: "#10b981", fontWeight: 700 }}>✅ Chính xác</span>
                          ) : (
                            <span style={{ color: "#ef4444" }}>
                              ❌ Đáp án đúng: <b>{q.correct_answer}</b>
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Lời giải chi tiết sau khi nộp */}
                {isSubmitted && q.explanation && (
                  <div style={styles.explanationBox}>
                    <b>💡 Lời giải & Phân tích chi tiết:</b>
                    <div style={{ marginTop: 4, color: "#374151", lineHeight: 1.5 }}>
                      <MathView text={q.explanation} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Cột phải: Bảng điều hướng câu hỏi (Floating Question Matrix) */}
        <div style={styles.sidebarSticky}>
          <div style={styles.matrixCard}>
            <div style={{ fontWeight: 700, fontSize: 15, color: "#1f2937", marginBottom: 8 }}>
              📋 Danh Sách Câu Hỏi
            </div>
            <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 14 }}>
              Tiến độ: <b>{answeredCount}</b> / {exam.questions.length} câu
            </div>

            {/* Chú thích màu sắc */}
            <div style={styles.legendRow}>
              <div style={styles.legendItem}><span style={{ ...styles.dot, background: "#10b981" }} /> Đã làm</div>
              <div style={styles.legendItem}><span style={{ ...styles.dot, background: "#f59e0b" }} /> Phân vân</div>
              <div style={styles.legendItem}><span style={{ ...styles.dot, background: "#e5e7eb" }} /> Chưa làm</div>
            </div>

            {/* Lưới các ô câu hỏi */}
            <div style={styles.matrixGrid}>
              {exam.questions.map((q) => {
                const a = answers[q.id];
                const isAnswered = a && (q.question_type !== "true_false" || !a.includes("_"));
                const isFlag = flagged[q.id];

                let bg = "#f3f4f6";
                let textCol = "#4b5563";
                let borderCol = "#e5e7eb";

                if (isAnswered) { bg = "#10b981"; textCol = "#fff"; borderCol = "#059669"; }
                if (isFlag) { borderCol = "#d97706"; }

                return (
                  <button
                    key={q.id}
                    onClick={() => scrollToQuestion(q.id)}
                    style={{
                      ...styles.matrixBtn,
                      background: bg,
                      color: textCol,
                      borderColor: borderCol,
                      borderWidth: isFlag ? 2 : 1,
                    }}
                  >
                    {q.question_number}
                  </button>
                );
              })}
            </div>

            {/* Nút nộp bài */}
            {!result && (
              <div style={{ marginTop: 20 }}>
                <button
                  onClick={confirmAndSubmit}
                  disabled={isSubmitting}
                  style={styles.submitBtnFull}
                >
                  {isSubmitting ? "Đang chấm điểm..." : "📝 Nộp bài thi"}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: { maxWidth: 1160, margin: "0 auto", padding: "20px 24px" },
  header: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    borderBottom: "1px solid #e5e7eb", paddingBottom: 16, marginBottom: 20, flexWrap: "wrap", gap: 12,
  },
  backBtn: {
    background: "transparent", border: "none", color: "#3b82f6",
    fontSize: 13, fontWeight: 600, cursor: "pointer", padding: 0, marginBottom: 4,
  },
  badgeSchool: { background: "#eff6ff", color: "#1d4ed8", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700, border: "1px solid #bfdbfe" },
  badgeProvince: { background: "#fffbeb", color: "#b45309", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600, border: "1px solid #fde68a" },
  badgeStandard: { background: "#ecfdf5", color: "#047857", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700, border: "1px solid #a7f3d0" },
  timerBox: { background: "#eff6ff", border: "1px solid", borderRadius: 8, padding: "8px 18px", textAlign: "center" },
  resultBox: { background: "#ecfdf5", border: "1px solid #a7f3d0", borderRadius: 8, padding: "8px 20px", textAlign: "center" },
  completedBanner: { background: "#ecfdf5", border: "1px solid #a7f3d0", borderRadius: 10, padding: 18, marginBottom: 20 },
  bodyLayout: { display: "flex", gap: 24, alignItems: "flex-start" },
  questionCard: { background: "#fff", border: "1px solid", borderRadius: 10, padding: 20, marginBottom: 16, boxShadow: "0 1px 2px rgba(0,0,0,0.04)" },
  qHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  qNumber: { fontSize: 15, fontWeight: 800, color: "#111827" },
  qTypeBadge: { background: "#f3f4f6", color: "#4b5563", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 4 },
  tagTopic: { background: "#e0e7ff", color: "#3730a3", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 4 },
  flagBtn: { border: "none", borderRadius: 4, padding: "3px 8px", fontSize: 12, fontWeight: 600, cursor: "pointer" },
  qText: { fontSize: 15, color: "#1f2937", lineHeight: 1.6, marginBottom: 14 },
  optionsList: { display: "flex", flexDirection: "column", gap: 8 },
  optionCard: { display: "flex", alignItems: "center", padding: "10px 14px", borderRadius: 8, border: "1px solid", fontSize: 14, transition: "all 0.15s ease" },
  optLetter: { fontWeight: 800, width: 28, color: "#1f2937" },
  tagCorrect: { color: "#059669", fontWeight: 700, fontSize: 12, marginLeft: 8 },
  tagWrong: { color: "#dc2626", fontWeight: 700, fontSize: 12, marginLeft: 8 },
  tfRow: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderBottom: "1px solid #f3f4f6", fontSize: 14 },
  tfBtn: { padding: "4px 12px", border: "none", borderRadius: 6, fontSize: 12, fontWeight: 700, cursor: "pointer" },
  shortInput: { width: 260, padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 14, outline: "none" },
  explanationBox: { background: "#fffbeb", borderLeft: "4px solid #f59e0b", padding: "10px 14px", borderRadius: 6, marginTop: 14, fontSize: 14 },
  sidebarSticky: { width: 280, position: "sticky", top: 20 },
  matrixCard: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: 18, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" },
  legendRow: { display: "flex", gap: 10, fontSize: 11, color: "#6b7280", marginBottom: 12 },
  legendItem: { display: "flex", alignItems: "center", gap: 4 },
  dot: { width: 8, height: 8, borderRadius: "50%" },
  matrixGrid: { display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 6 },
  matrixBtn: { height: 36, borderRadius: 6, border: "1px solid", fontSize: 13, fontWeight: 700, cursor: "pointer" },
  submitBtnFull: { width: "100%", padding: "11px 0", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontSize: 15, fontWeight: 700, cursor: "pointer" },
  btnPrimary: { padding: "8px 16px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, fontWeight: 600, fontSize: 13, cursor: "pointer" },
  btnSecondary: { padding: "8px 14px", background: "#f3f4f6", color: "#374151", border: "1px solid #d1d5db", borderRadius: 6, fontWeight: 600, fontSize: 13, cursor: "pointer" },
  toast: { position: "fixed", bottom: 24, right: 24, color: "#fff", padding: "12px 20px", borderRadius: 8, fontSize: 14, fontWeight: 600, zIndex: 9999, boxShadow: "0 4px 12px rgba(0,0,0,0.15)" },
  modalBackdrop: { position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 },
  modalBox: { background: "#fff", borderRadius: 12, padding: 24, maxWidth: 460, width: "90%", boxShadow: "0 10px 25px rgba(0,0,0,0.15)" },
  skeletonHeader: { height: 60, background: "#f3f4f6", borderRadius: 8 },
  skeletonCard: { height: 140, background: "#f3f4f6", borderRadius: 10, marginBottom: 14, padding: 16 },
  skeletonLineShort: { height: 16, width: "30%", background: "#e5e7eb", borderRadius: 4, marginBottom: 10 },
  skeletonLineFull: { height: 14, width: "100%", background: "#e5e7eb", borderRadius: 4, marginBottom: 8 },
  skeletonSidebar: { width: 280, height: 350, background: "#f3f4f6", borderRadius: 10 },
};

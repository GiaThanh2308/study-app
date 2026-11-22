import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api";
import MathView from "../components/MathView";

function optionEntries(options) {
  if (Array.isArray(options)) return options.map((value, index) => [String.fromCharCode(65 + index), value]);
  if (!options || typeof options !== "object") return [];
  return Object.entries(options).map(([key, value]) => [key.replace(/^option_?/i, "").toUpperCase(), value]);
}

function formatAnswer(answer) {
  if (Array.isArray(answer)) return answer.map((item) => item === "T" ? "Đúng" : item === "F" ? "Sai" : String(item ?? "—")).join(" · ");
  if (answer && typeof answer === "object" && Array.isArray(answer.accepted)) return answer.accepted.join(" hoặc ");
  if (answer && typeof answer === "object" && answer.choice) return String(answer.choice);
  if (answer && typeof answer === "object") return JSON.stringify(answer);
  return answer === null || answer === undefined || answer === "" ? "Không trả lời" : String(answer);
}

export default function ExamTake() {
  const { examId, attemptId } = useParams();
  const navigate = useNavigate();
  const [exam, setExam] = useState(null);
  const [attempt, setAttempt] = useState(null);
  const [answers, setAnswers] = useState({});
  const [timeLeft, setTimeLeft] = useState(0);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const submitLock = useRef(false);
  const automaticSubmitStarted = useRef(false);
  const submitRef = useRef(null);
  const storageKey = `studyapp_attempt_${attemptId}`;

  useEffect(() => {
    let alive = true;
    submitLock.current = false;
    automaticSubmitStarted.current = false;
    setExam(null);
    setAttempt(null);
    setAnswers({});
    setTimeLeft(0);
    setResult(null);
    setError("");
    setLoading(true);
    Promise.all([
      api.get(`/exams/${examId}`),
      api.get(`/attempts/${attemptId}?exam_id=${examId}`),
    ]).then(([examResponse, attemptResponse]) => {
      if (!alive) return;
      const examData = examResponse.data;
      const attemptData = attemptResponse.data;
      setExam(examData);
      setAttempt(attemptData);
      if (attemptData.status === "completed") {
        setResult(attemptData);
        setAnswers(Object.fromEntries(attemptData.results.map((item) => [item.question_id, item.response])));
        localStorage.removeItem(storageKey);
      } else {
        const elapsed = Math.max(0, Math.floor((Date.now() - new Date(attemptData.started_at).getTime()) / 1000));
        setTimeLeft(Math.max(0, examData.duration_minutes * 60 - elapsed));
        try {
          const saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
          setAnswers(saved.answers || {});
        } catch {
          setAnswers({});
        }
      }
    }).catch((requestError) => {
      if (alive) setError(requestError.response?.data?.detail || "Không tải được đề hoặc lượt làm bài.");
    }).finally(() => {
      if (alive) setLoading(false);
    });
    return () => { alive = false; };
  }, [examId, attemptId, storageKey]);

  useEffect(() => {
    if (!exam || result || !attempt || attempt.status !== "in_progress") return;
    localStorage.setItem(storageKey, JSON.stringify({ answers }));
  }, [answers, exam, result, attempt, storageKey]);

  const submitAttempt = useCallback(async () => {
    if (submitLock.current || result || !exam) return;
    submitLock.current = true;
    setIsSubmitting(true);
    setError("");
    try {
      const response = await api.post(`/attempts/${attemptId}/submit`, {
        answers: exam.questions.map((question) => ({
          question_id: question.id,
          response: answers[question.id] ?? null,
        })),
      });
      setResult(response.data);
      localStorage.removeItem(storageKey);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (requestError) {
      submitLock.current = false;
      setError(requestError.response?.data?.detail || "Không nộp được bài. Hãy thử lại.");
    } finally {
      setIsSubmitting(false);
    }
  }, [answers, attemptId, exam, result, storageKey]);

  useEffect(() => { submitRef.current = submitAttempt; }, [submitAttempt]);

  useEffect(() => {
    if (!exam || !attempt || result || loading || error) return;
    if (timeLeft <= 0) {
      if (!automaticSubmitStarted.current) {
        automaticSubmitStarted.current = true;
        submitRef.current?.();
      }
      return;
    }
    const timer = window.setTimeout(() => setTimeLeft((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [attempt, error, exam, loading, result, timeLeft]);

  const resultByQuestion = useMemo(
    () => new Map((result?.results || []).map((item) => [item.question_id, item])),
    [result],
  );
  const answeredCount = exam?.questions.reduce((count, question) => {
    const value = answers[question.id];
    const answered = Array.isArray(value) ? value.some(Boolean) : String(value ?? "").trim().length > 0;
    return count + Number(answered);
  }, 0) || 0;

  const setChoice = (questionId, value) => setAnswers((current) => ({ ...current, [questionId]: value }));
  const setTrueFalse = (questionId, index, value) => setAnswers((current) => {
    const choices = [...(current[questionId] || ["", "", "", ""])];
    choices[index] = value;
    return { ...current, [questionId]: choices };
  });

  if (loading) return <div style={styles.center}>Đang tải lượt làm bài...</div>;
  if (error && !exam) return <div style={styles.page}><div style={styles.error}>{error}</div><button onClick={() => navigate("/exams")}>Về kho đề</button></div>;
  if (!exam) return null;

  const timerText = `${String(Math.floor(timeLeft / 60)).padStart(2, "0")}:${String(timeLeft % 60).padStart(2, "0")}`;

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <div>
          <button style={styles.backButton} onClick={() => navigate("/exams")}>← Kho đề</button>
          <h2 style={{ margin: "8px 0 5px" }}>{exam.subject_icon} {exam.title}</h2>
          <div style={styles.meta}>{exam.subject_name} · {exam.total_questions} câu · {exam.duration_minutes} phút · {exam.provenance_status}</div>
        </div>
        <div style={result ? styles.scoreBox : styles.timerBox}>
          {result ? <><small>KẾT QUẢ</small><strong>{result.score} / {result.max_score}</strong><span>Đúng trọn câu {result.total_correct}/{result.total_questions}</span></> : <><small>CÒN LẠI</small><strong>{timerText}</strong><span>Đã trả lời {answeredCount}/{exam.questions.length} câu</span></>}
        </div>
      </header>

      {error && <div role="alert" style={styles.error}>{error}</div>}
      {result && <div style={styles.success}>Đã lưu kết quả. Câu sai hoặc bỏ trống được ghi vào Sổ lỗi sai; câu đúng/sai có thể nhận điểm thành phần theo ma trận.</div>}

      <section style={styles.questions}>
        {exam.questions.map((question) => {
          const outcome = resultByQuestion.get(question.id);
          const response = result ? outcome?.response : answers[question.id];
          const options = optionEntries(question.options);
          const type = question.question_type;
          return (
            <article key={question.id} style={{ ...styles.card, borderColor: outcome ? (outcome.is_correct ? "#86efac" : "#fecaca") : "#e2e8f0" }}>
              <div style={styles.questionHeader}>
                <div><b>Câu {question.position}</b><span style={styles.typeBadge}>{type === "multiple_choice" ? "Chọn đáp án" : type === "true_false" ? "Đúng / Sai" : "Trả lời ngắn"}</span>{question.topic && <span style={styles.topic}>{question.topic}</span>}</div>
                {outcome && <b style={{ color: outcome.is_correct ? "#15803d" : "#b91c1c" }}>{outcome.score_earned}/{outcome.max_points ?? question.max_points ?? 1} điểm</b>}
              </div>
              <div style={styles.questionText}><MathView text={question.content} /></div>

              {type === "multiple_choice" && <div style={styles.options}>
                {options.map(([key, value]) => {
                  const selected = response === key;
                  const correct = outcome && String(formatAnswer(outcome.expected_answer)).toUpperCase() === key;
                  return <button key={key} disabled={Boolean(result)} onClick={() => setChoice(question.id, key)} style={{ ...styles.option, ...(selected ? styles.selected : {}), ...(correct ? styles.correctOption : {}), ...(selected && outcome && !outcome.is_correct ? styles.wrongOption : {}) }}><b>{key}.</b><MathView text={String(value)} />{correct && <span>Đáp án đúng</span>}</button>;
                })}
              </div>}

              {type === "true_false" && <div style={styles.tfList}>
                {options.map(([key, value], index) => {
                  const userValue = Array.isArray(response) ? response[index] : null;
                  const expected = Array.isArray(outcome?.expected_answer) ? outcome.expected_answer[index] : null;
                  return <div key={key || index} style={styles.tfRow}>
                    <div><b>{String(key || String.fromCharCode(97 + index)).toLowerCase()})</b> <MathView text={String(value)} /></div>
                    <div style={styles.tfChoices}>{["T", "F"].map((choice) => <button key={choice} disabled={Boolean(result)} onClick={() => setTrueFalse(question.id, index, choice)} style={{ ...styles.tfButton, ...(userValue === choice ? styles.selected : {}), ...(outcome && expected === choice ? styles.correctOption : {}) }}>{choice === "T" ? "Đúng" : "Sai"}</button>)}</div>
                    {outcome && <small>Đáp án: {expected === "T" ? "Đúng" : "Sai"}</small>}
                  </div>;
                })}
              </div>}

              {type === "short_answer" && <input disabled={Boolean(result)} value={response ?? ""} onChange={(event) => setChoice(question.id, event.target.value)} placeholder="Nhập đáp án" style={styles.textInput} />}

              {outcome && <div style={styles.feedback}><b>Đáp án:</b> {formatAnswer(outcome.expected_answer)}{outcome.explanation && <div style={{ marginTop: 6 }}><b>Giải thích:</b> <MathView text={outcome.explanation} /></div>}</div>}
            </article>
          );
        })}
      </section>

      <footer style={styles.footer}>
        <span>{result ? "Lượt làm bài đã hoàn tất." : "Câu trả lời được lưu tạm trên máy này."}</span>
        {result ? <button style={styles.primaryButton} onClick={() => navigate("/mistakes")}>Mở sổ lỗi sai</button> : <button disabled={isSubmitting} style={styles.primaryButton} onClick={() => window.confirm(`Nộp bài với ${answeredCount}/${exam.questions.length} câu đã trả lời?`) && submitAttempt()}>{isSubmitting ? "Đang chấm..." : "Nộp bài"}</button>}
      </footer>
    </main>
  );
}

const styles = {
  page: { maxWidth: 1000, margin: "0 auto", padding: 24, color: "#1f2937" },
  center: { padding: 50, textAlign: "center", color: "#64748b" },
  header: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 18, marginBottom: 18 },
  backButton: { border: 0, background: "transparent", color: "#2563eb", padding: 0, cursor: "pointer", fontWeight: 700 },
  meta: { color: "#64748b", fontSize: 13 },
  timerBox: { minWidth: 150, padding: 12, display: "grid", gap: 2, textAlign: "center", background: "#eff6ff", borderRadius: 10, color: "#1d4ed8" },
  scoreBox: { minWidth: 150, padding: 12, display: "grid", gap: 2, textAlign: "center", background: "#ecfdf5", borderRadius: 10, color: "#047857" },
  error: { padding: 12, marginBottom: 14, border: "1px solid #fecaca", background: "#fef2f2", borderRadius: 8, color: "#b91c1c" },
  success: { padding: 12, marginBottom: 14, border: "1px solid #bbf7d0", background: "#f0fdf4", borderRadius: 8, color: "#166534" },
  questions: { display: "grid", gap: 14 },
  card: { border: "1px solid #e2e8f0", borderRadius: 12, background: "white", padding: 18 },
  questionHeader: { display: "flex", justifyContent: "space-between", gap: 12, fontSize: 13, color: "#334155" },
  typeBadge: { marginLeft: 8, background: "#eff6ff", color: "#1d4ed8", padding: "3px 8px", borderRadius: 999 },
  topic: { marginLeft: 8, color: "#64748b" },
  questionText: { margin: "16px 0", lineHeight: 1.7, whiteSpace: "pre-wrap" },
  options: { display: "grid", gap: 8 },
  option: { display: "flex", alignItems: "center", gap: 10, textAlign: "left", border: "1px solid #e2e8f0", borderRadius: 8, padding: 11, background: "#fff", cursor: "pointer", color: "#1f2937" },
  selected: { borderColor: "#60a5fa", background: "#eff6ff" },
  correctOption: { borderColor: "#4ade80", background: "#f0fdf4" },
  wrongOption: { borderColor: "#f87171", background: "#fef2f2" },
  tfList: { display: "grid", gap: 8 },
  tfRow: { display: "grid", gridTemplateColumns: "1fr auto auto", alignItems: "center", gap: 10, padding: "9px 0", borderTop: "1px solid #f1f5f9" },
  tfChoices: { display: "flex", gap: 6 },
  tfButton: { border: "1px solid #cbd5e1", borderRadius: 7, padding: "7px 10px", background: "white", cursor: "pointer" },
  textInput: { width: "100%", maxWidth: 420, boxSizing: "border-box", border: "1px solid #cbd5e1", borderRadius: 8, padding: 11 },
  feedback: { marginTop: 14, borderTop: "1px solid #e2e8f0", paddingTop: 12, color: "#475569", lineHeight: 1.6 },
  footer: { position: "sticky", bottom: 0, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "14px 0", marginTop: 12, background: "#fff", color: "#64748b" },
  primaryButton: { border: 0, borderRadius: 8, padding: "11px 16px", background: "#2563eb", color: "white", cursor: "pointer", fontWeight: 700 },
};

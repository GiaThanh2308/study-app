import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../api";

const TABS = ["Tạo đề thi", "AI Gia sư"];

export default function Practice() {
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") === "tutor" ? "AI Gia sư" : TABS[0];
  const initialTopic = searchParams.get("topic") || "";

  const [tab, setTab] = useState(initialTab);
  const [subjects, setSubjects] = useState([]);

  useEffect(() => {
    api.get("/subjects").then((res) => setSubjects(res.data));
  }, []);

  return (
    <div className="page">
      <h2>Luyện tập</h2>
      <p style={{ color: "var(--color-text-muted)" }}>
        Tạo đề thi thử bằng AI dựa trên tài liệu bạn đã upload, hoặc luyện tập
        theo từng chủ đề với AI Gia sư.
      </p>

      <div style={styles.segmentedControl}>
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              ...styles.segmentBtn,
              ...(tab === t ? styles.segmentBtnActive : {}),
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div style={styles.tabContent}>
        {tab === "Tạo đề thi" && <ExamTab subjects={subjects} />}
        {tab === "AI Gia sư" && <TutorTab subjects={subjects} initialTopic={initialTopic} />}
      </div>
    </div>
  );
}

// ============================================================
// TẠO ĐỀ THI — quét toàn bộ tài liệu môn học, AI soạn đề đúng
// cấu trúc THPT (3 phần), chấm điểm thật khi nộp bài.
// ============================================================
function ExamTab({ subjects }) {
  const [subjectId, setSubjectId] = useState("");
  const [part1Count, setPart1Count] = useState(12);
  const [part2Count, setPart2Count] = useState(4);
  const [part3Count, setPart3Count] = useState(6);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [examList, setExamList] = useState([]);
  const [exam, setExam] = useState(null);
  const [mcqAnswers, setMcqAnswers] = useState({});
  const [tfAnswers, setTfAnswers] = useState({});
  const [shortAnswers, setShortAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setExam(null);
    setResult(null);
    if (subjectId) loadExamList();
    else setExamList([]);
  }, [subjectId]);

  const loadExamList = async () => {
    const res = await api.get(`/practice/exams?subject_id=${subjectId}`);
    setExamList(res.data);
  };

  const generate = async () => {
    if (!subjectId) {
      setError("Chọn môn học trước.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const genRes = await api.post("/practice/exams/generate", {
        subject_id: Number(subjectId),
        part1_count: Number(part1Count),
        part2_count: Number(part2Count),
        part3_count: Number(part3Count),
      });
      await openExam(genRes.data.id);
      loadExamList();
    } catch (e) {
      setError(e.response?.data?.detail || "Không tạo được đề, thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const openExam = async (examId) => {
    const res = await api.get(`/practice/exams/${examId}`);
    setExam(res.data);
    setMcqAnswers({});
    setTfAnswers({});
    setShortAnswers({});
    setResult(null);
  };

  const deleteExam = async (examId, e) => {
    e.stopPropagation();
    await api.delete(`/practice/exams/${examId}`);
    loadExamList();
  };

  const toggleTf = (questionId, statementId, value) => {
    setTfAnswers((prev) => ({
      ...prev,
      [questionId]: { ...(prev[questionId] || {}), [statementId]: value },
    }));
  };

  const submitExam = async () => {
    setSubmitting(true);
    try {
      const res = await api.post(`/practice/exams/${exam.id}/submit`, {
        mcq_answers: mcqAnswers,
        truefalse_answers: tfAnswers,
        short_answers: shortAnswers,
      });
      setResult(res.data);
      loadExamList();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setSubmitting(false);
    }
  };

  const detailFor = (qid) => result?.details.find((d) => d.question_id === qid);

  // ---------- Màn hình cấu hình / danh sách đề đã tạo ----------
  if (!exam) {
    return (
      <div style={{ maxWidth: 640 }}>
        <div style={styles.chipRow}>
          {subjects.map((s) => (
            <button
              key={s.id}
              style={{ ...styles.chip, ...(subjectId === String(s.id) ? styles.chipActive : {}) }}
              onClick={() => setSubjectId(String(s.id))}
            >
              {s.name}
            </button>
          ))}
        </div>

        {subjectId && (
          <>
            <div style={styles.configCard}>
              <h4 style={{ margin: "0 0 12px" }}>
                Cấu trúc đề (chuẩn THPT Quốc Gia)
              </h4>
              <div style={styles.stepRow}>
                <StepField
                  stepNumber={1}
                  icon="✅"
                  label="Trắc nghiệm"
                  sublabel="0.25đ/câu · tổng 3đ"
                  value={part1Count}
                  onChange={setPart1Count}
                />
                <StepField
                  stepNumber={2}
                  icon="⚖️"
                  label="Đúng / Sai"
                  sublabel="4 ý mỗi câu · tổng 4đ"
                  value={part2Count}
                  onChange={setPart2Count}
                />
                <StepField
                  stepNumber={3}
                  icon="✍️"
                  label="Trả lời ngắn"
                  sublabel="đáp số ngắn · tổng 3đ"
                  value={part3Count}
                  onChange={setPart3Count}
                />
              </div>
              <p
                style={{
                  fontSize: 12,
                  color: "var(--color-text-muted)",
                  margin: "10px 0 0",
                }}
              >
                AI sẽ quét toàn bộ tài liệu/video đã "Xử lý AI" của môn học này
                để soạn đề — thang điểm tổng luôn là 10.
              </p>
              <button
                style={{ ...styles.btn, marginTop: 14 }}
                onClick={generate}
                disabled={loading}
              >
                {loading
                  ? "AI đang soạn đề... (có thể mất vài phút)"
                  : "🪄 Tạo đề thi bằng AI"}
              </button>
              {error && (
                <p style={{ color: "var(--color-danger)", marginTop: 8 }}>
                  {error}
                </p>
              )}
            </div>

            {examList.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <h4 style={{ color: "var(--color-text-muted)" }}>
                  Đề đã tạo trước đó
                </h4>
                {examList.map((e) => (
                  <div
                    key={e.id}
                    style={styles.examListRow}
                    onClick={() => openExam(e.id)}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>{e.title}</div>
                      <div
                        style={{
                          fontSize: 12,
                          color: "var(--color-text-muted)",
                        }}
                      >
                        {e.total_questions} câu
                      </div>
                    </div>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 12 }}
                    >
                      {e.best_score != null && (
                        <span
                          style={{
                            ...styles.scoreBadge,
                            background: scoreColor(e.best_score).bg,
                            color: scoreColor(e.best_score).fg,
                          }}
                        >
                          {e.best_score.toFixed(2)}/10
                        </span>
                      )}
                      <button
                        style={styles.deleteBtn}
                        onClick={(ev) => deleteExam(e.id, ev)}
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  // ---------- Màn hình kết quả sau khi nộp ----------
  if (result) {
    const parts = [
      { label: "Phần I — Trắc nghiệm", score: result.part1_score, max: 3 },
      { label: "Phần II — Đúng/Sai", score: result.part2_score, max: 4 },
      { label: "Phần III — Trả lời ngắn", score: result.part3_score, max: 3 },
    ];
    return (
      <div>
        <div style={styles.resultSummary}>
          <div
            style={{
              fontSize: 42,
              fontWeight: 800,
              color: scoreColor(result.total_score).fg,
            }}
          >
            {result.total_score.toFixed(2)}
            <span style={{ fontSize: 20, color: "var(--color-text-muted)" }}>
              /10
            </span>
          </div>
          <div
            style={{
              display: "flex",
              gap: 20,
              marginTop: 14,
              flexWrap: "wrap",
            }}
          >
            {parts.map((p) => (
              <div key={p.label} style={styles.partScoreBox}>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                  {p.label}
                </div>
                <div style={{ fontWeight: 700 }}>
                  {p.score.toFixed(2)}/{p.max}
                </div>
              </div>
            ))}
          </div>
        </div>

        {[
          "Phần I — Trắc nghiệm",
          "Phần II — Đúng/Sai",
          "Phần III — Trả lời ngắn",
        ].map((title, idx) => {
          const partNum = idx + 1;
          const items = exam[`part${partNum}`];
          if (!items.length) return null;
          return (
            <div key={title} style={{ marginTop: 22 }}>
              <h4>{title}</h4>
              {items.map((q, i) => {
                const d = detailFor(q.id);
                return (
                  <div key={q.id} style={styles.questionBox}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <p style={{ fontWeight: 600 }}>
                        Câu {i + 1}. {q.content}
                      </p>
                      <span
                        style={{
                          ...styles.pointsBadge,
                          color:
                            d.earned_points > 0
                              ? "var(--color-success)"
                              : "var(--color-danger)",
                        }}
                      >
                        {d.earned_points}/{d.max_points}đ
                      </span>
                    </div>
                    <p
                      style={{ fontSize: 13, color: "var(--color-text-muted)" }}
                    >
                      ✔ Đáp án đúng: {d.correct_display}
                    </p>
                    {d.explanation && (
                      <p
                        style={{
                          fontSize: 13,
                          background: "var(--color-bg)",
                          padding: 8,
                          borderRadius: 6,
                        }}
                      >
                        {d.explanation}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}

        <button
          style={{ ...styles.btn, marginTop: 20 }}
          onClick={() => setExam(null)}
        >
          ← Quay lại danh sách đề
        </button>
      </div>
    );
  }

  // ---------- Màn hình làm bài ----------
  const answeredCount =
    Object.keys(mcqAnswers).length +
    Object.keys(tfAnswers).length +
    Object.keys(shortAnswers).filter((k) => shortAnswers[k]?.trim()).length;
  const totalCount = exam.part1.length + exam.part2.length + exam.part3.length;

  return (
    <div>
      <div style={styles.examHeader}>
        <div>
          <h3 style={{ margin: 0 }}>{exam.title}</h3>
          {exam.source_files.length > 0 && (
            <p
              style={{
                fontSize: 12,
                color: "var(--color-text-muted)",
                margin: "4px 0 0",
              }}
            >
              Nguồn: {exam.source_files.join(", ")}
            </p>
          )}
        </div>
        <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
          {answeredCount}/{totalCount} câu đã trả lời
        </span>
      </div>

      {exam.part1.length > 0 && (
        <section style={{ marginTop: 20 }}>
          <h4>Phần I — Trắc nghiệm nhiều lựa chọn</h4>
          {exam.part1.map((q, i) => (
            <div key={q.id} style={styles.questionBox}>
              <p style={{ fontWeight: 600 }}>
                Câu {i + 1}. {q.content}
              </p>
              {q.answers.map((a, ai) => (
                <div
                  key={a.id}
                  style={{
                    ...styles.answerRow,
                    background:
                      mcqAnswers[q.id] === a.id
                        ? "var(--color-primary-light)"
                        : "#fff",
                  }}
                  onClick={() =>
                    setMcqAnswers((prev) => ({ ...prev, [q.id]: a.id }))
                  }
                >
                  <b style={{ marginRight: 8 }}>
                    {String.fromCharCode(65 + ai)}.
                  </b>
                  {a.content}
                </div>
              ))}
            </div>
          ))}
        </section>
      )}

      {exam.part2.length > 0 && (
        <section style={{ marginTop: 20 }}>
          <h4>Phần II — Đúng / Sai</h4>
          <p style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
            Mỗi ý a, b, c, d đúng hoặc sai độc lập nhau.
          </p>
          {exam.part2.map((q, i) => (
            <div key={q.id} style={styles.questionBox}>
              <p style={{ fontWeight: 600 }}>
                Câu {i + 1}. {q.content}
              </p>
              {q.answers.map((a, ai) => {
                const current = tfAnswers[q.id]?.[a.id];
                return (
                  <div key={a.id} style={styles.tfRow}>
                    <span style={{ flex: 1 }}>
                      {String.fromCharCode(97 + ai)}) {a.content}
                    </span>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        style={{
                          ...styles.tfBtn,
                          ...(current === true ? styles.tfBtnActiveTrue : {}),
                        }}
                        onClick={() => toggleTf(q.id, a.id, true)}
                      >
                        Đúng
                      </button>
                      <button
                        style={{
                          ...styles.tfBtn,
                          ...(current === false ? styles.tfBtnActiveFalse : {}),
                        }}
                        onClick={() => toggleTf(q.id, a.id, false)}
                      >
                        Sai
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </section>
      )}

      {exam.part3.length > 0 && (
        <section style={{ marginTop: 20 }}>
          <h4>Phần III — Trả lời ngắn</h4>
          {exam.part3.map((q, i) => (
            <div key={q.id} style={styles.questionBox}>
              <p style={{ fontWeight: 600 }}>
                Câu {i + 1}. {q.content}
              </p>
              <input
                placeholder="Nhập đáp án..."
                value={shortAnswers[q.id] || ""}
                onChange={(e) =>
                  setShortAnswers((prev) => ({
                    ...prev,
                    [q.id]: e.target.value,
                  }))
                }
                style={{
                  ...styles.input,
                  width: "100%",
                  boxSizing: "border-box",
                }}
              />
            </div>
          ))}
        </section>
      )}

      <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
        <button style={styles.btn} onClick={submitExam} disabled={submitting}>
          {submitting ? "Đang chấm điểm..." : "✅ Nộp bài"}
        </button>
        <button style={styles.btnGhost} onClick={() => setExam(null)}>
          Hủy, quay lại
        </button>
      </div>
    </div>
  );
}

function StepField({ stepNumber, icon, label, sublabel, value, onChange }) {
  const dec = () => onChange(Math.max(1, Number(value) - 1));
  const inc = () => onChange(Math.min(30, Number(value) + 1));
  return (
    <div style={styles.stepBlock}>
      <div style={styles.stepBadge}>{stepNumber}</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
          <span>{icon}</span> {label}
        </div>
        <div style={{ fontSize: 11.5, color: "var(--color-text-muted)", marginTop: 1 }}>{sublabel}</div>
      </div>
      <div style={styles.stepperGroup}>
        <button
          type="button"
          style={styles.stepperBtn}
          onClick={dec}
          disabled={value <= 1}
          aria-label="Giảm số câu"
        >
          −
        </button>
        <input
          type="number"
          min={1}
          max={30}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          style={styles.stepInput}
        />
        <button
          type="button"
          style={styles.stepperBtn}
          onClick={inc}
          disabled={value >= 30}
          aria-label="Tăng số câu"
        >
          +
        </button>
      </div>
      <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>câu</span>
    </div>
  );
}

function ConfigField({ label, value, onChange }) {
  return (
    <div style={{ flex: "1 1 160px" }}>
      <div
        style={{
          fontSize: 12,
          color: "var(--color-text-muted)",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <input
        type="number"
        min={1}
        max={30}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ ...styles.input, width: "100%", boxSizing: "border-box" }}
      />
    </div>
  );
}

function scoreColor(score) {
  if (score >= 8)
    return { bg: "var(--color-success-light)", fg: "var(--color-success)" };
  if (score >= 5)
    return { bg: "var(--color-warning-light)", fg: "var(--color-warning)" };
  return { bg: "var(--color-danger-light)", fg: "var(--color-danger)" };
}

// ============================================================
// AI GIA SƯ — giữ nguyên logic, chỉ chỉnh style nhẹ cho đồng bộ
// ============================================================
function TutorTab({ subjects, initialTopic = "" }) {
  const [subjectId, setSubjectId] = useState("");
  const [weakTopics, setWeakTopics] = useState(null);
  const [topic, setTopic] = useState(initialTopic);
  const [count, setCount] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [questions, setQuestions] = useState([]);
  const [current, setCurrent] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [result, setResult] = useState(null);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [deepExplain, setDeepExplain] = useState("");
  const [explainLoading, setExplainLoading] = useState(false);
  const [videoSuggestions, setVideoSuggestions] = useState(null);

  const loadWeakTopics = async () => {
    if (!subjectId) return;
    const res = await api.get(`/tutor/weak-topics?subject_id=${subjectId}`);
    setWeakTopics(res.data);
  };

  const startSession = async () => {
    if (!subjectId || !topic.trim()) {
      setError("Chọn môn học và nhập chủ đề cần luyện.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const genRes = await api.post("/tutor/generate", {
        subject_id: Number(subjectId),
        topic,
        count,
      });
      const idsParam = genRes.data.question_ids.join(",");
      const qRes = await api.get(`/practice/questions/by-ids?ids=${idsParam}`);
      setQuestions(qRes.data);
      setCurrent(0);
      setResult(null);
      setSelectedAnswer(null);
      setScore({ correct: 0, total: 0 });
      setVideoSuggestions(null);
    } catch (e) {
      setError(e.response?.data?.detail || "Không tạo được bài tập, thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const submit = async () => {
    if (selectedAnswer === null) return;
    const q = questions[current];
    const res = await api.post("/practice/submit", {
      question_id: q.id,
      answer_id: selectedAnswer,
    });
    setResult(res.data);
    setDeepExplain("");
    setScore((s) => ({
      correct: s.correct + (res.data.is_correct ? 1 : 0),
      total: s.total + 1,
    }));
  };

  const askDeepExplain = async () => {
    const q = questions[current];
    setExplainLoading(true);
    try {
      const res = await api.post("/tutor/explain", {
        question_id: q.id,
        chosen_answer_id: selectedAnswer,
      });
      setDeepExplain(res.data.explanation);
    } finally {
      setExplainLoading(false);
    }
  };

  const nextQuestion = async () => {
    if (current + 1 >= questions.length) {
      const res = await api.get(
        `/tutor/suggest-video?subject_id=${subjectId}&topic=${encodeURIComponent(topic)}`,
      );
      setVideoSuggestions(res.data.suggestions);
    }
    setCurrent((c) => c + 1);
    setSelectedAnswer(null);
    setResult(null);
    setDeepExplain("");
  };

  if (questions.length === 0) {
    return (
      <div style={{ maxWidth: 550 }}>
        <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>
          AI Gia sư tạo bài tập nhắm ĐÚNG 1 chủ đề bạn chọn (dựa trên nội dung
          tài liệu đã xử lý AI), và có thể chỉ ra bạn đang yếu chủ đề nào dựa
          trên lịch sử làm bài trước đó.
        </p>

        <div style={styles.chipRow}>
          {subjects.map((s) => (
            <button
              key={s.id}
              style={{ ...styles.chip, ...(subjectId === String(s.id) ? styles.chipActive : {}) }}
              onClick={() => {
                setSubjectId(String(s.id));
                setWeakTopics(null);
              }}
            >
              {s.name}
            </button>
          ))}
        </div>

        {subjectId && (
          <button
            style={{ ...styles.btnGhost, marginBottom: 12 }}
            onClick={loadWeakTopics}
          >
            Xem chủ đề đang yếu
          </button>
        )}

        {weakTopics && weakTopics.length === 0 && (
          <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>
            Chưa có đủ dữ liệu (cần từng luyện tập ít nhất 1 chủ đề trước qua AI
            Gia sư này).
          </p>
        )}
        {weakTopics && weakTopics.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            {weakTopics.map((t) => (
              <div
                key={t.topic}
                style={styles.weakTopicRow}
                onClick={() => setTopic(t.topic)}
              >
                <span>{t.topic}</span>
                <span
                  style={{
                    color:
                      t.percent_correct < 50
                        ? "var(--color-danger)"
                        : "var(--color-warning)",
                  }}
                >
                  {t.percent_correct}% đúng ({t.attempts} lần)
                </span>
              </div>
            ))}
          </div>
        )}

        <input
          placeholder="Chủ đề cần luyện (VD: Este, Đạo hàm, Dao động điều hòa...)"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          style={{
            ...styles.input,
            width: "100%",
            boxSizing: "border-box",
            marginBottom: 10,
          }}
        />
        <div style={{ marginBottom: 10 }}>
          Số câu:{" "}
          <input
            type="number"
            min={3}
            max={20}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            style={{ ...styles.input, width: 60 }}
          />
        </div>

        <button style={styles.btn} onClick={startSession} disabled={loading}>
          {loading ? "Đang soạn bài tập..." : "Bắt đầu luyện tập chủ đề này"}
        </button>
        {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}
      </div>
    );
  }

  if (current >= questions.length) {
    return (
      <div style={styles.resultBox}>
        <h3>Hoàn thành!</h3>
        <p>
          Đúng {score.correct}/{score.total} câu về chủ đề "{topic}"
        </p>

        {videoSuggestions && videoSuggestions.length > 0 && (
          <div
            style={{ textAlign: "left", maxWidth: 400, margin: "16px auto" }}
          >
            <h4>🎥 Video liên quan gợi ý xem lại</h4>
            {videoSuggestions.map((v, i) => (
              <div key={i} style={styles.weakTopicRow}>
                <span>{v.source_name}</span>
                <span style={{ color: "var(--color-text-muted)" }}>
                  phút {v.timestamp}
                </span>
              </div>
            ))}
          </div>
        )}
        {videoSuggestions && videoSuggestions.length === 0 && (
          <p style={{ color: "var(--color-text-muted)", fontSize: 13 }}>
            Không có video liên quan tới chủ đề này trong dữ liệu đã xử lý.
          </p>
        )}

        <button style={styles.btn} onClick={() => setQuestions([])}>
          Luyện chủ đề khác
        </button>
      </div>
    );
  }

  const q = questions[current];
  return (
    <div>
      <p style={{ color: "var(--color-text-muted)" }}>
        Chủ đề: <b>{topic}</b> · Câu {current + 1}/{questions.length}
      </p>
      <div style={styles.questionBox}>
        <p style={{ fontWeight: 600 }}>{q.content}</p>
        {q.answers.map((a) => {
          let bg = "#fff";
          if (result) {
            if (a.id === result.correct_answer_id)
              bg = "var(--color-success-light)";
            else if (a.id === selectedAnswer) bg = "var(--color-danger-light)";
          } else if (a.id === selectedAnswer) {
            bg = "var(--color-primary-light)";
          }
          return (
            <div
              key={a.id}
              style={{ ...styles.answerRow, background: bg }}
              onClick={() => !result && setSelectedAnswer(a.id)}
            >
              {a.content}
            </div>
          );
        })}

        {result && (
          <div style={styles.explanationBox}>
            {result.is_correct ? "✅ Chính xác!" : "❌ Sai rồi."}
            {result.explanation && (
              <p style={{ marginTop: 6 }}>{result.explanation}</p>
            )}

            {!result.is_correct && !deepExplain && (
              <button
                style={{ ...styles.btnGhost, marginTop: 8, fontSize: 13 }}
                onClick={askDeepExplain}
                disabled={explainLoading}
              >
                {explainLoading
                  ? "AI đang giải thích..."
                  : "🎓 Giải thích sâu hơn"}
              </button>
            )}
            {deepExplain && (
              <p
                style={{
                  marginTop: 8,
                  background: "var(--color-surface)",
                  padding: 8,
                  borderRadius: 6,
                }}
              >
                {deepExplain}
              </p>
            )}
          </div>
        )}

        {!result ? (
          <button
            style={styles.btn}
            onClick={submit}
            disabled={selectedAnswer === null}
          >
            Nộp đáp án
          </button>
        ) : (
          <button style={styles.btn} onClick={nextQuestion}>
            Câu tiếp theo
          </button>
        )}
      </div>
    </div>
  );
}

// ============================================================
// STYLES
// ============================================================
const styles = {
  chipRow: { display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 },
  chip: {
    padding: "7px 16px",
    borderRadius: 20,
    border: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    color: "var(--color-text-muted)",
    fontSize: 13.5,
    fontWeight: 500,
    cursor: "pointer",
  },
  chipActive: {
    background: "var(--color-primary)",
    color: "#fff",
    border: "1px solid var(--color-primary)",
  },
  segmentedControl: {
    display: "inline-flex",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: 12,
    padding: 4,
    marginBottom: 20,
    gap: 2,
  },
  stepRow: { display: "flex", flexDirection: "column", gap: 10, marginTop: 4 },
  stepBlock: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "10px 14px",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: 10,
  },
  stepBadge: {
    width: 26,
    height: 26,
    borderRadius: "50%",
    background: "var(--color-primary)",
    color: "#fff",
    fontSize: 12.5,
    fontWeight: 700,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  stepperGroup: {
    display: "flex",
    alignItems: "center",
    border: "1px solid var(--color-border)",
    borderRadius: 8,
    overflow: "hidden",
    background: "var(--color-surface)",
  },
  stepperBtn: {
    width: 26,
    height: 30,
    border: "none",
    background: "var(--color-surface)",
    color: "var(--color-primary)",
    fontSize: 16,
    fontWeight: 700,
    cursor: "pointer",
    lineHeight: 1,
  },
  stepInput: {
    width: 40,
    padding: "6px 4px",
    border: "none",
    borderLeft: "1px solid var(--color-border)",
    borderRight: "1px solid var(--color-border)",
    textAlign: "center",
    fontSize: 14,
    fontWeight: 600,
    background: "transparent",
    color: "var(--color-text)",
  },
  segmentBtn: {
    padding: "8px 20px",
    border: "none",
    background: "transparent",
    borderRadius: 9,
    fontSize: 14,
    fontWeight: 500,
    color: "var(--color-text-muted)",
    cursor: "pointer",
    transition: "background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease",
  },
  segmentBtnActive: {
    background: "var(--color-surface)",
    color: "var(--color-primary)",
    boxShadow: "var(--shadow-sm)",
    fontWeight: 600,
  },
  tabBar: {
    display: "flex",
    gap: 6,
    marginBottom: 20,
    borderBottom: "1px solid var(--color-border)",
    paddingBottom: 2,
  },
  tabBtn: {
    padding: "8px 16px",
    border: "none",
    background: "transparent",
    borderRadius: "8px 8px 0 0",
    fontSize: 14,
    fontWeight: 500,
    color: "var(--color-text-muted)",
    cursor: "pointer",
  },
  tabBtnActive: {
    background: "var(--color-primary-light)",
    color: "var(--color-primary-dark)",
    fontWeight: 700,
  },
  tabContent: {},
  select: {
    display: "block",
    width: "100%",
    maxWidth: 320,
    padding: "10px 12px",
    marginBottom: 16,
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    fontSize: 14,
    background: "var(--color-surface)",
  },
  input: {
    padding: "9px 12px",
    border: "1px solid var(--color-border)",
    borderRadius: 8,
    fontSize: 14,
  },
  textarea: {
    width: "100%",
    minHeight: 70,
    padding: "9px 12px",
    border: "1px solid var(--color-border)",
    borderRadius: 8,
    fontSize: 14,
    marginBottom: 10,
    boxSizing: "border-box",
    fontFamily: "inherit",
  },
  btn: {
    background: "var(--color-primary)",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    padding: "10px 20px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  btnGhost: {
    background: "var(--color-surface)",
    color: "var(--color-primary-dark)",
    border: "1px solid var(--color-primary)",
    borderRadius: 8,
    padding: "10px 20px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  configCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 18,
    boxShadow: "var(--shadow-sm)",
  },
  configRow: { display: "flex", gap: 12, flexWrap: "wrap" },
  examListRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 16px",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: 10,
    marginBottom: 8,
    cursor: "pointer",
  },
  scoreBadge: {
    fontSize: 13,
    fontWeight: 700,
    padding: "4px 10px",
    borderRadius: 20,
  },
  deleteBtn: {
    background: "transparent",
    border: "none",
    cursor: "pointer",
    fontSize: 15,
  },
  examHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingBottom: 12,
    borderBottom: "1px solid var(--color-border)",
  },
  questionBox: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 16,
    marginBottom: 12,
    boxShadow: "var(--shadow-sm)",
  },
  answerRow: {
    padding: "10px 12px",
    border: "1px solid var(--color-border)",
    borderRadius: 8,
    marginTop: 8,
    cursor: "pointer",
    fontSize: 14,
  },
  tfRow: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "8px 0",
    borderBottom: "1px dashed var(--color-border)",
    fontSize: 14,
  },
  tfBtn: {
    border: "1px solid var(--color-border)",
    background: "var(--color-surface)",
    borderRadius: 6,
    padding: "5px 12px",
    fontSize: 13,
    cursor: "pointer",
  },
  tfBtnActiveTrue: {
    background: "var(--color-success)",
    color: "#fff",
    borderColor: "var(--color-success)",
  },
  tfBtnActiveFalse: {
    background: "var(--color-danger)",
    color: "#fff",
    borderColor: "var(--color-danger)",
  },
  pointsBadge: { fontSize: 13, fontWeight: 700, whiteSpace: "nowrap" },
  explanationBox: {
    marginTop: 12,
    padding: 12,
    background: "var(--color-bg)",
    borderRadius: 8,
    fontSize: 14,
  },
  resultBox: { textAlign: "center", padding: 40 },
  resultSummary: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    padding: 24,
    textAlign: "center",
    boxShadow: "var(--shadow-md)",
  },
  partScoreBox: {
    background: "var(--color-bg)",
    borderRadius: 8,
    padding: "8px 16px",
    flex: "1 1 140px",
    textAlign: "center",
  },
  weakTopicRow: {
    display: "flex",
    justifyContent: "space-between",
    padding: "8px 10px",
    borderBottom: "1px solid var(--color-border)",
    cursor: "pointer",
    fontSize: 13,
  },
};

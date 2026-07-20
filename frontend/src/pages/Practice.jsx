import { useEffect, useState } from "react";
import api from "../api";

const TABS = ["Làm bài", "Đề thi thử", "Thêm câu hỏi", "AI tạo câu hỏi", "Flashcard"];

export default function Practice() {
  const [tab, setTab] = useState("Làm bài");
  const [subjects, setSubjects] = useState([]);

  useEffect(() => {
    api.get("/subjects").then((res) => setSubjects(res.data));
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <h2>Luyện tập</h2>

      <div style={styles.tabBar}>
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{ ...styles.tabBtn, ...(tab === t ? styles.tabBtnActive : {}) }}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Làm bài" && <QuizTab subjects={subjects} />}
      {tab === "Đề thi thử" && <ExamTab subjects={subjects} />}
      {tab === "Thêm câu hỏi" && <AddQuestionTab subjects={subjects} />}
      {tab === "AI tạo câu hỏi" && <AiGenerateTab subjects={subjects} />}
      {tab === "Flashcard" && <FlashcardTab subjects={subjects} />}
    </div>
  );
}

// ---------------- Làm bài (Quiz) ----------------
function QuizTab({ subjects }) {
  const [subjectId, setSubjectId] = useState("");
  const [questions, setQuestions] = useState([]);
  const [current, setCurrent] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [result, setResult] = useState(null); // { is_correct, correct_answer_id, explanation }
  const [score, setScore] = useState({ correct: 0, total: 0 });

  const startQuiz = async () => {
    if (!subjectId) return;
    const res = await api.get(`/practice/quiz?subject_id=${subjectId}&count=10`);
    setQuestions(res.data);
    setCurrent(0);
    setResult(null);
    setSelectedAnswer(null);
    setScore({ correct: 0, total: 0 });
  };

  const submit = async () => {
    if (selectedAnswer === null) return;
    const q = questions[current];
    const res = await api.post("/practice/submit", { question_id: q.id, answer_id: selectedAnswer });
    setResult(res.data);
    setScore((s) => ({ correct: s.correct + (res.data.is_correct ? 1 : 0), total: s.total + 1 }));
  };

  const nextQuestion = () => {
    setCurrent((c) => c + 1);
    setSelectedAnswer(null);
    setResult(null);
  };

  if (questions.length === 0) {
    return (
      <div>
        <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} style={styles.select}>
          <option value="">-- Chọn môn học --</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <button onClick={startQuiz} style={styles.btn}>Bắt đầu làm bài (10 câu ngẫu nhiên)</button>
        <p style={{ color: "#718096", fontSize: 13, marginTop: 8 }}>
          Cần có sẵn câu hỏi trong môn học này (nhập tay hoặc AI tạo trước) mới làm được.
        </p>
      </div>
    );
  }

  if (current >= questions.length) {
    return (
      <div style={styles.resultBox}>
        <h3>Hoàn thành!</h3>
        <p>Đúng {score.correct}/{score.total} câu ({Math.round((score.correct / score.total) * 100)}%)</p>
        <button style={styles.btn} onClick={() => setQuestions([])}>Làm bài khác</button>
      </div>
    );
  }

  const q = questions[current];
  return (
    <div>
      <p style={{ color: "#718096" }}>Câu {current + 1}/{questions.length}</p>
      <div style={styles.questionBox}>
        <p style={{ fontWeight: 600 }}>{q.content}</p>
        {q.answers.map((a) => {
          let bg = "#fff";
          if (result) {
            if (a.id === result.correct_answer_id) bg = "#c6f6d5";
            else if (a.id === selectedAnswer) bg = "#fed7d7";
          } else if (a.id === selectedAnswer) {
            bg = "#ebf8ff";
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
            {result.explanation && <p style={{ marginTop: 6 }}>{result.explanation}</p>}
          </div>
        )}

        {!result ? (
          <button style={styles.btn} onClick={submit} disabled={selectedAnswer === null}>Nộp đáp án</button>
        ) : (
          <button style={styles.btn} onClick={nextQuestion}>Câu tiếp theo</button>
        )}
      </div>
    </div>
  );
}

// ---------------- Đề thi thử (chọn ngẫu nhiên nhiều file đề, gộp thành 1 đề) ----------------
function ExamTab({ subjects }) {
  const [subjectId, setSubjectId] = useState("");
  const [numFiles, setNumFiles] = useState(3);
  const [perFile, setPerFile] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [examInfo, setExamInfo] = useState(null); // { source_files, total_questions }
  const [questions, setQuestions] = useState([]);
  const [current, setCurrent] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [result, setResult] = useState(null);
  const [score, setScore] = useState({ correct: 0, total: 0 });

  const generateExam = async () => {
    if (!subjectId) {
      setError("Chọn môn học trước.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/practice/generate-exam", {
        subject_id: Number(subjectId),
        num_files: numFiles,
        questions_per_file: perFile,
      });
      setExamInfo(res.data);

      const idsParam = res.data.question_ids.join(",");
      const qRes = await api.get(`/practice/questions/by-ids?ids=${idsParam}`);
      setQuestions(qRes.data);
      setCurrent(0);
      setResult(null);
      setSelectedAnswer(null);
      setScore({ correct: 0, total: 0 });
    } catch (e) {
      setError(e.response?.data?.detail || "Không tạo được đề thi, thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const submit = async () => {
    if (selectedAnswer === null) return;
    const q = questions[current];
    const res = await api.post("/practice/submit", { question_id: q.id, answer_id: selectedAnswer });
    setResult(res.data);
    setScore((s) => ({ correct: s.correct + (res.data.is_correct ? 1 : 0), total: s.total + 1 }));
  };

  const nextQuestion = () => {
    setCurrent((c) => c + 1);
    setSelectedAnswer(null);
    setResult(null);
  };

  if (questions.length === 0) {
    return (
      <div style={{ maxWidth: 500 }}>
        <p style={{ color: "#718096", fontSize: 13 }}>
          AI sẽ chọn ngẫu nhiên vài file đề thi (PDF loại "đề thi", đã xử lý AI) trong môn học,
          lấy vài câu từ mỗi file, gộp thành 1 đề hoàn chỉnh để bạn làm thử.
        </p>

        <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} style={styles.select}>
          <option value="">-- Chọn môn học --</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        <div style={{ marginBottom: 10 }}>
          Số file đề lấy ngẫu nhiên:{" "}
          <input type="number" min={1} max={10} value={numFiles} onChange={(e) => setNumFiles(Number(e.target.value))} style={{ ...styles.input, width: 60 }} />
        </div>
        <div style={{ marginBottom: 10 }}>
          Số câu mỗi file:{" "}
          <input type="number" min={1} max={10} value={perFile} onChange={(e) => setPerFile(Number(e.target.value))} style={{ ...styles.input, width: 60 }} />
        </div>

        <button style={styles.btn} onClick={generateExam} disabled={loading}>
          {loading ? "Đang tạo đề... (có thể mất vài phút)" : "Tạo đề thi thử"}
        </button>
        {error && <p style={{ color: "#c53030" }}>{error}</p>}
      </div>
    );
  }

  if (current >= questions.length) {
    return (
      <div style={styles.resultBox}>
        <h3>Hoàn thành đề thi!</h3>
        <p>Đúng {score.correct}/{score.total} câu ({Math.round((score.correct / score.total) * 100)}%)</p>
        {examInfo && (
          <p style={{ fontSize: 12, color: "#718096" }}>
            Đề lấy từ: {examInfo.source_files.join(", ")}
          </p>
        )}
        <button style={styles.btn} onClick={() => setQuestions([])}>Tạo đề khác</button>
      </div>
    );
  }

  const q = questions[current];
  return (
    <div>
      {examInfo && (
        <p style={{ fontSize: 12, color: "#718096" }}>
          Đề gồm {examInfo.total_questions} câu, lấy từ: {examInfo.source_files.join(", ")}
        </p>
      )}
      <p style={{ color: "#718096" }}>Câu {current + 1}/{questions.length}</p>
      <div style={styles.questionBox}>
        <p style={{ fontWeight: 600 }}>{q.content}</p>
        {q.answers.map((a) => {
          let bg = "#fff";
          if (result) {
            if (a.id === result.correct_answer_id) bg = "#c6f6d5";
            else if (a.id === selectedAnswer) bg = "#fed7d7";
          } else if (a.id === selectedAnswer) {
            bg = "#ebf8ff";
          }
          return (
            <div key={a.id} style={{ ...styles.answerRow, background: bg }} onClick={() => !result && setSelectedAnswer(a.id)}>
              {a.content}
            </div>
          );
        })}

        {result && (
          <div style={styles.explanationBox}>
            {result.is_correct ? "✅ Chính xác!" : "❌ Sai rồi."}
            {result.explanation && <p style={{ marginTop: 6 }}>{result.explanation}</p>}
          </div>
        )}

        {!result ? (
          <button style={styles.btn} onClick={submit} disabled={selectedAnswer === null}>Nộp đáp án</button>
        ) : (
          <button style={styles.btn} onClick={nextQuestion}>Câu tiếp theo</button>
        )}
      </div>
    </div>
  );
}

// ---------------- Thêm câu hỏi thủ công ----------------
function AddQuestionTab({ subjects }) {
  const [subjectId, setSubjectId] = useState("");
  const [content, setContent] = useState("");
  const [answers, setAnswers] = useState([
    { content: "", is_correct: true },
    { content: "", is_correct: false },
    { content: "", is_correct: false },
    { content: "", is_correct: false },
  ]);
  const [explanation, setExplanation] = useState("");
  const [message, setMessage] = useState("");

  const updateAnswer = (i, field, value) => {
    const updated = [...answers];
    if (field === "is_correct") {
      // chỉ 1 đáp án đúng — bỏ tick các cái khác
      updated.forEach((a, idx) => (a.is_correct = idx === i));
    } else {
      updated[i][field] = value;
    }
    setAnswers(updated);
  };

  const save = async () => {
    if (!subjectId || !content.trim() || answers.some((a) => !a.content.trim())) {
      setMessage("Vui lòng điền đủ môn học, câu hỏi và tất cả đáp án.");
      return;
    }
    await api.post("/practice/questions", {
      subject_id: Number(subjectId),
      content,
      answers,
      explanation: explanation || null,
    });
    setContent("");
    setAnswers(answers.map((a, i) => ({ content: "", is_correct: i === 0 })));
    setExplanation("");
    setMessage("✅ Đã lưu câu hỏi.");
  };

  return (
    <div style={{ maxWidth: 600 }}>
      <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} style={styles.select}>
        <option value="">-- Chọn môn học --</option>
        {subjects.map((s) => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>

      <textarea
        placeholder="Nội dung câu hỏi"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        style={styles.textarea}
      />

      {answers.map((a, i) => (
        <div key={i} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
          <input
            type="radio"
            checked={a.is_correct}
            onChange={() => updateAnswer(i, "is_correct", true)}
            title="Đánh dấu là đáp án đúng"
          />
          <input
            placeholder={`Đáp án ${String.fromCharCode(65 + i)}`}
            value={a.content}
            onChange={(e) => updateAnswer(i, "content", e.target.value)}
            style={{ ...styles.input, flex: 1 }}
          />
        </div>
      ))}

      <textarea
        placeholder="Giải thích đáp án (hiện khi làm sai) - không bắt buộc"
        value={explanation}
        onChange={(e) => setExplanation(e.target.value)}
        style={styles.textarea}
      />

      <button style={styles.btn} onClick={save}>Lưu câu hỏi</button>
      {message && <p style={{ marginTop: 8, color: "#2f855a" }}>{message}</p>}
    </div>
  );
}

// ---------------- AI tạo câu hỏi ----------------
function AiGenerateTab({ subjects }) {
  const [subjectId, setSubjectId] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [ragDocs, setRagDocs] = useState([]);
  const [count, setCount] = useState(5);
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/rag/documents").then((res) => setRagDocs(res.data));
  }, []);

  const generate = async () => {
    if (!subjectId || !documentId) {
      setError("Chọn môn học và tài liệu đã xử lý AI trước.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/practice/generate-ai", {
        subject_id: Number(subjectId),
        document_id: Number(documentId),
        count,
      });
      setDrafts(res.data.draft_questions);
    } catch (e) {
      setError(e.response?.data?.detail || "Có lỗi khi tạo câu hỏi, thử lại.");
    } finally {
      setLoading(false);
    }
  };

  const saveDraft = async (draft, index) => {
    await api.post("/practice/questions", {
      subject_id: Number(subjectId),
      content: draft.content,
      answers: draft.answers,
      explanation: draft.explanation,
    });
    setDrafts((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div style={{ maxWidth: 700 }}>
      <p style={{ color: "#718096", fontSize: 13 }}>
        AI sẽ đọc nội dung 1 tài liệu đã xử lý (Giai đoạn 4) và tự soạn câu hỏi. Kiểm tra kỹ trước khi lưu —
        AI có thể tạo câu hỏi/đáp án chưa chính xác 100%.
      </p>

      <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} style={styles.select}>
        <option value="">-- Chọn môn học --</option>
        {subjects.map((s) => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>

      <select value={documentId} onChange={(e) => setDocumentId(e.target.value)} style={styles.select}>
        <option value="">-- Chọn tài liệu đã xử lý AI --</option>
        {ragDocs.map((d) => (
          <option key={d.id} value={d.id}>{d.name}</option>
        ))}
      </select>

      <input
        type="number"
        min={1}
        max={15}
        value={count}
        onChange={(e) => setCount(Number(e.target.value))}
        style={{ ...styles.input, width: 80 }}
      />
      <button style={styles.btn} onClick={generate} disabled={loading}>
        {loading ? "Đang tạo câu hỏi... (có thể mất 1-2 phút)" : "Tạo câu hỏi bằng AI"}
      </button>

      {error && <p style={{ color: "#c53030" }}>{error}</p>}

      {drafts.map((d, i) => (
        <div key={i} style={styles.questionBox}>
          <p style={{ fontWeight: 600 }}>{d.content}</p>
          {d.answers.map((a, ai) => (
            <div key={ai} style={{ ...styles.answerRow, background: a.is_correct ? "#c6f6d5" : "#fff" }}>
              {a.content} {a.is_correct && "✓"}
            </div>
          ))}
          {d.explanation && <p style={{ fontSize: 13, color: "#718096", marginTop: 6 }}>{d.explanation}</p>}
          <button style={styles.btn} onClick={() => saveDraft(d, i)}>Lưu câu hỏi này</button>
        </div>
      ))}
    </div>
  );
}

// ---------------- Flashcard ----------------
function FlashcardTab({ subjects }) {
  const [subjectId, setSubjectId] = useState("");
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [dueCards, setDueCards] = useState([]);
  const [current, setCurrent] = useState(0);
  const [flipped, setFlipped] = useState(false);

  const loadDue = async () => {
    const res = await api.get("/flashcards/due");
    setDueCards(res.data);
    setCurrent(0);
    setFlipped(false);
  };

  useEffect(() => {
    loadDue();
  }, []);

  const addCard = async () => {
    if (!subjectId || !front.trim() || !back.trim()) return;
    await api.post("/flashcards", { subject_id: Number(subjectId), front, back });
    setFront("");
    setBack("");
    loadDue();
  };

  const review = async (quality) => {
    const card = dueCards[current];
    await api.post(`/flashcards/${card.id}/review`, { quality });
    setFlipped(false);
    setCurrent((c) => c + 1);
  };

  return (
    <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
      <div style={{ flex: 1, minWidth: 280 }}>
        <h4>Thêm flashcard mới</h4>
        <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} style={styles.select}>
          <option value="">-- Chọn môn học --</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <textarea placeholder="Mặt trước (câu hỏi/thuật ngữ)" value={front} onChange={(e) => setFront(e.target.value)} style={styles.textarea} />
        <textarea placeholder="Mặt sau (đáp án/giải thích)" value={back} onChange={(e) => setBack(e.target.value)} style={styles.textarea} />
        <button style={styles.btn} onClick={addCard}>Thêm thẻ</button>
      </div>

      <div style={{ flex: 1, minWidth: 280 }}>
        <h4>Ôn tập hôm nay ({dueCards.length} thẻ đến hạn)</h4>
        {dueCards.length === 0 && <p style={{ color: "#718096" }}>Không có thẻ nào đến hạn ôn hôm nay 🎉</p>}
        {current < dueCards.length && (
          <div style={styles.flashcardBox} onClick={() => setFlipped(!flipped)}>
            <p style={{ fontSize: 18, textAlign: "center" }}>
              {flipped ? dueCards[current].back : dueCards[current].front}
            </p>
            <p style={{ fontSize: 12, color: "#a0aec0", textAlign: "center" }}>
              {flipped ? "(mặt sau - bấm để lật lại)" : "(bấm để lật thẻ)"}
            </p>
          </div>
        )}
        {flipped && current < dueCards.length && (
          <div style={{ display: "flex", gap: 6, marginTop: 12, flexWrap: "wrap" }}>
            <button style={styles.reviewBtnBad} onClick={() => review(0)}>Quên hết</button>
            <button style={styles.reviewBtnMed} onClick={() => review(3)}>Nhớ mơ hồ</button>
            <button style={styles.reviewBtnGood} onClick={() => review(5)}>Nhớ rõ</button>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  tabBar: { display: "flex", gap: 8, marginBottom: 20, borderBottom: "1px solid #e2e8f0", paddingBottom: 8 },
  tabBtn: {
    padding: "8px 14px",
    background: "#f7fafc",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 14,
  },
  tabBtnActive: { background: "#3182ce", color: "#fff" },
  select: { padding: 8, border: "1px solid #cbd5e0", borderRadius: 6, marginRight: 8, marginBottom: 10, display: "block" },
  input: { padding: 8, border: "1px solid #cbd5e0", borderRadius: 6 },
  textarea: { width: "100%", padding: 8, border: "1px solid #cbd5e0", borderRadius: 6, marginBottom: 10, minHeight: 60, boxSizing: "border-box" },
  btn: {
    padding: "10px 18px",
    background: "#3182ce",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
  },
  questionBox: {
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: 16,
    marginTop: 12,
    maxWidth: 600,
  },
  answerRow: {
    padding: "8px 12px",
    border: "1px solid #e2e8f0",
    borderRadius: 6,
    marginBottom: 6,
    cursor: "pointer",
  },
  explanationBox: {
    background: "#f7fafc",
    padding: 10,
    borderRadius: 6,
    marginTop: 8,
    fontSize: 14,
  },
  resultBox: { textAlign: "center", padding: 40 },
  flashcardBox: {
    border: "1px solid #cbd5e0",
    borderRadius: 10,
    padding: 40,
    minHeight: 120,
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    cursor: "pointer",
    background: "#fafafa",
  },
  reviewBtnBad: { padding: "8px 14px", background: "#e53e3e", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" },
  reviewBtnMed: { padding: "8px 14px", background: "#dd6b20", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" },
  reviewBtnGood: { padding: "8px 14px", background: "#38a169", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" },
};

import { useEffect, useState } from "react";
import api from "../api";
import { useNavigate } from "react-router-dom";
import MathView from "../components/MathView";

export default function Exams() {
  const [subjects, setSubjects] = useState([]);
  const [exams, setExams] = useState([]);
  const [counter, setCounter] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showWebHarvester, setShowWebHarvester] = useState(false);
  const [harvesting, setHarvesting] = useState(false);
  const [harvestForm, setHarvestForm] = useState({
    subject_id: 1,
    topic_query: "Đề thi thử THPT Quốc gia 2024",
    web_url: "",
  });

  const navigate = useNavigate();

  useEffect(() => {
    api.get("/subjects").then((r) => {
      setSubjects(r.data);
      if (r.data.length > 0) {
        setHarvestForm((prev) => ({ ...prev, subject_id: r.data[0].id }));
      }
    });
    loadExams();
    api.get("/exam-counter").then((r) => setCounter(r.data));
  }, []);

  const loadExams = (subjectId = null) => {
    const url = subjectId ? `/exams?subject_id=${subjectId}` : "/exams";
    api.get(url).then((r) => setExams(r.data));
  };

  const filterBySubject = (subjectId) => {
    setSelectedSubject(subjectId);
    loadExams(subjectId);
  };

  const startExam = async (examId) => {
    try {
      const res = await api.post(`/exams/${examId}/start`);
      navigate(`/exam-take/${examId}/${res.data.id}`);
    } catch (err) {
      alert("Lỗi khi bắt đầu làm bài: " + (err.response?.data?.detail || err.message));
    }
  };

  const deleteExam = async (examId) => {
    if (!window.confirm("Xóa đề thi này?")) return;
    await api.delete(`/exams/${examId}`);
    loadExams(selectedSubject);
    api.get("/exam-counter").then((r) => setCounter(r.data));
  };

  // Hành động kích hoạt AI lên mạng cào đề thi
  const handleHarvestFromWeb = async () => {
    if (!harvestForm.topic_query.trim()) {
      return alert("Vui lòng nhập tên đề hoặc chủ đề cần tìm!");
    }
    setHarvesting(true);
    try {
      const res = await api.post("/exams/harvest-from-web", harvestForm);
      alert(res.data.message);
      setShowWebHarvester(false);
      loadExams(selectedSubject);
      api.get("/exam-counter").then((r) => setCounter(r.data));
      // Tự động mở đề vừa cào về cho học sinh làm thử
      if (window.confirm("Bạn có muốn vào làm bài thi vừa thu thập được ngay không?")) {
        startExam(res.data.exam_id);
      }
    } catch (err) {
      alert("Lỗi khi thu thập đề từ mạng: " + (err.response?.data?.detail || err.message));
    } finally {
      setHarvesting(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
        <h2>📝 Kho Đề Thi Ôn Luyện</h2>
        <div style={{ display: "flex", gap: 10 }}>
          <button style={styles.harvestBtn} onClick={() => setShowWebHarvester(true)}>
            🌐 AI Thu Thập Đề Từ Internet
          </button>
          <button style={styles.btn} onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? "✕ Đóng" : "+ Tạo đề thủ công"}
          </button>
        </div>
      </div>

      {/* Bộ đếm */}
      <div style={styles.counterRow}>
        {counter.map((c) => (
          <div
            key={c.subject_id}
            style={{
              ...styles.counterChip,
              background: selectedSubject === c.subject_id ? "#3182ce" : "#edf2f7",
              color: selectedSubject === c.subject_id ? "#fff" : "#2d3748",
              cursor: "pointer",
            }}
            onClick={() => filterBySubject(selectedSubject === c.subject_id ? null : c.subject_id)}
          >
            {c.subject_icon} {c.subject_name}: <b>{c.completed_exams}/{c.total_exams}</b>
          </div>
        ))}
        {selectedSubject && (
          <div
            style={{ ...styles.counterChip, background: "#fed7d7", color: "#c53030", cursor: "pointer" }}
            onClick={() => filterBySubject(null)}
          >
            ✕ Bỏ lọc
          </div>
        )}
      </div>

      {/* Popup / Modal: AI Thu thập đề thi từ Internet */}
      {showWebHarvester && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ margin: 0, color: "#2b6cb0" }}>🌐 AI Tự Động Thu Thập Đề Thi Từ Internet</h3>
              <button style={{ border: "none", background: "transparent", fontSize: 18, cursor: "pointer" }} onClick={() => setShowWebHarvester(false)}>✕</button>
            </div>
            
            <p style={{ fontSize: 13, color: "#4a5568", lineHeight: 1.5, background: "#ebf8ff", padding: 10, borderRadius: 6, border: "1px solid #bee3f8" }}>
              <b>💡 Tiêu chuẩn đề thi chính thống 2025 (GDPT 2018):</b><br/>
              Hệ thống chỉ cung cấp đề thi nguyên bản 100% từ các Sở GD&ĐT và Trường Chuyên toàn quốc. AI tuyệt đối <b>không tự bịa câu hỏi</b> hoặc chắp vá câu hỏi rời rạc.
            </p>

            <div style={{ marginBottom: 12 }}>
              <label style={styles.label}>1. Chọn Môn Học:</label>
              <select
                value={harvestForm.subject_id}
                onChange={(e) => setHarvestForm({ ...harvestForm, subject_id: Number(e.target.value) })}
                style={styles.select}
              >
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={styles.label}>2. Tìm theo Tỉnh, Trường Chuyên hoặc Chủ đề:</label>
              <input
                placeholder="VD: Sở Hà Nội, THPT Chuyên Lam Sơn, KHTN, Sở Nghệ An, Đạo hàm, Este..."
                value={harvestForm.topic_query}
                onChange={(e) => setHarvestForm({ ...harvestForm, topic_query: e.target.value })}
                style={styles.inputFull}
              />
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
                {["Sở Hà Nội", "Chuyên Lam Sơn", "Chuyên KHTN", "Sở Nghệ An", "Sở Nam Định", "Sở Bắc Ninh"].map((tag) => (
                  <span
                    key={tag}
                    onClick={() => setHarvestForm({ ...harvestForm, topic_query: tag })}
                    style={{ fontSize: 12, background: "#edf2f7", padding: "2px 8px", borderRadius: 12, cursor: "pointer", color: "#2b6cb0" }}
                  >
                    🏷️ {tag}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 18 }}>
              <label style={styles.label}>3. Hoặc Dán Link Web chứa đề thi chính thức (Tùy chọn):</label>
              <input
                placeholder="https://vietjack.com/... hoặc https://toanmath.com/..."
                value={harvestForm.web_url}
                onChange={(e) => setHarvestForm({ ...harvestForm, web_url: e.target.value })}
                style={styles.inputFull}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button style={styles.cancelBtn} onClick={() => setShowWebHarvester(false)}>Hủy</button>
              <button style={styles.startHarvestBtn} onClick={handleHarvestFromWeb} disabled={harvesting}>
                {harvesting ? "⏳ Đang quét đề trên mạng..." : "🚀 Tìm kiếm & Nạp đề ngay"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Form tạo đề thủ công */}
      {showCreate && (
        <CreateExamForm
          subjects={subjects}
          onCreated={() => {
            setShowCreate(false);
            loadExams(selectedSubject);
            api.get("/exam-counter").then((r) => setCounter(r.data));
          }}
        />
      )}

      {/* Danh sách đề thi */}
      {exams.length === 0 ? (
        <p style={{ color: "#718096", marginTop: 20 }}>Chưa có đề thi nào. Bấm nút <b>"🌐 AI Thu Thập Đề Từ Internet"</b> để lấy đề về ngay!</p>
      ) : (
        <div style={{ marginTop: 16 }}>
          {exams.map((exam) => {
            const subjectName = subjects.find((s) => s.id === exam.subject_id)?.name || "";
            return (
              <div key={exam.id} style={styles.examCard}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 16 }}><MathView text={exam.title} /></div>
                  
                  {/* Huy hiệu thông tin nguồn gốc (Provenance Badges) */}
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
                    {exam.school_or_dept && (
                      <span style={styles.schoolBadge}>🏛️ {exam.school_or_dept}</span>
                    )}
                    {exam.province && (
                      <span style={styles.provinceBadge}>📍 {exam.province}</span>
                    )}
                    {exam.exam_year && (
                      <span style={styles.yearBadge}>📅 Năm {exam.exam_year}</span>
                    )}
                    {exam.curriculum_standard && (
                      <span style={styles.curriculumBadge}>🎯 {exam.curriculum_standard}</span>
                    )}
                  </div>

                  <div style={{ fontSize: 13, color: "#718096", marginTop: 6 }}>
                    📘 {subjectName} · {exam.total_questions} câu · {exam.duration_minutes} phút ·{" "}
                    <span style={styles.typeBadge}>{exam.exam_type}</span>
                  </div>
                  {exam.description && (
                    <div style={{ fontSize: 13, color: "#4a5568", marginTop: 4 }}>{exam.description}</div>
                  )}
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button style={styles.startBtn} onClick={() => startExam(exam.id)}>
                    ▶ Làm bài
                  </button>
                  <button style={styles.deleteBtn} onClick={() => deleteExam(exam.id)}>
                    🗑
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ============ Form tạo đề thi thủ công ============ */
function CreateExamForm({ subjects, onCreated }) {
  const [form, setForm] = useState({
    subject_id: subjects[0]?.id || 1,
    title: "",
    description: "",
    duration_minutes: 90,
    exam_type: "practice",
  });
  const [questions, setQuestions] = useState([emptyQuestion(1)]);

  function emptyQuestion(num) {
    return {
      question_number: num,
      question_type: "multiple_choice",
      question_text: "",
      option_a: "",
      option_b: "",
      option_c: "",
      option_d: "",
      correct_answer: "A",
      explanation: "",
      topic_tag: "",
    };
  }

  const addQuestion = () => setQuestions([...questions, emptyQuestion(questions.length + 1)]);
  const removeQuestion = (idx) => setQuestions(questions.filter((_, i) => i !== idx).map((q, i) => ({ ...q, question_number: i + 1 })));
  const updateQ = (idx, field, value) => {
    const updated = [...questions];
    updated[idx] = { ...updated[idx], [field]: value };
    setQuestions(updated);
  };

  const submit = async () => {
    if (!form.title.trim()) return alert("Nhập tiêu đề đề thi");
    try {
      await api.post("/exams", { ...form, questions });
      onCreated();
    } catch (err) {
      alert("Lỗi tạo đề: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div style={styles.createForm}>
      <h3>Tạo đề thi thủ công (Chuẩn 2025)</h3>
      <div style={styles.formRow}>
        <select
          value={form.subject_id}
          onChange={(e) => setForm({ ...form, subject_id: Number(e.target.value) })}
          style={styles.select}
        >
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <input
          placeholder="Tiêu đề đề thi"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={styles.input}
        />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "14px 0 8px" }}>
        <h4 style={{ margin: 0 }}>Câu hỏi ({questions.length})</h4>
        <button type="button" onClick={addQuestion} style={{ ...styles.btn, fontSize: 13 }}>+ Thêm câu hỏi</button>
      </div>

      {questions.map((q, idx) => (
        <div key={idx} style={styles.questionBlock}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <b>Câu {q.question_number}</b>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <select
                value={q.question_type}
                onChange={(e) => updateQ(idx, "question_type", e.target.value)}
                style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #cbd5e0", fontSize: 13 }}
              >
                <option value="multiple_choice">Phần I: 4 Lựa chọn</option>
                <option value="true_false">Phần II: Đúng / Sai 4 ý</option>
                <option value="short_answer">Phần III: Trả lời ngắn</option>
              </select>
              {questions.length > 1 && (
                <button type="button" onClick={() => removeQuestion(idx)} style={{ color: "#e53e3e", border: "none", background: "transparent", cursor: "pointer", fontSize: 13 }}>
                  Xóa
                </button>
              )}
            </div>
          </div>

          <textarea
            placeholder="Nội dung câu hỏi (hỗ trợ công thức LaTeX ví dụ: $y = x^2$)..."
            value={q.question_text}
            onChange={(e) => updateQ(idx, "question_text", e.target.value)}
            style={styles.textarea}
          />

          {/* Dạng 1: Multiple choice */}
          {q.question_type === "multiple_choice" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 8 }}>
              {["a", "b", "c", "d"].map((opt) => (
                <input
                  key={opt}
                  placeholder={`Phương án ${opt.toUpperCase()}`}
                  value={q[`option_${opt}`]}
                  onChange={(e) => updateQ(idx, `option_${opt}`, e.target.value)}
                  style={styles.input}
                />
              ))}
              <div style={{ gridColumn: "span 2", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>Đáp án đúng:</span>
                <select
                  value={q.correct_answer}
                  onChange={(e) => updateQ(idx, "correct_answer", e.target.value)}
                  style={{ padding: 6, borderRadius: 4, border: "1px solid #cbd5e0" }}
                >
                  <option value="A">A</option>
                  <option value="B">B</option>
                  <option value="C">C</option>
                  <option value="D">D</option>
                </select>
              </div>
            </div>
          )}

          {/* Dạng 2: True / False */}
          {q.question_type === "true_false" && (
            <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
              {["a", "b", "c", "d"].map((opt) => (
                <input
                  key={opt}
                  placeholder={`Mệnh đề ${opt})`}
                  value={q[`option_${opt}`]}
                  onChange={(e) => updateQ(idx, `option_${opt}`, e.target.value)}
                  style={styles.input}
                />
              ))}
              <input
                placeholder="Chuỗi đáp án (VD: T,F,T,T hoặc Đ,S,Đ,Đ)"
                value={q.correct_answer}
                onChange={(e) => updateQ(idx, "correct_answer", e.target.value)}
                style={styles.input}
              />
            </div>
          )}

          {/* Dạng 3: Short answer */}
          {q.question_type === "short_answer" && (
            <div style={{ marginTop: 8 }}>
              <input
                placeholder="Đáp số chính xác (VD: 10, 0.4, 73.6)"
                value={q.correct_answer}
                onChange={(e) => updateQ(idx, "correct_answer", e.target.value)}
                style={styles.input}
              />
            </div>
          )}
        </div>
      ))}
      <button style={styles.submitBtn} onClick={submit}>💾 Lưu đề thi</button>
    </div>
  );
}

const styles = {
  harvestBtn: {
    padding: "9px 18px", background: "linear-gradient(135deg, #319795, #2b6cb0)", color: "#fff",
    border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 700, fontSize: 14,
    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
  },
  btn: {
    padding: "8px 16px", background: "#edf2f7", color: "#2d3748",
    border: "1px solid #cbd5e0", borderRadius: 8, cursor: "pointer", fontWeight: 600,
  },
  modalOverlay: {
    position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
    background: "rgba(0, 0, 0, 0.5)", display: "flex", alignItems: "center", justifyContent: "center",
    zIndex: 9999,
  },
  modalContent: {
    background: "#fff", borderRadius: 12, padding: 24, width: "90%", maxWidth: 540,
    boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
  },
  label: { display: "block", fontSize: 13, fontWeight: 700, color: "#2d3748", marginBottom: 6 },
  inputFull: {
    width: "100%", padding: 10, border: "1px solid #cbd5e0", borderRadius: 6, fontSize: 14, boxSizing: "border-box",
  },
  startHarvestBtn: {
    padding: "10px 20px", background: "#319795", color: "#fff", border: "none", borderRadius: 6,
    fontWeight: 700, cursor: "pointer", fontSize: 14,
  },
  cancelBtn: {
    padding: "10px 16px", background: "#edf2f7", border: "none", borderRadius: 6, cursor: "pointer",
  },
  counterRow: { display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" },
  counterChip: { padding: "6px 14px", borderRadius: 20, fontSize: 13, fontWeight: 500 },
  examCard: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: 16, marginBottom: 10,
  },
  typeBadge: { background: "#edf2f7", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  schoolBadge: { background: "#ebf8ff", color: "#2b6cb0", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700, border: "1px solid #bee3f8" },
  provinceBadge: { background: "#feebc8", color: "#c05621", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600, border: "1px solid #fbd38d" },
  yearBadge: { background: "#e2e8f0", color: "#4a5568", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  curriculumBadge: { background: "#c6f6d5", color: "#22543d", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700, border: "1px solid #9ae6b4" },
  startBtn: {
    padding: "8px 16px", background: "#38a169", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600,
  },
  deleteBtn: { padding: "8px 12px", background: "#fed7d7", color: "#c53030", border: "none", borderRadius: 6, cursor: "pointer" },
  createForm: { background: "#f7fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: 20, marginTop: 16 },
  formRow: { display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" },
  input: { padding: 8, border: "1px solid #cbd5e0", borderRadius: 6, flex: 1, fontSize: 14 },
  select: { width: "100%", padding: 10, border: "1px solid #cbd5e0", borderRadius: 6, fontSize: 14, boxSizing: "border-box" },
  questionBlock: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 6, padding: 12, marginBottom: 10 },
  textarea: { width: "100%", minHeight: 60, padding: 8, border: "1px solid #cbd5e0", borderRadius: 6, marginTop: 6, fontSize: 14 },
  submitBtn: { padding: "8px 18px", background: "#3182ce", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 },
};

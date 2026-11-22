import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";
import api from "../api";

const categories = [
  ["national_previous_year", "Đề tốt nghiệp các năm trước"],
  ["mock", "Thi thử"],
  ["midterm", "Giữa kỳ"],
  ["final", "Cuối kỳ"],
  ["monthly", "Kiểm tra tháng"],
  ["reference", "Đề tham khảo"],
  ["generated", "Đề luyện tạo theo ma trận"],
];

export default function Exams() {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState([]);
  const [filters, setFilters] = useState({ subject_id: "", category: "", year_from: "", year_to: "", semester: "", month: "", province: "", school: "", provenance_status: "", source_kind: "", topic_id: "", q: "" });
  const [appliedFilters, setAppliedFilters] = useState({});
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [startingExamId, setStartingExamId] = useState(null);
  const pageSize = 30;

  useEffect(() => {
    api.get("/catalog/subjects").then((response) => setSubjects(response.data)).catch(() => setSubjects([]));
  }, []);

  const selectedSubject = subjects.find((subject) => String(subject.id) === filters.subject_id);
  const availableTopics = useMemo(() => selectedSubject?.topics || [], [selectedSubject]);

  const loadExams = async (nextFilters = appliedFilters, nextOffset = 0) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value !== "" && value !== null && value !== undefined) params.set(key, value);
      });
      params.set("limit", String(pageSize));
      params.set("offset", String(nextOffset));
      params.set("sort", "newest");
      const response = await api.get(`/exams?${params.toString()}`);
      setItems(response.data.items || []);
      setTotal(response.data.total || 0);
      setOffset(nextOffset);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Không tải được catalog đề thi.");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExams({}, 0);
  }, []);

  const updateFilter = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value, ...(key === "subject_id" ? { topic_id: "" } : {}) }));
  };

  const applyFilters = (event) => {
    event.preventDefault();
    const next = { ...filters };
    setAppliedFilters(next);
    loadExams(next, 0);
  };

  const startExam = async (exam) => {
    setStartingExamId(exam.id);
    setError("");
    try {
      const response = await api.post(`/exams/${exam.id}/start`);
      navigate(`/exam-take/${exam.id}/${response.data.id}`);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Không bắt đầu được lượt làm bài.");
    } finally {
      setStartingExamId(null);
    }
  };

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <h2 style={{ margin: 0 }}>Kho đề thi</h2>
          <p style={styles.subtitle}>Lọc theo metadata đã có. Đề không khớp điều kiện sẽ không bị thay bằng đề khác.</p>
        </div>
        <span style={styles.totalBadge}>{total} đề</span>
        <Link to="/generate" style={{ ...styles.primaryButton, textDecoration: "none" }}>✨ Sinh đề theo ma trận</Link>
      </header>

      <form onSubmit={applyFilters} style={styles.filterPanel}>
        <label style={styles.field}>Môn
          <select value={filters.subject_id} onChange={(event) => updateFilter("subject_id", event.target.value)} style={styles.input}>
            <option value="">Tất cả môn</option>
            {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
          </select>
        </label>
        <label style={styles.field}>Loại đề
          <select value={filters.category} onChange={(event) => updateFilter("category", event.target.value)} style={styles.input}>
            <option value="">Tất cả loại</option>
            {categories.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label style={styles.field}>Từ năm
          <input type="number" min="2000" max="2100" value={filters.year_from} onChange={(event) => updateFilter("year_from", event.target.value)} style={styles.input} />
        </label>
        <label style={styles.field}>Đến năm
          <input type="number" min="2000" max="2100" value={filters.year_to} onChange={(event) => updateFilter("year_to", event.target.value)} style={styles.input} />
        </label>
        <label style={styles.field}>Học kỳ
          <select value={filters.semester} onChange={(event) => updateFilter("semester", event.target.value)} style={styles.input}>
            <option value="">Tất cả</option><option value="HK1">Học kỳ 1</option><option value="HK2">Học kỳ 2</option><option value="CaNam">Cả năm</option>
          </select>
        </label>
        <label style={styles.field}>Tháng
          <select value={filters.month} onChange={(event) => updateFilter("month", event.target.value)} style={styles.input}>
            <option value="">Tất cả</option>{Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={index + 1}>Tháng {index + 1}</option>)}
          </select>
        </label>
        <label style={styles.field}>Tỉnh/thành
          <input value={filters.province} onChange={(event) => updateFilter("province", event.target.value)} style={styles.input} placeholder="Ví dụ: Hà Nội" />
        </label>
        <label style={styles.field}>Trường/Sở
          <input value={filters.school} onChange={(event) => updateFilter("school", event.target.value)} style={styles.input} placeholder="Tên trường hoặc sở" />
        </label>
        <label style={styles.field}>Trạng thái nguồn
          <select value={filters.provenance_status} onChange={(event) => updateFilter("provenance_status", event.target.value)} style={styles.input}>
            <option value="">Tất cả</option><option value="unverified">Chưa xác minh</option><option value="source_verified">Đã xác minh nguồn</option><option value="reviewed">Đã rà soát</option>
          </select>
        </label>
        <label style={styles.field}>Loại nguồn
          <select value={filters.source_kind} onChange={(event) => updateFilter("source_kind", event.target.value)} style={styles.input}>
            <option value="">Tất cả nguồn</option><option value="web">Internet</option><option value="user_import">Tôi nhập</option><option value="generated">AI tạo</option>
          </select>
        </label>
        <label style={styles.field}>Chủ đề
          <select value={filters.topic_id} onChange={(event) => updateFilter("topic_id", event.target.value)} style={styles.input} disabled={!filters.subject_id}>
            <option value="">Tất cả chủ đề</option>
            {availableTopics.map((topic) => <option key={topic.id} value={topic.id}>Lớp {topic.grade} · {topic.name}</option>)}
          </select>
        </label>
        <label style={{ ...styles.field, gridColumn: "span 2" }}>Từ khóa
          <input value={filters.q} onChange={(event) => updateFilter("q", event.target.value)} style={styles.input} placeholder="Tìm trong tiêu đề và nội dung câu hỏi" />
        </label>
        <button type="submit" style={styles.primaryButton}>Áp dụng bộ lọc</button>
      </form>

      {error && <div role="alert" style={styles.error}>{error}</div>}
      {loading ? <div style={styles.empty}>Đang tìm đề...</div> : items.length === 0 ? (
        <div style={styles.emptyState}>
          <div style={{ fontSize: 42 }}>📚</div>
          <h3>Chưa có đề nào khớp bộ lọc</h3>
          <p>Hãy tìm đề trên Internet hoặc nhập đề bạn đã có. Mọi nguồn sẽ được rà soát trước khi xuất bản vào kho chung.</p>
          <Link to="/imports" style={{ ...styles.primaryButton, display: "inline-block", textDecoration: "none" }}>Tìm và nhập đề</Link>
        </div>
      ) : (
        <div style={styles.list}>
          {items.map((exam) => (
            <article key={exam.id} style={styles.card}>
              <div style={{ flex: 1 }}>
                <div style={styles.subject}>{exam.subject_icon || "📝"} {exam.subject_name}</div>
                <h3 style={styles.title}>{exam.title}</h3>
                <div style={styles.badges}>
                  <span style={styles.badge}>{categories.find(([value]) => value === exam.category)?.[1] || exam.category}</span>
                  {exam.exam_year && <span style={styles.badge}>{exam.exam_year}</span>}
                  {exam.semester && <span style={styles.badge}>{exam.semester}</span>}
                  {exam.exam_month && <span style={styles.badge}>Tháng {exam.exam_month}</span>}
                  {exam.province && <span style={styles.badge}>📍 {exam.province}</span>}
                  {exam.school_name && <span style={styles.badge}>🏫 {exam.school_name}</span>}
                  {exam.source_kinds?.map((source) => <span key={source} style={styles.badge}>{source}</span>)}
                  <span style={exam.provenance_status === "reviewed" ? styles.verifiedBadge : styles.badge}>{exam.provenance_status}</span>
                </div>
                <div style={styles.meta}>{exam.total_questions} câu · {exam.duration_minutes || "—"} phút · tối đa {exam.max_score}/10</div>
              </div>
              <div style={styles.actionArea}>
                {exam.can_practice ? (
                  <button style={styles.primaryButton} disabled={startingExamId === exam.id} onClick={() => startExam(exam)}>
                    {startingExamId === exam.id ? "Đang mở..." : "Bắt đầu làm"}
                  </button>
                ) : <span style={styles.readOnly}>Chưa đủ đáp án đã xác minh để chấm</span>}
              </div>
            </article>
          ))}
        </div>
      )}

      {total > pageSize && <div style={styles.pagination}>
        <button disabled={offset === 0 || loading} onClick={() => loadExams(appliedFilters, Math.max(0, offset - pageSize))} style={styles.pageButton}>Trước</button>
        <span>{offset + 1}–{Math.min(offset + pageSize, total)} / {total}</span>
        <button disabled={offset + pageSize >= total || loading} onClick={() => loadExams(appliedFilters, offset + pageSize)} style={styles.pageButton}>Sau</button>
      </div>}
    </div>
  );
}

const styles = {
  page: { padding: 24, maxWidth: 1120, margin: "0 auto", color: "#1f2937" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 18 },
  subtitle: { color: "#64748b", margin: "6px 0 0" },
  totalBadge: { background: "#eff6ff", color: "#1d4ed8", borderRadius: 999, padding: "7px 12px", fontWeight: 700, whiteSpace: "nowrap" },
  filterPanel: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(155px, 1fr))", gap: 12, padding: 16, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12, marginBottom: 18, alignItems: "end" },
  field: { display: "flex", flexDirection: "column", gap: 5, fontSize: 13, color: "#475569", fontWeight: 600 },
  input: { minWidth: 0, width: "100%", boxSizing: "border-box", border: "1px solid #cbd5e1", borderRadius: 7, padding: "9px 10px", background: "white", color: "#1f2937" },
  primaryButton: { border: 0, borderRadius: 8, padding: "10px 14px", background: "#2563eb", color: "white", fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap" },
  error: { padding: 12, marginBottom: 14, border: "1px solid #fecaca", background: "#fef2f2", borderRadius: 8, color: "#b91c1c" },
  empty: { padding: 40, textAlign: "center", color: "#64748b" },
  emptyState: { padding: 42, textAlign: "center", border: "1px dashed #cbd5e1", borderRadius: 12, color: "#64748b", background: "#fbfdff" },
  list: { display: "flex", flexDirection: "column", gap: 12 },
  card: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 18, padding: 18, border: "1px solid #e2e8f0", borderRadius: 12, background: "white", boxShadow: "0 1px 2px #0f172a0a" },
  subject: { color: "#2563eb", fontSize: 13, fontWeight: 700 },
  title: { margin: "5px 0 10px", fontSize: 17 },
  badges: { display: "flex", flexWrap: "wrap", gap: 6 },
  badge: { fontSize: 11, background: "#f1f5f9", color: "#475569", borderRadius: 999, padding: "4px 8px" },
  verifiedBadge: { fontSize: 11, background: "#dcfce7", color: "#166534", borderRadius: 999, padding: "4px 8px" },
  meta: { marginTop: 9, fontSize: 13, color: "#64748b" },
  actionArea: { display: "flex", justifyContent: "flex-end", minWidth: 175 },
  readOnly: { color: "#92400e", fontSize: 12, textAlign: "right", maxWidth: 180 },
  pagination: { display: "flex", alignItems: "center", justifyContent: "center", gap: 16, margin: "20px 0", color: "#475569" },
  pageButton: { border: "1px solid #cbd5e1", borderRadius: 7, padding: "7px 12px", background: "white", cursor: "pointer" },
};

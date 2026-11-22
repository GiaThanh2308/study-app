import { useEffect, useState } from "react";
import api from "../api";

const categories = [
  ["national_previous_year", "Đề tốt nghiệp các năm trước"], ["mock", "Thi thử"],
  ["midterm", "Giữa kỳ"], ["final", "Cuối kỳ"], ["monthly", "Kiểm tra tháng"], ["reference", "Đề tham khảo"],
];
const initialMetadata = { subject_id: "", title: "", category: "national_previous_year", exam_year: "", semester: "", exam_month: "", duration_minutes: "", province: "", school_name: "" };
const styles = {
  page: { maxWidth: 1180, margin: "0 auto", padding: 24, color: "#1f2937" },
  panel: { border: "1px solid #e2e8f0", borderRadius: 12, padding: 18, marginBottom: 16, background: "white" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))", gap: 12 },
  field: { display: "flex", flexDirection: "column", gap: 5, fontSize: 13, color: "#475569", fontWeight: 600 },
  input: { boxSizing: "border-box", width: "100%", border: "1px solid #cbd5e1", borderRadius: 7, padding: "9px 10px", background: "white", color: "#1f2937" },
  button: { border: 0, borderRadius: 7, padding: "9px 13px", background: "#2563eb", color: "white", cursor: "pointer", fontWeight: 700 },
  mutedButton: { border: "1px solid #cbd5e1", borderRadius: 7, padding: "8px 12px", background: "white", cursor: "pointer", color: "#334155" },
  badge: { display: "inline-block", background: "#f1f5f9", color: "#475569", padding: "4px 8px", borderRadius: 99, fontSize: 12, marginRight: 5, marginBottom: 5 },
  error: { padding: 12, borderRadius: 8, background: "#fef2f2", color: "#b91c1c", marginBottom: 12 },
  warning: { padding: 12, borderRadius: 8, background: "#fffbeb", color: "#92400e", margin: "8px 0" },
};

function cleanMetadata(metadata) {
  const result = { ...metadata, subject_id: Number(metadata.subject_id) };
  ["exam_year", "exam_month", "duration_minutes"].forEach((key) => { result[key] = result[key] ? Number(result[key]) : null; });
  ["semester", "province", "school_name"].forEach((key) => { result[key] = result[key] || null; });
  return result;
}

export default function ImportExams() {
  const [subjects, setSubjects] = useState([]);
  const [metadata, setMetadata] = useState(initialMetadata);
  const [mode, setMode] = useState("search");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [staged, setStaged] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [answerDrafts, setAnswerDrafts] = useState({});
  const [editingQuestions, setEditingQuestions] = useState(false);
  const [questionsJson, setQuestionsJson] = useState("[]");

  const load = async () => {
    try { const response = await api.get("/imports/staged"); setStaged(response.data); }
    catch (err) { setError(err.response?.data?.detail || "Không tải được hàng chờ nhập."); }
  };
  useEffect(() => {
    api.get("/catalog/subjects").then((response) => {
      setSubjects(response.data);
      if (response.data.length) setMetadata((current) => ({ ...current, subject_id: String(response.data[0].id) }));
    }).catch(() => setError("Không tải được danh sách môn."));
    load();
  }, []);

  const reportError = (err) => {
    const detail = err.response?.data?.detail;
    setError(typeof detail === "string" ? detail : detail?.message || "Thao tác không thành công.");
  };
  const openStage = async (stage) => {
    setSelected(stage);
    setEditingQuestions(false);
    try {
      const response = await api.get(`/imports/staged/${stage.id}`);
      setSelected(response.data);
      setQuestionsJson(JSON.stringify(response.data.questions || [], null, 2));
    } catch (err) { reportError(err); }
  };
  const search = async (event) => {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try { const response = await api.get("/search/web", { params: { q: query, max_results: 10 } }); setResults(response.data.results || []); }
    catch (err) { reportError(err); }
    finally { setBusy(false); }
  };
  const importSource = async (event) => {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      const meta = cleanMetadata(metadata);
      let response;
      if (mode === "url") {
        const form = new FormData(); form.append("url", url); form.append("metadata", JSON.stringify(meta));
        response = await api.post("/imports/url", form);
      } else if (mode === "file") {
        const form = new FormData(); form.append("file", file); form.append("metadata", JSON.stringify(meta));
        response = await api.post("/imports/file", form);
      } else {
        response = await api.post("/imports/text", { ...meta, text });
      }
      setSelected(response.data); setQuestionsJson(JSON.stringify(response.data.questions || [], null, 2)); setNotice("Nguồn đã lưu nguyên bản và được đưa vào hàng chờ duyệt.");
      setUrl(""); setFile(null); setText(""); await load();
    } catch (err) { reportError(err); }
    finally { setBusy(false); }
  };
  const publish = async (stage, allowSimilar = false) => {
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await api.post(`/imports/staged/${stage.id}/publish`, { allow_similar_duplicate: allowSimilar });
      setNotice(response.data.status === "duplicate_linked" ? `Nguồn đã liên kết với đề có sẵn: ${response.data.title}.` : `Đã đưa “${response.data.title}” vào kho đề.`);
      setSelected(null); await load();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 409 && detail?.duplicates) {
        setError(`${detail.message} Hãy bấm “Vẫn lưu thành đề riêng” bên dưới nếu đã kiểm tra.`);
        setSelected({ ...stage, duplicates: detail.duplicates, needsDuplicateConfirmation: true });
      } else reportError(err);
    } finally { setBusy(false); }
  };
  const verifyAnswer = async (stage, question, index) => {
    setBusy(true); setError("");
    try {
      const raw = answerDrafts[`${stage.id}-${index}`] || "";
      let answer;
      try { answer = JSON.parse(raw); } catch { answer = { choice: raw.trim().toUpperCase() }; }
      const response = await api.post(`/imports/staged/${stage.id}/verify-answer`, { position: index + 1, answer });
      setSelected(response.data); await load();
    } catch (err) { reportError(err); }
    finally { setBusy(false); }
  };
  const reject = async (stage) => {
    setBusy(true); setError("");
    try { await api.post(`/imports/staged/${stage.id}/reject`); setSelected(null); await load(); }
    catch (err) { reportError(err); }
    finally { setBusy(false); }
  };
  const saveQuestions = async () => {
    setBusy(true); setError("");
    try {
      const response = await api.patch(`/imports/staged/${selected.id}`, { questions: JSON.parse(questionsJson) });
      setSelected(response.data); setQuestionsJson(JSON.stringify(response.data.questions || [], null, 2));
      setEditingQuestions(false); await load();
    } catch (err) { if (err instanceof SyntaxError) setError("JSON câu hỏi không hợp lệ."); else reportError(err); }
    finally { setBusy(false); }
  };

  const setMeta = (key, value) => setMetadata((current) => ({ ...current, [key]: value }));
  const currentStage = selected;

  return <main style={styles.page}>
    <header style={{ marginBottom: 18 }}>
      <h1 style={{ margin: 0 }}>Tìm và nhập đề</h1>
      <p style={{ color: "#64748b", margin: "7px 0 0" }}>Tìm Internet, nhập URL, tải file hoặc dán đề. Mọi nguồn đều được lưu nguyên bản trước khi bạn duyệt vào cùng kho đề.</p>
    </header>
    {error && <div role="alert" style={styles.error}>{error}</div>}
    {notice && <div role="status" style={{ ...styles.warning, background: "#f0fdf4", color: "#166534" }}>{notice}</div>}

    <section style={styles.panel}>
      <h2 style={{ marginTop: 0 }}>1. Chọn thông tin đề</h2>
      <div style={styles.grid}>
        <label style={styles.field}>Môn<select style={styles.input} value={metadata.subject_id} onChange={(e) => setMeta("subject_id", e.target.value)}>{subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
        <label style={styles.field}>Loại đề<select style={styles.input} value={metadata.category} onChange={(e) => setMeta("category", e.target.value)}>{categories.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label style={styles.field}>Tiêu đề<input style={styles.input} required minLength={2} value={metadata.title} onChange={(e) => setMeta("title", e.target.value)} placeholder="Ví dụ: Đề thi thử THPT 2026 – Sở ..." /></label>
        <label style={styles.field}>Năm<input style={styles.input} type="number" min="2000" max="2100" value={metadata.exam_year} onChange={(e) => setMeta("exam_year", e.target.value)} /></label>
        <label style={styles.field}>Học kỳ<select style={styles.input} value={metadata.semester} onChange={(e) => setMeta("semester", e.target.value)}><option value="">Chưa rõ</option><option>HK1</option><option>HK2</option><option>CaNam</option></select></label>
        <label style={styles.field}>Tháng<input style={styles.input} type="number" min="1" max="12" value={metadata.exam_month} onChange={(e) => setMeta("exam_month", e.target.value)} /></label>
        <label style={styles.field}>Thời gian (phút)<input style={styles.input} type="number" min="1" max="600" value={metadata.duration_minutes} onChange={(e) => setMeta("duration_minutes", e.target.value)} /></label>
        <label style={styles.field}>Tỉnh/thành<input style={styles.input} value={metadata.province} onChange={(e) => setMeta("province", e.target.value)} /></label>
        <label style={styles.field}>Trường/Sở<input style={styles.input} value={metadata.school_name} onChange={(e) => setMeta("school_name", e.target.value)} /></label>
      </div>
    </section>

    <section style={styles.panel}>
      <h2 style={{ marginTop: 0 }}>2. Chọn cách lấy đề</h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 14 }}>
        {[["search", "Tìm Internet"], ["url", "Dán URL"], ["file", "Tải file"], ["text", "Dán nội dung"]].map(([value, label]) => <button key={value} type="button" style={mode === value ? styles.button : styles.mutedButton} onClick={() => setMode(value)}>{label}</button>)}
      </div>
      {mode === "search" && <>
        <form onSubmit={search} style={{ display: "flex", gap: 8 }}><input style={styles.input} required minLength={2} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ví dụ: đề thi thử THPT 2026 môn Toán PDF" /><button style={styles.button} disabled={busy}>{busy ? "Đang tìm..." : "Tìm"}</button></form>
        {!results.length && <p style={{ color: "#64748b" }}>Tìm kiếm dùng Tavily Basic miễn phí khi đã cấu hình key. Nếu dịch vụ tạm lỗi hoặc chưa cấu hình, dán URL ở tab bên cạnh.</p>}
        {results.map((item) => <article key={item.url} style={{ borderTop: "1px solid #e2e8f0", marginTop: 12, paddingTop: 12 }}><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a><p style={{ margin: "5px 0", color: "#64748b" }}>{item.snippet}</p><button type="button" style={styles.mutedButton} onClick={() => { setUrl(item.url); setMeta("title", metadata.title || item.title); setMode("url"); }}>Nhập nguồn này</button></article>)}
      </>}
      {mode !== "search" && <form onSubmit={importSource} style={{ display: "grid", gap: 10 }}>
        {mode === "url" && <label style={styles.field}>URL nguồn<input style={styles.input} type="url" required value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." /></label>}
        {mode === "file" && <label style={styles.field}>File đề (PDF, DOCX, TXT, MD, HTML, JPG, PNG, WebP)<input style={styles.input} type="file" required accept=".pdf,.docx,.txt,.md,.html,.htm,.jpg,.jpeg,.png,.webp" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label>}
        {mode === "text" && <label style={styles.field}>Nội dung đề<textarea style={{ ...styles.input, minHeight: 180, fontFamily: "inherit" }} required value={text} onChange={(e) => setText(e.target.value)} placeholder="Dán nguyên văn đề và đáp án nếu có. Nội dung sẽ không bị AI diễn đạt lại." /></label>}
        <div><button style={styles.button} disabled={busy || (mode === "file" && !file)}>{busy ? "Đang nhập..." : "Lưu nguyên bản và xem trước"}</button></div>
      </form>}
    </section>

    <section style={styles.panel}>
      <h2 style={{ marginTop: 0 }}>3. Duyệt nguồn chờ nhập ({staged.length})</h2>
      {staged.length === 0 ? <p style={{ color: "#64748b" }}>Chưa có nguồn nào đang chờ duyệt.</p> : <div style={{ display: "grid", gridTemplateColumns: "minmax(200px, .75fr) minmax(350px, 1.5fr)", gap: 14 }}>
        <div style={{ display: "grid", alignContent: "start", gap: 7 }}>{staged.map((item) => <button key={item.id} onClick={() => openStage(item)} style={{ ...styles.mutedButton, textAlign: "left", background: currentStage?.id === item.id ? "#eff6ff" : "white" }}>{item.metadata?.title || item.source?.original_filename || `Nguồn #${item.id}`}<small style={{ display: "block", color: "#64748b", marginTop: 3 }}>{item.source?.source_kind} · {item.questions?.length || 0} câu</small></button>)}</div>
        {currentStage ? <div>
          <h3 style={{ marginTop: 0 }}>{currentStage.metadata?.title || `Nguồn #${currentStage.id}`}</h3>
          {currentStage.source?.source_url && <p><a href={currentStage.source.source_url} target="_blank" rel="noreferrer">Mở URL gốc</a></p>}
          {currentStage.source?.raw_url && <p><a href={`http://127.0.0.1:8000${currentStage.source.raw_url}`} target="_blank" rel="noreferrer">Mở file gốc đã lưu</a> · SHA-256: <code>{currentStage.source.sha256}</code></p>}
          {currentStage.warnings?.map((warning) => <div key={warning} style={styles.warning}>{warning}</div>)}
          {currentStage.duplicates?.map((duplicate, index) => <div key={index} style={styles.warning}>Cảnh báo trùng: {duplicate.match_kind}{duplicate.exam_title ? ` với “${duplicate.exam_title}”` : ""}{duplicate.similarity != null ? ` (${Math.round(duplicate.similarity * 100)}%)` : ""}</div>)}
          <p>{currentStage.questions?.length || 0} câu được nhận diện · nguồn: {currentStage.source?.source_kind}</p>
          {currentStage.source?.source_kind === "user_import" && <div style={{ marginBottom: 10 }}>
            <button style={styles.mutedButton} onClick={() => setEditingQuestions((value) => !value)}>{editingQuestions ? "Ẩn trình sửa câu hỏi" : "Sửa phần trích xuất"}</button>
            {editingQuestions && <div style={{ marginTop: 8 }}>
              <p style={{ color: "#64748b", fontSize: 13 }}>Chỉ sửa dữ liệu câu hỏi đã trích xuất; file/text nguồn gốc được giữ nguyên. Mỗi câu cần có content; answer_status chỉ được xác minh khi candidate_answer có giá trị.</p>
              <textarea aria-label="JSON câu hỏi trích xuất" style={{ ...styles.input, minHeight: 220, fontFamily: "monospace", fontSize: 12 }} value={questionsJson} onChange={(e) => setQuestionsJson(e.target.value)} />
              <button style={{ ...styles.button, marginTop: 7 }} disabled={busy} onClick={saveQuestions}>Lưu phần trích xuất</button>
            </div>}
          </div>}
          <div style={{ maxHeight: 420, overflow: "auto", border: "1px solid #e2e8f0", borderRadius: 8, padding: 10 }}>
            {(currentStage.questions || []).map((question, index) => <article key={`${question.position}-${index}`} style={{ padding: "8px 0", borderBottom: "1px solid #e2e8f0" }}>
              <b>Câu {index + 1} · {question.question_type}</b> {question.answer_status === "verified" && <span style={{ color: "#15803d" }}>· đáp án đã xác minh</span>}
              <div style={{ whiteSpace: "pre-wrap", margin: "5px 0" }}>{question.content}</div>
              {question.options && <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(question.options, null, 2)}</pre>}
              {question.candidate_answer != null && <small>Đáp án trích được (chưa xác minh): {JSON.stringify(question.candidate_answer)}</small>}
              {question.answer_status !== "verified" && <div style={{ display: "flex", gap: 6, marginTop: 6 }}><input style={styles.input} placeholder="Đáp án: A hoặc JSON cho dạng khác" value={answerDrafts[`${currentStage.id}-${index}`] ?? (typeof question.candidate_answer === "object" && question.candidate_answer?.choice ? question.candidate_answer.choice : "")} onChange={(e) => setAnswerDrafts((state) => ({ ...state, [`${currentStage.id}-${index}`]: e.target.value }))} /><button style={styles.mutedButton} disabled={busy} onClick={() => verifyAnswer(currentStage, question, index)}>Xác minh đáp án</button></div>}
            </article>)}
          </div>
          <details style={{ marginTop: 10 }}><summary>Xem text trích xuất nguyên văn</summary><pre style={{ whiteSpace: "pre-wrap", maxHeight: 220, overflow: "auto" }}>{currentStage.raw_payload}</pre></details>
          {currentStage.needsDuplicateConfirmation ? <button style={{ ...styles.button, background: "#b45309", marginTop: 10 }} disabled={busy} onClick={() => publish(currentStage, true)}>Vẫn lưu thành đề riêng</button> : <button style={{ ...styles.button, marginTop: 10 }} disabled={busy} onClick={() => publish(currentStage)}>Xuất bản vào kho đề</button>}
          <button style={{ ...styles.mutedButton, marginLeft: 8, marginTop: 10 }} disabled={busy} onClick={() => reject(currentStage)}>Từ chối nguồn</button>
        </div> : <p style={{ color: "#64748b" }}>Chọn một nguồn để xem trước.</p>}
      </div>}
    </section>
    <p style={{ fontSize: 12, color: "#64748b" }}>File gốc được giữ bất biến. Web search chỉ tìm ứng viên; bạn tự mở và quyết định nguồn. Đề nhập từ Internet không bị diễn đạt lại. Đáp án chỉ dùng để chấm sau khi bạn xác minh.</p>
  </main>;
}

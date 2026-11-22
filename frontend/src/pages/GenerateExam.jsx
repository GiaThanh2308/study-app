import { useCallback, useEffect, useMemo, useState } from "react";
import api from "../api";

const initialDifficulty = { easy: 30, medium: 50, hard: 20 };
const terminal = new Set(["completed_awaiting_review", "failed", "cancelled", "interrupted", "published"]);

export default function GenerateExam() {
  const [blueprints, setBlueprints] = useState([]);
  const [selectedSlug, setSelectedSlug] = useState("");
  const [mode, setMode] = useState("full");
  const [difficulty, setDifficulty] = useState(initialDifficulty);
  const [sectionNames, setSectionNames] = useState([]);
  const [topicIds, setTopicIds] = useState([]);
  const [count, setCount] = useState(5);
  const [title, setTitle] = useState("");
  const [jobs, setJobs] = useState([]);
  const [job, setJob] = useState(null);
  const [review, setReview] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const subject = blueprints.find((item) => item.slug === selectedSlug);
  const selectedJobId = job?.id;

  const loadJobs = useCallback(async () => {
    try {
      const response = await api.get("/generation-jobs");
      setJobs(response.data);
      if (!selectedJobId && response.data.length) setJob(response.data[0]);
    } catch { setJobs([]); }
  }, [selectedJobId]);

  const refreshJob = useCallback(async (id) => {
    if (!id) return;
    try {
      const response = await api.get(`/generation-jobs/${id}`);
      setJob(response.data);
      if (response.data.status === "completed_awaiting_review" && !review) {
        const details = await api.get(`/generation-jobs/${id}/review`);
        setReview(details.data);
        setDrafts(Object.fromEntries(details.data.questions.map((question) => [question.position, question])));
      }
      loadJobs();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Không tải được trạng thái job.");
    }
  }, [loadJobs, review]);

  useEffect(() => {
    api.get("/generation/blueprints").then(({ data }) => {
      setBlueprints(data.subjects || []);
      setSelectedSlug(data.subjects?.[0]?.slug || "");
      if (!data.gemini_configured) setError("Chưa có GEMINI_API_KEY. Thêm key trong backend/.env; StudyApp không tự chuyển sang dịch vụ trả phí.");
    }).catch((requestError) => setError(requestError.response?.data?.detail || "Không tải được ma trận."));
    loadJobs();
  }, []);

  useEffect(() => {
    if (!selectedJobId || terminal.has(job?.status)) return undefined;
    const timer = window.setInterval(() => refreshJob(selectedJobId), 1800);
    return () => window.clearInterval(timer);
  }, [selectedJobId, job?.status, refreshJob]);

  const changeDifficulty = (key, value) => setDifficulty((current) => ({ ...current, [key]: Number(value) }));
  const toggleList = (current, setCurrent, value) => setCurrent(current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);

  const start = async (event) => {
    event.preventDefault();
    setBusy(true); setError(""); setReview(null); setDrafts({});
    try {
      const response = await api.post("/generation-jobs", {
        subject_slug: selectedSlug, mode, title: title || null, difficulty,
        section_names: mode === "focused" ? sectionNames : [],
        topic_ids: mode === "focused" ? topicIds : [], questions_per_section: Number(count),
      });
      setJob(response.data);
      loadJobs();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Không thể bắt đầu tạo đề.");
    } finally { setBusy(false); }
  };

  const openReview = async () => {
    if (!job) return;
    try {
      const { data } = await api.get(`/generation-jobs/${job.id}/review`);
      setReview(data); setDrafts(Object.fromEntries(data.questions.map((question) => [question.position, question])));
      setError("");
    } catch (requestError) { setError(requestError.response?.data?.detail || "Chưa có bản đề để duyệt."); }
  };

  const updateDraft = (position, key, value) => setDrafts((current) => ({ ...current, [position]: { ...current[position], [key]: value, _dirty: true } }));
  const saveQuestion = async (question, confirm = false) => {
    const value = drafts[question.position];
    let answer = value.answer;
    if (question.question_type === "multiple_choice") answer = String(value.answer || "").toUpperCase();
    if (question.question_type === "short_answer") {
      const accepted = typeof value.acceptedInput === "string" ? value.acceptedInput.split(",").map((item) => item.trim()).filter(Boolean) : value.answer?.accepted;
      answer = { accepted: accepted || [], tolerance: value.toleranceInput ?? value.answer?.tolerance ?? "0" };
    }
    setBusy(true); setError("");
    try {
      await api.patch(`/generation-jobs/${job.id}/questions/${question.position}`, {
        content: value.content, options: value.options, answer, explanation: value.explanation, confirm,
      });
      await openReview();
      await refreshJob(job.id);
    } catch (requestError) { setError(requestError.response?.data?.detail || "Không lưu được câu hỏi."); }
    finally { setBusy(false); }
  };

  const confirmAll = async () => {
    setBusy(true); setError("");
    try { await api.post(`/generation-jobs/${job.id}/confirm-all`); await openReview(); }
    catch (requestError) { setError(requestError.response?.data?.detail || "Không xác nhận được đáp án."); }
    finally { setBusy(false); }
  };

  const publish = async () => {
    setBusy(true); setError("");
    try {
      await api.post(`/generation-jobs/${job.id}/publish`);
      await refreshJob(job.id); setReview(null);
      setJob((current) => ({ ...current, status: "published" }));
    } catch (requestError) { setError(requestError.response?.data?.detail || "Chưa thể đưa đề vào kho."); }
    finally { setBusy(false); }
  };

  const jobAction = async (action) => {
    setBusy(true); setError("");
    try { const { data } = await api.post(`/generation-jobs/${job.id}/${action}`); setJob(data); }
    catch (requestError) { setError(requestError.response?.data?.detail || "Thao tác không thành công."); }
    finally { setBusy(false); }
  };

  const summary = useMemo(() => {
    const entries = Object.values(drafts).flatMap((question) => question.assessment_breakdown || []);
    const countBy = (key) => entries.reduce((acc, entry) => ({ ...acc, [entry[key]]: (acc[entry[key]] || 0) + 1 }), {});
    return { prompts: entries.length, grade: countBy("grade"), cognitive: countBy("cognitive_level"), difficulty: countBy("difficulty"), targets: review?.targets || {} };
  }, [drafts, review]);

  const distributionText = (actual, target) => Object.keys({ ...target, ...actual }).sort().map((key) => `${key}: ${actual[key] || 0}/${target[key] || 0}`).join(" · ");

  return <main style={styles.page}>
    <header style={styles.header}><div><h1 style={styles.heading}>Sinh đề theo ma trận</h1><p style={styles.sub}>Đề AI tạo là đề luyện tập, không phải đề chính thức của Bộ.</p></div>
      <span style={styles.model}>Gemini · chạy tuần tự</span></header>
    {error && <div role="alert" style={styles.error}>{error}</div>}
    <div style={styles.grid}>
      <form onSubmit={start} style={styles.panel}>
        <h2 style={styles.panelTitle}>Tạo đề luyện</h2>
        <label style={styles.field}>Môn<select style={styles.input} value={selectedSlug} onChange={(event) => { setSelectedSlug(event.target.value); setSectionNames([]); setTopicIds([]); }}>
          {blueprints.map((item) => <option key={item.slug} value={item.slug}>{item.icon} {item.name}</option>)}</select></label>
        <label style={styles.field}>Kiểu tạo<select style={styles.input} value={mode} onChange={(event) => setMode(event.target.value)}><option value="full">Đề đầy đủ theo ma trận</option><option value="focused">Bộ câu hỏi theo chủ đề</option></select></label>
        <label style={styles.field}>Tên đề<input style={styles.input} value={title} maxLength={300} onChange={(event) => setTitle(event.target.value)} placeholder="Tự đặt nếu muốn" /></label>
        <div style={styles.ratios}><strong>Độ khó luyện tập</strong><span style={styles.note}>Mặc định StudyApp 30/50/20, tách biệt với nhận thức</span>
          {[["easy", "Dễ"], ["medium", "Vừa"], ["hard", "Khó"]].map(([key, label]) => <label key={key} style={styles.ratio}>{label}<input type="number" min="0" max="100" value={difficulty[key]} onChange={(event) => changeDifficulty(key, event.target.value)} />%</label>)}
          <span style={Number(difficulty.easy) + Number(difficulty.medium) + Number(difficulty.hard) === 100 ? styles.ok : styles.bad}>Tổng: {Number(difficulty.easy) + Number(difficulty.medium) + Number(difficulty.hard)}%</span>
        </div>
        {mode === "focused" && subject && <>
          <fieldset style={styles.fieldset}><legend>Phần thi</legend>{subject.sections.map((section) => <label key={section.name} style={styles.check}><input type="checkbox" checked={sectionNames.includes(section.name)} onChange={() => toggleList(sectionNames, setSectionNames, section.name)} />{section.name}</label>)}</fieldset>
          <label style={styles.field}>Số nhóm câu mỗi phần<input style={styles.input} type="number" min="1" max="20" value={count} onChange={(event) => setCount(event.target.value)} /></label>
          <fieldset style={styles.fieldset}><legend>Chủ đề</legend><div style={styles.topicList}>{subject.topics.map((topic) => <label key={topic.id} style={styles.check}><input type="checkbox" checked={topicIds.includes(topic.id)} onChange={() => toggleList(topicIds, setTopicIds, topic.id)} />Lớp {topic.grade} · {topic.name}</label>)}</div></fieldset>
        </>}
        <div style={styles.notice}>Đề đầy đủ: {subject?.question_count} nhóm câu · {subject?.prompt_count} lệnh hỏi được chấm · {subject?.duration_minutes} phút. Độ khó 30/50/20 là preset bạn chọn, không phải tỷ lệ của Bộ.</div>
        <button disabled={busy || Number(difficulty.easy) + Number(difficulty.medium) + Number(difficulty.hard) !== 100 || !selectedSlug} style={styles.primary}>{busy ? "Đang xử lý…" : "Bắt đầu tạo"}</button>
      </form>

      <section style={styles.panel}><h2 style={styles.panelTitle}>Tiến độ / job đã tạo</h2>
        <label style={styles.field}>Chọn job<select style={styles.input} value={job?.id || ""} onChange={(event) => { const next = jobs.find((item) => String(item.id) === event.target.value); setJob(next || null); setReview(null); }}><option value="">Chưa chọn</option>{jobs.map((item) => <option key={item.id} value={item.id}>#{item.id} · {item.status} · {item.model}</option>)}</select></label>
        {job && <><div style={styles.status}>{job.status.replaceAll("_", " ")}</div><p style={styles.note}>{job.progress?.current_section || (job.result_exam_id ? `Bản đề #${job.result_exam_id}` : "Chờ worker")} · {job.progress?.completed || 0}/{job.progress?.total || 0} phần hoàn tất</p>
          {job.error && <div role="alert" style={styles.error}>{job.error}</div>}
          <div style={styles.actions}>{["queued", "running"].includes(job.status) && <button style={styles.secondary} disabled={busy} onClick={() => jobAction("cancel")}>Hủy sau phần hiện tại</button>}
            {["failed", "interrupted", "cancelled"].includes(job.status) && <button style={styles.primary} disabled={busy} onClick={() => jobAction("resume")}>Tiếp tục phần còn thiếu</button>}
            {job.result_exam_id && job.status !== "published" && <button style={styles.secondary} onClick={openReview}>Mở phần duyệt</button>}
            {job.status === "published" && <a href="/exams" style={styles.link}>Mở kho đề →</a>}</div>
        </>}
        {jobs.length === 0 && <p style={styles.note}>Job tạo đề sẽ hiện ở đây và được lưu lại khi bạn tải lại trang.</p>}
      </section>
    </div>

    {review && <section style={styles.review}>
      <div style={styles.reviewHeader}><div><h2 style={styles.panelTitle}>Duyệt đáp án và lời giải</h2><p style={styles.note}>{review.exam.title} · {review.questions.length} nhóm câu · {summary.prompts} lệnh hỏi</p></div>
        <div style={styles.actions}><button style={styles.secondary} disabled={busy || Object.values(drafts).some((draft) => draft._dirty)} onClick={confirmAll}>Tôi đã xem, xác nhận đáp án cả đề</button><button style={styles.primary} disabled={busy || Object.values(drafts).some((draft) => draft._dirty) || review.questions.some((question) => drafts[question.position]?.answer_status !== "verified")} onClick={publish}>Đưa vào kho đề</button></div></div>
      <div style={styles.stats}><span>Nhận thức (thực tế/mục tiêu): {distributionText(summary.cognitive, summary.targets.cognitive_level)}</span><span>Độ khó (thực tế/mục tiêu): {distributionText(summary.difficulty, summary.targets.difficulty)}</span><span>Lớp (thực tế/mục tiêu): {distributionText(summary.grade, summary.targets.grade)}</span></div>
      <p style={styles.notice}>Xem key và lời giải AI ở từng câu. Bạn có thể sửa rồi xác nhận riêng, hoặc xác nhận cả đề sau khi rà. Sau đó app dùng bộ chấm tự động để chấm bài làm của bạn.</p>
      {review.questions.map((question) => {
        const draft = drafts[question.position] || question;
        const setOption = (key, value) => updateDraft(question.position, "options", { ...draft.options, [key]: value });
        const setTF = (index, value) => updateDraft(question.position, "answer", draft.answer.map((item, part) => part === index ? value === "true" : item));
        const shortAccepted = draft.acceptedInput ?? draft.answer?.accepted?.join(", ") ?? "";
        return <article key={question.position} style={styles.question}>
          <div style={styles.qheader}><strong>Câu {question.position} · {question.question_type.replaceAll("_", " ")}</strong><span style={draft.answer_status === "verified" ? styles.verified : styles.unverified}>{draft.answer_status === "verified" ? "Đã xác nhận" : "Chưa xác nhận"}</span></div>
          <label style={styles.field}>Nội dung<textarea style={styles.textarea} value={draft.content} onChange={(event) => updateDraft(question.position, "content", event.target.value)} /></label>
          {question.question_type === "multiple_choice" && <div style={styles.options}>{["A", "B", "C", "D"].map((key) => <label key={key} style={styles.field}>{key}<input style={styles.input} value={draft.options?.[key] || ""} onChange={(event) => setOption(key, event.target.value)} /></label>)}<label style={styles.field}>Đáp án<select style={styles.input} value={draft.answer || ""} onChange={(event) => updateDraft(question.position, "answer", event.target.value)}>{["A", "B", "C", "D"].map((key) => <option key={key} value={key}>{key}</option>)}</select></label></div>}
          {question.question_type === "true_false" && <div style={styles.tfgrid}>{["a", "b", "c", "d"].map((key, index) => <div key={key} style={styles.tfitem}><label style={styles.field}><b>{key})</b><input style={styles.input} value={draft.options?.[key] || ""} onChange={(event) => setOption(key, event.target.value)} /></label><select style={styles.input} value={String(draft.answer?.[index])} onChange={(event) => setTF(index, event.target.value)}><option value="true">Đúng</option><option value="false">Sai</option></select></div>)}</div>}
          {question.question_type === "short_answer" && <div style={styles.options}><label style={styles.field}>Đáp án chấp nhận<input style={styles.input} value={shortAccepted} onChange={(event) => updateDraft(question.position, "acceptedInput", event.target.value)} placeholder="Các giá trị số, cách nhau bởi dấu phẩy" /></label><label style={styles.field}>Sai số cho phép<input style={styles.input} value={draft.toleranceInput ?? draft.answer?.tolerance ?? "0"} onChange={(event) => updateDraft(question.position, "toleranceInput", event.target.value)} /></label></div>}
          <label style={styles.field}>Lời giải<textarea style={styles.textarea} value={draft.explanation || ""} onChange={(event) => updateDraft(question.position, "explanation", event.target.value)} /></label>
          <div style={styles.qfooter}><small>{(draft.assessment_breakdown || []).map((entry, index) => `${entry.topic} · lớp ${entry.grade} · ${entry.cognitive_level} · ${entry.difficulty}`).join(" / ")}</small><div style={styles.actions}><button style={styles.secondary} disabled={busy} onClick={() => saveQuestion(question, false)}>Lưu sửa đổi</button><button style={styles.primary} disabled={busy} onClick={() => saveQuestion(question, true)}>Lưu và xác nhận câu này</button></div></div>
        </article>;
      })}
    </section>}
  </main>;
}

const styles = {
  page: { padding: 24, maxWidth: 1200, margin: "0 auto", color: "#1f2937" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, marginBottom: 20 },
  heading: { margin: 0, fontSize: 26 }, sub: { color: "#64748b", margin: "6px 0 0" }, model: { background: "#eff6ff", color: "#1d4ed8", borderRadius: 20, padding: "8px 12px", whiteSpace: "nowrap" },
  grid: { display: "grid", gridTemplateColumns: "minmax(300px, 1fr) minmax(300px, .8fr)", gap: 16, alignItems: "start" }, panel: { border: "1px solid #e2e8f0", borderRadius: 12, padding: 18, background: "white" }, panelTitle: { margin: "0 0 14px", fontSize: 19 },
  field: { display: "flex", flexDirection: "column", gap: 6, color: "#475569", fontSize: 13, fontWeight: 600, marginBottom: 12 }, input: { border: "1px solid #cbd5e1", borderRadius: 7, padding: "9px 10px", font: "inherit", color: "#1f2937", background: "white" }, textarea: { minHeight: 76, border: "1px solid #cbd5e1", borderRadius: 7, padding: 9, font: "inherit", color: "#1f2937", resize: "vertical" },
  ratios: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8, padding: 12, borderRadius: 9, background: "#f8fafc", marginBottom: 14 }, note: { color: "#64748b", fontSize: 13, margin: "4px 0 10px" }, ratio: { display: "flex", gap: 5, alignItems: "center", fontSize: 13 }, fieldset: { border: "1px solid #e2e8f0", borderRadius: 8, margin: "0 0 12px", padding: 10 }, check: { display: "flex", gap: 7, alignItems: "start", fontSize: 13, padding: "4px 0", color: "#334155" }, topicList: { maxHeight: 230, overflow: "auto" },
  primary: { border: 0, borderRadius: 8, padding: "10px 14px", background: "#2563eb", color: "white", fontWeight: 700, cursor: "pointer" }, secondary: { border: "1px solid #cbd5e1", borderRadius: 8, padding: "9px 12px", background: "white", color: "#334155", fontWeight: 650, cursor: "pointer" }, actions: { display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" },
  notice: { display: "block", background: "#fffbeb", border: "1px solid #fde68a", color: "#92400e", borderRadius: 8, padding: 10, fontSize: 13, margin: "10px 0 14px" }, ok: { color: "#15803d", fontSize: 12 }, bad: { color: "#b91c1c", fontSize: 12 }, error: { padding: 12, marginBottom: 14, background: "#fef2f2", border: "1px solid #fecaca", color: "#b91c1c", borderRadius: 8 }, status: { display: "inline-block", textTransform: "capitalize", padding: "7px 10px", background: "#f1f5f9", borderRadius: 8, fontWeight: 700 }, link: { color: "#2563eb" },
  review: { marginTop: 20, borderTop: "1px solid #e2e8f0", paddingTop: 22 }, reviewHeader: { display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }, stats: { display: "flex", gap: 14, flexWrap: "wrap", color: "#475569", fontSize: 13, padding: 10, background: "#f8fafc", borderRadius: 8 }, question: { marginTop: 12, padding: 15, border: "1px solid #e2e8f0", borderRadius: 10, background: "white" }, qheader: { display: "flex", justifyContent: "space-between", marginBottom: 10 }, verified: { color: "#166534", background: "#dcfce7", borderRadius: 20, padding: "3px 8px", fontSize: 12 }, unverified: { color: "#92400e", background: "#fef3c7", borderRadius: 20, padding: "3px 8px", fontSize: 12 }, options: { display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(145px,1fr))", gap: 8 }, tfgrid: { display: "grid", gap: 8, margin: "10px 0" }, tfitem: { display: "grid", gridTemplateColumns: "1fr 130px", gap: 10, alignItems: "center", background: "#f8fafc", padding: 8, borderRadius: 7, fontSize: 13 }, qfooter: { display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center", marginTop: 8 },
};

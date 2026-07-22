import { useEffect, useMemo, useState } from "react";
import api from "../api";

// 3 môn cố định — sửa danh sách này nếu muốn đổi môn
const FIXED_SUBJECTS = [
  { name: "Toán", icon: "📐", color: "#4f46e5", bg: "#eef1ff" },
  { name: "Lý", icon: "⚡", color: "#b45309", bg: "#fef3e2" },
  { name: "Hóa", icon: "🧪", color: "#0f766e", bg: "#e6f6f4" },
];

const STATUS_MAP = {
  pending: { text: "Chưa xử lý", color: "#697180", bg: "#eef0f4", dot: "#a0a8b8" },
  processing: { text: "Đang xử lý", color: "#b45309", bg: "#fef3e2", dot: "#f59e0b" },
  ready: { text: "Sẵn sàng", color: "#0f766e", bg: "#e6f6f4", dot: "#0d9488" },
  error: { text: "Lỗi xử lý", color: "#b91c1c", bg: "#fdeceb", dot: "#e53e3e" },
};

function StatusBadge({ status }) {
  const s = STATUS_MAP[status] || STATUS_MAP.pending;
  return (
    <span style={{ ...styles.badge, color: s.color, background: s.bg }}>
      <span style={{ ...styles.badgeDot, background: s.dot }} />
      {s.text}
    </span>
  );
}

export default function Subjects() {
  const [tree, setTree] = useState([]);
  const [ready, setReady] = useState(false);
  const [selectedSubjectId, setSelectedSubjectId] = useState(null);
  const [expandedChapter, setExpandedChapter] = useState(null);
  const [newChapterName, setNewChapterName] = useState({});
  const [newLessonTitle, setNewLessonTitle] = useState({});
  const [ragStatuses, setRagStatuses] = useState({});
  const [ragProgress, setRagProgress] = useState({});
  const [videoRagStatuses, setVideoRagStatuses] = useState({});
  const [videoRagProgress, setVideoRagProgress] = useState({});

  const loadTree = async () => {
    const res = await api.get("/tree");
    setTree(res.data);
    return res.data;
  };

  // Đảm bảo luôn tồn tại đúng 3 môn cố định — tạo hộ nếu backend chưa có
  const ensureFixedSubjects = async () => {
    const current = await loadTree();
    const existingNames = new Set(current.map((s) => s.name));
    const missing = FIXED_SUBJECTS.filter((s) => !existingNames.has(s.name));
    if (missing.length > 0) {
      await Promise.all(missing.map((s) => api.post("/subjects", { name: s.name })));
      await loadTree();
    }
    setReady(true);
  };

  useEffect(() => {
    ensureFixedSubjects();
  }, []);

  const addChapter = async (subjectId) => {
    const name = newChapterName[subjectId];
    if (!name?.trim()) return;
    await api.post("/chapters", { subject_id: subjectId, name });
    setNewChapterName({ ...newChapterName, [subjectId]: "" });
    loadTree();
  };

  const addLesson = async (chapterId) => {
    const title = newLessonTitle[chapterId];
    if (!title?.trim()) return;
    await api.post("/lessons", { chapter_id: chapterId, title });
    setNewLessonTitle({ ...newLessonTitle, [chapterId]: "" });
    loadTree();
  };

  const processVideo = async (videoId) => {
    await api.post(`/video/process/${videoId}`);
    setVideoRagStatuses((prev) => ({ ...prev, [videoId]: "processing" }));
    pollVideoStatus(videoId);
  };

  const pollVideoStatus = (videoId) => {
    const interval = setInterval(async () => {
      const res = await api.get(`/video/status/${videoId}`);
      const { status, percent, eta_seconds, current_time, total_time } = res.data;
      setVideoRagStatuses((prev) => ({ ...prev, [videoId]: status }));
      if (percent !== undefined) {
        setVideoRagProgress((prev) => ({
          ...prev,
          [videoId]: { percent, eta_seconds, current_time, total_time },
        }));
      }
      if (status === "ready" || status === "error") {
        clearInterval(interval);
        setVideoRagProgress((prev) => {
          const updated = { ...prev };
          delete updated[videoId];
          return updated;
        });
      }
    }, 2000);
  };

  const processDocument = async (documentId) => {
    await api.post(`/rag/process/${documentId}`);
    setRagStatuses((prev) => ({ ...prev, [documentId]: "processing" }));
    pollStatus(documentId);
  };

  const pollStatus = (documentId) => {
    const interval = setInterval(async () => {
      const res = await api.get(`/rag/status/${documentId}`);
      const { status, percent, eta_seconds, current_page, total_pages } = res.data;
      setRagStatuses((prev) => ({ ...prev, [documentId]: status }));
      if (percent !== undefined) {
        setRagProgress((prev) => ({
          ...prev,
          [documentId]: { percent, eta_seconds, current_page, total_pages },
        }));
      }
      if (status === "ready" || status === "error") {
        clearInterval(interval);
        setRagProgress((prev) => {
          const updated = { ...prev };
          delete updated[documentId];
          return updated;
        });
      }
    }, 2000);
  };

  const formatEta = (seconds) => {
    if (seconds === null || seconds === undefined) return "đang tính...";
    if (seconds < 60) return `~${seconds} giây`;
    const minutes = Math.round(seconds / 60);
    return `~${minutes} phút`;
  };

  const uploadFile = async (lessonId, file, type) => {
    const formData = new FormData();
    formData.append("lesson_id", lessonId);
    formData.append("file", file);
    if (type === "video") {
      await api.post("/upload/video", formData);
    } else {
      formData.append("doc_type", type === "exam" ? "exam" : "pdf");
      await api.post("/upload/document", formData);
    }
    loadTree();
  };

  // Map tên môn cố định -> dữ liệu thật từ backend (theo đúng tên)
  const subjectBoxes = useMemo(
    () => FIXED_SUBJECTS.map((fixed) => ({ ...fixed, data: tree.find((s) => s.name === fixed.name) })),
    [tree]
  );

  const selectedSubject = tree.find((s) => s.id === selectedSubjectId);

  if (!ready) return <div style={styles.loading}>Đang chuẩn bị môn học...</div>;

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div style={styles.eyebrow}>Quản lý nội dung học</div>
        <h1 style={styles.title}>Môn học</h1>
      </div>

      {/* 3 hộp môn cố định */}
      <div style={styles.subjectGrid}>
        {subjectBoxes.map((box) => {
          const isSelected = box.data && box.data.id === selectedSubjectId;
          const chapterCount = box.data ? box.data.chapters.length : 0;
          return (
            <button
              key={box.name}
              onClick={() => box.data && setSelectedSubjectId(isSelected ? null : box.data.id)}
              style={{
                ...styles.subjectBox,
                borderColor: isSelected ? box.color : "var(--color-border)",
                boxShadow: isSelected
                  ? `0 0 0 3px ${box.bg}, 0 8px 20px -10px rgba(30,36,51,0.25)`
                  : "0 1px 2px rgba(30,36,51,0.04)",
              }}
            >
              <span style={{ ...styles.subjectBoxIcon, background: box.bg }}>{box.icon}</span>
              <span style={styles.subjectBoxName}>{box.name}</span>
              <span style={styles.subjectBoxMeta}>{chapterCount} chương</span>
            </button>
          );
        })}
      </div>

      {!selectedSubject && (
        <div style={styles.hintBox}>
          👆 Chọn 1 môn học ở trên để xem chương, bài học và tải tài liệu.
        </div>
      )}

      {selectedSubject && (
        <div style={styles.detailCard}>
          <div style={styles.detailHeader}>
            <h3 style={styles.detailTitle}>{selectedSubject.name}</h3>
          </div>

          <div style={styles.addChapterBar}>
            <input
              placeholder="+ Tên chương mới..."
              value={newChapterName[selectedSubject.id] || ""}
              onChange={(e) =>
                setNewChapterName({ ...newChapterName, [selectedSubject.id]: e.target.value })
              }
              onKeyDown={(e) => e.key === "Enter" && addChapter(selectedSubject.id)}
              style={styles.addChapterInput}
            />
            <button onClick={() => addChapter(selectedSubject.id)} style={styles.primaryBtn}>
              + Thêm chương
            </button>
          </div>

          {selectedSubject.chapters.map((chapter) => {
            const isOpen = expandedChapter === chapter.id;
            return (
              <div key={chapter.id} style={styles.chapterCard}>
                <div
                  style={styles.chapterHeader}
                  onClick={() => setExpandedChapter(isOpen ? null : chapter.id)}
                >
                  <span style={{ ...styles.chevron, transform: isOpen ? "rotate(90deg)" : "none" }}>
                    ›
                  </span>
                  <span style={styles.chapterName}>{chapter.name}</span>
                  <span style={styles.chapterCount}>{chapter.lessons.length} bài</span>
                </div>

                {isOpen && (
                  <div style={styles.lessonList}>
                    {chapter.lessons.map((lesson) => (
                      <div key={lesson.id} style={styles.lessonCard}>
                        <div style={styles.lessonHeader}>
                          <span style={styles.lessonTitle}>{lesson.title}</span>
                          <span style={styles.lessonMeta}>
                            {lesson.videos.length} video · {lesson.documents.length} tài liệu
                          </span>
                        </div>

                        {lesson.videos.map((v) => {
                          const vStatus = videoRagStatuses[v.id] || v.rag_status || "pending";
                          const vProgress = videoRagProgress[v.id];
                          return (
                            <div key={v.id} style={styles.fileBlock}>
                              <div style={styles.fileRow}>
                                <span style={styles.fileName}>🎥 {v.original_filename}</span>
                                <StatusBadge status={vStatus} />
                                <button style={styles.processBtn} onClick={() => processVideo(v.id)}>
                                  {vStatus === "ready" ? "Xử lý lại" : "Xử lý AI"}
                                </button>
                              </div>
                              {vStatus === "processing" && vProgress && (
                                <div style={styles.progressWrap}>
                                  <div style={styles.progressBarBg}>
                                    <div
                                      style={{
                                        ...styles.progressBarFill,
                                        width: `${vProgress.percent}%`,
                                      }}
                                    />
                                  </div>
                                  <div style={styles.progressText}>
                                    {vProgress.percent}% ({vProgress.current_time}/{vProgress.total_time}) ·
                                    còn {formatEta(vProgress.eta_seconds)}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}

                        {lesson.documents.map((doc) => {
                          const status = ragStatuses[doc.id] || doc.rag_status || "pending";
                          const progress = ragProgress[doc.id];
                          return (
                            <div key={doc.id} style={styles.fileBlock}>
                              <div style={styles.fileRow}>
                                <span style={styles.fileName}>📄 {doc.original_filename}</span>
                                <StatusBadge status={status} />
                                <button
                                  style={styles.processBtn}
                                  onClick={() => processDocument(doc.id)}
                                >
                                  {status === "ready"
                                    ? "Xử lý lại"
                                    : status === "processing"
                                    ? "Xử lý lại từ đầu"
                                    : "Xử lý AI"}
                                </button>
                              </div>
                              {status === "processing" && progress && (
                                <div style={styles.progressWrap}>
                                  <div style={styles.progressBarBg}>
                                    <div
                                      style={{
                                        ...styles.progressBarFill,
                                        width: `${progress.percent}%`,
                                      }}
                                    />
                                  </div>
                                  <div style={styles.progressText}>
                                    {progress.percent}% (trang {progress.current_page}/
                                    {progress.total_pages}) · còn {formatEta(progress.eta_seconds)}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}

                        <div style={styles.uploadRow}>
                          <label style={styles.uploadLabel}>
                            + Video
                            <input
                              type="file"
                              accept=".mp4,.mkv,.avi,.mov"
                              hidden
                              onChange={(e) => uploadFile(lesson.id, e.target.files[0], "video")}
                            />
                          </label>
                          <label style={styles.uploadLabel}>
                            + PDF/DOCX
                            <input
                              type="file"
                              accept=".pdf,.docx"
                              hidden
                              onChange={(e) => uploadFile(lesson.id, e.target.files[0], "pdf")}
                            />
                          </label>
                          <label style={styles.uploadLabel}>
                            + Đề thi
                            <input
                              type="file"
                              accept=".pdf,.docx"
                              hidden
                              onChange={(e) => uploadFile(lesson.id, e.target.files[0], "exam")}
                            />
                          </label>
                        </div>
                      </div>
                    ))}

                    <div style={styles.inlineAddRow}>
                      <input
                        placeholder="Tên bài học mới"
                        value={newLessonTitle[chapter.id] || ""}
                        onChange={(e) =>
                          setNewLessonTitle({ ...newLessonTitle, [chapter.id]: e.target.value })
                        }
                        onKeyDown={(e) => e.key === "Enter" && addLesson(chapter.id)}
                        style={styles.inputSmall}
                      />
                      <button onClick={() => addLesson(chapter.id)} style={styles.secondaryBtn}>
                        + Thêm bài
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const styles = {
  page: {
    padding: "28px 32px 48px",
    maxWidth: 1040,
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    color: "var(--color-text)",
  },
  loading: { padding: 24, color: "var(--color-text-muted)" },
  header: { marginBottom: 20 },
  eyebrow: { fontSize: 13, color: "var(--color-text-muted)", marginBottom: 4 },
  title: { fontSize: 28, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" },

  subjectGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: 14,
    marginBottom: 20,
  },
  subjectBox: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: 10,
    background: "var(--color-surface)",
    border: "2px solid var(--color-border)",
    borderRadius: 16,
    padding: "18px 20px",
    cursor: "pointer",
    textAlign: "left",
    transition: "box-shadow 0.15s ease, border-color 0.15s ease",
    font: "inherit",
    color: "inherit",
  },
  subjectBoxIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 19,
  },
  subjectBoxName: { fontSize: 17, fontWeight: 700 },
  subjectBoxMeta: { fontSize: 12.5, color: "var(--color-text-muted)", fontWeight: 500 },

  hintBox: {
    textAlign: "center",
    padding: "40px 24px",
    background: "var(--color-surface)",
    border: "1px dashed var(--color-border)",
    borderRadius: 14,
    color: "var(--color-text-muted)",
    fontSize: 14,
  },

  detailCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: 16,
    padding: 22,
    boxShadow: "0 1px 2px rgba(30,36,51,0.04)",
  },
  detailHeader: { marginBottom: 14 },
  detailTitle: { fontSize: 18, fontWeight: 700, margin: 0 },
  addChapterBar: {
    display: "flex",
    gap: 8,
    marginBottom: 16,
    padding: 10,
    background: "var(--color-bg)",
    border: "1px dashed var(--color-border)",
    borderRadius: 10,
  },
  addChapterInput: {
    flex: 1,
    padding: "9px 12px",
    border: "1px solid var(--color-border)",
    borderRadius: 8,
    fontSize: 13.5,
    outline: "none",
    background: "var(--color-surface)",
    color: "var(--color-text)",
  },

  chapterCard: {
    background: "var(--color-bg)",
    borderRadius: 12,
    padding: "12px 14px",
    marginTop: 10,
  },
  chapterHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    cursor: "pointer",
    userSelect: "none",
  },
  chevron: {
    display: "inline-block",
    fontSize: 18,
    color: "var(--color-text-muted)",
    transition: "transform 0.15s ease",
    width: 12,
  },
  chapterName: { fontWeight: 600, fontSize: 14.5, flex: 1 },
  chapterCount: { fontSize: 12, color: "var(--color-text-muted)" },

  lessonList: { marginTop: 10, display: "flex", flexDirection: "column", gap: 8 },
  lessonCard: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: 10,
    padding: 14,
  },
  lessonHeader: { display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 },
  lessonTitle: { fontWeight: 600, fontSize: 14 },
  lessonMeta: { fontSize: 12, color: "var(--color-text-muted)" },

  fileBlock: { marginBottom: 6 },
  fileRow: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    fontSize: 13,
    padding: "6px 0",
  },
  fileName: { flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  badge: {
    fontSize: 11.5,
    padding: "3px 10px",
    borderRadius: 20,
    fontWeight: 600,
    display: "inline-flex",
    alignItems: "center",
    gap: 5,
    whiteSpace: "nowrap",
  },
  badgeDot: { width: 6, height: 6, borderRadius: "50%", display: "inline-block" },
  processBtn: {
    fontSize: 11.5,
    padding: "5px 12px",
    background: "#1e2433",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    fontWeight: 600,
    whiteSpace: "nowrap",
  },

  progressWrap: { margin: "2px 0 8px" },
  progressBarBg: {
    width: "100%",
    height: 6,
    background: "var(--color-border)",
    borderRadius: 3,
    overflow: "hidden",
  },
  progressBarFill: {
    height: "100%",
    background: "linear-gradient(90deg, #0d9488, #14b8a6)",
    transition: "width 0.3s ease",
  },
  progressText: { fontSize: 11, color: "var(--color-text-muted)", marginTop: 3 },

  uploadRow: { display: "flex", gap: 8, marginTop: 8 },
  uploadLabel: {
    fontSize: 12,
    padding: "6px 12px",
    background: "var(--color-bg)",
    color: "var(--color-text-muted)",
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: 600,
  },

  inlineAddRow: { display: "flex", gap: 8, marginTop: 12 },
  inputSmall: {
    flex: 1,
    padding: "9px 12px",
    border: "1px solid var(--color-border)",
    borderRadius: 8,
    fontSize: 13.5,
    outline: "none",
  },
  primaryBtn: {
    padding: "0 18px",
    background: "#4f46e5",
    color: "#fff",
    border: "none",
    borderRadius: 10,
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 14,
  },
  secondaryBtn: {
    padding: "0 16px",
    background: "#0d9488",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: 600,
    fontSize: 13,
  },
};

import { useEffect, useState } from "react";
import api from "../api";

function statusBadge(status) {
  const map = {
    pending: { text: "Chưa xử lý", color: "#a0aec0", bg: "#f7fafc" },
    processing: { text: "⏳ Đang xử lý...", color: "#c05621", bg: "#fffaf0" },
    ready: { text: "✅ Sẵn sàng", color: "#276749", bg: "#f0fff4" },
    error: { text: "❌ Lỗi xử lý", color: "#c53030", bg: "#fff5f5" },
  };
  const s = map[status] || map.pending;
  return (
    <span
      style={{
        fontSize: 11,
        padding: "2px 8px",
        borderRadius: 4,
        color: s.color,
        background: s.bg,
      }}
    >
      {s.text}
    </span>
  );
}

export default function Subjects() {
  const [tree, setTree] = useState([]);
  const [newSubject, setNewSubject] = useState("");
  const [expandedChapter, setExpandedChapter] = useState(null);
  const [newChapterName, setNewChapterName] = useState({});
  const [newLessonTitle, setNewLessonTitle] = useState({});
  const [ragStatuses, setRagStatuses] = useState({}); // { [documentId]: "pending"|"processing"|"ready"|"error" }
  const [ragProgress, setRagProgress] = useState({}); // { [documentId]: { percent, eta_seconds, current_page, total_pages } }
  const [videoRagStatuses, setVideoRagStatuses] = useState({});
  const [videoRagProgress, setVideoRagProgress] = useState({});

  const loadTree = async () => {
    const res = await api.get("/tree");
    setTree(res.data);
  };

  useEffect(() => {
    loadTree();
  }, []);

  const addSubject = async () => {
    if (!newSubject.trim()) return;
    await api.post("/subjects", { name: newSubject });
    setNewSubject("");
    loadTree();
  };

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
    }, 2000); // hỏi lại mỗi 2 giây
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

  return (
    <div className="page">
      <h2>Môn học</h2>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <input
          placeholder="Tên môn học mới (VD: Toán)"
          value={newSubject}
          onChange={(e) => setNewSubject(e.target.value)}
          style={styles.input}
        />
        <button onClick={addSubject} style={styles.btn}>+ Thêm môn</button>
      </div>

      {tree.map((subject) => (
        <div key={subject.id} style={styles.subjectCard}>
          <h3>📘 {subject.name}</h3>

          {subject.chapters.map((chapter) => (
            <div key={chapter.id} style={styles.chapterCard}>
              <div
                style={{ cursor: "pointer", fontWeight: 600 }}
                onClick={() =>
                  setExpandedChapter(
                    expandedChapter === chapter.id ? null : chapter.id
                  )
                }
              >
                📂 {chapter.name} ({chapter.lessons.length} bài)
              </div>

              {expandedChapter === chapter.id && (
                <div style={{ marginLeft: 16, marginTop: 8 }}>
                  {chapter.lessons.map((lesson) => (
                    <div key={lesson.id} style={styles.lessonCard}>
                      <div>📄 {lesson.title}</div>
                      <div style={{ fontSize: 12, color: "#666", margin: "4px 0" }}>
                        {lesson.videos.length} video · {lesson.documents.length} tài liệu
                      </div>

                      {lesson.videos.map((v) => {
                        const vStatus = videoRagStatuses[v.id] || v.rag_status || "pending";
                        const vProgress = videoRagProgress[v.id];
                        return (
                          <div key={v.id}>
                            <div style={styles.docRow}>
                              🎥 {v.original_filename}
                              {statusBadge(vStatus)}
                              <button style={styles.smallBtn} onClick={() => processVideo(v.id)}>
                                {vStatus === "ready" ? "Xử lý lại" : "Xử lý AI"}
                              </button>
                            </div>
                            {vStatus === "processing" && vProgress && (
                              <div style={styles.progressWrap}>
                                <div style={styles.progressBarBg}>
                                  <div style={{ ...styles.progressBarFill, width: `${vProgress.percent}%` }} />
                                </div>
                                <div style={styles.progressText}>
                                  {vProgress.percent}% ({vProgress.current_time}/{vProgress.total_time}) ·
                                  {" "}còn {formatEta(vProgress.eta_seconds)}
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
                          <div key={doc.id}>
                            <div style={styles.docRow}>
                              📄 {doc.original_filename}
                              {statusBadge(status)}
                              <button
                                style={styles.smallBtn}
                                onClick={() => processDocument(doc.id)}
                              >
                                {status === "ready" ? "Xử lý lại" : status === "processing" ? "Xử lý lại từ đầu" : "Xử lý AI"}
                              </button>
                            </div>
                            {status === "processing" && progress && (
                              <div style={styles.progressWrap}>
                                <div style={styles.progressBarBg}>
                                  <div style={{ ...styles.progressBarFill, width: `${progress.percent}%` }} />
                                </div>
                                <div style={styles.progressText}>
                                  {progress.percent}% (trang {progress.current_page}/{progress.total_pages}) ·
                                  {" "}còn {formatEta(progress.eta_seconds)}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                      <div style={{ display: "flex", gap: 8 }}>
                        <label style={styles.uploadLabel}>
                          + Video
                          <input
                            type="file"
                            accept=".mp4,.mkv,.avi,.mov"
                            hidden
                            onChange={(e) =>
                              uploadFile(lesson.id, e.target.files[0], "video")
                            }
                          />
                        </label>
                        <label style={styles.uploadLabel}>
                          + PDF
                          <input
                            type="file"
                            accept=".pdf"
                            hidden
                            onChange={(e) =>
                              uploadFile(lesson.id, e.target.files[0], "pdf")
                            }
                          />
                        </label>
                        <label style={styles.uploadLabel}>
                          + Đề thi
                          <input
                            type="file"
                            accept=".pdf"
                            hidden
                            onChange={(e) =>
                              uploadFile(lesson.id, e.target.files[0], "exam")
                            }
                          />
                        </label>
                      </div>
                    </div>
                  ))}

                  <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                    <input
                      placeholder="Tên bài học mới"
                      value={newLessonTitle[chapter.id] || ""}
                      onChange={(e) =>
                        setNewLessonTitle({
                          ...newLessonTitle,
                          [chapter.id]: e.target.value,
                        })
                      }
                      style={styles.input}
                    />
                    <button onClick={() => addLesson(chapter.id)} style={styles.btn}>
                      + Thêm bài
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}

          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <input
              placeholder="Tên chương mới"
              value={newChapterName[subject.id] || ""}
              onChange={(e) =>
                setNewChapterName({ ...newChapterName, [subject.id]: e.target.value })
              }
              style={styles.input}
            />
            <button onClick={() => addChapter(subject.id)} style={styles.btn}>
              + Thêm chương
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

const styles = {
  input: { padding: "9px 12px", border: "1px solid #cbd5e0", borderRadius: 8, flex: 1, fontSize: 14 },
  btn: {
    padding: "9px 16px",
    background: "var(--color-primary)",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 500,
  },
  subjectCard: {
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius)",
    boxShadow: "var(--shadow-sm)",
    padding: 18,
    marginBottom: 16,
    background: "#fff",
  },
  chapterCard: {
    background: "var(--color-bg)",
    borderRadius: 8,
    padding: 12,
    marginTop: 10,
    border: "1px solid transparent",
  },
  lessonCard: {
    background: "#fff",
    border: "1px solid var(--color-border)",
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  uploadLabel: {
    fontSize: 12,
    padding: "4px 10px",
    background: "#edf2f7",
    borderRadius: 4,
    cursor: "pointer",
  },
  docRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: 13,
    padding: "4px 0",
  },
  smallBtn: {
    fontSize: 11,
    padding: "3px 8px",
    background: "#38a169",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
  },
  progressWrap: {
    margin: "4px 0 8px",
  },
  progressBarBg: {
    width: "100%",
    height: 6,
    background: "#e2e8f0",
    borderRadius: 3,
    overflow: "hidden",
  },
  progressBarFill: {
    height: "100%",
    background: "#3182ce",
    transition: "width 0.3s ease",
  },
  progressText: {
    fontSize: 11,
    color: "#718096",
    marginTop: 3,
  },
};

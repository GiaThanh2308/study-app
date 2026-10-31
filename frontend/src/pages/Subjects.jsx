import { useEffect, useState } from "react";
import api from "../api";

export default function Subjects() {
  const [tree, setTree] = useState([]);
  const [newSubject, setNewSubject] = useState("");
  const [expandedChapter, setExpandedChapter] = useState(null);
  const [newChapterName, setNewChapterName] = useState({});
  const [newLessonTitle, setNewLessonTitle] = useState({});

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

  const uploadFile = async (lessonId, file, type) => {
    const formData = new FormData();
    formData.append("lesson_id", lessonId);
    formData.append("file", file);
    if (type === "video") {
      await api.post("/upload/video", formData);
    } else {
      formData.append("doc_type", "pdf");
      await api.post("/upload/document", formData);
    }
    loadTree();
  };

  return (
    <div style={{ padding: 24 }}>
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
  input: { padding: 8, border: "1px solid #cbd5e0", borderRadius: 6, flex: 1 },
  btn: {
    padding: "8px 14px",
    background: "#3182ce",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
  },
  subjectCard: {
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
  },
  chapterCard: {
    background: "#f7fafc",
    borderRadius: 6,
    padding: 12,
    marginTop: 8,
  },
  lessonCard: {
    background: "#fff",
    border: "1px solid #edf2f7",
    borderRadius: 6,
    padding: 10,
    marginBottom: 6,
  },
  uploadLabel: {
    fontSize: 12,
    padding: "4px 10px",
    background: "#edf2f7",
    borderRadius: 4,
    cursor: "pointer",
  },
};

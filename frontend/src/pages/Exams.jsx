import { useEffect, useState } from "react";
import api from "../api";
import { useNavigate } from "react-router-dom";
import MathView from "../components/MathView";

export default function Exams() {
  const [subjects, setSubjects] = useState([]);
  const [exams, setExams] = useState([]);
  const [counter, setCounter] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  
  // Chế độ xem: "hierarchy" (Phân cấp 3 miền) hoặc "flat" (Tất cả đề)
  const [viewMode, setViewMode] = useState("hierarchy");

  // Dữ liệu phân cấp
  const [regions, setRegions] = useState([]);
  const [selectedRegionId, setSelectedRegionId] = useState(null);
  const [provinces, setProvinces] = useState([]);
  const [selectedProvinceId, setSelectedProvinceId] = useState(null);
  const [schools, setSchools] = useState([]);
  const [selectedSchoolId, setSelectedSchoolId] = useState(null);
  const [schoolExamData, setSchoolExamData] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [onlyProvincesWithExams, setOnlyProvincesWithExams] = useState(false);

  // Modal AI Harvester & Form tạo đề
  const [showCreate, setShowCreate] = useState(false);
  const [showWebHarvester, setShowWebHarvester] = useState(false);
  const [harvesting, setHarvesting] = useState(false);
  const [harvestForm, setHarvestForm] = useState({
    subject_id: 1,
    topic_query: "Đề thi thử THPT Quốc gia 2026 môn Toán",
    web_url: "",
    province: "",
    school_or_dept: "",
    exam_category: "mock",
  });

  // State cho tính năng Quét 1-Click Toàn Quốc (Toán · Lý · Hóa) & Chống trùng lặp
  const [batchSyncing, setBatchSyncing] = useState(false);
  const [batchResult, setBatchResult] = useState(null);
  const [showBatchModal, setShowBatchModal] = useState(false);

  const navigate = useNavigate();

  // Load danh sách môn học, bộ đếm, đề thi phẳng và cây phân cấp 3 miền
  useEffect(() => {
    api.get("/subjects").then((r) => {
      setSubjects(r.data);
      if (r.data.length > 0) {
        setHarvestForm((prev) => ({ ...prev, subject_id: r.data[0].id }));
      }
    });
    loadExams();
    api.get("/exam-counter").then((r) => setCounter(r.data));
    loadRegions();
  }, []);

  const loadExams = (subjectId = null) => {
    const url = subjectId ? `/exams?subject_id=${subjectId}` : "/exams";
    api.get(url).then((r) => setExams(r.data));
  };

  const loadRegions = async () => {
    try {
      const res = await api.get("/hierarchy/regions");
      setRegions(res.data);
      if (res.data.length > 0 && !selectedRegionId) {
        // Mặc định chọn Miền Bắc
        selectRegion(res.data[0].id);
      }
    } catch (err) {
      console.error("Lỗi tải danh sách miền:", err);
    }
  };

  // Chọn Miền -> tải danh sách Tỉnh
  const selectRegion = async (regionId) => {
    setSelectedRegionId(regionId);
    setSelectedProvinceId(null);
    setSelectedSchoolId(null);
    setSchoolExamData(null);
    try {
      const res = await api.get(`/hierarchy/regions/${regionId}/provinces`);
      setProvinces(res.data);
      // Nếu có tỉnh có đề thi, tự động chọn tỉnh đầu tiên có đề
      const provWithExams = res.data.find((p) => p.exam_count > 0);
      if (provWithExams) {
        selectProvince(provWithExams.id);
      } else if (res.data.length > 0) {
        selectProvince(res.data[0].id);
      }
    } catch (err) {
      console.error("Lỗi tải danh sách tỉnh:", err);
    }
  };

  // Chọn Tỉnh -> tải danh sách Trường
  const selectProvince = async (provinceId) => {
    setSelectedProvinceId(provinceId);
    setSelectedSchoolId(null);
    setSchoolExamData(null);
    try {
      const res = await api.get(`/hierarchy/provinces/${provinceId}/schools`);
      setSchools(res.data);
      if (res.data.length > 0) {
        selectSchool(res.data[0].id);
      }
    } catch (err) {
      console.error("Lỗi tải danh sách trường:", err);
    }
  };

  // Chọn Trường -> tải danh sách Đề thi theo phân loại
  const selectSchool = async (schoolId, cat = "all") => {
    setSelectedSchoolId(schoolId);
    setSelectedCategory(cat);
    try {
      const subParam = selectedSubject ? `&subject_id=${selectedSubject}` : "";
      const catParam = cat !== "all" ? `&category=${cat}` : "";
      const res = await api.get(`/hierarchy/schools/${schoolId}/exams?_t=${Date.now()}${subParam}${catParam}`);
      setSchoolExamData(res.data);
    } catch (err) {
      console.error("Lỗi tải đề thi của trường:", err);
    }
  };

  const filterBySubject = (subjectId) => {
    setSelectedSubject(subjectId);
    loadExams(subjectId);
    if (selectedSchoolId) {
      selectSchool(selectedSchoolId, selectedCategory);
    }
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
    if (!window.confirm("Xóa đề thi này khỏi hệ thống?")) return;
    await api.delete(`/exams/${examId}`);
    loadExams(selectedSubject);
    api.get("/exam-counter").then((r) => setCounter(r.data));
    loadRegions();
    if (selectedSchoolId) {
      selectSchool(selectedSchoolId, selectedCategory);
    }
  };

  // Mở modal cào đề và gán sẵn Tỉnh / Trường hiện tại
  const openHarvesterForSchool = (schoolName, provinceName) => {
    setHarvestForm({
      ...harvestForm,
      topic_query: `Đề thi thử THPT 2026 ${schoolName} ${provinceName}`,
      province: provinceName,
      school_or_dept: schoolName,
      exam_category: "mock",
    });
    setShowWebHarvester(true);
  };

  // AI Cào đề từ Internet
  const handleHarvestFromWeb = async () => {
    if (!harvestForm.topic_query.trim() && !harvestForm.web_url.trim()) {
      return alert("Vui lòng nhập từ khóa tìm kiếm hoặc dán đường dẫn file PDF / link tài liệu!");
    }
    setHarvesting(true);
    try {
      const res = await api.post("/exams/harvest-from-web", harvestForm);
      alert(res.data.message);
      setShowWebHarvester(false);
      loadExams(selectedSubject);
      api.get("/exam-counter").then((r) => setCounter(r.data));
      loadRegions();
      if (selectedSchoolId) {
        selectSchool(selectedSchoolId, selectedCategory);
      }
      if (window.confirm("🎉 Thu thập thành công! Bạn có muốn vào làm bài ngay không?")) {
        startExam(res.data.exam_id);
      }
    } catch (err) {
      alert("Lỗi khi thu thập đề từ mạng: " + (err.response?.data?.detail || err.message));
    } finally {
      setHarvesting(false);
    }
  };

  // 1-Click Quét & Đồng Bộ Kho Đề Toàn Quốc (Toán · Lý · Hóa) & Chống trùng lặp
  const handleBatchSyncNationwide = async () => {
    setBatchSyncing(true);
    setBatchResult(null);
    setShowBatchModal(true);
    try {
      const res = await api.post("/exams/batch-sync-nationwide");
      setBatchResult(res.data);
      loadExams(selectedSubject);
      api.get("/exam-counter").then((r) => setCounter(r.data));
      loadRegions();
      if (selectedSchoolId) {
        selectSchool(selectedSchoolId, selectedCategory);
      }
    } catch (err) {
      alert("Lỗi khi quét kho đề toàn quốc: " + (err.response?.data?.detail || err.message));
      setShowBatchModal(false);
    } finally {
      setBatchSyncing(false);
    }
  };

  // Lọc tỉnh hiển thị
  const filteredProvinces = onlyProvincesWithExams
    ? provinces.filter((p) => p.exam_count > 0)
    : provinces;

  const currentProvince = provinces.find((p) => p.id === selectedProvinceId);
  const currentSchool = schools.find((s) => s.id === selectedSchoolId);

  return (
    <div style={{ padding: 24, maxWidth: 1300, margin: "0 auto" }}>
      {/* HEADER & HÀNH ĐỘNG CHÍNH */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h2 style={{ margin: "0 0 4px 0", color: "#1a202c" }}>🏛️ Kho Đề Thi Phân Cấp & Ôn Luyện</h2>
          <p style={{ margin: 0, fontSize: 13, color: "#718096" }}>
            Hệ thống phân cấp 3 Miền (Bắc - Trung - Nam) · 63 Tỉnh Thành · Trường THPT & Sở GD&ĐT · Chuẩn cấu trúc GDPT 2018 (22 câu)
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            style={styles.batchBtn}
            onClick={handleBatchSyncNationwide}
            disabled={batchSyncing}
          >
            ⚡ {batchSyncing ? "⏳ Đang cào đề từ Internet..." : "1-Click: Cào Đề Mới Từ Internet (Toán · Lý · Hóa)"}
          </button>
          <button style={styles.harvestBtn} onClick={() => setShowWebHarvester(true)}>
            🌐 AI Thu Thập Từng Đề
          </button>
          <button style={styles.btn} onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? "✕ Đóng" : "+ Tạo đề thủ công"}
          </button>
        </div>
      </div>

      {/* BỘ ĐẾM MÔN HỌC & CHUYỂN CHẾ ĐỘ XEM */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10, marginTop: 16 }}>
        <div style={styles.counterRow}>
          {counter.map((c) => (
            <div
              key={c.subject_id}
              style={{
                ...styles.counterChip,
                background: selectedSubject === c.subject_id ? "#3182ce" : "#edf2f7",
                color: selectedSubject === c.subject_id ? "#fff" : "#2d3748",
                cursor: "pointer",
                fontWeight: 600,
              }}
              onClick={() => filterBySubject(selectedSubject === c.subject_id ? null : c.subject_id)}
            >
              {c.subject_icon} {c.subject_name}: <b>{c.completed_exams}/{c.total_exams} đề</b>
            </div>
          ))}
          {selectedSubject && (
            <div
              style={{ ...styles.counterChip, background: "#fed7d7", color: "#c53030", cursor: "pointer" }}
              onClick={() => filterBySubject(null)}
            >
              ✕ Bỏ lọc môn
            </div>
          )}
        </div>

        {/* Tab chuyển đổi chế độ xem */}
        <div style={styles.viewModeToggle}>
          <button
            style={viewMode === "hierarchy" ? styles.viewModeActive : styles.viewModeInactive}
            onClick={() => setViewMode("hierarchy")}
          >
            🏛️ Phân Cấp 3 Miền
          </button>
          <button
            style={viewMode === "flat" ? styles.viewModeActive : styles.viewModeInactive}
            onClick={() => setViewMode("flat")}
          >
            📋 Tất Cả Đề Thi ({exams.length})
          </button>
        </div>
      </div>

      {/* ==================== CHẾ ĐỘ XEM 1: PHÂN CẤP 3 MIỀN (DEFAULT) ==================== */}
      {viewMode === "hierarchy" && (
        <div style={{ marginTop: 20 }}>
          {/* CẤP 1: 3 MIỀN (BẮC - TRUNG - NAM) */}
          <div style={styles.regionGrid}>
            {regions.map((reg) => {
              const isSelected = selectedRegionId === reg.id;
              const icon = reg.code === "bac" ? "🏞️" : reg.code === "trung" ? "🌊" : "🌴";
              return (
                <div
                  key={reg.id}
                  style={{
                    ...styles.regionCard,
                    borderColor: isSelected ? "#3182ce" : "#e2e8f0",
                    background: isSelected ? "#ebf8ff" : "#fff",
                    boxShadow: isSelected ? "0 4px 12px rgba(49, 130, 206, 0.18)" : "0 1px 3px rgba(0,0,0,0.06)",
                  }}
                  onClick={() => selectRegion(reg.id)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div style={{ fontSize: 24 }}>{icon}</div>
                    <span style={{
                      ...styles.badge,
                      background: reg.exam_count > 0 ? "#c6f6d5" : "#edf2f7",
                      color: reg.exam_count > 0 ? "#22543d" : "#718096",
                    }}>
                      {reg.exam_count} đề thi
                    </span>
                  </div>
                  <div style={{ fontWeight: 800, fontSize: 18, marginTop: 8, color: "#2d3748" }}>
                    Miền {reg.name}
                  </div>
                  <div style={{ fontSize: 12, color: "#718096", marginTop: 4 }}>
                    {reg.province_count} Tỉnh / Thành phố
                  </div>
                  <div style={{ fontSize: 11, color: isSelected ? "#2b6cb0" : "#a0aec0", marginTop: 8, fontWeight: 600 }}>
                    {isSelected ? "● Đang duyệt miền này" : "Nhấp để duyệt"}
                  </div>
                </div>
              );
            })}
          </div>

          {/* CẤP 2 & 3: GRID 2 CỘT (TỈNH & TRƯỜNG THPT) */}
          <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 20, marginTop: 20 }}>
            {/* CỘT TRÁI: DANH SÁCH TỈNH & TRƯỜNG */}
            <div style={styles.sidebarPanel}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <b style={{ fontSize: 14, color: "#2d3748" }}>📍 Tỉnh / Thành phố ({filteredProvinces.length})</b>
                <label style={{ fontSize: 11, color: "#4a5568", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
                  <input
                    type="checkbox"
                    checked={onlyProvincesWithExams}
                    onChange={(e) => setOnlyProvincesWithExams(e.target.checked)}
                  />
                  Có đề ({provinces.filter((p) => p.exam_count > 0).length})
                </label>
              </div>

              {/* Danh sách tỉnh */}
              <div style={styles.scrollList}>
                {filteredProvinces.map((prov) => {
                  const isProvSelected = selectedProvinceId === prov.id;
                  return (
                    <div
                      key={prov.id}
                      style={{
                        ...styles.provinceItem,
                        background: isProvSelected ? "#3182ce" : "#fff",
                        color: isProvSelected ? "#fff" : "#2d3748",
                      }}
                      onClick={() => selectProvince(prov.id)}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span>📍</span>
                        <span style={{ fontWeight: isProvSelected ? 700 : 500 }}>{prov.name}</span>
                      </div>
                      {prov.exam_count > 0 ? (
                        <span style={{
                          ...styles.miniBadge,
                          background: isProvSelected ? "#fff" : "#e6fffa",
                          color: isProvSelected ? "#3182ce" : "#234e52",
                        }}>
                          {prov.exam_count} đề
                        </span>
                      ) : (
                        <span style={{ fontSize: 11, color: isProvSelected ? "#e2e8f0" : "#a0aec0" }}>
                          0 đề
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Danh sách trường THPT trong tỉnh đã chọn */}
              {currentProvince && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <b style={{ fontSize: 13, color: "#2d3748" }}>🏛️ Trường / Sở tại {currentProvince.name}</b>
                    <button
                      style={styles.smallHarvestBtn}
                      onClick={() => openHarvesterForSchool(`Sở GD&ĐT ${currentProvince.name}`, currentProvince.name)}
                      title="AI quét đề cho tỉnh này"
                    >
                      + Quét đề
                    </button>
                  </div>

                  {schools.length === 0 ? (
                    <div style={{ padding: 12, background: "#f7fafc", borderRadius: 6, fontSize: 12, color: "#718096" }}>
                      Chưa có trường nào lưu đề thi. Bấm <b>"+ Quét đề"</b> để AI tìm đề thi của tỉnh này ngay!
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {schools.map((sch) => {
                        const isSchSelected = selectedSchoolId === sch.id;
                        return (
                          <div
                            key={sch.id}
                            style={{
                              ...styles.schoolItem,
                              borderLeft: isSchSelected ? "4px solid #3182ce" : "1px solid #e2e8f0",
                              background: isSchSelected ? "#ebf8ff" : "#fff",
                            }}
                            onClick={() => selectSchool(sch.id, selectedCategory)}
                          >
                            <div style={{ fontWeight: 600, fontSize: 13, color: isSchSelected ? "#2b6cb0" : "#2d3748" }}>
                              {sch.school_type === "dept" ? "🏢 " : "🏫 "}
                              {sch.name}
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
                              <span style={{ fontSize: 11, color: "#718096" }}>{sch.exam_count} đề thi</span>
                              <span
                                style={{ fontSize: 11, color: "#319795", cursor: "pointer", textDecoration: "underline" }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openHarvesterForSchool(sch.name, currentProvince.name);
                                }}
                              >
                                🌐 Quét thêm đề
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* CỘT PHẢI: CẤP 4 - PHÂN LOẠI & DANH SÁCH ĐỀ THI THEO TRƯỜNG */}
            <div style={styles.mainPanel}>
              {currentSchool ? (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 10 }}>
                    <div>
                      <h3 style={{ margin: "0 0 4px 0", color: "#2d3748" }}>
                        🏛️ {currentSchool.name}
                      </h3>
                      <div style={{ fontSize: 13, color: "#718096" }}>
                        📍 {currentProvince?.name} · Thuộc Miền {regions.find((r) => r.id === selectedRegionId)?.name}
                      </div>
                    </div>
                    <button
                      style={styles.harvestSchoolBtn}
                      onClick={() => openHarvesterForSchool(currentSchool.name, currentProvince.name)}
                    >
                      🌐 AI Thu Thập Thêm Đề Cho Trường Này
                    </button>
                  </div>

                  {/* Tabs Phân loại đề thi: Giữa kì · Cuối kì · Thi thử · Thường xuyên */}
                  <div style={styles.categoryTabs}>
                    {[
                      { key: "all", label: "Tất cả đề" },
                      { key: "mock", label: "🎯 Đề thi thử THPT" },
                      { key: "midterm", label: "📝 Đề thi giữa kì" },
                      { key: "final", label: "🏆 Đề thi cuối kì" },
                      { key: "regular", label: "⏱️ Thường xuyên / 1 tiết" },
                    ].map((cat) => (
                      <button
                        key={cat.key}
                        style={{
                          ...styles.categoryTab,
                          borderBottom: selectedCategory === cat.key ? "3px solid #3182ce" : "3px solid transparent",
                          color: selectedCategory === cat.key ? "#3182ce" : "#718096",
                          fontWeight: selectedCategory === cat.key ? 700 : 500,
                        }}
                        onClick={() => selectSchool(currentSchool.id, cat.key)}
                      >
                        {cat.label}
                      </button>
                    ))}
                  </div>

                  {/* Danh sách đề thi */}
                  {(!schoolExamData || schoolExamData.all_exams.length === 0) ? (
                    <div style={styles.emptyBox}>
                      <div style={{ fontSize: 36 }}>📭</div>
                      <div style={{ fontWeight: 600, marginTop: 8 }}>Chưa có đề thi nào trong phân loại này</div>
                      <p style={{ fontSize: 13, color: "#718096", maxWidth: 400, margin: "6px auto 14px" }}>
                        Hãy bấm nút bên dưới để AI tự động lên mạng tìm kiếm và bóc tách đề thi chuẩn của trường này!
                      </p>
                      <button
                        style={styles.harvestBtn}
                        onClick={() => openHarvesterForSchool(currentSchool.name, currentProvince.name)}
                      >
                        🚀 AI Quét & Nạp Đề Cho Trường Này Ngay
                      </button>
                    </div>
                  ) : (
                    <div style={{ marginTop: 16 }}>
                      {schoolExamData.all_exams.map((exam) => {
                        const subjectName = subjects.find((s) => s.id === exam.subject_id)?.name || "";
                        const categoryLabel =
                          exam.exam_category === "midterm" ? "Đề Giữa kì" :
                          exam.exam_category === "final" ? "Đề Cuối kì" :
                          exam.exam_category === "regular" ? "Kiểm tra 1 tiết" : "Đề Thi thử THPT";
                        
                        return (
                          <div key={exam.id} style={styles.examCard}>
                            <div style={{ flex: 1 }}>
                              <div style={{ fontWeight: 700, fontSize: 16, color: "#1a202c" }}>
                                <MathView text={exam.title} />
                              </div>

                              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
                                <span style={styles.categoryBadge}>📌 {categoryLabel}</span>
                                <span style={styles.curriculumBadge}>🎯 {exam.curriculum_standard || "GDPT 2018"}</span>
                                <span style={styles.yearBadge}>📅 Năm {exam.exam_year || 2025}</span>
                                <span style={styles.questionCountBadge}>📝 {exam.total_questions} câu</span>
                                <span style={styles.timeBadge}>⏱️ {exam.duration_minutes} phút</span>
                              </div>

                              <div style={{ fontSize: 13, color: "#718096", marginTop: 6 }}>
                                📘 Môn {subjectName} · 🏛️ {exam.school_or_dept} · 📍 {exam.province}
                              </div>
                            </div>
                            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                              <button style={styles.startBtn} onClick={() => startExam(exam.id)}>
                                ▶ Làm bài
                              </button>
                              <button style={styles.deleteBtn} onClick={() => deleteExam(exam.id)} title="Xóa đề">
                                🗑
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ) : (
                <div style={styles.emptyBox}>
                  <div style={{ fontSize: 36 }}>👆</div>
                  <div style={{ fontWeight: 600, marginTop: 8 }}>Vui lòng chọn Tỉnh và Trường THPT ở cột bên trái</div>
                  <p style={{ fontSize: 13, color: "#718096" }}>
                    Hệ thống sẽ hiển thị toàn bộ đề thi giữa kì, cuối kì và thi thử của trường đó!
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ==================== CHẾ ĐỘ XEM 2: TẤT CẢ ĐỀ THI (DẠNG PHẲNG) ==================== */}
      {viewMode === "flat" && (
        <div style={{ marginTop: 20 }}>
          {exams.length === 0 ? (
            <p style={{ color: "#718096", marginTop: 20 }}>Chưa có đề thi nào. Bấm nút <b>"🌐 AI Thu Thập Đề Từ Internet"</b> để lấy đề về ngay!</p>
          ) : (
            <div>
              {exams.map((exam) => {
                const subjectName = subjects.find((s) => s.id === exam.subject_id)?.name || "";
                return (
                  <div key={exam.id} style={styles.examCard}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 16 }}>
                        <MathView text={exam.title} />
                      </div>
                      
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
                        {exam.school_or_dept && (
                          <span style={styles.schoolBadge}>🏛️ {exam.school_or_dept}</span>
                        )}
                        {exam.province && (
                          <span style={styles.provinceBadge}>📍 {exam.province}</span>
                        )}
                        <span style={styles.curriculumBadge}>🎯 {exam.curriculum_standard || "GDPT 2018"}</span>
                        <span style={styles.questionCountBadge}>📝 {exam.total_questions} câu</span>
                        <span style={styles.timeBadge}>⏱️ {exam.duration_minutes} phút</span>
                      </div>

                      <div style={{ fontSize: 13, color: "#718096", marginTop: 6 }}>
                        📘 {subjectName} · Loại đề: <b>{exam.exam_category || exam.exam_type}</b>
                      </div>
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
      )}

      {/* ==================== POPUP: 1-CLICK QUÉT TOÀN QUỐC & CHỐNG TRÙNG LẶP ==================== */}
      {showBatchModal && (
        <div style={styles.modalOverlay}>
          <div style={{ ...styles.modalContent, maxWidth: 680 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h3 style={{ margin: 0, color: "#2b6cb0", display: "flex", alignItems: "center", gap: 8 }}>
                ⚡ Cào Đề Thi Liên Tục Từ Internet (Toán · Lý · Hóa)
              </h3>
              {!batchSyncing && (
                <button
                  style={{ border: "none", background: "transparent", fontSize: 20, cursor: "pointer" }}
                  onClick={() => setShowBatchModal(false)}
                >
                  ✕
                </button>
              )}
            </div>

            {batchSyncing ? (
              <div style={{ textAlign: "center", padding: "40px 20px" }}>
                <div style={{ fontSize: 44 }}>🔄</div>
                <h4 style={{ color: "#2b6cb0", margin: "16px 0 8px" }}>
                  Đang lật trang trên Internet để tìm đề thi mới...
                </h4>
                <p style={{ fontSize: 13, color: "#718096", maxWidth: 480, margin: "0 auto", lineHeight: 1.5 }}>
                  AI đang tự động truy cập trang tiếp theo trên ToanMath, LoiGiaiHay để tìm các đề thi MỚI chưa có trong hệ thống, tải PDF, bóc tách chuẩn GDPT 2018 và tự động phân loại theo Miền → Tỉnh → Trường THPT.
                </p>
                <div style={{ marginTop: 20, fontSize: 12, color: "#319795", fontWeight: 600 }}>
                  🔄 Mỗi lần bấm nút, hệ thống sẽ lật sang trang tiếp theo trên internet để luôn nạp thêm đề mới!
                </div>
              </div>
            ) : batchResult ? (
              <div>
                {/* THỐNG KÊ 3 THẺ */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: 16 }}>
                  <div style={{ background: "#f0fff4", border: "1px solid #c6f6d5", borderRadius: 8, padding: 12, textAlign: "center" }}>
                    <div style={{ fontSize: 22, fontWeight: 800, color: "#22543d" }}>+{batchResult.new_imported}</div>
                    <div style={{ fontSize: 12, color: "#276749", fontWeight: 600 }}>Đề mới đã nạp</div>
                  </div>
                  <div style={{ background: "#fffaf0", border: "1px solid #feebc8", borderRadius: 8, padding: 12, textAlign: "center" }}>
                    <div style={{ fontSize: 22, fontWeight: 800, color: "#7b341e" }}>{batchResult.skipped_duplicates}</div>
                    <div style={{ fontSize: 12, color: "#9c4221", fontWeight: 600 }}>Bỏ qua (Trùng lặp)</div>
                  </div>
                  <div style={{ background: "#ebf8ff", border: "1px solid #bee3f8", borderRadius: 8, padding: 12, textAlign: "center" }}>
                    <div style={{ fontSize: 22, fontWeight: 800, color: "#2b6cb0" }}>{batchResult.total_scanned}</div>
                    <div style={{ fontSize: 12, color: "#2c5282", fontWeight: 600 }}>Tổng số đã quét</div>
                  </div>
                </div>

                <div style={{ fontSize: 13, color: "#4a5568", background: "#f7fafc", padding: 10, borderRadius: 6, marginBottom: 12 }}>
                  💡 <b>Thông báo:</b> {batchResult.message}
                  {batchResult.sources_crawled && batchResult.sources_crawled.length > 0 && (
                    <div style={{ marginTop: 6, fontSize: 12, color: "#2b6cb0" }}>
                      🌐 <b>Nguồn đã quét:</b> {batchResult.sources_crawled.join(" · ")}
                    </div>
                  )}
                </div>

                {/* DANH SÁCH CHI TIẾT */}
                <div style={{ maxHeight: 260, overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: 8, padding: 8 }}>
                  {batchResult.results.map((item, idx) => (
                    <div key={idx} style={{
                      display: "flex", justifyContent: "space-between", alignItems: "center",
                      padding: "8px 10px", borderBottom: idx < batchResult.results.length - 1 ? "1px solid #edf2f7" : "none",
                      fontSize: 12
                    }}>
                      <div style={{ flex: 1, paddingRight: 10 }}>
                        <div style={{ fontWeight: 600, color: "#2d3748" }}>{item.title}</div>
                        <div style={{ color: "#718096", fontSize: 11, marginTop: 2 }}>
                          📘 {item.subject} · 📍 {item.province} · 🏛️ {item.school}
                        </div>
                      </div>
                      <div>
                        {item.status === "imported" ? (
                          <span style={{ background: "#c6f6d5", color: "#22543d", padding: "3px 8px", borderRadius: 12, fontSize: 11, fontWeight: 700 }}>
                            🟢 Nạp mới ({item.total_questions || 22} câu)
                          </span>
                        ) : item.status === "skipped_duplicate" ? (
                          <span style={{ background: "#feebc8", color: "#7b341e", padding: "3px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600 }}>
                            🟡 Đã có (Bỏ qua)
                          </span>
                        ) : (
                          <span style={{ background: "#fed7d7", color: "#9b2c2c", padding: "3px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600 }}>
                            🔴 Lỗi
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
                  <button
                    style={{ ...styles.batchBtn, padding: "10px 24px" }}
                    onClick={() => setShowBatchModal(false)}
                  >
                    🎉 Đóng & Khám Phá Kho Đề
                  </button>
                  <button
                    style={{ ...styles.batchBtn, padding: "10px 24px", background: "linear-gradient(135deg, #38a169, #2f855a)" }}
                    onClick={() => { setShowBatchModal(false); handleBatchSyncNationwide(); }}
                  >
                    🔄 Bấm Tiếp Để Cào Thêm Đề Mới
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* ==================== POPUP: AI THU THẬP ĐỀ THI TỪ INTERNET ==================== */}
      {showWebHarvester && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h3 style={{ margin: 0, color: "#2b6cb0" }}>🌐 AI Tự Động Thu Thập Đề Thi Chuẩn GDPT 2018</h3>
              <button
                style={{ border: "none", background: "transparent", fontSize: 20, cursor: "pointer" }}
                onClick={() => setShowWebHarvester(false)}
              >
                ✕
              </button>
            </div>
            
            <p style={{ fontSize: 12, color: "#4a5568", lineHeight: 1.5, background: "#ebf8ff", padding: 10, borderRadius: 6, border: "1px solid #bee3f8", margin: "0 0 14px 0" }}>
              <b>💡 Chuẩn cấu trúc đề thi 2025 - 2026 (22 câu):</b><br/>
              Hệ thống tự động tải file <b>PDF, Word (.docx) hoặc link Google Drive</b>, bóc tách chính xác 22 câu (12 câu Phần I + 4 câu Phần II + 6 câu Phần III), kèm bảng đáp án chính thức và tự động xếp vào đúng vị trí Miền → Tỉnh → Trường THPT!
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
              <div>
                <label style={styles.label}>1. Môn học:</label>
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

              <div>
                <label style={styles.label}>2. Loại đề thi:</label>
                <select
                  value={harvestForm.exam_category}
                  onChange={(e) => setHarvestForm({ ...harvestForm, exam_category: e.target.value })}
                  style={styles.select}
                >
                  <option value="mock">🎯 Đề thi thử THPT Quốc gia</option>
                  <option value="midterm">📝 Đề thi giữa kì (GK)</option>
                  <option value="final">🏆 Đề thi cuối kì (CK)</option>
                  <option value="regular">⏱️ Kiểm tra thường xuyên</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: 10 }}>
              <label style={styles.label}>3. Tìm kiếm theo Tỉnh, Trường hoặc Chủ đề:</label>
              <input
                placeholder="VD: Sở Hà Nội, THPT Chuyên Lam Sơn, Đà Nẵng, KHTN, Bắc Ninh, Nghệ An..."
                value={harvestForm.topic_query}
                onChange={(e) => setHarvestForm({ ...harvestForm, topic_query: e.target.value })}
                style={styles.inputFull}
              />
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
                {["Sở Hà Nội", "Đà Nẵng", "Chuyên Lam Sơn", "Sở Bắc Ninh", "Chuyên KHTN", "Sở Nghệ An"].map((tag) => (
                  <span
                    key={tag}
                    onClick={() => setHarvestForm({ ...harvestForm, topic_query: `Đề thi thử THPT 2026 ${tag}` })}
                    style={{ fontSize: 11, background: "#edf2f7", padding: "3px 8px", borderRadius: 12, cursor: "pointer", color: "#2b6cb0", fontWeight: 600 }}
                  >
                    🏷️ {tag}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={styles.label}>4. Hoặc Dán Trực Tiếp Link File (PDF / Word / Google Drive / ToanMath):</label>
              <input
                placeholder="Dán link file .pdf, link Google Drive, bài viết ToanMath hoặc VietJack..."
                value={harvestForm.web_url}
                onChange={(e) => setHarvestForm({ ...harvestForm, web_url: e.target.value })}
                style={styles.inputFull}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button style={styles.cancelBtn} onClick={() => setShowWebHarvester(false)}>Hủy</button>
              <button style={styles.startHarvestBtn} onClick={handleHarvestFromWeb} disabled={harvesting}>
                {harvesting ? "⏳ Đang quét & bóc tách đề..." : "🚀 Tìm kiếm & Nạp đề ngay"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================== FORM TẠO ĐỀ THỦ CÔNG ==================== */}
      {showCreate && (
        <CreateExamForm
          subjects={subjects}
          onCreated={() => {
            setShowCreate(false);
            loadExams(selectedSubject);
            api.get("/exam-counter").then((r) => setCounter(r.data));
            loadRegions();
          }}
        />
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
    exam_category: "mock",
    province: "Hà Nội",
    school_or_dept: "Tự biên soạn",
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
  batchBtn: {
    padding: "9px 18px", background: "linear-gradient(135deg, #d69e2e, #dd6b20)", color: "#fff",
    border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 700, fontSize: 13,
    boxShadow: "0 2px 6px rgba(221, 107, 32, 0.35)",
  },
  harvestBtn: {
    padding: "9px 18px", background: "linear-gradient(135deg, #319795, #2b6cb0)", color: "#fff",
    border: "none", borderRadius: 8, cursor: "pointer", fontWeight: 700, fontSize: 13,
    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
  },
  btn: {
    padding: "8px 16px", background: "#edf2f7", color: "#2d3748",
    border: "1px solid #cbd5e0", borderRadius: 8, cursor: "pointer", fontWeight: 600, fontSize: 13,
  },
  viewModeToggle: {
    display: "flex", background: "#edf2f7", borderRadius: 8, padding: 3, gap: 4,
  },
  viewModeActive: {
    padding: "6px 14px", background: "#fff", color: "#2b6cb0", border: "none",
    borderRadius: 6, fontWeight: 700, fontSize: 13, cursor: "pointer",
    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
  },
  viewModeInactive: {
    padding: "6px 14px", background: "transparent", color: "#718096", border: "none",
    borderRadius: 6, fontWeight: 600, fontSize: 13, cursor: "pointer",
  },
  regionGrid: {
    display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14,
  },
  regionCard: {
    border: "2px solid #e2e8f0", borderRadius: 12, padding: 16, cursor: "pointer",
    transition: "all 0.2s ease",
  },
  badge: {
    padding: "3px 8px", borderRadius: 12, fontSize: 11, fontWeight: 700,
  },
  sidebarPanel: {
    background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 16,
    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
  },
  mainPanel: {
    background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20,
    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
  },
  scrollList: {
    maxHeight: 260, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4,
    paddingRight: 4,
  },
  provinceItem: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "7px 10px", borderRadius: 6, cursor: "pointer", fontSize: 13,
    transition: "background 0.15s ease",
  },
  miniBadge: {
    padding: "2px 6px", borderRadius: 10, fontSize: 10, fontWeight: 700,
  },
  schoolItem: {
    padding: "10px 12px", borderRadius: 6, cursor: "pointer", marginBottom: 6,
    border: "1px solid #e2e8f0", transition: "all 0.15s ease",
  },
  smallHarvestBtn: {
    padding: "3px 8px", background: "#ebf8ff", color: "#2b6cb0", border: "1px solid #bee3f8",
    borderRadius: 4, fontSize: 11, fontWeight: 700, cursor: "pointer",
  },
  harvestSchoolBtn: {
    padding: "7px 14px", background: "#e6fffa", color: "#234e52", border: "1px solid #81e6d9",
    borderRadius: 6, fontSize: 12, fontWeight: 700, cursor: "pointer",
  },
  categoryTabs: {
    display: "flex", gap: 12, borderBottom: "1px solid #e2e8f0", marginTop: 14, overflowX: "auto",
  },
  categoryTab: {
    background: "transparent", border: "none", padding: "8px 12px", cursor: "pointer",
    fontSize: 13, whiteSpace: "nowrap",
  },
  emptyBox: {
    textAlign: "center", padding: "40px 20px", background: "#f7fafc",
    borderRadius: 10, border: "1px dashed #cbd5e0", marginTop: 16,
  },
  counterRow: { display: "flex", gap: 8, flexWrap: "wrap" },
  counterChip: { padding: "6px 14px", borderRadius: 20, fontSize: 13 },
  examCard: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: 16, marginBottom: 12,
    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
  },
  categoryBadge: { background: "#ebf8ff", color: "#2b6cb0", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700 },
  curriculumBadge: { background: "#c6f6d5", color: "#22543d", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700, border: "1px solid #9ae6b4" },
  yearBadge: { background: "#edf2f7", color: "#4a5568", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  questionCountBadge: { background: "#fefcbf", color: "#744210", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700 },
  timeBadge: { background: "#feebc8", color: "#7b341e", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  schoolBadge: { background: "#ebf8ff", color: "#2b6cb0", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700 },
  provinceBadge: { background: "#feebc8", color: "#c05621", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 },
  startBtn: {
    padding: "8px 16px", background: "#38a169", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 700, fontSize: 13,
  },
  deleteBtn: { padding: "8px 12px", background: "#fed7d7", color: "#c53030", border: "none", borderRadius: 6, cursor: "pointer" },
  modalOverlay: {
    position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
    background: "rgba(0, 0, 0, 0.5)", display: "flex", alignItems: "center", justifyContent: "center",
    zIndex: 9999,
  },
  modalContent: {
    background: "#fff", borderRadius: 12, padding: 22, width: "92%", maxWidth: 540,
    boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
  },
  label: { display: "block", fontSize: 12, fontWeight: 700, color: "#2d3748", marginBottom: 4 },
  inputFull: {
    width: "100%", padding: 9, border: "1px solid #cbd5e0", borderRadius: 6, fontSize: 13, boxSizing: "border-box",
  },
  select: { width: "100%", padding: 9, border: "1px solid #cbd5e0", borderRadius: 6, fontSize: 13, boxSizing: "border-box" },
  startHarvestBtn: {
    padding: "9px 18px", background: "#319795", color: "#fff", border: "none", borderRadius: 6,
    fontWeight: 700, cursor: "pointer", fontSize: 13,
  },
  cancelBtn: {
    padding: "9px 14px", background: "#edf2f7", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13,
  },
  createForm: { background: "#f7fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: 20, marginTop: 16 },
  formRow: { display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" },
  input: { padding: 8, border: "1px solid #cbd5e0", borderRadius: 6, flex: 1, fontSize: 14 },
  questionBlock: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 6, padding: 12, marginBottom: 10 },
  textarea: { width: "100%", minHeight: 60, padding: 8, border: "1px solid #cbd5e0", borderRadius: 6, marginTop: 6, fontSize: 14 },
  submitBtn: { padding: "8px 18px", background: "#3182ce", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 },
};

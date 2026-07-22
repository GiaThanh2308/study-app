import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";

const menuItems = [
  { path: "/", label: "Dashboard", icon: "🏠" },
  { path: "/subjects", label: "Môn học", icon: "📚" },
  { path: "/chat", label: "Chat AI", icon: "💬" },
  { path: "/practice", label: "Luyện tập", icon: "📝" },
  { path: "/mistakes", label: "Sổ lỗi sai", icon: "❌" },
];

export default function Sidebar() {
  const [theme, setTheme] = useState(() => localStorage.getItem("studyapp-theme") || "light");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("studyapp-theme", theme);
  }, [theme]);

  return (
    <aside style={styles.sidebar}>
      <div style={styles.logoBox}>
        <div style={styles.logoIcon}>🎓</div>
        <div style={styles.logoText}>StudyApp</div>
      </div>

      <nav style={styles.nav}>
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            style={({ isActive }) => ({
              ...styles.link,
              background: isActive ? "rgba(255,255,255,0.12)" : "transparent",
              color: isActive ? "#fff" : "#a0aec0",
              fontWeight: isActive ? 600 : 500,
            })}
          >
            {({ isActive }) => (
              <>
                <span style={{ width: 3, height: 20, borderRadius: 2, background: isActive ? "#63b3ed" : "transparent" }} />
                <span style={{ fontSize: 17 }}>{item.icon}</span>
                <span>{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <button
        style={styles.themeToggle}
        onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
        title="Chuyển giao diện sáng/tối"
      >
        {theme === "light" ? "🌙 Chế độ tối" : "☀️ Chế độ sáng"}
      </button>

      <div style={styles.footer}>Ôn thi THPT · Offline AI</div>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: 230,
    background: "linear-gradient(180deg, #1a202c 0%, #171d29 100%)",
    color: "#fff",
    height: "100vh",
    padding: "20px 0",
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    position: "sticky",
    top: 0,
    flexShrink: 0,
  },
  logoBox: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "0 22px 24px",
  },
  logoIcon: { fontSize: 22 },
  logoText: { fontSize: 19, fontWeight: 700, letterSpacing: -0.3 },
  nav: { display: "flex", flexDirection: "column", gap: 2, padding: "0 10px", flex: 1 },
  link: {
    display: "flex",
    gap: 10,
    alignItems: "center",
    padding: "10px 12px",
    textDecoration: "none",
    fontSize: 14,
    borderRadius: 8,
    transition: "background 0.15s ease, color 0.15s ease",
  },
  themeToggle: {
    margin: "0 10px 12px",
    padding: "9px 12px",
    borderRadius: 8,
    border: "1px solid rgba(255,255,255,0.12)",
    background: "rgba(255,255,255,0.06)",
    color: "#cbd5e0",
    fontSize: 13,
    cursor: "pointer",
    textAlign: "left",
  },
  footer: {
    padding: "12px 22px 0",
    fontSize: 11,
    color: "#4a5568",
    borderTop: "1px solid rgba(255,255,255,0.06)",
    marginTop: 12,
  },
};

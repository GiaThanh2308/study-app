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
              background: isActive ? "var(--color-primary-light)" : "transparent",
              color: isActive ? "var(--color-primary)" : "var(--color-text-muted)",
              fontWeight: isActive ? 600 : 500,
            })}
          >
            {({ isActive }) => (
              <>
                <span
                  style={{
                    width: 3,
                    height: 20,
                    borderRadius: 2,
                    background: isActive ? "var(--color-primary)" : "transparent",
                  }}
                />
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
        <span style={styles.themeToggleLabel}>
          {theme === "light" ? "☀️ Chế độ sáng" : "🌙 Chế độ tối"}
        </span>
        <span
          style={{
            ...styles.switchTrack,
            background: theme === "dark" ? "#4f46e5" : "var(--color-border)",
          }}
        >
          <span
            style={{
              ...styles.switchThumb,
              transform: theme === "dark" ? "translateX(16px)" : "translateX(0)",
            }}
          />
        </span>
      </button>

      <div style={styles.footer}>Ôn thi THPT · Offline AI</div>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: 230,
    background: "var(--color-surface)",
    color: "var(--color-text)",
    borderRight: "1px solid var(--color-border)",
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
    border: "1px solid var(--color-border)",
    background: "var(--color-bg)",
    color: "var(--color-text-muted)",
    fontSize: 13,
    cursor: "pointer",
    textAlign: "left",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  themeToggleLabel: { flex: 1 },
  switchTrack: {
    display: "inline-block",
    width: 34,
    height: 18,
    borderRadius: 9,
    position: "relative",
    flexShrink: 0,
    transition: "background 0.2s ease",
  },
  switchThumb: {
    position: "absolute",
    top: 2,
    left: 2,
    width: 14,
    height: 14,
    borderRadius: "50%",
    background: "#fff",
    transition: "transform 0.2s ease",
  },
  footer: {
    padding: "12px 22px 0",
    fontSize: 11,
    color: "var(--color-text-muted)",
    borderTop: "1px solid var(--color-border)",
    marginTop: 12,
  },
};




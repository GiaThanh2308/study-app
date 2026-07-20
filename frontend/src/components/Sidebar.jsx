import { NavLink } from "react-router-dom";

const menuItems = [
  { path: "/", label: "Dashboard", icon: "🏠" },
  { path: "/subjects", label: "Môn học", icon: "📚" },
  { path: "/chat", label: "Chat AI", icon: "💬" },
  { path: "/practice", label: "Luyện tập", icon: "📝" },
  { path: "/mistakes", label: "Sổ lỗi sai", icon: "❌" },
  { path: "/stats", label: "Thống kê", icon: "📊" },
  { path: "/settings", label: "Cài đặt", icon: "⚙️" },
];

export default function Sidebar() {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.logo}>StudyApp</div>
      <nav>
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            style={({ isActive }) => ({
              ...styles.link,
              background: isActive ? "#2d3748" : "transparent",
            })}
          >
            <span>{item.icon}</span> {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: 220,
    background: "#1a202c",
    color: "#fff",
    height: "100vh",
    padding: "16px 0",
    boxSizing: "border-box",
  },
  logo: { fontSize: 20, fontWeight: 700, padding: "0 20px 20px" },
  link: {
    display: "flex",
    gap: 10,
    alignItems: "center",
    padding: "10px 20px",
    color: "#e2e8f0",
    textDecoration: "none",
    fontSize: 14,
  },
};

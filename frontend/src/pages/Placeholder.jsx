export default function Placeholder({ title, message }) {
  return (
    <div style={{ padding: 24 }}>
      <h2>{title}</h2>
      <p style={{ color: "#718096" }}>
        {message || "Module này chưa sẵn sàng trong bản chuyển đổi hiện tại."}
      </p>
    </div>
  );
}

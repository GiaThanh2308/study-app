import React from "react";
import katex from "katex";

export default function MathView({ text, style }) {
  if (!text) return null;

  // Nếu text không có ký hiệu toán học $ hoặc \, render text thông thường
  if (!text.includes("$") && !text.includes("\\")) {
    return <span style={style}>{text}</span>;
  }

  // Tách text theo $...$ và $$...$$
  const parts = [];
  const regex = /(\$\$[\s\S]*?\$\$|\$[\s\S]*?\$)/g;
  let lastIdx = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push({ type: "text", content: text.substring(lastIdx, match.index) });
    }
    const token = match[0];
    if (token.startsWith("$$") && token.endsWith("$$")) {
      parts.push({ type: "display", content: token.slice(2, -2).trim() });
    } else if (token.startsWith("$") && token.endsWith("$")) {
      parts.push({ type: "inline", content: token.slice(1, -1).trim() });
    }
    lastIdx = regex.lastIndex;
  }

  if (lastIdx < text.length) {
    parts.push({ type: "text", content: text.substring(lastIdx) });
  }

  return (
    <span style={style}>
      {parts.map((p, i) => {
        if (p.type === "text") {
          return <span key={i}>{p.content}</span>;
        }
        try {
          const html = katex.renderToString(p.content, {
            displayMode: p.type === "display",
            throwOnError: false,
          });
          return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />;
        } catch (e) {
          return <span key={i}>{p.content}</span>;
        }
      })}
    </span>
  );
}

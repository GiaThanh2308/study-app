import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

/**
 * AI (Ollama/qwen) thường trả công thức toán theo cú pháp LaTeX kiểu \( ... \) và \[ ... \]
 * (cú pháp "inline"/"display" chuẩn LaTeX), nhưng thư viện remark-math chỉ tự nhận diện
 * cú pháp $ ... $ và $$ ... $$ (chuẩn Markdown). Nên cần đổi ký hiệu trước khi render.
 */
function normalizeLatexDelimiters(text) {
  if (!text) return text;
  return text
    .replace(/\\\[/g, "$$")
    .replace(/\\\]/g, "$$")
    .replace(/\\\(/g, "$")
    .replace(/\\\)/g, "$");
}

export default function MarkdownMessage({ content }) {
  const normalized = normalizeLatexDelimiters(content);

  return (
    <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
      {normalized}
    </ReactMarkdown>
  );
}

import { useMemo } from "react";
import hljs from "highlight.js/lib/core";
import json from "highlight.js/lib/languages/json";
import "highlight.js/styles/github.css";

hljs.registerLanguage("json", json);

interface CodeBlockProps {
  code: string;
  language?: string;
}

function CodeBlock({ code, language = "json" }: CodeBlockProps) {
  const highlightedHtml = useMemo(() => {
    return hljs.highlight(code, { language }).value;
  }, [code, language]);

  return (
    <pre className="code-block">
      <code
        className={`hljs language-${language}`}
        dangerouslySetInnerHTML={{ __html: highlightedHtml }}
      />
    </pre>
  );
}

export default CodeBlock;

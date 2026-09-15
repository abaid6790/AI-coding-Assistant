/**
 * Deliberately not a full markdown renderer — just enough to make code
 * blocks in AI responses readable (the thing that actually matters for
 * a coding assistant) without pulling in a markdown + sanitizer
 * dependency for Phase 7. Splits on ``` fences and renders code segments
 * in a <pre>, everything else as plain wrapped text.
 */
export default function ChatMessageContent({ content }) {
  const segments = content.split(/```(\w*)\n?/);
  // After splitting on the fence pattern, segments alternate:
  // [text, lang, code, text, lang, code, text, ...]
  const nodes = [];
  for (let i = 0; i < segments.length; i++) {
    if (i % 3 === 0) {
      if (segments[i]) nodes.push({ type: "text", value: segments[i] });
    } else if (i % 3 === 2) {
      nodes.push({ type: "code", lang: segments[i - 1], value: segments[i] });
    }
  }

  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {nodes.map((node, i) =>
        node.type === "code" ? (
          <pre key={i} className="overflow-x-auto rounded-md bg-surface-950 p-3 font-mono text-xs text-gray-200">
            {node.lang && <div className="mb-1 text-[10px] uppercase tracking-wide text-gray-500">{node.lang}</div>}
            <code>{node.value.replace(/\n$/, "")}</code>
          </pre>
        ) : (
          <p key={i} className="whitespace-pre-wrap text-gray-200">
            {node.value.trim()}
          </p>
        )
      )}
    </div>
  );
}

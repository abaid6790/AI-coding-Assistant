const LANGUAGE_MAP = {
  python: "python",
  javascript: "javascript",
  typescript: "typescript",
  java: "java",
  cpp: "cpp",
  c: "c",
  csharp: "csharp",
  php: "php",
  html: "html",
  css: "css",
  sql: "sql",
  json: "json",
  markdown: "markdown",
  go: "go",
  rb: "ruby",
  ruby: "ruby",
  rust: "rust",
  rs: "rust",
  text: "plaintext",
};

export function toMonacoLanguage(language) {
  if (!language) return "plaintext";
  return LANGUAGE_MAP[language.toLowerCase()] || "plaintext";
}

// Languages Monaco ships a built-in document formatter for out of the box.
// For everything else, "Format" is a harmless no-op — real formatting for
// those languages comes from the AI-assisted optimize/review features in
// later phases, not from Monaco itself.
const BUILTIN_FORMATTABLE = new Set(["javascript", "typescript", "json", "html", "css"]);

export function supportsBuiltinFormat(language) {
  return BUILTIN_FORMATTABLE.has(toMonacoLanguage(language));
}

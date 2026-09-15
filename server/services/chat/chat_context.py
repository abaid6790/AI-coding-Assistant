"""
Controlled context selection for AI chat (Phase 7) and, later, the
code-intelligence features (Phase 8) that also need "current file +
selection + history" without sending an entire project.

Per the spec: "Do not automatically send an entire large project to the
AI. Use controlled context selection to reduce token usage." Everything
here is capped — history length, file size, selection size — so a huge
file or a long-running conversation can't blow up the prompt (and the
bill) silently.
"""

SYSTEM_PROMPT = (
    "You are an AI coding assistant embedded in a code editor. Answer "
    "clearly and concisely. When you include code, use fenced markdown "
    "code blocks with a language tag. If you're not certain about "
    "something, say so rather than guessing."
)

MAX_HISTORY_MESSAGES = 10  # most recent messages, not the whole conversation
MAX_FILE_CONTEXT_CHARS = 6000
MAX_SELECTION_CHARS = 4000


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… (truncated, {len(text) - limit} more characters)"


def build_prompt(
    *,
    conversation_messages: list,
    new_message: str,
    file=None,
    selection: str | None = None,
) -> str:
    """
    conversation_messages: prior Message rows for this conversation, oldest
        first (only the most recent MAX_HISTORY_MESSAGES are used).
    file: an optional ProjectFile — its content is included (truncated)
        so the assistant has context without the caller re-pasting it.
    selection: an optional snippet of code the user has selected in the
        editor — takes priority over the full file when both are present,
        since it's the more specific signal of what they're asking about.
    """
    parts = []

    if file is not None:
        content = _truncate(file.content or "", MAX_FILE_CONTEXT_CHARS)
        label = f"{file.folder_path + '/' if file.folder_path else ''}{file.filename}"
        parts.append(f"Current file ({label}, language: {file.language or 'unknown'}):\n```\n{content}\n```")

    if selection:
        parts.append(f"Selected code the user is asking about:\n```\n{_truncate(selection, MAX_SELECTION_CHARS)}\n```")

    history = conversation_messages[-MAX_HISTORY_MESSAGES:]
    if history:
        transcript = "\n".join(f"{m.role.capitalize()}: {m.content}" for m in history)
        parts.append(f"Conversation so far:\n{transcript}")

    parts.append(f"User: {new_message}")

    return "\n\n".join(parts)


def default_title_from_message(content: str, max_len: int = 60) -> str:
    single_line = " ".join(content.split())
    if len(single_line) <= max_len:
        return single_line or "New conversation"
    return single_line[:max_len].rstrip() + "…"

"""
One prompt-builder per code-intelligence feature (Phase 8). Each returns
(system_prompt, user_prompt) for AIService.generate(). Keeping these
here — rather than inline in api/code.py — means the prompt wording
can be iterated on without touching route/persistence logic, and the
same builders are reusable if these features get exposed anywhere else
(e.g. a CLI or a batch job) later.

Code is always truncated before going into a prompt — same "controlled
context selection" principle as chat (see services/chat/chat_context.py) — this is
the code-review/generation equivalent of not sending a whole project.
"""
from services.ai.parsing import truncate

MAX_CODE_CHARS = 8000


def _fmt_code(code: str, language: str) -> str:
    return f"```{language or ''}\n{truncate(code, MAX_CODE_CHARS)}\n```"


def explain_prompt(code: str, language: str) -> tuple[str, str]:
    system = (
        "You are an AI coding assistant. Explain code clearly for a "
        "developer who can read code but hasn't seen this snippet before."
    )
    user = (
        f"Explain the following {language or ''} code. Cover, as sections with "
        "short markdown headers: Overall explanation, Line-by-line explanation "
        "(only for non-trivial lines), Function/class explanation, Inputs and "
        "outputs, Potential problems, Complexity analysis, and Improvement "
        f"suggestions.\n\n{_fmt_code(code, language)}"
    )
    return system, user


def generate_prompt(description: str, language: str) -> tuple[str, str]:
    system = (
        "You are an AI coding assistant. Generate clean, working code from a "
        "natural-language description. Respond with ONLY a JSON object — no "
        "prose outside it — matching exactly: "
        '{"code": "<the generated code as a string>", "explanation": "<brief '
        'explanation of what the code does and how to use it>"}'
    )
    user = f"Language: {language or 'infer from the description'}\n\nDescription:\n{description}"
    return system, user


def debug_prompt(code: str, error_message: str, stack_trace: str, language: str) -> tuple[str, str]:
    system = (
        "You are an AI debugging assistant. Diagnose the described error. "
        "Be clear that this is a suggested fix, not a guaranteed one. "
        "Respond with ONLY a JSON object — no prose outside it — matching "
        'exactly: {"likely_cause": "...", "problematic_code": "...", '
        '"suggested_fix": "...", "corrected_code": "...", "explanation": "..."}'
    )
    user = (
        f"{_fmt_code(code, language)}\n\n"
        f"Error message:\n{error_message or '(none provided)'}\n\n"
        f"Stack trace:\n{truncate(stack_trace or '(none provided)', MAX_CODE_CHARS)}"
    )
    return system, user


def review_prompt(code: str, language: str) -> tuple[str, str]:
    system = (
        "You are an AI code reviewer. Identify bugs, security issues, "
        "performance problems, bad practices, maintainability concerns, "
        "readability issues, and duplicate logic. These are AI-assisted "
        "estimates, not authoritative security certifications. Respond "
        "with ONLY a JSON object — no prose outside it — matching exactly: "
        '{"findings": [{"severity": "Critical|High|Medium|Low|Suggestion", '
        '"title": "...", "description": "...", "line": <int or null>}], '
        '"scores": {"quality": <0-100>, "security": <0-100>, '
        '"performance": <0-100>, "maintainability": <0-100>}, '
        '"complexity": "<one or two sentence complexity assessment>"}'
    )
    user = f"Review this {language or ''} code:\n\n{_fmt_code(code, language)}"
    return system, user


def optimize_prompt(code: str, language: str) -> tuple[str, str]:
    system = (
        "You are an AI coding assistant focused on optimization. Suggest "
        "performance improvements, memory improvements, a cleaner "
        "implementation, better algorithms, and better database queries "
        "where applicable. Respond with ONLY a JSON object — no prose "
        'outside it — matching exactly: {"optimized_code": "...", '
        '"explanation": "..."}. If the code is already well-optimized, '
        "return the same code and say so in the explanation."
    )
    user = f"Optimize this {language or ''} code:\n\n{_fmt_code(code, language)}"
    return system, user


def tests_prompt(code: str, language: str, framework: str) -> tuple[str, str]:
    system = (
        "You are an AI coding assistant that writes unit tests. Include "
        "normal cases, edge cases, invalid inputs, and error cases. "
        "Respond with ONLY the test code in a single fenced code block — "
        "no prose before or after it."
    )
    user = f"Write {framework} tests for this {language or ''} code:\n\n{_fmt_code(code, language)}"
    return system, user


def documentation_prompt(code: str, language: str, doc_type: str) -> tuple[str, str]:
    doc_type_instructions = {
        "docstring": "Write docstrings for every function/class, in the idiomatic style for this language.",
        "comments": "Add clear inline comments explaining non-obvious logic. Return the full code with comments added.",
        "readme": "Write a README section (markdown) describing what this code does, how to use it, and any notable behavior.",
        "api_docs": "Write API documentation (markdown) describing inputs, outputs, and behavior for each public function/endpoint.",
    }
    instruction = doc_type_instructions.get(doc_type, doc_type_instructions["docstring"])
    system = f"You are an AI documentation assistant. {instruction}"
    user = f"{_fmt_code(code, language)}"
    return system, user

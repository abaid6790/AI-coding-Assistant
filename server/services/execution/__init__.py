"""
Public interface for the execution service. Callers (services/code/
execution_service.py) should import from here — run_code() — rather
than reaching into python_runner.py directly, so adding a language
(Phase 16: JavaScript via Node) means adding one entry to
SUPPORTED_LANGUAGES, not touching any calling code.
"""
from services.execution.common import ExecutionResult, DEFAULT_TIMEOUT_SECONDS, ExecutionCapacityError
from services.execution.python_runner import run_python
from services.execution.node_runner import run_javascript

SUPPORTED_LANGUAGES = {
    "python": run_python,
    "javascript": run_javascript,
}


class UnsupportedLanguageError(Exception):
    def __init__(self, language: str):
        self.language = language
        super().__init__(f"Unsupported language: {language!r}")


def run_code(language: str, code: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> ExecutionResult:
    runner = SUPPORTED_LANGUAGES.get((language or "").strip().lower())
    if runner is None:
        raise UnsupportedLanguageError(language)
    return runner(code, timeout=timeout)
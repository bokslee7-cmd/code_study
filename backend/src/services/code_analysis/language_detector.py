"""Language detection for uploaded code (T065).

Detection order: file extension -> shebang -> content heuristics -> Pygments guess -> "text".
Pure functions, no I/O. Returned names are the normalized values stored in
``uploaded_code.detected_language`` (e.g. "python", "javascript").
"""

import re
from collections import Counter
from collections.abc import Iterable

from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

__all__ = [
    "detect_dominant_language",
    "detect_language",
    "get_language_for_extension",
    "get_lexer_alias",
]

TEXT = "text"
_DOC_LANGUAGES = frozenset({TEXT, "markdown"})

_EXTENSION_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".css": "css",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".txt": TEXT,
    ".md": "markdown",
}

_SHEBANG_LANGUAGES = (("python", "python"), ("node", "javascript"))

# Ordered: first match wins. Pygments alone misses Java/JS snippets, so check these first.
_CONTENT_PATTERNS = (
    ("html", re.compile(r"<!doctype\s+html|<html[\s>]", re.IGNORECASE)),
    (
        "java",
        re.compile(r"\b(public|private)\s+(static\s+)?(class|void|interface)\b|System\.out\."),
    ),
    ("cpp", re.compile(r"std::|#include\s*<(iostream|vector|string|map)>|\bnamespace\s+\w+")),
    ("c", re.compile(r"#include\s*[<\"]\w+\.h[>\"]")),
    (
        "python",
        re.compile(
            r"^\s*(def\s+\w+\(.*\)\s*:|class\s+\w+.*:|from\s+\S+\s+import\s|import\s+\w+\s*$)",
            re.M,
        ),
    ),
    (
        "javascript",
        re.compile(r"\b(const|let|var)\s+\w+\s*=|\bfunction\s*\w*\s*\(|=>|console\.log\("),
    ),
    ("css", re.compile(r"[.#]?[\w-]+\s*\{[^}]*\b[\w-]+\s*:\s*[^;}]+;", re.S)),
)

_PYGMENTS_ALIASES = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "html": "html",
    "css": "css",
    "java": "java",
    "cpp": "cpp",
    "c": "c",
    "markdown": "markdown",
}


def get_language_for_extension(extension: str) -> str | None:
    """Map an extension (with leading dot, case-insensitive) to a language, or None."""
    return _EXTENSION_LANGUAGES.get(extension.lower())


def _extension_of(file_name: str) -> str:
    dot = file_name.rfind(".")
    if dot <= 0 or dot == len(file_name) - 1:
        return ""
    return file_name[dot:]


def _from_shebang(content: str) -> str | None:
    first_line = content.split("\n", 1)[0]
    if not first_line.startswith("#!"):
        return None
    for needle, language in _SHEBANG_LANGUAGES:
        if needle in first_line:
            return language
    return None


def _from_content(content: str) -> str | None:
    for language, pattern in _CONTENT_PATTERNS:
        if pattern.search(content):
            return language
    return None


def _from_pygments(content: str) -> str | None:
    try:
        alias = guess_lexer(content).aliases[0]
    except (ClassNotFound, IndexError):
        return None
    return _PYGMENTS_ALIASES.get(alias)


def detect_language(content: str, file_name: str | None = None) -> str:
    """Detect the language of one file or pasted snippet; falls back to "text"."""
    if file_name:
        by_extension = get_language_for_extension(_extension_of(file_name))
        if by_extension:
            return by_extension
    if not content.strip():
        return TEXT
    return _from_shebang(content) or _from_content(content) or _from_pygments(content) or TEXT


def detect_dominant_language(files: Iterable[tuple[str, str]]) -> str | None:
    """Pick the language with the most lines across ``(file_name, content)`` pairs.

    Text/markdown only win when nothing else is present. Ties break alphabetically so
    the result is deterministic. Returns None for no files.
    """
    lines_by_language: Counter[str] = Counter()
    for file_name, content in files:
        lines_by_language[detect_language(content, file_name)] += max(len(content.splitlines()), 1)
    if not lines_by_language:
        return None
    code_only = {k: v for k, v in lines_by_language.items() if k not in _DOC_LANGUAGES}
    if not code_only:
        return TEXT
    return min(code_only, key=lambda language: (-code_only[language], language))


def get_lexer_alias(language: str) -> str:
    """Return a Pygments lexer alias usable for highlighting; unknown -> "text"."""
    try:
        get_lexer_by_name(language)
    except ClassNotFound:
        return TEXT
    return language

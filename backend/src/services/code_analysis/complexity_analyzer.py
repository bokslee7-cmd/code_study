"""Code complexity assessment for uploaded code (T066, FR-021).

Heuristic, regex/indent based and language-aware. Three metrics decide the level:
code lines (blank/comment lines and text/markdown files excluded), function count and
maximum nesting depth. The highest level reached by any metric wins. Pure functions, no I/O.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from src.services.code_analysis.language_detector import detect_language

__all__ = [
    "ADVANCED",
    "BEGINNER",
    "INTERMEDIATE",
    "ComplexityResult",
    "analyze_complexity",
    "count_functions",
    "max_nesting_depth",
]

BEGINNER = "beginner"
INTERMEDIATE = "intermediate"
ADVANCED = "advanced"

# A metric strictly above the first value is intermediate; at/above the second is advanced
# (lines and functions use "greater than", depth uses "at least"; see _level_of).
_LINES_INTERMEDIATE, _LINES_ADVANCED = 80, 300
_FUNCTIONS_INTERMEDIATE, _FUNCTIONS_ADVANCED = 5, 15
_DEPTH_INTERMEDIATE, _DEPTH_ADVANCED = 4, 6

_BRACE_LANGUAGES = frozenset({"javascript", "typescript", "java", "c", "cpp"})
_NON_CODE_LANGUAGES = frozenset({"text", "markdown"})
_SPACES_PER_INDENT = 4

_PYTHON_FUNCTION = re.compile(r"^\s*(?:async\s+)?def\s+\w+", re.M)
_JS_FUNCTION = re.compile(r"\bfunction\b|=>")
_C_KEYWORDS = frozenset({"if", "for", "while", "switch", "catch", "else", "return", "sizeof"})
_C_FUNCTION = re.compile(
    r"^[ \t]*(?:[\w<>\[\],.*&:]+[ \t]+)+(?P<name>\w+)[ \t]*"
    r"\([^;{}()]*(?:\([^)]*\)[^;{}()]*)*\)[ \t]*(?:const[ \t]*)?"
    r"(?:throws[ \t]+[\w., ]+)?[ \t]*\{",
    re.M,
)
_STRINGS_AND_COMMENTS = re.compile(
    r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`|//[^\n]*|/\*.*?\*/',
    re.S,
)


@dataclass(frozen=True)
class ComplexityResult:
    """Outcome of an analysis; ``level`` is stored in ``uploaded_code.complexity_level``."""

    level: str
    total_lines: int
    code_lines: int
    function_count: int
    max_nesting_depth: int


def _is_comment(line: str, language: str) -> bool:
    stripped = line.strip()
    if language == "python":
        return stripped.startswith("#")
    return stripped.startswith(("//", "/*", "*"))


def _code_lines(content: str, language: str) -> int:
    if language in _NON_CODE_LANGUAGES:
        return 0
    return sum(
        1 for line in content.splitlines() if line.strip() and not _is_comment(line, language)
    )


def count_functions(content: str, language: str) -> int:
    """Count function/method definitions; 0 for languages without a known pattern."""
    if language == "python":
        return len(_PYTHON_FUNCTION.findall(content))
    if language in ("javascript", "typescript"):
        return len(_JS_FUNCTION.findall(content))
    if language in ("java", "c", "cpp"):
        return sum(1 for m in _C_FUNCTION.finditer(content) if m["name"] not in _C_KEYWORDS)
    return 0


def _python_depth(content: str) -> int:
    depth = 0
    for line in content.splitlines():
        if not line.strip() or _is_comment(line, "python"):
            continue
        indent = line[: len(line) - len(line.lstrip(" \t"))]
        level = indent.count("\t") + indent.count(" ") // _SPACES_PER_INDENT
        depth = max(depth, level)
    return depth


def _brace_depth(content: str) -> int:
    depth = peak = 0
    for char in _STRINGS_AND_COMMENTS.sub("", content):
        if char == "{":
            depth += 1
            peak = max(peak, depth)
        elif char == "}":
            depth = max(depth - 1, 0)
    return peak


def max_nesting_depth(content: str, language: str) -> int:
    """Deepest block nesting (indent levels for Python, brace depth for C-like languages)."""
    if language == "python":
        return _python_depth(content)
    if language in _BRACE_LANGUAGES:
        return _brace_depth(content)
    return 0


def _level_of(code_lines: int, functions: int, depth: int) -> str:
    if code_lines > _LINES_ADVANCED or functions > _FUNCTIONS_ADVANCED or depth >= _DEPTH_ADVANCED:
        return ADVANCED
    if (
        code_lines > _LINES_INTERMEDIATE
        or functions > _FUNCTIONS_INTERMEDIATE
        or depth >= _DEPTH_INTERMEDIATE
    ):
        return INTERMEDIATE
    return BEGINNER


def analyze_complexity(files: Iterable[tuple[str, str]]) -> ComplexityResult:
    """Assess ``(file_name, content)`` pairs as one upload."""
    total_lines = code_lines = functions = depth = 0
    for file_name, content in files:
        language = detect_language(content, file_name)
        total_lines += len(content.splitlines())
        code_lines += _code_lines(content, language)
        functions += count_functions(content, language)
        depth = max(depth, max_nesting_depth(content, language))
    return ComplexityResult(
        _level_of(code_lines, functions, depth), total_lines, code_lines, functions, depth
    )

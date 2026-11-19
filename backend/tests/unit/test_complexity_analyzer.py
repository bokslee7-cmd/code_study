"""Unit tests for the code complexity analyzer (T066, FR-021)."""

import pytest
from src.services.code_analysis.complexity_analyzer import (
    ADVANCED,
    BEGINNER,
    INTERMEDIATE,
    ComplexityResult,
    analyze_complexity,
    count_functions,
    max_nesting_depth,
)

SIMPLE_PY = 'name = "Ann"\nprint("hello", name)\n'


def _nested_py(depth: int) -> str:
    lines = []
    for level in range(depth):
        lines.append("    " * level + "if x:")
    lines.append("    " * depth + "pass")
    return "\n".join(lines) + "\n"


def test_empty_upload_is_beginner_with_zero_metrics() -> None:
    result = analyze_complexity([])
    assert result == ComplexityResult(BEGINNER, 0, 0, 0, 0)


def test_simple_script_is_beginner() -> None:
    result = analyze_complexity([("a.py", SIMPLE_PY)])
    assert result.level == BEGINNER
    assert result.total_lines == 2
    assert result.function_count == 0


def test_total_lines_sums_all_files_including_blank_lines() -> None:
    files = [("a.py", "x = 1\n\ny = 2\n"), ("b.js", "var a = 1;\n")]
    assert analyze_complexity(files).total_lines == 4


def test_many_functions_raise_level() -> None:
    code = "".join(f"def f{i}():\n    return {i}\n" for i in range(8))
    result = analyze_complexity([("a.py", code)])
    assert result.function_count == 8
    assert result.level == INTERMEDIATE


def test_very_many_functions_are_advanced() -> None:
    code = "".join(f"def f{i}():\n    return {i}\n" for i in range(20))
    assert analyze_complexity([("a.py", code)]).level == ADVANCED


def test_long_code_is_intermediate_then_advanced() -> None:
    medium = "\n".join(f"x{i} = {i}" for i in range(100)) + "\n"
    long = "\n".join(f"x{i} = {i}" for i in range(400)) + "\n"
    assert analyze_complexity([("a.py", medium)]).level == INTERMEDIATE
    assert analyze_complexity([("a.py", long)]).level == ADVANCED


def test_blank_lines_and_comments_do_not_count_toward_level() -> None:
    padding = "\n" * 500 + "# note\n" * 500
    assert analyze_complexity([("a.py", SIMPLE_PY + padding)]).level == BEGINNER


def test_deep_nesting_raises_level() -> None:
    assert analyze_complexity([("a.py", _nested_py(4))]).level == INTERMEDIATE
    assert analyze_complexity([("a.py", _nested_py(6))]).level == ADVANCED


def test_level_is_max_across_metrics() -> None:
    code = _nested_py(6)
    assert analyze_complexity([("a.py", code)]).max_nesting_depth == 6


@pytest.mark.parametrize(
    ("language_file", "code", "expected"),
    [
        ("a.py", "def a():\n    pass\nasync def b():\n    pass\n", 2),
        ("a.js", "function a() {}\nconst b = () => 1;\nconst c = async (x) => x;\n", 3),
        ("a.ts", "function a(x: number): number { return x; }\n", 1),
        (
            "A.java",
            "public class A {\n  public static void main(String[] a) {\n    if (a == null) {}\n"
            "  }\n  private int f(int x) {\n    return x;\n  }\n}\n",
            2,
        ),
        ("a.c", "int main(void) {\n  for (;;) {}\n  return 0;\n}\n", 1),
        ("a.cpp", "void f() {}\nint g(int a) { while (a) {} return a; }\n", 2),
        ("a.html", "<html><body>function a() {}</body></html>", 0),
        ("a.md", "def a():\n", 0),
    ],
)
def test_count_functions(language_file: str, code: str, expected: int) -> None:
    from src.services.code_analysis.language_detector import detect_language

    assert count_functions(code, detect_language(code, language_file)) == expected


def test_control_keywords_are_not_functions_in_brace_languages() -> None:
    code = "void f() {\n  if (x) {\n  }\n  while (y) {\n  }\n  switch (z) {\n  }\n}\n"
    assert count_functions(code, "c") == 1


def test_python_nesting_uses_tabs_and_spaces() -> None:
    assert max_nesting_depth("if a:\n\tif b:\n\t\tpass\n", "python") == 2
    assert max_nesting_depth("if a:\n    if b:\n        pass\n", "python") == 2


def test_python_nesting_ignores_blank_and_comment_lines() -> None:
    code = "if a:\n\n            # deep comment\n    pass\n"
    assert max_nesting_depth(code, "python") == 1


def test_brace_nesting_depth() -> None:
    code = "function f() {\n  if (a) {\n    for (;;) {\n    }\n  }\n}\n"
    assert max_nesting_depth(code, "javascript") == 3


def test_brace_nesting_ignores_braces_in_strings_and_comments() -> None:
    code = "var s = \"{{{{\";\n// {{{{\nvar t = '}}';\nfunction f() {\n}\n"
    assert max_nesting_depth(code, "javascript") == 1


def test_unbalanced_closing_braces_do_not_go_negative() -> None:
    assert max_nesting_depth("}}}\nfunction f() {\n}\n", "javascript") == 1


@pytest.mark.parametrize("language", ["html", "text", "markdown", "css"])
def test_non_programming_languages_have_zero_nesting(language: str) -> None:
    assert max_nesting_depth("a {\n  b {\n  }\n}\n", language) == 0


def test_text_files_do_not_inflate_metrics() -> None:
    notes = "\n".join(f"line {i}" for i in range(1000))
    result = analyze_complexity([("notes.txt", notes), ("a.py", SIMPLE_PY)])
    assert result.level == BEGINNER
    assert result.total_lines == 1002


def test_result_is_immutable() -> None:
    result = analyze_complexity([("a.py", SIMPLE_PY)])
    with pytest.raises(AttributeError):
        result.level = ADVANCED  # type: ignore[misc]


def test_levels_match_model_check_constraint() -> None:
    assert (BEGINNER, INTERMEDIATE, ADVANCED) == ("beginner", "intermediate", "advanced")

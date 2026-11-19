"""Unit tests for the language detector (T065)."""

import pytest
from src.services.code_analysis.language_detector import (
    detect_dominant_language,
    detect_language,
    get_language_for_extension,
    get_lexer_alias,
)


@pytest.mark.parametrize(
    ("extension", "expected"),
    [
        (".py", "python"),
        (".js", "javascript"),
        (".jsx", "javascript"),
        (".ts", "typescript"),
        (".tsx", "typescript"),
        (".html", "html"),
        (".css", "css"),
        (".java", "java"),
        (".cpp", "cpp"),
        (".c", "c"),
        (".h", "c"),
        (".txt", "text"),
        (".md", "markdown"),
        (".PY", "python"),
    ],
)
def test_extension_mapping(extension: str, expected: str) -> None:
    assert get_language_for_extension(extension) == expected


@pytest.mark.parametrize("extension", [".xyz", "", ".", "py"])
def test_unknown_extension_returns_none(extension: str) -> None:
    assert get_language_for_extension(extension) is None


def test_filename_takes_priority_over_content() -> None:
    assert detect_language("print('hi')", file_name="main.java") == "java"


def test_filename_with_uppercase_extension() -> None:
    assert detect_language("", file_name="Main.JAVA") == "java"


def test_shebang_python() -> None:
    assert detect_language("#!/usr/bin/env python3\nprint(1)\n") == "python"


def test_shebang_node() -> None:
    assert detect_language("#!/usr/bin/env node\nconsole.log(1)\n") == "javascript"


def test_shebang_used_when_extension_unknown() -> None:
    assert detect_language("#!/usr/bin/python\nx = 1\n", file_name="script") == "python"


def test_content_python() -> None:
    assert detect_language("def foo(x):\n    return x\n\nimport os\n") == "python"


def test_content_java() -> None:
    code = (
        "public class A {\n  public static void main(String[] args) {\n"
        "    System.out.println(1);\n  }\n}\n"
    )
    assert detect_language(code) == "java"


def test_content_javascript() -> None:
    code = "const a = () => { console.log(1); };\nfunction f() {}\n"
    assert detect_language(code) == "javascript"


def test_content_c() -> None:
    assert detect_language("#include <stdio.h>\nint main() { return 0; }\n") == "c"


def test_content_cpp() -> None:
    code = "#include <iostream>\nint main() { std::cout << 1; }\n"
    assert detect_language(code) == "cpp"


def test_content_html() -> None:
    assert detect_language("<!DOCTYPE html><html><body></body></html>") == "html"


def test_content_css() -> None:
    assert detect_language("body {\n  color: red;\n}\n.a { margin: 0; }\n") == "css"


def test_plain_prose_is_text() -> None:
    assert detect_language("hello world this is text") == "text"


def test_empty_content_is_text() -> None:
    assert detect_language("") == "text"


def test_unknown_extension_falls_back_to_content() -> None:
    assert detect_language("def f():\n    pass\n", file_name="notes.zzz") == "python"


def test_dominant_language_by_line_count() -> None:
    files = [("a.py", "x = 1\ny = 2\nz = 3\n"), ("b.js", "var a = 1;\n")]
    assert detect_dominant_language(files) == "python"


def test_dominant_language_ignores_text_and_markdown_when_code_present() -> None:
    files = [("README.md", "a\nb\nc\nd\ne\n"), ("n.txt", "1\n2\n3\n"), ("a.py", "x = 1\n")]
    assert detect_dominant_language(files) == "python"


def test_dominant_language_only_docs() -> None:
    files = [("README.md", "# hi\n"), ("n.txt", "1\n2\n")]
    assert detect_dominant_language(files) == "text"


def test_dominant_language_empty_is_none() -> None:
    assert detect_dominant_language([]) is None


def test_dominant_language_tie_is_deterministic() -> None:
    files = [("b.js", "a\n"), ("a.py", "a\n")]
    assert detect_dominant_language(files) == "javascript"


def test_lexer_alias_for_highlighting() -> None:
    assert get_lexer_alias("python") == "python"
    assert get_lexer_alias("cpp") == "cpp"
    assert get_lexer_alias("text") == "text"
    assert get_lexer_alias("nonsense") == "text"


@pytest.mark.parametrize("file_name", [".bashrc", "trailing.", "noext"])
def test_dotfile_or_no_extension_uses_content(file_name: str) -> None:
    assert detect_language("def f():\n    pass\n", file_name=file_name) == "python"


def test_pygments_fallback_is_used_for_unmatched_content(monkeypatch: pytest.MonkeyPatch) -> None:
    from pygments.lexers import get_lexer_by_name
    from src.services.code_analysis import language_detector

    monkeypatch.setattr(language_detector, "guess_lexer", lambda _c: get_lexer_by_name("java"))
    assert detect_language("zzz qqq") == "java"


def test_pygments_failure_falls_back_to_text(monkeypatch: pytest.MonkeyPatch) -> None:
    from pygments.util import ClassNotFound
    from src.services.code_analysis import language_detector

    def boom(_content: str) -> None:
        raise ClassNotFound("none")

    monkeypatch.setattr(language_detector, "guess_lexer", boom)
    assert detect_language("zzz qqq") == "text"


def test_unknown_shebang_falls_through_to_text() -> None:
    assert detect_language("#!/bin/sh\nzzz qqq\n") == "text"

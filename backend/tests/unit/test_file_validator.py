import pytest
from src.models.code_file import SUPPORTED_EXTENSIONS
from src.models.uploaded_code import MAX_UPLOAD_SIZE_BYTES
from src.utils import file_validator
from src.utils.file_validator import (
    EXCLUDED_DIRECTORIES,
    MAX_FILES_PER_UPLOAD,
    FileValidationError,
    get_extension,
    is_binary,
    is_excluded_path,
    validate_code_file,
    validate_extension,
    validate_file_count,
    validate_not_binary,
    validate_size,
    validate_upload,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def _code(error: pytest.ExceptionInfo[FileValidationError]) -> str:
    return error.value.code


def test_limits_follow_the_spec():
    assert MAX_FILES_PER_UPLOAD == 20  # FR-018
    assert file_validator.MAX_UPLOAD_SIZE_BYTES == MAX_UPLOAD_SIZE_BYTES == 10 * 1024 * 1024
    assert file_validator.SUPPORTED_EXTENSIONS == SUPPORTED_EXTENSIONS


def test_validation_error_is_a_value_error_with_code_and_message():
    error = FileValidationError("too_big", "너무 큽니다")
    assert isinstance(error, ValueError)
    assert error.code == "too_big"
    assert str(error) == "너무 큽니다"


# --- get_extension -----------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("main.py", ".py"),
        ("App.JSX", ".jsx"),
        ("archive.tar.gz", ".gz"),
        ("src/components/App.tsx", ".tsx"),
        ("Makefile", ""),
        (".gitignore", ""),
        ("trailing.", ""),
        ("", ""),
    ],
)
def test_get_extension_is_lowercase_with_dot(name, expected):
    assert get_extension(name) == expected


# --- extension ---------------------------------------------------------------


@pytest.mark.parametrize("extension", SUPPORTED_EXTENSIONS)
def test_every_supported_extension_is_accepted(extension):
    assert validate_extension(f"file{extension}") == extension


def test_extension_check_is_case_insensitive():
    assert validate_extension("Main.PY") == ".py"


@pytest.mark.parametrize("name", ["virus.exe", "image.png", "notes.docx", "Makefile", "data.json"])
def test_unsupported_extension_is_rejected(name):
    with pytest.raises(FileValidationError) as error:
        validate_extension(name)
    assert _code(error) == "unsupported_extension"
    assert name in str(error.value)


# --- size --------------------------------------------------------------------


def test_size_at_the_limit_is_accepted():
    validate_size(MAX_UPLOAD_SIZE_BYTES)


def test_size_over_the_limit_is_rejected_with_10mb_message():
    with pytest.raises(FileValidationError) as error:
        validate_size(MAX_UPLOAD_SIZE_BYTES + 1)
    assert _code(error) == "file_too_large"
    assert "10MB" in str(error.value)


def test_negative_size_is_rejected():
    with pytest.raises(FileValidationError) as error:
        validate_size(-1)
    assert _code(error) == "invalid_size"


# --- binary detection --------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"print('hello')\n",
        "안녕하세요 — 한글 주석\n".encode(),
        b"\xef\xbb\xbfconst a = 1;\n",  # UTF-8 BOM
        b"line1\r\nline2\ttabbed\n",
    ],
)
def test_text_is_not_binary(content):
    assert is_binary(content) is False


@pytest.mark.parametrize(
    "content",
    [
        PNG_HEADER,
        b"\xff\xd8\xff\xe0\x00\x10JFIF",  # JPEG
        b"GIF89a\x01\x00\x01\x00",
        b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n",
        b"PK\x03\x04\x14\x00\x00\x00",  # ZIP / JAR / DOCX
        b"MZ\x90\x00\x03\x00\x00\x00",  # Windows executable
        b"\x7fELF\x02\x01\x01\x00",
        b"text before\x00text after",  # NUL byte
        b"\xff\xfe\xfd\xfc not utf-8",
    ],
)
def test_binary_content_is_detected(content):
    assert is_binary(content) is True


def test_multibyte_character_cut_at_the_sample_boundary_is_not_binary():
    # "한" is 3 bytes; the 8000-byte sample ends in the middle of a character.
    content = b"a" * 7999 + "한".encode() + b"b" * 100
    assert is_binary(content) is False


def test_nul_byte_after_the_sample_is_not_checked():
    assert is_binary(b"a" * 9000 + b"\x00") is False


def test_validate_not_binary_rejects_with_spec_message():
    with pytest.raises(FileValidationError) as error:
        validate_not_binary("logo.py", PNG_HEADER)
    assert _code(error) == "binary_file"
    assert "logo.py" in str(error.value)
    validate_not_binary("ok.py", b"x = 1\n")


# --- single file -------------------------------------------------------------


def test_valid_code_file_returns_its_extension():
    assert validate_code_file("src/App.jsx", b"export default 1\n") == ".jsx"


def test_binary_content_with_a_code_extension_is_rejected():
    with pytest.raises(FileValidationError) as error:
        validate_code_file("fake.py", PNG_HEADER)
    assert _code(error) == "binary_file"


def test_extension_is_checked_before_content():
    with pytest.raises(FileValidationError) as error:
        validate_code_file("logo.png", PNG_HEADER)
    assert _code(error) == "unsupported_extension"


def test_oversized_file_is_rejected():
    with pytest.raises(FileValidationError) as error:
        validate_code_file("big.txt", b"a" * (MAX_UPLOAD_SIZE_BYTES + 1))
    assert _code(error) == "file_too_large"


# --- file count --------------------------------------------------------------


@pytest.mark.parametrize("count", [1, 5, MAX_FILES_PER_UPLOAD])
def test_file_count_within_1_to_20_is_accepted(count):
    validate_file_count(count)


def test_zero_files_is_rejected():
    with pytest.raises(FileValidationError) as error:
        validate_file_count(0)
    assert _code(error) == "no_files"


def test_more_than_20_files_is_rejected_with_spec_message():
    with pytest.raises(FileValidationError) as error:
        validate_file_count(MAX_FILES_PER_UPLOAD + 1)
    assert _code(error) == "too_many_files"
    assert "20" in str(error.value)


# --- whole upload ------------------------------------------------------------


def test_valid_upload_returns_extensions_in_order():
    files = [("src/App.jsx", b"a"), ("src/utils.js", b"b"), ("public/index.html", b"<p>")]
    assert validate_upload(files) == [".jsx", ".js", ".html"]


def test_empty_upload_is_rejected():
    with pytest.raises(FileValidationError) as error:
        validate_upload([])
    assert _code(error) == "no_files"


def test_upload_with_too_many_files_is_rejected_before_looking_at_content():
    files = [(f"f{i}.py", PNG_HEADER) for i in range(MAX_FILES_PER_UPLOAD + 1)]
    with pytest.raises(FileValidationError) as error:
        validate_upload(files)
    assert _code(error) == "too_many_files"


def test_upload_total_over_10mb_is_rejected_even_if_each_file_is_small():
    chunk = b"a" * (MAX_UPLOAD_SIZE_BYTES // 2 + 1)
    with pytest.raises(FileValidationError) as error:
        validate_upload([("a.txt", chunk), ("b.txt", chunk)])
    assert _code(error) == "upload_too_large"
    assert "10MB" in str(error.value)


def test_upload_total_exactly_at_the_limit_is_accepted():
    half = b"a" * (MAX_UPLOAD_SIZE_BYTES // 2)
    assert validate_upload([("a.txt", half), ("b.txt", half)]) == [".txt", ".txt"]


def test_upload_with_one_bad_file_is_rejected():
    with pytest.raises(FileValidationError) as error:
        validate_upload([("ok.py", b"x = 1\n"), ("bad.exe", b"MZ")])
    assert _code(error) == "unsupported_extension"


# --- excluded folders --------------------------------------------------------


def test_excluded_directories_follow_the_spec():
    assert {".git", "node_modules", "__pycache__"} <= set(EXCLUDED_DIRECTORIES)


@pytest.mark.parametrize(
    "path",
    [
        ".git/config",
        "node_modules/react/index.js",
        "src/__pycache__/a.py",
        "app/node_modules/x.js",
        "src\\node_modules\\x.js",
        "./.git/HEAD",
    ],
)
def test_paths_inside_excluded_folders_are_excluded(path):
    assert is_excluded_path(path) is True


@pytest.mark.parametrize(
    "path",
    ["src/App.jsx", "main.py", "my_node_modules/a.js", "docs/.github/readme.md", ".gitignore"],
)
def test_other_paths_are_not_excluded(path):
    assert is_excluded_path(path) is False

"""Upload validation: extension whitelist, size limits, binary detection, file count (FR-014~018).

Pure functions with no I/O. Every rule failure raises FileValidationError carrying a stable
``code`` (for the API layer to map) and a Korean message that is safe to show to the user.
"""

import codecs
from collections.abc import Sequence

from src.models.code_file import SUPPORTED_EXTENSIONS
from src.models.uploaded_code import MAX_UPLOAD_SIZE_BYTES

__all__ = [
    "EXCLUDED_DIRECTORIES",
    "MAX_FILES_PER_UPLOAD",
    "MAX_UPLOAD_SIZE_BYTES",
    "SUPPORTED_EXTENSIONS",
    "FileValidationError",
    "get_extension",
    "is_binary",
    "is_excluded_path",
    "validate_code_file",
    "validate_extension",
    "validate_file_count",
    "validate_not_binary",
    "validate_size",
    "validate_upload",
]

MAX_FILES_PER_UPLOAD = 20
EXCLUDED_DIRECTORIES = (".git", "node_modules", "__pycache__")

_MAX_UPLOAD_MB = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
_BINARY_SAMPLE_BYTES = 8000
_BINARY_SIGNATURES = (
    b"\x89PNG",
    b"\xff\xd8\xff",  # JPEG
    b"GIF87a",
    b"GIF89a",
    b"%PDF-",
    b"PK\x03\x04",  # ZIP, JAR, DOCX
    b"\x7fELF",
)


class FileValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def get_extension(file_name: str) -> str:
    """Lowercase extension including the dot; empty for dotfiles, no extension or trailing dot."""
    base_name = file_name.replace("\\", "/").rsplit("/", 1)[-1]
    dot = base_name.rfind(".")
    if dot <= 0 or dot == len(base_name) - 1:
        return ""
    return base_name[dot:].lower()


def validate_extension(file_name: str) -> str:
    extension = get_extension(file_name)
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(SUPPORTED_EXTENSIONS)
        raise FileValidationError(
            "unsupported_extension",
            f"지원하지 않는 파일 형식입니다: {file_name}. 지원 확장자: {supported}",
        )
    return extension


def validate_size(size_bytes: int) -> None:
    if size_bytes < 0:
        raise FileValidationError("invalid_size", "파일 크기가 올바르지 않습니다.")
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise FileValidationError(
            "file_too_large",
            " ".join(
                (
                    f"파일 크기가 {_MAX_UPLOAD_MB}MB를 초과합니다.",
                    "더 작은 파일을 선택하거나 코드를 여러 태스크로 나누어 업로드하세요.",
                )
            ),
        )


def is_binary(content: bytes) -> bool:
    """Known binary signature, a NUL byte, or invalid UTF-8 within the first 8000 bytes."""
    sample = content[:_BINARY_SAMPLE_BYTES]
    if sample.startswith(_BINARY_SIGNATURES) or b"\x00" in sample:
        return True
    try:
        # Not final: a multibyte character cut off at the sample boundary is not an error.
        codecs.getincrementaldecoder("utf-8")().decode(sample, final=False)
    except UnicodeDecodeError:
        return True
    return False


def validate_not_binary(file_name: str, content: bytes) -> None:
    if is_binary(content):
        raise FileValidationError(
            "binary_file",
            " ".join(
                (
                    f"소스 코드 텍스트 파일만 업로드할 수 있습니다: {file_name}.",
                    ".py, .js, .html 등 텍스트 기반 코드 파일을 올려주세요.",
                )
            ),
        )


def validate_code_file(file_name: str, content: bytes) -> str:
    """Check one file (extension, then size, then content) and return its extension."""
    extension = validate_extension(file_name)
    validate_size(len(content))
    validate_not_binary(file_name, content)
    return extension


def validate_file_count(count: int) -> None:
    if count < 1:
        raise FileValidationError("no_files", "업로드할 파일을 한 개 이상 선택하세요.")
    if count > MAX_FILES_PER_UPLOAD:
        raise FileValidationError(
            "too_many_files",
            " ".join(
                (
                    f"업로드당 최대 {MAX_FILES_PER_UPLOAD}개 파일까지 가능합니다.",
                    "파일 수를 줄이거나 폴더 업로드를 사용하세요.",
                )
            ),
        )


def validate_upload(files: Sequence[tuple[str, bytes]]) -> list[str]:
    """Validate a whole upload of (file_name, content) pairs; return extensions in order."""
    validate_file_count(len(files))
    if sum(len(content) for _, content in files) > MAX_UPLOAD_SIZE_BYTES:
        raise FileValidationError(
            "upload_too_large",
            " ".join(
                (
                    f"업로드 전체 크기가 {_MAX_UPLOAD_MB}MB를 초과합니다.",
                    "코드를 여러 태스크로 나누어 업로드하세요.",
                )
            ),
        )
    return [validate_code_file(name, content) for name, content in files]


def is_excluded_path(path: str) -> bool:
    """True if any folder in the path is a build/system folder skipped on folder upload."""
    parts = path.replace("\\", "/").split("/")
    return any(part in EXCLUDED_DIRECTORIES for part in parts)

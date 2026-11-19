"""Turns file / folder / pasted-code uploads into stored files plus UploadedCode and CodeFile rows.

Two steps so a bad upload never consumes a task number or touches the disk:
prepare_*() validates and normalizes (pure, no I/O), then store() writes after the task exists.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import AppError, NotFoundException
from src.models import CodeFile, Task, UploadedCode
from src.services.code_analysis import file_storage
from src.services.code_analysis.complexity_analyzer import analyze_complexity
from src.services.code_analysis.language_detector import (
    detect_dominant_language,
    detect_language,
)
from src.utils.file_validator import (
    FileValidationError,
    is_excluded_path,
    validate_upload,
)

__all__ = [
    "PASTE_LANGUAGES",
    "CodeFileContent",
    "CodeUploadService",
    "PreparedFile",
    "PreparedUpload",
]

# Language dropdown value (FR-013) -> extension of the file the pasted code is saved as.
PASTE_LANGUAGES = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "html": ".html",
    "css": ".css",
    "java": ".java",
    "cpp": ".cpp",
    "c": ".c",
    "text": ".txt",
    "markdown": ".md",
}
_TOO_LARGE_CODES = frozenset({"file_too_large", "upload_too_large"})
_IGNORED_FILE_NAMES = frozenset({".DS_Store"})  # FR-017
_MIME_TYPE = "text/plain"  # binary files are rejected, so every stored file is text
_FILE_NOT_FOUND_MESSAGE = "저장된 코드 파일을 찾을 수 없습니다."
_NO_CODE_MESSAGE = "이 태스크에는 업로드된 코드가 없습니다."


@dataclass(frozen=True)
class PreparedFile:
    name: str
    extension: str
    content: bytes
    path: str | None  # relative path inside an uploaded folder; None for file/paste


@dataclass(frozen=True)
class PreparedUpload:
    method: str  # one of Task.UPLOAD_METHODS
    files: list[PreparedFile]


@dataclass(frozen=True)
class CodeFileContent:
    file: CodeFile
    content: str
    language: str


def _to_app_error(error: FileValidationError) -> AppError:
    status = 413 if error.code in _TOO_LARGE_CODES else 400
    return AppError(status, error.code, str(error))


def _base_name(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _validated(method: str, entries: Sequence[tuple[str, str | None, bytes]]) -> PreparedUpload:
    """entries are (name, relative path, content); raises AppError on the first rule broken."""
    try:
        extensions = validate_upload([(name, content) for name, _, content in entries])
    except FileValidationError as error:
        raise _to_app_error(error) from error
    return PreparedUpload(
        method,
        [
            PreparedFile(name, extension, content, path)
            for (name, path, content), extension in zip(entries, extensions, strict=True)
        ],
    )


class CodeUploadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def prepare_files(self, files: Sequence[tuple[str, bytes]]) -> PreparedUpload:
        """Plain file upload: (file name, content) pairs."""
        return _validated("file", [(_base_name(name), None, content) for name, content in files])

    def prepare_folder(self, files: Sequence[tuple[str, bytes]]) -> PreparedUpload:
        """Folder upload: (relative path, content) pairs; build/system entries are skipped."""
        entries: list[tuple[str, str | None, bytes]] = []
        for raw_path, content in files:
            try:
                path = file_storage.safe_relative_path(raw_path)
            except FileValidationError as error:
                raise _to_app_error(error) from error
            name = _base_name(path)
            if is_excluded_path(path) or name in _IGNORED_FILE_NAMES:
                continue
            entries.append((name, path, content))
        return _validated("folder", entries)

    def prepare_paste(self, code: str, language: str) -> PreparedUpload:
        """Pasted code plus the language picked in the dropdown."""
        extension = PASTE_LANGUAGES.get(language.strip().lower())
        if extension is None:
            raise AppError(
                400,
                "unsupported_language",
                f"지원하지 않는 언어입니다: {language}. 지원 언어: {', '.join(PASTE_LANGUAGES)}",
            )
        if not code.strip():
            raise AppError(400, "empty_code", "붙여넣은 코드가 비어 있습니다. 코드를 입력하세요.")
        return _validated("paste", [(f"code{extension}", None, code.encode("utf-8"))])

    async def store(self, user_id: uuid.UUID, task: Task, upload: PreparedUpload) -> UploadedCode:
        """Save the files, analyze them and add the rows. The task must already be flushed."""
        texts = [(f.name, f.content.decode("utf-8", errors="replace")) for f in upload.files]
        complexity = analyze_complexity(texts)
        uploaded = UploadedCode(
            task=task,
            detected_language=detect_dominant_language(texts),
            complexity_level=complexity.level,
            total_lines=complexity.total_lines,
            total_files=len(upload.files),
            upload_size_bytes=sum(len(f.content) for f in upload.files),
        )
        try:
            code_files = [
                CodeFile(
                    uploaded_code=uploaded,
                    file_name=f.name,
                    file_path=f.path,
                    file_extension=f.extension,
                    file_size_bytes=len(f.content),
                    storage_path=file_storage.save_file(user_id, task.id, f.extension, f.content),
                    mime_type=_MIME_TYPE,
                )
                for f in upload.files
            ]
            self._session.add(uploaded)
            self._session.add_all(code_files)
            await self._session.flush()
        except Exception:
            file_storage.delete_task_files(user_id, task.id)
            raise
        return uploaded

    async def get_code(self, task: Task) -> list[CodeFileContent]:
        """The task's uploaded files with their text, in path/name order."""
        if task.uploaded_code is None:
            raise NotFoundException(_NO_CODE_MESSAGE)
        result = await self._session.execute(
            select(CodeFile)
            .where(CodeFile.uploaded_code_id == task.uploaded_code.id)
            .order_by(CodeFile.file_path.asc(), CodeFile.file_name.asc())
        )
        contents = []
        for code_file in result.scalars().all():
            try:
                raw = file_storage.read_file(code_file.storage_path)
            except (FileNotFoundError, FileValidationError) as error:
                raise NotFoundException(_FILE_NOT_FOUND_MESSAGE) from error
            text = raw.decode("utf-8", errors="replace")
            contents.append(
                CodeFileContent(code_file, text, detect_language(text, code_file.file_name))
            )
        return contents

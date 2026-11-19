// backend/src/utils/file_validator.py 와 같은 규칙(FR-014~018)과 한국어 문구를 쓴다.
export const SUPPORTED_EXTENSIONS = [
  '.py',
  '.js',
  '.ts',
  '.jsx',
  '.tsx',
  '.html',
  '.css',
  '.java',
  '.cpp',
  '.c',
  '.txt',
  '.md',
]
export const MAX_FILES_PER_UPLOAD = 20
export const MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
export const EXCLUDED_DIRECTORIES = ['.git', 'node_modules', '__pycache__']
const EXCLUDED_FILE_NAMES = ['.DS_Store']

export const MIN_TASK_TITLE_LENGTH = 5
export const MAX_TASK_DESCRIPTION_LENGTH = 500

const FILE_TOO_LARGE_MESSAGE =
  '파일 업로드 실패: 파일 크기가 10MB를 초과합니다. 더 작은 파일을 선택하거나 코드를 여러 태스크로 나누어 업로드하세요.'
const UPLOAD_TOO_LARGE_MESSAGE =
  '업로드 전체 크기가 10MB를 초과합니다. 코드를 여러 태스크로 나누어 업로드하세요.'

function extensionOf(fileName: string): string {
  const baseName = fileName.slice(fileName.lastIndexOf('/') + 1)
  const dot = baseName.lastIndexOf('.')
  if (dot <= 0 || dot === baseName.length - 1) return ''
  return baseName.slice(dot).toLowerCase()
}

export function isExcludedPath(path: string): boolean {
  const parts = path.replace(/\\/g, '/').split('/')
  return parts.some(
    (part) => EXCLUDED_DIRECTORIES.includes(part) || EXCLUDED_FILE_NAMES.includes(part),
  )
}

export function validateUploadFiles(files: File[]): string | null {
  if (files.length < 1) return '업로드할 파일을 한 개 이상 선택하세요.'
  if (files.length > MAX_FILES_PER_UPLOAD) {
    return `업로드당 최대 ${MAX_FILES_PER_UPLOAD}개 파일까지 가능합니다. 파일 수를 줄이거나 폴더 업로드를 사용하세요.`
  }
  for (const file of files) {
    if (!SUPPORTED_EXTENSIONS.includes(extensionOf(file.name))) {
      return `지원하지 않는 파일 형식입니다: ${file.name}. 지원 확장자: ${SUPPORTED_EXTENSIONS.join(', ')}`
    }
    if (file.size > MAX_UPLOAD_SIZE_BYTES) return FILE_TOO_LARGE_MESSAGE
  }
  const totalSize = files.reduce((sum, file) => sum + file.size, 0)
  return totalSize > MAX_UPLOAD_SIZE_BYTES ? UPLOAD_TOO_LARGE_MESSAGE : null
}

export function validatePaste(code: string, language: string): string | null {
  if (code.trim() === '') return '붙여넣을 코드를 입력하세요.'
  if (language === '') return '프로그래밍 언어를 선택하세요.'
  if (new Blob([code]).size > MAX_UPLOAD_SIZE_BYTES) return FILE_TOO_LARGE_MESSAGE
  return null
}

export function validateTaskTitle(title: string): string | null {
  if (title.trim().length < MIN_TASK_TITLE_LENGTH) {
    return `태스크 제목은 최소 ${MIN_TASK_TITLE_LENGTH}자 이상이어야 합니다.`
  }
  return null
}

export function validateTaskDescription(description: string): string | null {
  if (description.trim().length > MAX_TASK_DESCRIPTION_LENGTH) {
    return `태스크 설명은 최대 ${MAX_TASK_DESCRIPTION_LENGTH}자까지 입력 가능합니다.`
  }
  return null
}

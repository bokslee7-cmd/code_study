import {
  EXCLUDED_DIRECTORIES,
  MAX_FILES_PER_UPLOAD,
  SUPPORTED_EXTENSIONS,
  isExcludedPath,
  validatePaste,
  validateTaskDescription,
  validateTaskTitle,
  validateUploadFiles,
} from '../../src/lib/upload-validation'
import { MB, makeFile } from '../fixtures/files'

describe('상수', () => {
  it('지원 확장자 12종, 최대 20개, 제외 폴더 3종', () => {
    expect(SUPPORTED_EXTENSIONS).toEqual([
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
    ])
    expect(MAX_FILES_PER_UPLOAD).toBe(20)
    expect(EXCLUDED_DIRECTORIES).toEqual(['.git', 'node_modules', '__pycache__'])
  })
})

describe('validateUploadFiles', () => {
  it('정상 파일이면 null', () => {
    expect(validateUploadFiles([makeFile('a.py'), makeFile('B.TSX')])).toBeNull()
  })

  it('파일이 없으면 안내한다', () => {
    expect(validateUploadFiles([])).toBe('업로드할 파일을 한 개 이상 선택하세요.')
  })

  it('21개부터 거부한다(20개는 통과)', () => {
    const twenty = Array.from({ length: 20 }, (_, i) => makeFile(`f${i}.py`))
    expect(validateUploadFiles(twenty)).toBeNull()
    expect(validateUploadFiles([...twenty, makeFile('x.py')])).toBe(
      '업로드당 최대 20개 파일까지 가능합니다. 파일 수를 줄이거나 폴더 업로드를 사용하세요.',
    )
  })

  it('지원하지 않는 확장자는 파일명과 지원 목록을 알려준다', () => {
    expect(validateUploadFiles([makeFile('photo.png')])).toBe(
      '지원하지 않는 파일 형식입니다: photo.png. 지원 확장자: .py, .js, .ts, .jsx, .tsx, .html, .css, .java, .cpp, .c, .txt, .md',
    )
  })

  it('확장자가 없는 파일과 점으로 시작하는 파일도 거부한다', () => {
    expect(validateUploadFiles([makeFile('Makefile')])).toMatch('지원하지 않는 파일 형식')
    expect(validateUploadFiles([makeFile('.py')])).toMatch('지원하지 않는 파일 형식')
  })

  it('파일 하나가 10MB를 넘으면 거부하고 정확히 10MB는 통과한다', () => {
    expect(validateUploadFiles([makeFile('a.py', 10 * MB)])).toBeNull()
    expect(validateUploadFiles([makeFile('a.py', 10 * MB + 1)])).toBe(
      '파일 업로드 실패: 파일 크기가 10MB를 초과합니다. 더 작은 파일을 선택하거나 코드를 여러 태스크로 나누어 업로드하세요.',
    )
  })

  it('합계가 10MB를 넘으면 거부한다', () => {
    expect(validateUploadFiles([makeFile('a.py', 6 * MB), makeFile('b.py', 5 * MB)])).toBe(
      '업로드 전체 크기가 10MB를 초과합니다. 코드를 여러 태스크로 나누어 업로드하세요.',
    )
  })
})

describe('isExcludedPath', () => {
  it.each([
    'proj/.git/config',
    'proj/node_modules/lib/index.js',
    'proj/src/__pycache__/a.pyc',
    'proj/.DS_Store',
    '.DS_Store',
    'proj\\node_modules\\x.js',
  ])('%s 는 제외한다', (path) => {
    expect(isExcludedPath(path)).toBe(true)
  })

  it.each(['proj/src/app.py', 'proj/node_modules_notes.md', 'proj/my.git/a.py'])(
    '%s 는 제외하지 않는다',
    (path) => {
      expect(isExcludedPath(path)).toBe(false)
    },
  )
})

describe('validatePaste', () => {
  it('코드가 비어 있으면 안내한다', () => {
    expect(validatePaste('  \n ', 'python')).toBe('붙여넣을 코드를 입력하세요.')
  })

  it('언어를 고르지 않으면 안내한다', () => {
    expect(validatePaste('print(1)', '')).toBe('프로그래밍 언어를 선택하세요.')
  })

  it('10MB를 넘으면 거부한다', () => {
    expect(validatePaste('a'.repeat(10 * MB + 1), 'python')).toMatch('10MB를 초과합니다')
  })

  it('정상이면 null', () => {
    expect(validatePaste('print(1)', 'python')).toBeNull()
  })
})

describe('validateTaskTitle / validateTaskDescription', () => {
  it('제목은 공백 제거 후 5자 이상이어야 한다', () => {
    expect(validateTaskTitle('  abcd ')).toBe('태스크 제목은 최소 5자 이상이어야 합니다.')
    expect(validateTaskTitle('abcde')).toBeNull()
  })

  it('설명은 500자까지 허용한다', () => {
    expect(validateTaskDescription('a'.repeat(500))).toBeNull()
    expect(validateTaskDescription('a'.repeat(501))).toBe(
      '태스크 설명은 최대 500자까지 입력 가능합니다.',
    )
  })
})

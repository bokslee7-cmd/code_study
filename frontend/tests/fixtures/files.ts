// 실제로 큰 메모리를 쓰지 않고 크기만 속인 File을 만든다.
export function makeFile(name: string, size = 10, relativePath?: string): File {
  const file = new File(['x'.repeat(Math.min(size, 10))], name, {
    type: 'text/plain',
    lastModified: 1_700_000_000_000,
  })
  Object.defineProperty(file, 'size', { value: size })
  if (relativePath !== undefined) {
    Object.defineProperty(file, 'webkitRelativePath', { value: relativePath })
  }
  return file
}

export const MB = 1024 * 1024

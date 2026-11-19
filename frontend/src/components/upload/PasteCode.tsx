import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

export interface PasteCodeValue {
  code: string
  language: string
}

interface PasteCodeProps {
  value: PasteCodeValue
  onChange: (value: PasteCodeValue) => void
  error?: string | null
  disabled?: boolean
}

const PASTE_LANGUAGES = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'html', label: 'HTML' },
  { value: 'css', label: 'CSS' },
  { value: 'java', label: 'Java' },
  { value: 'cpp', label: 'C++' },
  { value: 'c', label: 'C' },
]

export default function PasteCode({ value, onChange, error, disabled = false }: PasteCodeProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="paste-code-language">프로그래밍 언어</Label>
        <select
          id="paste-code-language"
          value={value.language}
          disabled={disabled}
          onChange={(event) => onChange({ ...value, language: event.target.value })}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
        >
          <option value="">언어 선택</option>
          {PASTE_LANGUAGES.map((language) => (
            <option key={language.value} value={language.value}>
              {language.label}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="paste-code-text">코드</Label>
        <Textarea
          id="paste-code-text"
          value={value.code}
          disabled={disabled}
          rows={10}
          spellCheck={false}
          className="font-mono"
          onChange={(event) => onChange({ ...value, code: event.target.value })}
        />
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

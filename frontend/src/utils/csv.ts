/**
 * CSV helpers shared by the data-export entry points.
 *
 * Values are escaped per RFC 4180 and the output is prefixed with a BOM so
 * spreadsheet apps open UTF-8 Chinese columns correctly.
 */
export interface CsvColumn<T> {
  key: string
  label: string
  value: (row: T) => string | number | null | undefined
}

/** Wraps a value in quotes and doubles any embedded quote characters. */
export const escapeCsvValue = (value: unknown): string => {
  if (value === null || value === undefined) return ''
  const text = String(value)
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

/** Renders rows as CSV using the supplied column order and labels. */
export const toCsv = <T>(rows: readonly T[], columns: readonly CsvColumn<T>[]): string => {
  const escapeRow = (cells: readonly unknown[]) => cells.map(escapeCsvValue).join(',')
  const header = escapeRow(columns.map((column) => column.label))
  const body = rows.map((row) => escapeRow(columns.map((column) => column.value(row))))
  return `\uFEFF${[header, ...body].join('\r\n')}\r\n`
}

/** Suggests `<name>-YYYY-MM-DD.csv` for export filenames. */
export const datedFilename = (name: string, date: Date = new Date()): string => {
  const pad = (value: number) => String(value).padStart(2, '0')
  const stamp = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  return `${name}-${stamp}.csv`
}

/**
 * Triggers a browser download for generated text. Returns false when a
 * document is unavailable (for example during SSR or unit tests).
 */
export const downloadTextFile = (
  filename: string,
  content: string,
  mime = 'text/csv;charset=utf-8',
): boolean => {
  if (typeof document === 'undefined') return false

  const url = URL.createObjectURL(new Blob([content], { type: mime }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
  return true
}

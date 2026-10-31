import { describe, expect, it } from 'vitest'
import { datedFilename, downloadTextFile, escapeCsvValue, toCsv } from './csv'

interface Row {
  name: string
  note: string | null
  score: number
}

describe('escapeCsvValue', () => {
  it('leaves plain values untouched', () => {
    expect(escapeCsvValue('深蹲')).toBe('深蹲')
    expect(escapeCsvValue(12)).toBe('12')
  })

  it('quotes values containing separators', () => {
    expect(escapeCsvValue('a,b')).toBe('"a,b"')
    expect(escapeCsvValue('line1\nline2')).toBe('"line1\nline2"')
  })

  it('doubles embedded quotes', () => {
    expect(escapeCsvValue('say "hi"')).toBe('"say ""hi"""')
  })

  it('renders null and undefined as empty cells', () => {
    expect(escapeCsvValue(null)).toBe('')
    expect(escapeCsvValue(undefined)).toBe('')
  })
})

describe('toCsv', () => {
  const columns = [
    { key: 'name', label: '动作', value: (row: Row) => row.name },
    { key: 'note', label: '备注', value: (row: Row) => row.note },
    { key: 'score', label: '评分', value: (row: Row) => row.score },
  ]

  it('writes a header row, CRLF line endings and a UTF-8 BOM', () => {
    const csv = toCsv<Row>([], columns)
    expect(csv.startsWith('\uFEFF')).toBe(true)
    expect(csv).toBe('\uFEFF动作,备注,评分\r\n')
  })

  it('escapes each data cell', () => {
    const csv = toCsv<Row>([{ name: '卧推, 上斜', note: null, score: 88 }], columns)
    expect(csv).toBe('\uFEFF动作,备注,评分\r\n"卧推, 上斜",,88\r\n')
  })
})

describe('datedFilename', () => {
  it('pads month and day', () => {
    expect(datedFilename('fitvision-training', new Date(2026, 0, 5))).toBe(
      'fitvision-training-2026-01-05.csv',
    )
  })
})

describe('downloadTextFile', () => {
  it('returns false when there is no document available', () => {
    expect(downloadTextFile('a.csv', 'content')).toBe(false)
  })
})

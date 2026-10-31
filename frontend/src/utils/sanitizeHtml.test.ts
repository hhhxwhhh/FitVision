import { describe, expect, it } from 'vitest'
import { formatRichText, sanitizeHtml } from './sanitizeHtml'

describe('sanitizeHtml', () => {
  it('keeps whitelisted structural tags', () => {
    expect(sanitizeHtml('<p>做得好</p>')).toBe('<p>做得好</p>')
    expect(sanitizeHtml('a<br>b')).toBe('a<br />b')
    expect(sanitizeHtml('<strong>核心收紧</strong>')).toBe('<strong>核心收紧</strong>')
  })

  it('strips every attribute so handlers cannot survive', () => {
    expect(sanitizeHtml('<p onclick="alert(1)">hi</p>')).toBe('<p>hi</p>')
    expect(sanitizeHtml('<img src="x" onerror="alert(1)">')).toBe('')
    expect(sanitizeHtml('<a href="javascript:alert(1)">click</a>')).toBe('click')
  })

  it('removes script blocks together with their content', () => {
    expect(sanitizeHtml('<script>alert("xss")</script>保持 keratin')).toBe('保持 keratin')
    expect(sanitizeHtml('<style>body{display:none}</style>ok')).toBe('ok')
  })

  it('keeps angle brackets that are not tags', () => {
    expect(sanitizeHtml('3 < 5 且 7 > 2')).toBe('3 &lt; 5 且 7 &gt; 2')
  })

  it('drops unknown tags but keeps their readable text', () => {
    expect(sanitizeHtml('<not-a-tag>text</not-a-tag>')).toBe('text')
    expect(sanitizeHtml('<div><p>保留</p></div>')).toBe('<p>保留</p>')
  })

  it('drops comments', () => {
    expect(sanitizeHtml('<!-- secret --><p>ok</p>')).toBe('<p>ok</p>')
  })

  it('handles empty input', () => {
    expect(sanitizeHtml('')).toBe('')
    expect(sanitizeHtml(null)).toBe('')
    expect(sanitizeHtml(undefined)).toBe('')
  })

  it('is idempotent for already-safe content', () => {
    const once = sanitizeHtml('<p>深蹲 4 组</p><ul><li>注意膝盖</li></ul>')
    expect(sanitizeHtml(once)).toBe(once)
  })
})

describe('formatRichText', () => {
  it('turns markdown bold into a strong tag', () => {
    expect(formatRichText('**核心收紧** 再做 2 组')).toBe('<p><strong>核心收紧</strong> 再做 2 组</p>')
  })

  it('converts single newlines to breaks and blank lines to paragraphs', () => {
    expect(formatRichText('第一行\n第二行')).toBe('<p>第一行<br />第二行</p>')
    expect(formatRichText('第一段\n\n第二段')).toBe('<p>第一段</p><p>第二段</p>')
  })

  it('sanitises hostile payloads hidden inside markdown', () => {
    const output = formatRichText('**注意**<script>alert(1)</script>')
    expect(output).not.toContain('script')
    expect(output).not.toContain('alert')
  })
})

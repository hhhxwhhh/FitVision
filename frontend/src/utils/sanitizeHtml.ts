/**
 * Conservative HTML sanitiser for AI-generated copy.
 *
 * The Rich text coming from the recommendation / analysis endpoints is not
 * trusted: it can contain markdown-style markup, stray tags copied from the
 * model output, or worse. Instead of pulling in a full sanitiser we whitelist
 * a small set of structural tags, drop every attribute (so there is nowhere
 * for event handlers or `javascript:` URLs to live) and escape anything that
 * is not a whitelisted tag.
 */
const ALLOWED_TAGS = new Set([
  'p',
  'br',
  'strong',
  'b',
  'em',
  'i',
  'u',
  's',
  'ul',
  'ol',
  'li',
  'h3',
  'h4',
  'blockquote',
  'code',
])

const VOID_TAGS = new Set(['br'])

/** Tags whose inner content is dropped together with the tag itself. */
const STRIP_CONTENT_TAGS = new Set(['script', 'style', 'iframe', 'object', 'embed', 'noscript'])

const escapeText = (text: string): string => text.replace(/</g, '&lt;').replace(/>/g, '&gt;')

/** Removes tags whose content should never reach the DOM, content included. */
const stripForbiddenBlocks = (html: string): string =>
  html.replace(
    new RegExp(`<\\s*(${[...STRIP_CONTENT_TAGS].join('|')})\\b[\\s\\S]*?<\\s*\\/\\s*\\1\\s*>`, 'gi'),
    '',
  )

const renderToken = (token: string): string => {
  const inner = token.slice(1, -1).trim()
  if (inner.startsWith('<!--')) return '' // drop comments entirely

  const isClosing = inner.startsWith('/')
  const match = /^\/?\s*([a-zA-Z][\w-]*)/.exec(inner)
  const name = match?.[1]?.toLowerCase()
  if (!name || !ALLOWED_TAGS.has(name)) return ''

  if (VOID_TAGS.has(name)) return `<${name} />`
  return isClosing ? `</${name}>` : `<${name}>`
}

/**
 * Returns a safe HTML fragment: only whitelisted tags survive, always without
 * attributes, and every other angle bracket is escaped.
 */
export const sanitizeHtml = (raw: string | null | undefined): string => {
  if (!raw) return ''

  const text = stripForbiddenBlocks(String(raw))
  let output = ''
  let index = 0

  while (index < text.length) {
    const openIndex = text.indexOf('<', index)
    if (openIndex === -1) {
      output += escapeText(text.slice(index))
      break
    }

    output += escapeText(text.slice(index, openIndex))

    // "<" only opens a tag when followed by a letter, a slash or "!".
    // Anything else (e.g. "3 < 5") is literal text and stays escaped.
    if (!/[a-zA-Z/!]/.test(text[openIndex + 1] ?? '')) {
      output += '&lt;'
      index = openIndex + 1
      continue
    }

    const closeIndex = text.indexOf('>', openIndex + 1)
    if (closeIndex === -1) {
      // Unterminated "<": nothing after it can be trusted as a tag.
      output += escapeText(text.slice(openIndex))
      break
    }

    output += renderToken(text.slice(openIndex, closeIndex + 1))
    index = closeIndex + 1
  }

  return output
}

/**
 * Renders the small markdown subset the AI responses rely on: `**bold**`
 * stays as an emphasised span, newlines become `<br />`. The result is always
 * sanitised, so callers can bind it with `v-html` safely.
 */
export const formatRichText = (raw: string | null | undefined): string => {
  if (!raw) return ''
  return sanitizeHtml(
    String(raw)
      .replace(/\*\*(.+?)\*\*/gs, '<strong>$1</strong>')
      .replace(/\r\n/g, '\n')
      .replace(/\n{2,}/g, '</p><p>')
      .replace(/\n/g, '<br />'),
  ).replace(/^/, '<p>').replace(/$/, '</p>')
}

// Global keyboard shortcuts: pure data + helpers so the behaviour can be unit
// tested without a DOM. The dialog/lifecycle lives in ShortcutsDialog.vue.

export interface ShortcutDef {
  keys: string
  label: string
}

export interface ShortcutGroup {
  title: string
  items: ShortcutDef[]
}

/** Leader key that prefixes navigation shortcuts (e.g. "g" then "t"). */
export const LEADER_KEY = 'g'

export const LEADER_MAP: Record<string, { path: string; label: string }> = {
  h: { path: '/', label: '首页' },
  t: { path: '/training', label: '智能训练' },
  e: { path: '/exercises', label: '动作百科' },
  a: { path: '/analytics', label: '数据中心' },
  g: { path: '/growth', label: '成长中心' },
  p: { path: '/profile', label: '个人中心' },
}

export const SHORTCUT_GROUPS: ShortcutGroup[] = [
  {
    title: '全局',
    items: [
      { keys: 'Ctrl / ⌘ + K', label: '打开命令面板' },
      { keys: '?', label: '显示快捷键' },
      { keys: 'Esc', label: '关闭弹层' },
    ],
  },
  {
    title: '快速导航（按 g 后再按）',
    items: [
      { keys: 'g h', label: '首页' },
      { keys: 'g t', label: '智能训练' },
      { keys: 'g e', label: '动作百科' },
      { keys: 'g a', label: '数据中心' },
      { keys: 'g g', label: '成长中心' },
      { keys: 'g p', label: '个人中心' },
    ],
  },
]

/** True when focus is in a field where keystrokes should be typed, not captured. */
export function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null
  if (!el) return false
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable === true
}

/** Resolve a leader-follow-up key to a navigation target (case-insensitive). */
export function resolveLeader(key: string): { path: string; label: string } | null {
  return LEADER_MAP[key.toLowerCase()] ?? null
}

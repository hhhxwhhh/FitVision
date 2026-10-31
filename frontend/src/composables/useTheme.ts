import { computed, ref } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'fitvision-theme'
const media = window.matchMedia('(prefers-color-scheme: dark)')

function readStoredMode(): ThemeMode {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system'
}

const mode = ref<ThemeMode>(readStoredMode())
const systemPrefersDark = ref(media.matches)

const resolved = computed<'light' | 'dark'>(() => {
  if (mode.value === 'system') return systemPrefersDark.value ? 'dark' : 'light'
  return mode.value
})

function applyTheme() {
  const isDark = resolved.value === 'dark'
  const root = document.documentElement
  root.classList.toggle('dark', isDark)
  root.dataset.theme = resolved.value
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', isDark ? '#070b16' : '#f6f7fb')
}

media.addEventListener('change', (event) => {
  systemPrefersDark.value = event.matches
  if (mode.value === 'system') applyTheme()
})

// Apply immediately so the shell matches the pre-paint theme set in index.html.
applyTheme()

export function useTheme() {
  const setMode = (next: ThemeMode) => {
    mode.value = next
    localStorage.setItem(STORAGE_KEY, next)
    applyTheme()
  }

  const toggle = () => {
    setMode(resolved.value === 'dark' ? 'light' : 'dark')
  }

  return { mode, resolved, setMode, toggle }
}

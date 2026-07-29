export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'theme'

let mediaQuery: MediaQueryList | null = null
let mediaListener: ((e: MediaQueryListEvent) => void) | null = null

function resolveEffectiveTheme(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return mode
}

function applyEffectiveTheme(mode: ThemeMode) {
  const effective = resolveEffectiveTheme(mode)
  document.documentElement.setAttribute('data-theme', effective)
  document.documentElement.setAttribute('data-theme-mode', mode)
}

function bindSystemListener(mode: ThemeMode) {
  unbindSystemListener()
  if (mode !== 'system') return
  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaListener = () => applyEffectiveTheme('system')
  mediaQuery.addEventListener('change', mediaListener)
}

function unbindSystemListener() {
  if (mediaQuery && mediaListener) {
    mediaQuery.removeEventListener('change', mediaListener)
  }
  mediaQuery = null
  mediaListener = null
}

export function getThemeMode(): ThemeMode {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored
  }
  return 'light'
}

export function setThemeMode(mode: ThemeMode) {
  localStorage.setItem(STORAGE_KEY, mode)
  applyEffectiveTheme(mode)
  bindSystemListener(mode)
}

export function initTheme() {
  const mode = getThemeMode()
  applyEffectiveTheme(mode)
  bindSystemListener(mode)
}

import { computed, onMounted, onUnmounted, ref } from 'vue'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const DISMISS_KEY = 'fitvision-install-dismissed'

/** Exposes a PWA install prompt when the browser supports it. */
export function usePwaInstall() {
  const deferredPrompt = ref<BeforeInstallPromptEvent | null>(null)
  const dismissed = ref(localStorage.getItem(DISMISS_KEY) === '1')
  const isStandalone = ref(
    window.matchMedia('(display-mode: standalone)').matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true,
  )

  const canInstall = computed(() => !!deferredPrompt.value && !dismissed.value && !isStandalone.value)

  const onBeforeInstall = (event: Event) => {
    event.preventDefault()
    deferredPrompt.value = event as BeforeInstallPromptEvent
  }

  const onInstalled = () => {
    deferredPrompt.value = null
    isStandalone.value = true
  }

  const install = async () => {
    if (!deferredPrompt.value) return false
    await deferredPrompt.value.prompt()
    const { outcome } = await deferredPrompt.value.userChoice
    if (outcome === 'accepted') {
      deferredPrompt.value = null
      return true
    }
    return false
  }

  const dismiss = () => {
    dismissed.value = true
    localStorage.setItem(DISMISS_KEY, '1')
  }

  onMounted(() => {
    window.addEventListener('beforeinstallprompt', onBeforeInstall)
    window.addEventListener('appinstalled', onInstalled)
  })

  onUnmounted(() => {
    window.removeEventListener('beforeinstallprompt', onBeforeInstall)
    window.removeEventListener('appinstalled', onInstalled)
  })

  return { canInstall, isStandalone, install, dismiss }
}

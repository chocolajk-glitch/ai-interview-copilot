import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { LLMProvider } from '@/api/types'

const STORAGE_KEY = 'ai-interview-copilot:settings:v1'

interface PersistedSettings {
  provider: LLMProvider
  topK: number
  temperature: number
  sessionId: string
  showReasoning: boolean
}

const DEFAULTS: PersistedSettings = {
  provider: 'qwen',
  topK: 3,
  temperature: 0.7,
  sessionId: cryptoRandomId(),
  showReasoning: true,
}

function cryptoRandomId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return (crypto as Crypto).randomUUID()
  }
  return 'sess-' + Math.random().toString(36).slice(2, 10)
}

function load(): PersistedSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...DEFAULTS, sessionId: cryptoRandomId() }
    return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULTS, sessionId: cryptoRandomId() }
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const initial = load()
  const provider = ref<LLMProvider>(initial.provider)
  const topK = ref<number>(initial.topK)
  const temperature = ref<number>(initial.temperature)
  const sessionId = ref<string>(initial.sessionId)
  const showReasoning = ref<boolean>(initial.showReasoning)

  watch(
    [provider, topK, temperature, sessionId, showReasoning],
    () => {
      const data: PersistedSettings = {
        provider: provider.value,
        topK: topK.value,
        temperature: temperature.value,
        sessionId: sessionId.value,
        showReasoning: showReasoning.value,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    },
    { deep: true },
  )

  function newSession() {
    sessionId.value = cryptoRandomId()
  }

  return { provider, topK, temperature, sessionId, showReasoning, newSession }
})

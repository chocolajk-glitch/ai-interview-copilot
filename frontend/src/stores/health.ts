import { defineStore } from 'pinia'
import { ref } from 'vue'
import { systemApi, type HealthInfo } from '@/api/system'

export const useHealthStore = defineStore('health', () => {
  const info = ref<HealthInfo | null>(null)
  const loading = ref(false)
  const lastChecked = ref<Date | null>(null)
  const error = ref<string | null>(null)

  async function check() {
    loading.value = true
    error.value = null
    try {
      info.value = await systemApi.health()
      lastChecked.value = new Date()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '健康检查失败'
      info.value = null
    } finally {
      loading.value = false
    }
  }

  return { info, loading, lastChecked, error, check }
})

import { get } from './http'

export interface HealthInfo {
  status: string
  llm_provider: string
  embedding_model: string
  version: string
}

export const systemApi = {
  health: () => get<HealthInfo>('/health', { silent: true }),
}

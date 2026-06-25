import { get, post } from './http'
import type { LLMProvider } from './types'

export interface DatasetInfo {
  total: number
  categories: Record<string, number>
}

export interface EvalResult {
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number
  sample_count: number
}

export interface EvalRunRequest {
  provider?: LLMProvider | null
  sample_size?: number | null
}

export type EvalStreamEvent =
  | { type: 'start'; total: number; phase: string }
  | { type: 'progress'; phase: string; current: number; total: number; elapsed_sec: number; message: string }
  | { type: 'phase_change'; phase: string; message: string }
  | { type: 'result'; data: EvalResult; total_elapsed_sec: number }
  | { type: 'error'; message: string }
  | { type: 'done' }

export const evalApi = {
  dataset: () => get<DatasetInfo>('/api/eval/dataset'),
  run: (req: EvalRunRequest) => post<EvalResult>('/api/eval/run', req),
  /**
   * 流式评估：返回 AsyncGenerator，yield {type, ...} 事件
   * - start: 开始
   * - progress: 每完成一个 sample 一次
   * - phase_change: 切换到 RAGAS 阶段
   * - result: 最终结果
   * - error/done: 结束
   */
  runStream: async function* (
    req: EvalRunRequest,
    signal?: AbortSignal,
  ): AsyncGenerator<EvalStreamEvent> {
    const resp = await fetch('/api/eval/run/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: req.provider ?? null,
        sample_size: req.sample_size ?? null,
      }),
      signal,
    })
    if (!resp.ok || !resp.body) {
      yield { type: 'error', message: `HTTP ${resp.status}` }
      return
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          const dataLine = line.split('\n').find((l) => l.startsWith('data: '))
          if (!dataLine) continue
          const payload = dataLine.slice(6)
          if (payload === '[DONE]') {
            yield { type: 'done' }
            return
          }
          try {
            const obj = JSON.parse(payload)
            yield obj as EvalStreamEvent
          } catch {
            /* ignore malformed */
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },
}

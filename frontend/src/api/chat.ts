import { post } from './http'
import type { LLMProvider } from './types'

export interface Citation {
  index: number
  chunk_id: string
  source: string
  heading: string | null
  position: number
  end: number
  is_code: boolean
}

export interface AskRequest {
  question: string
  provider?: LLMProvider | null
  top_k?: number
  session_id?: string | null
}

export interface AskResponse {
  answer: string
  citations: Citation[]
  provider: string
}

export interface FeedbackRequest {
  session_id: string
  question: string
  answer: string
  rating: 'thumbs_up' | 'thumbs_down'
  comment?: string | null
}

export const chatApi = {
  ask: (req: AskRequest) => post<AskResponse>('/api/chat/ask', req),
  feedback: (req: FeedbackRequest) =>
    post<{ message: string }>('/api/chat/feedback', req),
  stream: '/api/chat/agent/stream',
  // 解析 SSE 流
  streamParse: async function* (
    req: AskRequest,
    signal?: AbortSignal,
  ): AsyncGenerator<
    | { type: 'intent'; intent: string }
    | { type: 'chunk'; content: string }
    | { type: 'citations'; citations: Citation[] }
    | { type: 'done' }
    | { type: 'error'; error: string }
  > {
    const resp = await fetch('/api/chat/agent/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: req.question,
        provider: req.provider ?? null,
        top_k: req.top_k ?? 3,
        session_id: req.session_id ?? null,
      }),
      signal,
    })
    if (!resp.ok || !resp.body) {
      yield { type: 'error', error: `HTTP ${resp.status}` }
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
            if ('intent' in obj) yield { type: 'intent', intent: obj.intent }
            else if ('chunk' in obj) yield { type: 'chunk', content: obj.chunk }
            else if ('citations' in obj) yield { type: 'citations', citations: obj.citations }
          } catch {
            /* ignore */
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },
}

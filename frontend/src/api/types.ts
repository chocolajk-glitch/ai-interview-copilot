export type LLMProvider = 'deepseek' | 'qwen' | 'minimax'

export const LLM_PROVIDERS: { value: LLMProvider; label: string; desc: string }[] = [
  { value: 'deepseek', label: 'DeepSeek',  desc: '深度求索 · 性价比高' },
  { value: 'qwen',     label: 'Qwen 通义', desc: '阿里通义 · 中文 SOTA' },
  { value: 'minimax',  label: 'MiniMax',   desc: 'MiniMax · 国产大模型' },
]

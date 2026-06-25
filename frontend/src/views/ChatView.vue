<template>
  <div class="chat-page">
    <!-- 顶部工具条 -->
    <div class="chat-toolbar">
      <div class="toolbar-left">
        <span class="session-id">会话 · {{ shortSessionId }}</span>
        <el-button link size="small" @click="newSession">
          <el-icon><Refresh /></el-icon><span>新对话</span>
        </el-button>
      </div>
      <div class="toolbar-right">
        <el-select
          v-model="provider"
          size="small"
          style="width: 160px"
          @change="onProviderChange"
        >
          <el-option
            v-for="p in LLM_PROVIDERS"
            :key="p.value"
            :label="p.label"
            :value="p.value"
          >
            <span style="float:left">{{ p.label }}</span>
            <span style="float:right; font-size:11px; color:var(--text-tertiary)">
              {{ p.desc }}
            </span>
          </el-option>
        </el-select>
        <el-tooltip content="检索 Top-K" placement="bottom">
          <el-input-number
            v-model="topK"
            :min="1"
            :max="10"
            size="small"
            controls-position="right"
            style="width: 110px"
            @change="onTopKChange"
          />
        </el-tooltip>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="chat-scroll" ref="scrollRef">
      <div v-if="!messages.length" class="empty">
        <div class="empty-logo">🤖</div>
        <h3 class="empty-title">你好，我是 AI 面试助手</h3>
        <p class="empty-sub">
          基于你上传的 LeetCode 题解与八股文回答问题，支持引用溯源
        </p>
        <div class="empty-suggestions">
          <button
            v-for="s in SUGGESTIONS"
            :key="s"
            class="suggestion-chip"
            @click="sendExample(s)"
          >
            {{ s }}
          </button>
        </div>
      </div>

      <div
        v-for="(m, i) in messages"
        :key="i"
        :class="['msg', `msg-${m.role}`]"
      >
        <div class="msg-avatar">
          {{ m.role === 'user' ? '🧑' : '🤖' }}
        </div>
        <div class="msg-body">
          <div class="msg-meta">
            <span class="msg-author">{{ m.role === 'user' ? '我' : 'AI' }}</span>
            <span v-if="m.intent && m.intent !== 'factual'" class="msg-intent">
              <el-icon><Aim /></el-icon>
              {{ intentLabel(m.intent) }}
            </span>
          </div>
          <div
            class="msg-bubble"
            :class="{ 'msg-streaming': m.streaming, 'msg-error': m.error }"
          >
            <!-- 思考过程（仅 AI 消息，且确实有 <think> 内容，且开关打开） -->
            <div
              v-if="m.role === 'ai' && settings.showReasoning && m.reasoning"
              class="reasoning"
              :class="{ 'reasoning-open': m.reasoningExpanded }"
            >
              <button class="reasoning-header" @click="m.reasoningExpanded = !m.reasoningExpanded">
                <el-icon class="reasoning-icon"><MagicStick /></el-icon>
                <span class="reasoning-label">
                  {{ m.isThinking ? '正在思考…' : `已思考（${m.reasoning.length} 字）` }}
                </span>
                <el-icon class="reasoning-toggle">
                  <component :is="m.reasoningExpanded ? ArrowDown : ArrowRight" />
                </el-icon>
              </button>
              <pre v-show="m.reasoningExpanded" class="reasoning-body">{{ m.reasoning }}</pre>
            </div>

            <div v-if="m.role === 'ai'" class="markdown" v-html="renderMd(m.answer ?? '')"></div>
            <div v-else class="plain">{{ m.content }}</div>
            <span v-if="m.streaming" class="cursor">▍</span>
          </div>

          <!-- 引用 chips -->
          <div v-if="m.citations?.length" class="citations">
            <div class="citations-label">
              <el-icon><Document /></el-icon> 引用来源
            </div>
            <div class="citation-list">
              <div
                v-for="c in m.citations"
                :key="c.chunk_id"
                class="citation-chip"
                :class="{ 'is-code': c.is_code }"
                @click="openCitation(c)"
              >
                <span class="citation-idx">[{{ c.index }}]</span>
                <span class="citation-src">{{ c.source }}</span>
                <span v-if="c.heading" class="citation-h">· {{ c.heading }}</span>
              </div>
            </div>
          </div>

          <!-- 反馈按钮（仅 AI 消息、未流式、且非错误） -->
          <div v-if="m.role === 'ai' && !m.streaming && !m.error" class="msg-actions">
            <el-button
              link
              size="small"
              :type="m.feedback === 'up' ? 'primary' : ''"
              @click="sendFeedback(m, 'thumbs_up')"
            >
              <el-icon><CaretTop /></el-icon>
              有用
            </el-button>
            <el-button
              link
              size="small"
              :type="m.feedback === 'down' ? 'danger' : ''"
              @click="sendFeedback(m, 'thumbs_down')"
            >
              <el-icon><CaretBottom /></el-icon>
              答得不对
            </el-button>
            <el-button
              v-if="m.feedback"
              link
              size="small"
              @click="sendFeedback(m, null)"
            >
              <el-icon><Close /></el-icon>
              撤销
            </el-button>
            <span v-if="m.feedbackMsg" class="feedback-msg">{{ m.feedbackMsg }}</span>
          </div>
        </div>
      </div>

      <div v-if="loading" class="thinking">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ thinkingHint }}</span>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-composer">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        :autosize="{ minRows: 2, maxRows: 8 }"
        placeholder="输入你的面试问题…（Enter 发送 · Shift+Enter 换行）"
        :disabled="loading"
        @keydown="handleKeydown"
        resize="none"
      />
      <el-button
        v-if="!loading"
        type="primary"
        :icon="Promotion"
        :disabled="!input.trim()"
        @click="send"
      >
        发送
      </el-button>
      <el-button v-else type="danger" :icon="CircleClose" @click="abort">
        停止
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, computed, onMounted, onBeforeUnmount } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import bash from 'highlight.js/lib/languages/bash'
import json from 'highlight.js/lib/languages/json'
import go from 'highlight.js/lib/languages/go'
import 'highlight.js/styles/github.css'
import {
  Loading,
  Promotion,
  CircleClose,
  Refresh,
  Document,
  Aim,
  CaretTop,
  CaretBottom,
  Close,
  MagicStick,
  ArrowDown,
  ArrowRight,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { chatApi, type Citation } from '@/api/chat'
import { LLM_PROVIDERS, type LLMProvider } from '@/api/types'
import { useSettingsStore } from '@/stores/settings'
import { useHealthStore } from '@/stores/health'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('json', json)
hljs.registerLanguage('go', go)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight(str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${
          hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
        }</code></pre>`
      } catch {
        /* fall through */
      }
    }
    const escaped = str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    return `<pre class="hljs"><code>${escaped}</code></pre>`
  },
})

const SUGGESTIONS = [
  '两数之和的最优解是什么？',
  'HashMap 的底层原理',
  '反转链表的双指针解法',
  'TCP 三次握手的过程',
]

const settings = useSettingsStore()
const health = useHealthStore()

const provider = ref<LLMProvider>(settings.provider)
const topK = ref<number>(settings.topK)
const input = ref('')
const loading = ref(false)
const thinkingHint = ref('AI 正在思考…')
const scrollRef = ref<HTMLElement | null>(null)

interface Msg {
  role: 'user' | 'ai'
  content: string  // 原始累积内容（含 <think>）
  reasoning?: string  // 解析出的思考内容（仅 AI）
  answer?: string  // 解析出的最终答案（仅 AI）
  isThinking?: boolean  // 思考中（只有 <think> 还没有 </think>）
  streaming?: boolean
  citations?: Citation[]
  intent?: string
  error?: boolean
  feedback?: 'up' | 'down' | null
  feedbackMsg?: string
  reasoningExpanded?: boolean
}

function parseContent(content: string): { reasoning: string; answer: string; isThinking: boolean } {
  const closed = content.match(/<think>([\s\S]*?)<\/think>/)
  if (closed) {
    return {
      reasoning: closed[1].trim(),
      answer: content.replace(/<think>[\s\S]*?<\/think>/, '').trim(),
      isThinking: false,
    }
  }
  const opened = content.match(/<think>([\s\S]*)$/)
  if (opened) {
    return { reasoning: opened[1].trim(), answer: '', isThinking: true }
  }
  return { reasoning: '', answer: content, isThinking: false }
}

const messages = ref<Msg[]>([])

const shortSessionId = computed(() => settings.sessionId.slice(0, 8))

let currentController: AbortController | null = null

function onProviderChange(v: LLMProvider) {
  settings.provider = v
}

function onTopKChange(v: number | undefined) {
  settings.topK = v ?? 3
}

function newSession() {
  ElMessageBox.confirm('开始新对话？当前会话内容将被清空。', '提示', {
    type: 'warning',
    confirmButtonText: '开始新对话',
    cancelButtonText: '取消',
  })
    .then(() => {
      settings.newSession()
      messages.value = []
      ElMessage.success('已开启新对话')
    })
    .catch(() => {})
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
    e.preventDefault()
    send()
  }
}

function sendExample(q: string) {
  input.value = q
  send()
}

function intentLabel(intent: string) {
  return {
    factual: '事实型',
    code: '代码题',
    chat: '闲聊',
    concept: '概念型',
  }[intent] ?? intent
}

function openCitation(c: Citation) {
  ElMessage({
    message: `${c.source}${c.heading ? ' · ' + c.heading : ''}（位置 ${c.position}-${c.end}）`,
    type: 'info',
    duration: 3500,
  })
}

function renderMd(src: string): string {
  if (!src) return ''
  // 把模型输出的 [1] [2] 引用标号高亮成蓝
  const html = md.render(src)
  return html.replace(/\[(\d+)\]/g, '<span class="cite-mark">[$1]</span>')
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
}

async function send() {
  const q = input.value.trim()
  if (!q || loading.value) return
  input.value = ''

  messages.value.push({ role: 'user', content: q })
  const aiMsg: Msg = {
    role: 'ai',
    content: '',
    reasoning: '',
    answer: '',
    isThinking: false,
    streaming: true,
    reasoningExpanded: true,
  }
  messages.value.push(aiMsg)
  scrollToBottom()

  loading.value = true
  thinkingHint.value = 'AI 正在分析意图…'
  currentController = new AbortController()

  try {
    for await (const ev of chatApi.streamParse(
      {
        question: q,
        provider: provider.value,
        top_k: topK.value,
        session_id: settings.sessionId,
      },
      currentController.signal,
    )) {
      if (ev.type === 'intent') {
        aiMsg.intent = ev.intent
        thinkingHint.value =
          ev.intent === 'chat' ? '闲聊中…' : '正在检索知识库…'
      } else if (ev.type === 'chunk') {
        aiMsg.content += ev.content
        const parsed = parseContent(aiMsg.content)
        aiMsg.reasoning = parsed.reasoning
        aiMsg.answer = parsed.answer
        aiMsg.isThinking = parsed.isThinking
        thinkingHint.value = '正在生成回答…'
        messages.value = [...messages.value]
        scrollToBottom()
      } else if (ev.type === 'citations') {
        aiMsg.citations = ev.citations
        messages.value = [...messages.value]
      } else if (ev.type === 'done') {
        aiMsg.streaming = false
        // 最后再解析一次，确保完整
        const finalParsed = parseContent(aiMsg.content)
        aiMsg.reasoning = finalParsed.reasoning
        aiMsg.answer = finalParsed.answer
        aiMsg.isThinking = false
        messages.value = [...messages.value]
      } else if (ev.type === 'error') {
        aiMsg.content += `\n\n❌ ${ev.error}`
        aiMsg.error = true
        aiMsg.streaming = false
        messages.value = [...messages.value]
      }
    }
  } catch (e: unknown) {
    const err = e as { name?: string; message?: string }
    if (err?.name === 'AbortError') {
      aiMsg.content += '\n\n[已停止生成]'
    } else {
      aiMsg.content += `\n\n❌ 请求失败：${err?.message ?? e}`
      aiMsg.error = true
    }
    aiMsg.streaming = false
    messages.value = [...messages.value]
  } finally {
    loading.value = false
    currentController = null
  }
}

function abort() {
  currentController?.abort()
}

async function sendFeedback(m: Msg, rating: 'thumbs_up' | 'thumbs_down' | null) {
  if (rating === null) {
    m.feedback = null
    m.feedbackMsg = ''
    return
  }
  try {
    const userMsg = messages.value[messages.value.indexOf(m) - 1]
    await chatApi.feedback({
      session_id: settings.sessionId,
      question: userMsg?.content ?? '',
      answer: m.content,
      rating,
    })
    m.feedback = rating === 'thumbs_up' ? 'up' : 'down'
    m.feedbackMsg = rating === 'thumbs_up' ? '已记录👍' : '已记录👎'
    ElMessage.success(rating === 'thumbs_up' ? '感谢反馈！' : '我们会改进的')
  } catch {
    // 已被拦截器提示
  }
}

onMounted(async () => {
  if (!health.info) await health.check()
})

onBeforeUnmount(() => {
  currentController?.abort()
})
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-page);
}

.chat-toolbar {
  height: var(--topbar-h);
  flex-shrink: 0;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.session-id {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.chat-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0;
}

.empty {
  max-width: 720px;
  margin: 80px auto;
  text-align: center;
  padding: 0 24px;
}
.empty-logo {
  font-size: 56px;
  margin-bottom: 16px;
}
.empty-title {
  font-size: var(--fs-2xl);
  margin-bottom: 8px;
}
.empty-sub {
  color: var(--text-secondary);
  margin-bottom: 24px;
}
.empty-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.suggestion-chip {
  padding: 8px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text-primary);
  font-size: var(--fs-sm);
  cursor: pointer;
  transition: all 0.15s;
}
.suggestion-chip:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.msg {
  max-width: 820px;
  margin: 0 auto 24px;
  padding: 0 24px;
  display: flex;
  gap: 14px;
}
.msg-user {
  flex-direction: row-reverse;
}
.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  display: grid;
  place-items: center;
  font-size: 18px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  flex-shrink: 0;
}
.msg-body {
  flex: 1;
  min-width: 0;
}
.msg-user .msg-body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}
.msg-author {
  font-weight: 600;
  color: var(--text-secondary);
}
.msg-intent {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 8px;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 10px;
  font-size: 11px;
}
.msg-bubble {
  display: inline-block;
  max-width: 100%;
  padding: 12px 16px;
  border-radius: var(--radius);
  line-height: 1.65;
  font-size: var(--fs-md);
  word-wrap: break-word;
}

.reasoning {
  margin-bottom: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: #FAFAFB;
  overflow: hidden;
}
.reasoning-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  text-align: left;
}
.reasoning-header:hover {
  background: var(--bg-hover);
}
.reasoning-icon {
  color: #9333EA;
}
.reasoning-label {
  flex: 1;
}
.reasoning-toggle {
  color: var(--text-tertiary);
  transition: transform 0.15s;
}
.reasoning-body {
  margin: 0;
  padding: 0 14px 12px;
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  line-height: 1.6;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 360px;
  overflow-y: auto;
  background: transparent;
  border-top: 1px dashed var(--border);
  padding-top: 10px;
  margin-top: 0;
}
.msg-user .msg-bubble {
  background: var(--accent);
  color: var(--text-inverse);
}
.msg-ai .msg-bubble {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border);
}
.msg-bubble.msg-error {
  border-color: var(--danger);
  background: #FEF2F2;
}
.msg-streaming {
  border-color: var(--accent);
}
.cursor {
  display: inline-block;
  animation: blink 1s steps(2) infinite;
  color: var(--accent);
  margin-left: 2px;
}
@keyframes blink {
  50% { opacity: 0; }
}
.plain {
  white-space: pre-wrap;
}

.citations {
  margin-top: 10px;
  max-width: 100%;
}
.citations-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  margin-bottom: 6px;
}
.citation-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.citation-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: var(--fs-xs);
  cursor: pointer;
  transition: all 0.15s;
  max-width: 360px;
}
.citation-chip:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.citation-chip.is-code {
  background: #FEF3C7;
  border-color: #FDE68A;
}
.citation-idx {
  color: var(--accent);
  font-weight: 600;
  font-family: var(--font-mono);
}
.citation-src {
  color: var(--text-primary);
  font-weight: 500;
}
.citation-h {
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.msg-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: var(--fs-xs);
}
.feedback-msg {
  color: var(--text-tertiary);
  margin-left: 8px;
}

.thinking {
  max-width: 820px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}

.chat-composer {
  flex-shrink: 0;
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
  padding: 12px 24px 16px;
  max-width: 820px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  gap: 10px;
  align-items: flex-end;
}
</style>

<style>
/* Markdown 渲染样式（全局，因为是 v-html 注入） */
.markdown {
  line-height: 1.65;
}
.markdown p { margin: 0 0 8px; }
.markdown p:last-child { margin-bottom: 0; }
.markdown h1, .markdown h2, .markdown h3 {
  margin: 12px 0 8px;
  font-weight: 600;
  color: var(--text-primary);
}
.markdown h1 { font-size: 20px; }
.markdown h2 { font-size: 18px; }
.markdown h3 { font-size: 16px; }
.markdown ul, .markdown ol { margin: 6px 0; padding-left: 22px; }
.markdown li { margin: 2px 0; }
.markdown code {
  font-family: var(--font-mono);
  font-size: 13px;
  background: var(--bg-code);
  padding: 1px 6px;
  border-radius: 4px;
}
.markdown pre {
  margin: 8px 0;
  padding: 0;
  background: transparent;
  overflow-x: auto;
}
.markdown pre code.hljs {
  display: block;
  padding: 12px 14px;
  background: #f6f8fa;
  border-radius: var(--radius-sm);
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
}
.markdown blockquote {
  margin: 6px 0;
  padding: 4px 12px;
  border-left: 3px solid var(--border-strong);
  color: var(--text-secondary);
  background: var(--bg-hover);
  border-radius: 0 4px 4px 0;
}
.markdown a { color: var(--accent); text-decoration: underline; }
.markdown table {
  border-collapse: collapse;
  margin: 8px 0;
}
.markdown table th, .markdown table td {
  border: 1px solid var(--border);
  padding: 6px 10px;
}
.markdown .cite-mark {
  color: var(--accent);
  font-weight: 600;
  font-family: var(--font-mono);
  font-size: 0.9em;
}
</style>

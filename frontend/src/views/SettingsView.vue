<template>
  <div class="settings-page">
    <div class="page-container">
      <h1 class="page-title">设置</h1>
      <p class="page-subtitle">
        配置默认 LLM、检索参数。设置会保存在浏览器本地，下次打开自动恢复。
      </p>

      <!-- 模型设置 -->
      <div class="card">
        <div class="card-header">
          <h3>默认模型</h3>
          <span class="card-hint">影响对话、评估的默认 provider</span>
        </div>
        <el-radio-group v-model="provider" class="provider-group">
          <label
            v-for="p in LLM_PROVIDERS"
            :key="p.value"
            class="provider-card"
            :class="{ 'is-checked': provider === p.value }"
          >
            <el-radio :value="p.value" class="provider-radio">
              <span class="provider-label">{{ p.label }}</span>
              <span class="provider-desc">{{ p.desc }}</span>
            </el-radio>
          </label>
        </el-radio-group>
      </div>

      <!-- 检索参数 -->
      <div class="card">
        <div class="card-header">
          <h3>检索参数</h3>
          <span class="card-hint">影响 ChatView 每次提问的检索行为</span>
        </div>

        <div class="setting-row">
          <div class="row-label">
            <div class="label-title">Top-K</div>
            <div class="label-desc">检索返回的最大文档块数（1-10）</div>
          </div>
          <el-input-number
            v-model="topK"
            :min="1"
            :max="10"
            controls-position="right"
            style="width: 140px"
          />
        </div>

        <div class="setting-row">
          <div class="row-label">
            <div class="label-title">Temperature</div>
            <div class="label-desc">生成温度：0=确定性，1=平衡，2=最有创意</div>
          </div>
          <div class="temp-control">
            <el-slider
              v-model="temperature"
              :min="0"
              :max="2"
              :step="0.1"
              style="flex: 1; max-width: 320px"
              show-input
              :show-input-controls="false"
              input-size="small"
            />
          </div>
        </div>

        <div class="setting-row">
          <div class="row-label">
            <div class="label-title">显示推理过程</div>
            <div class="label-desc">
              对带思考的模型（如 MiniMax），在答案上方显示可折叠的「已思考」块
            </div>
          </div>
          <el-switch
            v-model="showReasoning"
            inline-prompt
            active-text="显示"
            inactive-text="隐藏"
            style="--el-switch-on-color: var(--accent)"
          />
        </div>
      </div>

      <!-- 会话 -->
      <div class="card">
        <div class="card-header">
          <h3>会话</h3>
        </div>
        <div class="setting-row">
          <div class="row-label">
            <div class="label-title">当前会话 ID</div>
            <div class="label-desc">用于服务端关联多轮对话上下文</div>
          </div>
          <div class="session-display">
            <code class="session-code">{{ settings.sessionId }}</code>
            <el-button :icon="Refresh" size="small" @click="resetSession">
              重置
            </el-button>
          </div>
        </div>
      </div>

      <!-- 后端状态 -->
      <div class="card">
        <div class="card-header">
          <h3>后端状态</h3>
          <el-button
            :icon="Refresh"
            size="small"
            link
            :loading="health.loading"
            @click="health.check()"
          >
            重新检查
          </el-button>
        </div>

        <div v-if="health.info" class="health-grid">
          <div class="health-item">
            <div class="health-label">状态</div>
            <div class="health-value">
              <span class="status-dot" :class="`is-${health.info.status}`"></span>
              <span>{{ health.info.status === 'ok' ? '运行中' : health.info.status }}</span>
            </div>
          </div>
          <div class="health-item">
            <div class="health-label">LLM Provider</div>
            <div class="health-value health-value-row">
              <span class="badge-active">{{ settings.provider }}</span>
              <span class="provider-arrow">←</span>
              <span class="badge-default">{{ health.info.llm_provider }}</span>
            </div>
            <div class="health-sub">
              <span class="health-sub-strong">当前</span> 你的选择
              <span class="health-sub-sep">·</span>
              <span class="health-sub-strong">后端</span> .env 默认
            </div>
          </div>
          <div class="health-item">
            <div class="health-label">Embedding 模型</div>
            <div class="health-value health-mono">{{ health.info.embedding_model }}</div>
          </div>
          <div class="health-item">
            <div class="health-label">后端版本</div>
            <div class="health-value health-mono">v{{ health.info.version }}</div>
          </div>
          <div class="health-item">
            <div class="health-label">上次检查</div>
            <div class="health-value health-mono">
              {{ formatTime(health.lastChecked) }}
            </div>
          </div>
        </div>
        <div v-else-if="health.loading" class="health-loading">检查中…</div>
        <div v-else class="health-error">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ health.error || '无法连接后端' }}</span>
          <span class="health-error-hint">请确认后端运行在 http://localhost:8000</span>
        </div>
      </div>

      <div class="footer-note">
        配置已自动保存到浏览器 localStorage · 切换模型后新对话立即生效
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, WarningFilled } from '@element-plus/icons-vue'
import { LLM_PROVIDERS, type LLMProvider } from '@/api/types'
import { useSettingsStore } from '@/stores/settings'
import { useHealthStore } from '@/stores/health'

const settings = useSettingsStore()
const health = useHealthStore()

const provider = computed<LLMProvider>({
  get: () => settings.provider,
  set: (v) => (settings.provider = v),
})
const topK = computed<number>({
  get: () => settings.topK,
  set: (v) => (settings.topK = v ?? 3),
})
const temperature = computed<number>({
  get: () => settings.temperature,
  set: (v) => (settings.temperature = v ?? 0.7),
})
const showReasoning = computed<boolean>({
  get: () => settings.showReasoning,
  set: (v) => (settings.showReasoning = v),
})

function resetSession() {
  settings.newSession()
  ElMessage.success('已重置会话 ID')
}

function formatTime(d: Date | null) {
  if (!d) return '—'
  return d.toLocaleTimeString('zh-CN')
}
</script>

<style scoped>
.settings-page {
  height: 100%;
  overflow-y: auto;
  padding-bottom: 40px;
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.card-header h3 {
  font-size: var(--fs-lg);
  font-weight: 600;
}
.card-hint {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

.provider-group {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}
@media (max-width: 720px) {
  .provider-group {
    grid-template-columns: 1fr;
  }
}
.provider-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 16px;
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.15s;
  min-height: 64px;
}
.provider-card:hover {
  border-color: var(--accent);
  background: var(--bg-hover);
}
.provider-card.is-checked {
  border-color: var(--accent);
  background: var(--accent-soft);
  box-shadow: 0 0 0 1px var(--accent) inset;
}
.provider-radio {
  width: 100%;
  height: 100%;
}
.provider-radio :deep(.el-radio__input) {
  margin-top: 2px;
}
.provider-radio :deep(.el-radio__label) {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  padding-left: 8px;
}
.provider-label {
  font-weight: 600;
  font-size: var(--fs-md);
  line-height: 1.3;
}
.provider-desc {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  line-height: 1.4;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  border-top: 1px solid var(--border);
  gap: 24px;
}
.setting-row:first-of-type {
  border-top: none;
  padding-top: 4px;
}
.row-label {
  flex: 1;
  min-width: 0;
}
.label-title {
  font-weight: 600;
  margin-bottom: 2px;
}
.label-desc {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

.temp-control {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  justify-content: flex-end;
}

.session-display {
  display: flex;
  align-items: center;
  gap: 10px;
}
.session-code {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  background: var(--bg-page);
  padding: 4px 10px;
  border-radius: 4px;
  color: var(--text-secondary);
  border: 1px solid var(--border);
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.health-item {
  padding: 12px 14px;
  background: var(--bg-page);
  border-radius: var(--radius-sm);
}
.health-label {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  margin-bottom: 4px;
}
.health-value {
  font-size: var(--fs-md);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}
.health-mono {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
}
.health-sub {
  display: block;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-weight: 400;
  margin-top: 2px;
}
.badge-active {
  display: inline-block;
  padding: 2px 8px;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: 500;
}
.badge-default {
  display: inline-block;
  padding: 2px 8px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: 500;
}
.health-value-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.provider-arrow {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
.health-sub-strong {
  color: var(--text-secondary);
  font-weight: 600;
}
.health-sub-sep {
  margin: 0 2px;
  color: var(--text-tertiary);
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
}
.status-dot.is-ok { background: var(--success); box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15); }
.status-dot.is-error { background: var(--danger); }

.health-loading {
  color: var(--text-tertiary);
  padding: 12px 0;
}
.health-error {
  padding: 16px;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  border-radius: var(--radius-sm);
  color: var(--danger);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.health-error-hint {
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  margin-left: auto;
}

.footer-note {
  text-align: center;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  padding: 20px 0;
}
</style>

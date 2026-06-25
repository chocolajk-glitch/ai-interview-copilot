<template>
  <div class="eval-page">
    <div class="page-container">
      <h1 class="page-title">RAGAS 评估</h1>
      <p class="page-subtitle">
        用 RAGAS 框架量化检索质量：忠实度、相关性、精确率、召回率。每次调优后跑一次，看指标变化。
      </p>

      <!-- 数据集 -->
      <div class="card">
        <div class="card-header">
          <h3>评估数据集</h3>
          <el-button
            :icon="Refresh"
            size="small"
            link
            :loading="loadingDataset"
            @click="loadDataset"
          >
            刷新
          </el-button>
        </div>
        <div v-if="dataset" class="dataset-info">
          <div class="dataset-stat">
            <div class="stat-num">{{ dataset.total }}</div>
            <div class="stat-label">测试用例总数</div>
          </div>
          <div class="dataset-cats">
            <div class="cats-label">分类分布</div>
            <div class="cats-list">
              <el-tag
                v-for="(n, cat) in dataset.categories"
                :key="cat"
                size="default"
                effect="plain"
                round
                class="cat-tag"
              >
                {{ cat }} · {{ n }}
              </el-tag>
            </div>
          </div>
        </div>
        <div v-else-if="loadingDataset" class="dataset-loading">加载中…</div>
        <div v-else class="dataset-error">数据集加载失败</div>
      </div>

      <!-- 运行配置 -->
      <div class="card">
        <div class="card-header">
          <h3>运行评估</h3>
        </div>
        <div class="run-form">
          <div class="form-item">
            <label>LLM 模型</label>
            <el-select v-model="runProvider" style="width: 220px">
              <el-option label="使用默认" value="" />
              <el-option
                v-for="p in LLM_PROVIDERS"
                :key="p.value"
                :label="p.label"
                :value="p.value"
              />
            </el-select>
          </div>
          <div class="form-item">
            <label>样本数量</label>
            <el-input-number
              v-model="sampleSize"
              :min="1"
              :max="50"
              :step="1"
              controls-position="right"
              style="width: 160px"
            />
            <span class="form-hint">建议先用 5-10 跑一次快速验证</span>
          </div>
          <el-button
            type="primary"
            :icon="VideoPlay"
            :loading="running"
            :disabled="running"
            size="large"
            @click="runEval"
          >
            {{ running ? '评估中…' : '开始评估' }}
          </el-button>
        </div>

        <div v-if="running" class="run-progress">
          <el-progress
            :percentage="progressPercent"
            :indeterminate="progressPercent === 0"
            :duration="2"
            :show-text="false"
            :stroke-width="6"
            color="#2563EB"
          />
          <div class="run-progress-text">
            <span v-if="progressMessage">{{ progressMessage }}</span>
            <span v-else>评估中…</span>
            <span class="progress-elapsed">已用时 {{ elapsedDisplay }}</span>
          </div>
        </div>
      </div>

      <!-- 结果 -->
      <div v-if="result" class="card">
        <div class="card-header">
          <h3>评估结果</h3>
          <div class="result-meta">
            <span v-if="resultRunAt" class="meta-time">{{ resultRunAt }}</span>
            <el-tag size="small" type="info" effect="plain">
              样本数 {{ result.sample_count }}
            </el-tag>
          </div>
        </div>

        <div class="metrics-grid">
          <MetricCard
            label="Faithfulness"
            label-cn="忠实度"
            :value="result.faithfulness"
            desc="回答里有多少事实能溯源到原文"
          />
          <MetricCard
            label="Answer Relevancy"
            label-cn="答案相关性"
            :value="result.answer_relevancy"
            desc="回答与问题的相关度"
          />
          <MetricCard
            label="Context Precision"
            label-cn="上下文精确率"
            :value="result.context_precision"
            desc="检索的 top-k 中相关文档的占比"
          />
          <MetricCard
            label="Context Recall"
            label-cn="上下文召回率"
            :value="result.context_recall"
            desc="相关文档被检索出的比例"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MetricCard from '@/components/MetricCard.vue'
import { evalApi, type DatasetInfo, type EvalResult } from '@/api/eval'
import { LLM_PROVIDERS, type LLMProvider } from '@/api/types'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()

const dataset = ref<DatasetInfo | null>(null)
const loadingDataset = ref(false)

const runProvider = ref<LLMProvider | ''>('')
const sampleSize = ref<number>(5)
const running = ref(false)
const result = ref<EvalResult | null>(null)
const resultRunAt = ref<string>('')
const progressPercent = ref<number>(0)
const progressMessage = ref<string>('')
const elapsedDisplay = ref<string>('0s')
let currentController: AbortController | null = null

async function loadDataset() {
  loadingDataset.value = true
  try {
    dataset.value = await evalApi.dataset()
  } catch {
    dataset.value = null
  } finally {
    loadingDataset.value = false
  }
}

async function runEval() {
  running.value = true
  result.value = null
  progressPercent.value = 0
  progressMessage.value = ''
  const start = Date.now()
  currentController = new AbortController()

  // 启动本地计时器，每秒刷新"已用时"
  const tick = setInterval(() => {
    const sec = (Date.now() - start) / 1000
    if (sec < 60) elapsedDisplay.value = `${sec.toFixed(0)}s`
    else elapsedDisplay.value = `${Math.floor(sec / 60)}m${Math.floor(sec % 60)}s`
  }, 1000)

  try {
    for await (const ev of evalApi.runStream(
      {
        provider: runProvider.value || null,
        sample_size: sampleSize.value,
      },
      currentController.signal,
    )) {
      if (ev.type === 'start') {
        progressMessage.value = `准备评估 ${ev.total} 个样本`
      } else if (ev.type === 'progress') {
        // 生成阶段：percent = current/total 的一半（剩下一半给 RAGAS）
        const half = (ev.current / ev.total) * 50
        progressPercent.value = Math.round(half)
        progressMessage.value = `[生成] ${ev.current}/${ev.total} · ${ev.elapsed_sec.toFixed(0)}s`
      } else if (ev.type === 'phase_change') {
        progressMessage.value = ev.message
      } else if (ev.type === 'result') {
        progressPercent.value = 100
        result.value = ev.data
        const totalSec = ev.total_elapsed_sec
        resultRunAt.value = `用时 ${totalSec.toFixed(1)}s · ${new Date().toLocaleTimeString('zh-CN')}`
        ElMessage.success('评估完成')
      } else if (ev.type === 'error') {
        ElMessage.error(ev.message)
      }
    }
  } catch (e) {
    if ((e as Error)?.name !== 'AbortError') {
      console.error('[runEval] error:', e)
    }
  } finally {
    clearInterval(tick)
    running.value = false
    currentController = null
  }
}

onMounted(async () => {
  await loadDataset()
  // 默认沿用 settings 里的 provider
  runProvider.value = settings.provider
})
</script>

<style scoped>
.eval-page {
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
}
.card-header h3 {
  font-size: var(--fs-lg);
  font-weight: 600;
}

.dataset-info {
  display: flex;
  align-items: center;
  gap: 40px;
  flex-wrap: wrap;
}
.dataset-stat {
  text-align: center;
  min-width: 120px;
}
.stat-num {
  font-size: 40px;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
}
.stat-label {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  margin-top: 6px;
}
.dataset-cats {
  flex: 1;
  min-width: 240px;
}
.cats-label {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.cats-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.cat-tag {
  font-family: var(--font-mono);
}
.dataset-loading,
.dataset-error {
  color: var(--text-tertiary);
  padding: 12px 0;
}

.run-form {
  display: flex;
  align-items: flex-end;
  gap: 20px;
  flex-wrap: wrap;
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-item label {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--text-secondary);
}
.form-hint {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  margin-top: 4px;
}

.run-progress {
  margin-top: 20px;
}
.run-progress-text {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.progress-elapsed {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--accent);
  font-weight: 500;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
}
.meta-time {
  font-family: var(--font-mono);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
@media (min-width: 1100px) {
  .metrics-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>

<template>
  <div class="kb-page">
    <div class="page-container">
      <h1 class="page-title">知识库</h1>
      <p class="page-subtitle">
        上传 LeetCode 题解、八股文等 Markdown / PDF 文档，AI 会基于其中的内容回答你的问题。
      </p>

      <!-- 上传区 -->
      <div
        class="upload-zone"
        :class="{ 'is-dragover': dragover, 'is-disabled': uploading }"
        @click="pickFile"
        @dragover.prevent="dragover = true"
        @dragleave.prevent="dragover = false"
        @drop.prevent="onDrop"
      >
        <input
          ref="fileInput"
          type="file"
          class="file-input"
          :accept="ACCEPTED_EXTS.join(',')"
          multiple
          @change="onPick"
        />
        <div class="upload-icon">
          <el-icon :size="32"><UploadFilled /></el-icon>
        </div>
        <div class="upload-text">
          <div class="upload-title">点击或拖拽文件到此处上传</div>
          <div class="upload-hint">
            支持 {{ ACCEPTED_EXTS.join(' / ') }} · 单文件 ≤ 20MB
          </div>
        </div>
        <el-button
          v-if="uploading"
          type="primary"
          :loading="true"
          size="default"
        >
          正在上传…
        </el-button>
        <el-button v-else type="primary" :icon="UploadFilled" size="default">
          选择文件
        </el-button>
      </div>

      <!-- 列表头 -->
      <div class="list-header">
        <div class="list-title">
          已上传文档
          <span class="list-count">{{ filteredDocs.length }} / {{ docs.length }}</span>
        </div>
        <div class="list-actions">
          <el-select
            v-model="statusFilter"
            placeholder="按状态筛选"
            clearable
            size="small"
            style="width: 140px"
          >
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="就绪" value="ready" />
            <el-option label="失败" value="failed" />
            <el-option label="重复" value="duplicate" />
          </el-select>
          <el-button :icon="Refresh" size="small" @click="loadDocs" :loading="loadingList">
            刷新
          </el-button>
        </div>
      </div>

      <!-- 列表 -->
      <el-table
        :data="filteredDocs"
        v-loading="loadingList && !docs.length"
        empty-text="还没有文档，去上传一个吧"
        class="docs-table"
        :row-key="(r: DocumentInfo) => r.doc_id"
      >
        <el-table-column label="文件名" min-width="280">
          <template #default="{ row }">
            <div class="file-cell">
              <div class="file-icon">
                <el-icon :size="18"><Document /></el-icon>
              </div>
              <div class="file-info">
                <div class="file-name" :title="row.filename">{{ row.filename }}</div>
                <div class="file-meta">
                  {{ formatSize(row) }} · {{ formatTime(row.created_at) }}
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small" effect="light">
              <span class="status-dot-inline" :class="`dot-${row.status}`"></span>
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="分块" width="180" align="center">
          <template #default="{ row }">
            <div v-if="row.status === 'ready'" class="chunk-info">
              <span class="chunk-new">+{{ row.new_chunks }}</span>
              <span class="chunk-sep">/</span>
              <span class="chunk-total">{{ row.chunk_count }} 总</span>
              <span v-if="row.skipped_chunks" class="chunk-skip">
                · 跳过 {{ row.skipped_chunks }}
              </span>
            </div>
            <span v-else class="text-tertiary">—</span>
          </template>
        </el-table-column>

        <el-table-column label="错误" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.error" class="error-text">{{ row.error }}</span>
            <span v-else class="text-tertiary">—</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="100" align="right" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              link
              type="danger"
              :disabled="row.status === 'processing'"
              @click="confirmDelete(row)"
            >
              <el-icon><Delete /></el-icon>删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  UploadFilled,
  Document,
  Refresh,
  Delete,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  documentApi,
  ACCEPTED_EXTS,
  MAX_FILE_SIZE,
  type DocumentInfo,
  type DocStatus,
} from '@/api/document'

const docs = ref<DocumentInfo[]>([])
const loadingList = ref(false)
const uploading = ref(false)
const dragover = ref(false)
const statusFilter = ref<DocStatus | ''>('')
const fileInput = ref<HTMLInputElement | null>(null)

const filteredDocs = computed(() => {
  if (!statusFilter.value) return docs.value
  return docs.value.filter((d) => d.status === statusFilter.value)
})

function statusType(s: DocStatus) {
  return {
    ready: 'success',
    processing: 'warning',
    pending: 'info',
    failed: 'danger',
    duplicate: 'info',
  }[s] as 'success' | 'warning' | 'info' | 'danger'
}

function statusLabel(s: DocStatus) {
  return {
    ready: '就绪',
    processing: '处理中',
    pending: '待处理',
    failed: '失败',
    duplicate: '重复',
  }[s] ?? s
}

function formatTime(iso: string) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatSize(_row: DocumentInfo) {
  // 后端没返回 byte 数（schema 里没有），留空
  return '—'
}

function pickFile() {
  if (uploading.value) return
  fileInput.value?.click()
}

function onPick(e: Event) {
  const list = (e.target as HTMLInputElement).files
  if (list) handleFiles(Array.from(list))
  if (fileInput.value) fileInput.value.value = ''
}

function onDrop(e: DragEvent) {
  dragover.value = false
  if (uploading.value) return
  const list = e.dataTransfer?.files
  if (list) handleFiles(Array.from(list))
}

function validate(file: File): string | null {
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
  if (!ACCEPTED_EXTS.includes(ext)) {
    return `不支持的文件类型：${ext}`
  }
  if (file.size > MAX_FILE_SIZE) {
    return `文件超过 20MB：${(file.size / 1024 / 1024).toFixed(1)}MB`
  }
  return null
}

async function handleFiles(files: File[]) {
  if (!files.length) return
  uploading.value = true
  const failures: { name: string; reason: string }[] = []
  for (const f of files) {
    const err = validate(f)
    if (err) {
      failures.push({ name: f.name, reason: err })
      continue
    }
    try {
      const r = await documentApi.upload(f)
      if (r.status === 'duplicate') {
        ElMessage.warning(`${f.name} 已存在（重复）`)
      } else {
        ElMessage.success(`${f.name} 已加入索引队列`)
      }
    } catch {
      // 拦截器已提示
    }
  }
  uploading.value = false
  if (failures.length) {
    ElMessageBox.alert(
      failures.map((f) => `· ${f.name}: ${f.reason}`).join('\n'),
      `${failures.length} 个文件未上传`,
      { type: 'warning' },
    )
  }
  await loadDocs()
}

async function loadDocs() {
  loadingList.value = true
  try {
    const r = await documentApi.list()
    docs.value = r.documents
  } catch {
    docs.value = []
  } finally {
    loadingList.value = false
  }
}

async function confirmDelete(row: DocumentInfo) {
  try {
    await ElMessageBox.confirm(
      `确认删除「${row.filename}」？该文档的所有向量也会一并清除。`,
      '删除文档',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await documentApi.delete(row.doc_id)
    ElMessage.success('已删除')
    docs.value = docs.value.filter((d) => d.doc_id !== row.doc_id)
  } catch {
    /* intercepted */
  }
}

let pollTimer: number | null = null
function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    const needPoll = docs.value.some(
      (d) => d.status === 'pending' || d.status === 'processing',
    )
    if (!needPoll) return
    const targets = docs.value
      .filter((d) => d.status === 'pending' || d.status === 'processing')
      .map((d) => d.doc_id)
    for (const id of targets) {
      try {
        const fresh = await documentApi.status(id)
        const idx = docs.value.findIndex((d) => d.doc_id === id)
        if (idx >= 0) docs.value[idx] = fresh
      } catch {
        /* 单个失败不影响其他 */
      }
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(async () => {
  await loadDocs()
  startPolling()
})

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.kb-page {
  height: 100%;
  overflow-y: auto;
  padding-bottom: 40px;
}

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 36px 24px;
  background: var(--bg-surface);
  border: 2px dashed var(--border-strong);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 32px;
}
.upload-zone:hover,
.upload-zone.is-dragover {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.upload-zone.is-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.file-input {
  display: none;
}
.upload-icon {
  color: var(--accent);
  background: var(--accent-soft);
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: grid;
  place-items: center;
}
.upload-title {
  font-size: var(--fs-md);
  font-weight: 600;
}
.upload-hint {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  margin-top: 4px;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.list-title {
  font-size: var(--fs-lg);
  font-weight: 600;
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.list-count {
  font-size: var(--fs-sm);
  font-weight: 400;
  color: var(--text-tertiary);
}
.list-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.docs-table {
  background: var(--bg-surface);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  overflow: hidden;
}

.file-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.file-icon {
  width: 36px;
  height: 36px;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.file-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.file-name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-meta {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

.status-dot-inline {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 5px;
  vertical-align: middle;
}
.dot-pending { background: var(--text-tertiary); }
.dot-processing { background: var(--warning); animation: pulse 1.2s infinite; }
.dot-ready { background: var(--success); }
.dot-failed { background: var(--danger); }
.dot-duplicate { background: var(--info); }
@keyframes pulse {
  50% { opacity: 0.4; }
}

.chunk-info {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-secondary);
}
.chunk-new {
  color: var(--success);
  font-weight: 600;
}
.chunk-sep {
  color: var(--text-tertiary);
  margin: 0 4px;
}
.chunk-total {
  color: var(--text-primary);
}
.chunk-skip {
  color: var(--text-tertiary);
  margin-left: 4px;
}

.error-text {
  color: var(--danger);
  font-size: var(--fs-sm);
}
</style>

<template>
  <div class="app-shell">
    <!-- 侧边栏 -->
    <aside class="app-sidebar">
      <div class="brand">
        <div class="brand-logo">🤖</div>
        <div class="brand-text">
          <div class="brand-title">AI 面试助手</div>
          <div class="brand-subtitle">RAG · LangGraph</div>
        </div>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="r in navRoutes"
          :key="r.path"
          :to="r.path"
          class="nav-item"
          active-class="nav-item-active"
        >
          <el-icon :size="18"><component :is="r.icon" /></el-icon>
          <span>{{ r.title }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar-footer">
        <div class="footer-row">
          <span class="status-dot" :class="healthClass"></span>
          <span class="footer-label">{{ healthLabel }}</span>
        </div>
        <el-tooltip
          v-if="health.info"
          :content="`后端默认 LLM: ${health.info.llm_provider} · Embedding: ${health.info.embedding_model}`"
          placement="right"
        >
          <div class="footer-meta footer-meta-clickable">查看后端详情</div>
        </el-tooltip>
        <div class="footer-meta">v0.1.0</div>
      </div>
    </aside>

    <!-- 主区域 -->
    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </RouterView>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { ChatLineRound, Files, DataAnalysis, Setting } from '@element-plus/icons-vue'
import { useHealthStore } from '@/stores/health'

const health = useHealthStore()

const navRoutes = [
  { path: '/chat', title: '对话', icon: ChatLineRound },
  { path: '/kb', title: '知识库', icon: Files },
  { path: '/eval', title: '评估', icon: DataAnalysis },
  { path: '/settings', title: '设置', icon: Setting },
]

const healthClass = computed(() => {
  if (health.loading) return 'is-loading'
  if (health.error) return 'is-error'
  if (health.info?.status === 'ok') return 'is-ok'
  return 'is-unknown'
})

const healthLabel = computed(() => {
  if (health.loading) return '检查中…'
  if (health.error) return '后端离线'
  if (health.info) return '后端正常'
  return '未检查'
})

onMounted(async () => {
  await health.check()
})
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: var(--bg-page);
}

.app-sidebar {
  width: var(--sidebar-w);
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
}
.brand-logo {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  font-size: 20px;
  background: var(--accent-soft);
  border-radius: var(--radius);
}
.brand-title {
  font-size: var(--fs-md);
  font-weight: 600;
  line-height: 1.2;
}
.brand-subtitle {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  margin-top: 2px;
}

.nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--fs);
  font-weight: 500;
  transition: all 0.15s;
  cursor: pointer;
}
.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.nav-item-active {
  background: var(--accent-soft);
  color: var(--accent);
}
.nav-item-active:hover {
  background: var(--accent-soft);
  color: var(--accent);
}

.sidebar-footer {
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.footer-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.status-dot.is-ok { background: var(--success); box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15); }
.status-dot.is-error { background: var(--danger); }
.status-dot.is-loading { background: var(--warning); animation: pulse 1.2s infinite; }
.status-dot.is-unknown { background: var(--text-tertiary); }
@keyframes pulse {
  50% { opacity: 0.4; }
}
.footer-meta {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}
.footer-meta-clickable {
  cursor: help;
  transition: color 0.15s;
}
.footer-meta-clickable:hover {
  color: var(--text-secondary);
}

.app-main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

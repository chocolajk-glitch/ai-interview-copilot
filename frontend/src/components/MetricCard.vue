<template>
  <div class="metric-card" :class="band">
    <div class="metric-label">
      <span class="label-en">{{ label }}</span>
      <span class="label-cn">{{ labelCn }}</span>
    </div>
    <div class="metric-value">
      {{ formatted }}
      <span class="metric-unit">/ 1.00</span>
    </div>
    <div class="metric-bar">
      <div class="metric-bar-fill" :style="{ width: pct + '%' }"></div>
    </div>
    <div class="metric-desc">{{ desc }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  labelCn: string
  value: number
  desc: string
}>()

const pct = computed(() => Math.max(0, Math.min(1, props.value)) * 100)
const formatted = computed(() => props.value.toFixed(3))

const band = computed(() => {
  if (props.value >= 0.85) return 'band-good'
  if (props.value >= 0.7) return 'band-ok'
  return 'band-low'
})
</script>

<style scoped>
.metric-card {
  padding: 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
  overflow: hidden;
}
.metric-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--accent);
}
.metric-card.band-good::before { background: var(--success); }
.metric-card.band-ok::before   { background: var(--warning); }
.metric-card.band-low::before  { background: var(--danger); }

.metric-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.label-en {
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
}
.label-cn {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--text-primary);
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-primary);
  line-height: 1.1;
}
.metric-card.band-good .metric-value { color: var(--success); }
.metric-card.band-ok   .metric-value { color: var(--warning); }
.metric-card.band-low  .metric-value { color: var(--danger); }
.metric-unit {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  font-weight: 400;
  margin-left: 4px;
}

.metric-bar {
  height: 6px;
  background: var(--bg-hover);
  border-radius: 3px;
  overflow: hidden;
}
.metric-bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.4s ease;
}
.metric-card.band-good .metric-bar-fill { background: var(--success); }
.metric-card.band-ok   .metric-bar-fill { background: var(--warning); }
.metric-card.band-low  .metric-bar-fill { background: var(--danger); }

.metric-desc {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  line-height: 1.5;
  min-height: 32px;
}
</style>

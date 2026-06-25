import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { title: '对话', icon: 'ChatLineRound' },
  },
  {
    path: '/kb',
    name: 'kb',
    component: () => import('@/views/KnowledgeBaseView.vue'),
    meta: { title: '知识库', icon: 'Files' },
  },
  {
    path: '/eval',
    name: 'eval',
    component: () => import('@/views/EvaluationView.vue'),
    meta: { title: '评估', icon: 'DataAnalysis' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '设置', icon: 'Setting' },
  },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

import { createRouter, createWebHistory } from 'vue-router'

const WorkspacePage = () => import('@/views/WorkspacePage.vue')
const DevicePage = () => import('@/views/DevicePage.vue')

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/workspace' },
    { path: '/workspace', component: WorkspacePage },
    { path: '/devices', component: DevicePage }
  ]
})

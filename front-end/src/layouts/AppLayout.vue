<script setup lang="ts">
import AppSidebar from '@/components/AppSidebar.vue'
import NotificationToast from '@/components/NotificationToast.vue'
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()

const breadcrumbs = computed(() => {
  const map: Record<string, string> = {
    '/dashboard':           '总览',
    '/applications':        '我的申请',
    '/applications/new':    '新建申请',
    '/venues':              '场地日历',
    '/admin':               '管理概览',
    '/admin/applications':  '申请管理',
    '/admin/users':         '用户管理',
  }
  return map[route.path] || '...'
})
</script>

<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <!-- Header -->
      <header class="app-header">
        <div class="header-breadcrumb">
          <span class="text-sm text-[rgba(232,245,240,0.4)]">美育系统</span>
          <span class="text-sm text-[rgba(232,245,240,0.25)] mx-2">/</span>
          <span class="text-sm font-medium text-[rgba(232,245,240,0.85)]">{{ breadcrumbs }}</span>
        </div>
        <div class="header-right">
          <slot name="header-actions" />
        </div>
      </header>

      <!-- Page content -->
      <main class="app-content">
        <slot />
      </main>
    </div>

    <NotificationToast />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: #060e0c;
}

/* Decorative background */
.app-shell::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse at 20% 10%,  rgba(61, 217, 172, 0.06), transparent 40%),
    radial-gradient(ellipse at 80% 80%,  rgba(247, 202, 117, 0.05), transparent 40%),
    radial-gradient(ellipse at 50% 50%,  rgba(61, 217, 172, 0.03), transparent 60%);
  pointer-events: none;
  z-index: 0;
}

.app-main {
  margin-left: 240px;
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  height: 58px;
  background: rgba(6, 14, 12, 0.7);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(16px);
}

.header-breadcrumb {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-content {
  flex: 1;
  padding: 28px;
  max-width: 1200px;
  width: 100%;
}
</style>

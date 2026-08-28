<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  LayoutDashboard, FileText, Calendar, Users, Settings,
  LogOut, Building2, Shield, PlusCircle, ChevronRight,
} from 'lucide-vue-next'

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()

const userNavItems = [
  { icon: LayoutDashboard, label: '总览',     to: '/dashboard' },
  { icon: FileText,        label: '我的申请', to: '/applications' },
  { icon: Calendar,        label: '场地日历', to: '/venues' },
]

const adminNavItems = [
  { icon: Shield,        label: '管理概览', to: '/admin' },
  { icon: FileText,      label: '申请管理', to: '/admin/applications' },
  { icon: Users,         label: '用户管理', to: '/admin/users' },
]

const isActive = (path: string) => {
  if (path === '/dashboard') return route.path === '/dashboard'
  if (path === '/admin')     return route.path === '/admin'
  return route.path.startsWith(path)
}

function logout() {
  auth.logout()
  router.push('/login')
}

const initials = computed(() => {
  if (!auth.user?.email) return '?'
  return auth.user.email.charAt(0).toUpperCase()
})
</script>

<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar-logo">
      <div class="logo-icon">
        <Building2 :size="20" />
      </div>
      <div>
        <span class="logo-title">美育系统</span>
        <span class="logo-sub">Meiyu System</span>
      </div>
    </div>

    <!-- Nav -->
    <nav class="sidebar-nav">
      <div class="nav-section">
        <p class="nav-label">主菜单</p>
        <RouterLink
          v-for="item in userNavItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
        >
          <component :is="item.icon" :size="18" class="nav-icon" />
          <span>{{ item.label }}</span>
          <ChevronRight :size="14" class="nav-arrow" />
        </RouterLink>
      </div>

      <!-- Quick action -->
      <RouterLink to="/applications/new" class="nav-action">
        <PlusCircle :size="16" />
        <span>新建申请</span>
      </RouterLink>

      <!-- Admin section -->
      <div v-if="auth.isAdmin" class="nav-section">
        <p class="nav-label">管理员</p>
        <RouterLink
          v-for="item in adminNavItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
        >
          <component :is="item.icon" :size="18" class="nav-icon" />
          <span>{{ item.label }}</span>
          <ChevronRight :size="14" class="nav-arrow" />
        </RouterLink>
      </div>
    </nav>

    <!-- User profile -->
    <div class="sidebar-footer">
      <div class="user-card">
        <div class="user-avatar">{{ initials }}</div>
        <div class="user-info">
          <p class="user-email">{{ auth.user?.email }}</p>
          <p class="user-role">{{ auth.isAdmin ? '管理员' : '普通用户' }}</p>
        </div>
      </div>
      <button class="logout-btn" @click="logout" title="退出登录">
        <LogOut :size="16" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  left: 0; top: 0; bottom: 0;
  width: 240px;
  display: flex;
  flex-direction: column;
  background: rgba(6, 14, 12, 0.82);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(20px);
  z-index: 40;
}

/* Logo */
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.logo-icon {
  width: 40px; height: 40px;
  display: grid; place-items: center;
  background: linear-gradient(135deg, #3DD9AC22, #F7CA7522);
  border: 1px solid rgba(61, 217, 172, 0.3);
  border-radius: 10px;
  color: #3DD9AC;
}

.logo-title {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: #e8f5f0;
  line-height: 1.2;
}

.logo-sub {
  display: block;
  font-size: 10px;
  color: rgba(232, 245, 240, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  line-height: 1.2;
}

/* Nav */
.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.nav-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-label {
  margin: 0 0 8px 8px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(232, 245, 240, 0.35);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  color: rgba(232, 245, 240, 0.62);
  text-decoration: none;
  transition: background 0.2s ease, color 0.2s ease;
  position: relative;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #e8f5f0;
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(61, 217, 172, 0.14), rgba(61, 217, 172, 0.06));
  color: #3DD9AC;
  border: 1px solid rgba(61, 217, 172, 0.2);
}

.nav-arrow {
  margin-left: auto;
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity 0.2s, transform 0.2s;
}

.nav-item:hover .nav-arrow,
.nav-item.active .nav-arrow {
  opacity: 1;
  transform: translateX(0);
}

.nav-icon {
  flex-shrink: 0;
}

.nav-action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(61, 217, 172, 0.18), rgba(247, 202, 117, 0.12));
  border: 1px solid rgba(61, 217, 172, 0.28);
  color: #3DD9AC;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s ease;
}

.nav-action:hover {
  background: linear-gradient(135deg, rgba(61, 217, 172, 0.28), rgba(247, 202, 117, 0.18));
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(61, 217, 172, 0.15);
}

/* Footer */
.sidebar-footer {
  padding: 14px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.user-avatar {
  width: 34px; height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3DD9AC, #F7CA75);
  display: grid; place-items: center;
  font-size: 13px;
  font-weight: 700;
  color: #060e0c;
  flex-shrink: 0;
}

.user-info {
  min-width: 0;
}

.user-email {
  margin: 0;
  font-size: 12px;
  color: rgba(232, 245, 240, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  margin: 1px 0 0;
  font-size: 11px;
  color: rgba(232, 245, 240, 0.4);
}

.logout-btn {
  background: transparent;
  border: 0;
  padding: 7px;
  border-radius: 8px;
  color: rgba(232, 245, 240, 0.4);
  cursor: pointer;
  transition: color 0.2s, background 0.2s;
  flex-shrink: 0;
}

.logout-btn:hover {
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}
</style>

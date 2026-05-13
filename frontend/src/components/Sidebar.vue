<script setup>
import { inject } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const togglePopup = inject('togglePopup')

const navItems = [
  { page: 'dashboard', icon: '☰', text: '仪表盘' },
  { page: 'learn', icon: '✍', text: '学习' },
  { page: 'review', icon: '↺', text: '复习' },
  { page: 'wordbank', icon: '📚', text: '词库' },
  { page: 'stats', icon: '📊', text: '统计' },
  { page: 'calendar', icon: '📅', text: '日历' },
]
</script>

<template>
  <nav class="sidebar">
    <div class="sidebar-header">
      <img src="/images/app_logo.png" alt="Logo" class="sidebar-logo">
      <h1>Hu Learn English</h1>
      <p class="subtitle">胡学-你的每日英语学习伙伴</p>
    </div>
    <ul class="nav-list">
      <li
        v-for="item in navItems"
        :key="item.page"
        class="nav-item"
        :class="{ active: route.name === item.page }"
        @click="$router.push({ name: item.page })"
      >
        <span class="nav-icon" v-html="item.icon"></span>
        <span class="nav-text">{{ item.text }}</span>
      </li>
    </ul>
    <div class="sidebar-footer" @click="togglePopup">
      <div class="user-info">
        <span class="user-avatar">{{ auth.initial }}</span>
        <span class="user-name">{{ auth.username }}</span>
        <span class="user-arrow">›</span>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.sidebar {
  position: fixed;
  left: 0; top: 0;
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--surface);
  border-right: 1px solid var(--border);
  z-index: 100;
  overflow-y: auto;
  padding-bottom: 60px;
}

.sidebar-header {
  padding: 24px 20px 16px;
  border-bottom: 1px solid var(--border);
  text-align: center;
}

.sidebar-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  margin-bottom: 8px;
}

.sidebar-header h1 {
  font-size: 20px;
  color: var(--primary);
}

.sidebar-header .subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.nav-list { list-style: none; padding: 8px 0; }

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
  font-size: 14px;
}

.nav-item:hover { background: var(--bg); color: var(--text); }
.nav-item.active { color: var(--primary); background: #eef2ff; font-weight: 600; }
.nav-icon { font-size: 18px; width: 24px; text-align: center; }

.sidebar-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  transition: background 0.15s;
}

.sidebar-footer:hover { background: var(--bg); }

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-arrow {
  font-size: 18px;
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .sidebar { display: none; }
}
</style>

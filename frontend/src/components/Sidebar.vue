<script setup>
import { inject } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const togglePopup = inject('togglePopup')

const navItems = [
  { page: 'dashboard', icon: '🏠', text: '首页' },
  { page: 'learn', icon: '✍', text: '学习' },
  { page: 'review', icon: '🔄', text: '复习' },
  { page: 'word-bank', icon: '📚', text: '词库' },
  { page: 'stats', icon: '📊', text: '统计' },
]
</script>

<template>
  <nav class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-logo-wrap">
        <img src="/images/app_logo.png" alt="Logo" class="sidebar-logo">
      </div>
      <h1>Hu Learn English</h1>
      <p class="subtitle">胡学 - 每日英语学习伙伴</p>
    </div>
    <ul class="nav-list">
      <li
        v-for="item in navItems"
        :key="item.page"
        class="nav-item"
        :class="{ active: route.name === item.page }"
        @click="$router.push({ name: item.page })"
      >
        <span class="nav-bar"></span>
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
  padding: 28px 20px 20px;
  border-bottom: 1px solid var(--border);
  text-align: center;
}

.sidebar-logo-wrap {
  display: inline-block;
  padding: 3px;
  border-radius: 14px;
  background: var(--gradient-primary);
  margin-bottom: 10px;
}

.sidebar-logo {
  width: 44px;
  height: 44px;
  border-radius: 11px;
  border: 2px solid var(--surface);
}

.sidebar-header h1 {
  font-size: 18px;
  font-weight: 800;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sidebar-header .subtitle {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
  font-weight: 500;
}

.nav-list { list-style: none; padding: 12px 0; }

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
  font-size: 14px;
  font-weight: 500;
  position: relative;
}

.nav-bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  border-radius: 0 3px 3px 0;
  background: var(--gradient-primary);
  transition: height 0.2s;
}

.nav-item:hover { color: var(--text); background: rgba(99,102,241,0.03); }
.nav-item.active { color: var(--primary); font-weight: 700; }
.nav-item.active .nav-bar { height: 20px; }
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
  gap: 10px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(99,102,241,0.3);
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
  color: var(--text-tertiary);
}

@media (max-width: 768px) {
  .sidebar { display: none; }
}
</style>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { page: 'dashboard', icon: '☰', text: '首页' },
  { page: 'learn', icon: '✍', text: '学习' },
  { page: 'review', icon: '↺', text: '复习' },
  { page: 'wordbank', icon: '📚', text: '词库' },
  { page: 'calendar', icon: '📅', text: '日历' },
]
</script>

<template>
  <nav class="mobile-nav">
    <div
      v-for="item in navItems"
      :key="item.page"
      class="mobile-nav-item"
      :class="{ active: route.name === item.page }"
      @click="$router.push({ name: item.page })"
    >
      <span class="mobile-nav-icon" v-html="item.icon"></span>
      <span>{{ item.text }}</span>
    </div>
  </nav>
</template>

<style scoped>
.mobile-nav {
  display: none;
  position: fixed;
  bottom: 0; left: 0;
  width: 100%;
  height: var(--mobile-nav-height);
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--surface);
  border-top: 1px solid var(--border);
  z-index: 100;
  justify-content: space-around;
  align-items: center;
}

.mobile-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px 12px;
}

.mobile-nav-item.active { color: var(--primary); }
.mobile-nav-icon { font-size: 20px; }

@media (max-width: 768px) {
  .mobile-nav { display: flex; }
}
</style>

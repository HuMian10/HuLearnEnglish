<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { page: 'dashboard', icon: '🏠', text: '首页' },
  { page: 'learn', icon: '✍', text: '学习' },
  { page: 'news', icon: '📰', text: '新闻' },
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
      <div v-if="route.name === item.page" class="nav-indicator"></div>
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
  z-index: 100;
  justify-content: space-around;
  align-items: center;
}

.mobile-nav::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border) 20%, var(--border) 80%, transparent);
}

.mobile-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 6px 16px;
  min-width: 64px;
  position: relative;
  transition: color 0.2s;
}

.mobile-nav-item.active { color: var(--primary); }

.mobile-nav-icon {
  font-size: 22px;
  transition: transform 0.2s;
}

.mobile-nav-item.active .mobile-nav-icon {
  transform: scale(1.1);
}

.nav-indicator {
  position: absolute;
  bottom: 2px;
  width: 16px;
  height: 3px;
  border-radius: 2px;
  background: var(--gradient-primary);
}

@media (max-width: 768px) {
  .mobile-nav { display: flex; }
}
</style>

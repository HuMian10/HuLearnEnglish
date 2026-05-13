<script setup>
import { inject } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const togglePopup = inject('togglePopup')
</script>

<template>
  <header class="mobile-header">
    <div class="mobile-header-brand">
      <img src="/images/app_logo.png" alt="Logo" class="mobile-header-logo">
      <span class="mobile-header-title">Hu Learn English</span>
    </div>
    <div class="mobile-header-avatar" @click="togglePopup">{{ auth.initial }}</div>
  </header>
</template>

<style scoped>
.mobile-header {
  display: none;
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 52px;
  padding-top: env(safe-area-inset-top);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  z-index: 100;
  align-items: center;
  justify-content: space-between;
  padding-left: 16px;
  padding-right: 16px;
}

.mobile-header-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-header-logo {
  width: 28px;
  height: 28px;
  border-radius: 6px;
}

.mobile-header-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--primary);
}

.mobile-header-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.2s;
}

.mobile-header-avatar:active { opacity: 0.8; }

@media (max-width: 768px) {
  .mobile-header { display: flex; }
}
</style>

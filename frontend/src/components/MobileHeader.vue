<script setup>
import { inject } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const togglePopup = inject('togglePopup')
</script>

<template>
  <header class="mobile-header">
    <div class="mobile-header-brand">
      <div class="mobile-header-logo-wrap">
        <img src="/images/app_logo.png" alt="Logo" class="mobile-header-logo">
      </div>
      <span class="mobile-header-title">Hu Learn</span>
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
  z-index: 100;
  align-items: center;
  justify-content: space-between;
  padding-left: 16px;
  padding-right: 16px;
}

.mobile-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border) 20%, var(--border) 80%, transparent);
}

.mobile-header-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-header-logo-wrap {
  padding: 2px;
  border-radius: 7px;
  background: var(--gradient-primary);
}

.mobile-header-logo {
  width: 24px;
  height: 24px;
  border-radius: 5px;
  border: 1.5px solid var(--surface);
}

.mobile-header-title {
  font-size: 16px;
  font-weight: 800;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.mobile-header-avatar {
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
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;
  box-shadow: 0 2px 6px rgba(99,102,241,0.3);
}

.mobile-header-avatar:active { opacity: 0.8; transform: scale(0.95); }

@media (max-width: 768px) {
  .mobile-header { display: flex; }
}
</style>

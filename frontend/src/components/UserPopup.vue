<script setup>
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'open-settings', 'logout'])

function openSettings(tab) {
  emit('update:modelValue', false)
  emit('open-settings', tab)
}

function handleLogout() {
  emit('update:modelValue', false)
  emit('logout')
}
</script>

<template>
  <Transition name="popup">
    <div v-if="modelValue" class="user-popup">
      <div class="popup-user-summary">
        <span class="popup-avatar">{{ auth.initial }}</span>
        <div class="popup-user-text">
          <div class="popup-username">{{ auth.username }}</div>
          <div class="popup-email-preview">{{ auth.user?.email || '未绑定邮箱' }}</div>
        </div>
      </div>
      <div class="popup-menu-list">
        <div class="popup-menu-item" @click="openSettings('user-info')">
          <div class="popup-menu-icon-wrap"><span>👤</span></div>
          <span class="popup-menu-text">用户信息</span>
          <span class="popup-menu-arrow">›</span>
        </div>
        <div class="popup-menu-item" @click="openSettings('learning-settings')">
          <div class="popup-menu-icon-wrap"><span>⚙</span></div>
          <span class="popup-menu-text">学习设置</span>
          <span class="popup-menu-arrow">›</span>
        </div>
        <div class="popup-menu-item" @click="openSettings('llm-settings')">
          <div class="popup-menu-icon-wrap"><span>🤖</span></div>
          <span class="popup-menu-text">LLM 配置</span>
          <span class="popup-menu-arrow">›</span>
        </div>
        <div class="popup-menu-item popup-menu-danger" @click="handleLogout">
          <div class="popup-menu-icon-wrap danger"><span>🚪</span></div>
          <span class="popup-menu-text">退出登录</span>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.user-popup {
  position: fixed;
  bottom: 80px;
  right: 24px;
  width: 240px;
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 150;
  overflow: hidden;
}

.popup-enter-active, .popup-leave-active {
  transition: opacity 0.2s, transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.popup-enter-from, .popup-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.96);
}

.popup-user-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--border);
}

.popup-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--gradient-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(99,102,241,0.3);
}

.popup-user-text { flex: 1; min-width: 0; }
.popup-username { font-size: 15px; font-weight: 700; color: var(--text); }
.popup-email-preview { font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.popup-menu-list { padding: 8px 0; }
.popup-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 14px;
  color: var(--text);
  font-weight: 500;
}

.popup-menu-item:hover { background: var(--bg); }

.popup-menu-icon-wrap {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  background: rgba(99,102,241,0.06);
  flex-shrink: 0;
}

.popup-menu-icon-wrap.danger {
  background: rgba(239,68,68,0.06);
}

.popup-menu-text { flex: 1; }
.popup-menu-arrow { font-size: 18px; color: var(--text-tertiary); }
.popup-menu-danger { color: var(--danger); }
.popup-menu-danger:hover { background: rgba(239,68,68,0.04); }

@media (max-width: 768px) {
  .user-popup {
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    max-height: 60vh;
    overflow-y: auto;
  }
}
</style>

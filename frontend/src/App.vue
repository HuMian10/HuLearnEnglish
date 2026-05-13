<script setup>
import { ref, provide, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from './stores/auth'
import { useRouter } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import MobileHeader from './components/MobileHeader.vue'
import MobileNav from './components/MobileNav.vue'
import UserPopup from './components/UserPopup.vue'
import SettingsModal from './components/SettingsModal.vue'

const auth = useAuthStore()
const router = useRouter()
const showSettings = ref(false)
const popupShow = ref(false)

function openSettings(tab) {
  showSettings.value = true
}

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}

provide('togglePopup', () => { popupShow.value = !popupShow.value })

// Close popup when clicking outside
function handleDocumentClick(e) {
  if (!popupShow.value) return
  if (e.target.closest('.user-popup')) return
  if (e.target.closest('.sidebar-footer')) return
  if (e.target.closest('.mobile-header-avatar')) return
  popupShow.value = false
}

onMounted(() => document.addEventListener('click', handleDocumentClick))
onUnmounted(() => document.removeEventListener('click', handleDocumentClick))
</script>

<template>
  <router-view v-if="!auth.isLoggedIn" />
  <div v-else class="app-container">
    <MobileHeader />
    <Sidebar />
    <main class="main-content">
      <router-view />
    </main>
    <MobileNav />
    <UserPopup v-model="popupShow" @open-settings="openSettings" @logout="handleLogout" />
    <SettingsModal v-model="showSettings" />
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
}
</style>

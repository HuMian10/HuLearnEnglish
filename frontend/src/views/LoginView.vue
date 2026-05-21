<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const tab = ref('login')
const error = ref('')

const loginForm = ref({ username: '', password: '' })
const registerForm = ref({ username: '', password: '', password2: '', email: '' })

async function handleLogin() {
  error.value = ''
  try {
    await auth.login(loginForm.value.username, loginForm.value.password)
    router.push({ name: 'dashboard' })
  } catch (e) {
    error.value = e.message
  }
}

async function handleRegister() {
  error.value = ''
  if (registerForm.value.password !== registerForm.value.password2) {
    error.value = '两次密码不一致'
    return
  }
  try {
    await auth.register(
      registerForm.value.username,
      registerForm.value.password,
      registerForm.value.email,
    )
    router.push({ name: 'dashboard' })
  } catch (e) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo-wrap">
        <img src="/images/app_logo.png" alt="Logo" class="login-logo">
      </div>
      <h1 class="login-title">Hu Learn English</h1>
      <p class="login-subtitle">你的每日英语学习伙伴</p>

      <div class="login-tabs">
        <div class="login-tab-track" :class="{ right: tab === 'register' }"></div>
        <button class="login-tab" :class="{ active: tab === 'login' }" @click="tab = 'login'; error = ''">登录</button>
        <button class="login-tab" :class="{ active: tab === 'register' }" @click="tab = 'register'; error = ''">注册</button>
      </div>

      <form v-if="tab === 'login'" @submit.prevent="handleLogin">
        <div class="form-field">
          <input v-model="loginForm.username" type="text" placeholder="用户名" required minlength="2" maxlength="20">
        </div>
        <div class="form-field">
          <input v-model="loginForm.password" type="password" placeholder="密码" required minlength="4">
        </div>
        <button type="submit" class="btn btn-primary login-btn">登录</button>
        <p class="form-error">{{ error }}</p>
      </form>

      <form v-else @submit.prevent="handleRegister">
        <div class="form-field">
          <input v-model="registerForm.username" type="text" placeholder="用户名 (2-20字符)" required minlength="2" maxlength="20">
        </div>
        <div class="form-field">
          <input v-model="registerForm.password" type="password" placeholder="密码 (至少4位)" required minlength="4">
        </div>
        <div class="form-field">
          <input v-model="registerForm.password2" type="password" placeholder="确认密码" required minlength="4">
        </div>
        <div class="form-field">
          <input v-model="registerForm.email" type="email" placeholder="邮箱 (选填，可用于找回密码)">
        </div>
        <button type="submit" class="btn btn-primary login-btn">注册</button>
        <p class="form-error">{{ error }}</p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.login-page::before {
  content: '';
  position: absolute;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: rgba(255,255,255,0.06);
  top: -100px;
  right: -100px;
}

.login-page::after {
  content: '';
  position: absolute;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: rgba(255,255,255,0.04);
  bottom: -80px;
  left: -60px;
}

.login-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 40px 32px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 0 0 1px rgba(255,255,255,0.2);
  text-align: center;
  position: relative;
  z-index: 1;
}

.login-logo-wrap {
  display: inline-block;
  padding: 4px;
  border-radius: 18px;
  background: var(--gradient-primary);
  margin-bottom: 12px;
  box-shadow: 0 4px 16px rgba(99,102,241,0.3);
}

.login-logo {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  border: 3px solid white;
}

.login-title {
  font-size: 26px;
  font-weight: 800;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
  margin-bottom: 28px;
  font-weight: 500;
}

.login-tabs {
  display: flex;
  position: relative;
  margin-bottom: 24px;
  background: var(--bg);
  border-radius: 10px;
  padding: 3px;
}

.login-tab-track {
  position: absolute;
  top: 3px;
  left: 3px;
  width: calc(50% - 3px);
  height: calc(100% - 6px);
  background: var(--surface);
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.login-tab-track.right {
  transform: translateX(100%);
}

.login-tab {
  flex: 1;
  padding: 10px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  position: relative;
  z-index: 1;
  transition: color 0.2s;
}

.login-tab.active { color: var(--primary); }

.form-field { margin-bottom: 14px; }
.form-field input {
  width: 100%;
  padding: 14px 16px;
  border: 1.5px solid var(--border);
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: var(--surface);
  color: var(--text);
}

.form-field input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
}

.login-btn {
  width: 100%;
  padding: 14px;
  font-size: 16px;
  margin-top: 8px;
  justify-content: center;
  border-radius: 10px;
}

.form-error {
  color: var(--danger);
  font-size: 13px;
  margin-top: 10px;
  text-align: center;
  min-height: 20px;
  font-weight: 500;
}
</style>

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
      <img src="/images/app_logo.png" alt="Logo" class="login-logo">
      <h1 class="login-title">Hu Learn English</h1>
      <p class="login-subtitle">胡学-你的每日英语学习伙伴</p>

      <div class="login-tabs">
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: var(--surface);
  border-radius: 16px;
  padding: 40px 32px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  text-align: center;
}

.login-logo { width: 72px; height: 72px; border-radius: 16px; margin-bottom: 12px; }
.login-title { font-size: 28px; font-weight: 700; color: var(--primary); }
.login-subtitle { font-size: 14px; color: var(--text-secondary); margin-top: 4px; margin-bottom: 24px; }

.login-tabs { display: flex; margin-bottom: 20px; border-bottom: 2px solid var(--border); }
.login-tab {
  flex: 1;
  padding: 10px;
  border: none;
  background: none;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}
.login-tab.active { color: var(--primary); border-bottom-color: var(--primary); }
.login-tab:hover { color: var(--primary); }

.form-field { margin-bottom: 14px; }
.form-field input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
.form-field input:focus { border-color: var(--primary); }

.login-btn { width: 100%; padding: 12px; font-size: 16px; margin-top: 4px; justify-content: center; }
.form-error { color: var(--danger); font-size: 13px; margin-top: 8px; text-align: center; min-height: 20px; }
</style>

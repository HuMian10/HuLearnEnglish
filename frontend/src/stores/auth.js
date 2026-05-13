import { defineStore } from 'pinia'
import { api } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    checked: false,
  }),
  getters: {
    isLoggedIn: (s) => !!s.user,
    username: (s) => s.user?.username || '',
    initial: (s) => s.user?.username?.[0]?.toUpperCase() || '',
  },
  actions: {
    async check() {
      try {
        const data = await api('auth/me')
        if (data.ok) {
          this.user = { id: data.user_id, username: data.username, email: data.email, created_at: data.created_at }
        } else {
          this.user = null
        }
      } catch {
        this.user = null
      }
      this.checked = true
    },
    async login(username, password) {
      const data = await api('auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      if (data.ok) {
        this.user = { id: data.user_id, username: data.username, email: '' }
        return true
      }
      throw new Error(data.error || '登录失败')
    },
    async register(username, password, email) {
      const data = await api('auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, password, email }),
      })
      if (data.ok) {
        this.user = { id: data.user_id, username: data.username, email: email || '' }
        return true
      }
      throw new Error(data.error || '注册失败')
    },
    async logout() {
      await api('auth/logout', { method: 'POST' }).catch(() => {})
      this.user = null
    },
    async updateEmail(email) {
      const data = await api('auth/email', {
        method: 'PUT',
        body: JSON.stringify({ email }),
      })
      if (data.ok) {
        if (this.user) this.user.email = email
        return true
      }
      throw new Error(data.error || '绑定失败')
    },
  },
})

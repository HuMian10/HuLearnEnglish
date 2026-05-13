import { defineStore } from 'pinia'
import { api } from '../api'

export const useLearningStore = defineStore('learning', {
  state: () => ({
    stats: null,
    settings: null,
    recognizeMode: 'direct',
    learnMode: 'flip',
  }),
  actions: {
    async fetchStats() {
      this.stats = await api('learning/stats')
    },
    async fetchSettings() {
      this.settings = await api('learning/settings')
      this.recognizeMode = this.settings?.recognize_mode || 'direct'
      this.learnMode = this.settings?.learn_mode || 'flip'
    },
    async saveSetting(key, value) {
      await api('learning/settings', {
        method: 'POST',
        body: JSON.stringify({ key, value }),
      })
    },
  },
})

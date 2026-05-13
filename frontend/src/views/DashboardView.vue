<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const route = useRoute()
const stats = ref({})
const pct = ref(0)
const plan = ref(null)
const planWords = ref([])
const completedIds = ref([])

onMounted(loadDashboard)
watch(() => route.path, (val) => { if (val === '/dashboard') loadDashboard() })

async function loadDashboard() {
  stats.value = await api('learning/stats')
  pct.value = stats.value.today_total > 0
    ? Math.round(stats.value.today_completed / stats.value.today_total * 100)
    : 0

  const planData = await api('plan/today')
  plan.value = planData.plan
  planWords.value = planData.words || []
  completedIds.value = JSON.parse(planData.plan?.completed_ids || '[]')
}

async function generatePlan() {
  await api('plan/generate', { method: 'POST' })
  await loadDashboard()
}
</script>

<template>
  <h2 class="page-title">今日学习</h2>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-value">{{ stats.today_total || 0 }}</div>
      <div class="stat-label">今日单词</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ stats.today_completed || 0 }}</div>
      <div class="stat-label">已完成</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ stats.mastered_count || 0 }}</div>
      <div class="stat-label">已掌握</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ stats.due_review || 0 }}</div>
      <div class="stat-label">待复习</div>
    </div>
  </div>

  <div class="section">
    <div class="section-header"><h3>学习进度</h3></div>
    <div class="progress-bar-container">
      <div class="progress-bar" :style="{ width: pct + '%' }"></div>
    </div>
    <p class="progress-text">{{ pct }}%</p>
  </div>

  <div class="section">
    <div class="section-header">
      <h3>今日计划</h3>
      <button v-if="!plan" class="btn btn-primary" @click="generatePlan">生成今日计划</button>
    </div>
    <div class="plan-words-list">
      <span
        v-for="w in planWords"
        :key="w.id"
        class="plan-word-chip"
        :class="{ done: completedIds.includes(w.id) }"
        @click="router.push({ name: 'learn' })"
      >{{ w.word }}</span>
    </div>
  </div>

  <div class="section">
    <h3>总体进度</h3>
    <div class="overall-stats">
      <div class="overall-stat"><span class="dot new"></span><span>未学习: <strong>{{ stats.unlearned || 0 }}</strong></span></div>
      <div class="overall-stat"><span class="dot learning"></span><span>学习中: <strong>{{ stats.learning_count || 0 }}</strong></span></div>
      <div class="overall-stat"><span class="dot mastered"></span><span>已掌握: <strong>{{ stats.mastered_count || 0 }}</strong></span></div>
    </div>
  </div>
</template>

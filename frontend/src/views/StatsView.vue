<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const stats = ref({})
const categories = ref([])

onMounted(loadStats)

async function loadStats() {
  stats.value = await api('learning/stats')
  categories.value = await api('words/categories')
}
</script>

<template>
  <h2 class="page-title">学习统计</h2>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-value">{{ stats.total_words || 0 }}</div>
      <div class="stat-label">总词汇量</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ stats.mastered_count || 0 }}</div>
      <div class="stat-label">已掌握</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ stats.learning_count || 0 }}</div>
      <div class="stat-label">学习中</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ stats.new_count || 0 }}</div>
      <div class="stat-label">已接触</div>
    </div>
  </div>

  <div class="section">
    <h3>分类进度</h3>
    <div class="category-progress-list">
      <div v-for="c in categories" :key="c.category" class="cat-progress-item">
        <span class="cat-progress-name">{{ c.category }}</span>
        <div class="cat-progress-bar">
          <div class="cat-progress-fill" :style="{ width: (stats.total_words > 0 ? Math.round(stats.mastered_count / stats.total_words * 100) : 0) + '%' }"></div>
        </div>
        <span class="cat-progress-text">{{ stats.total_words > 0 ? Math.round(stats.mastered_count / stats.total_words * 100) : 0 }}%</span>
      </div>
    </div>
  </div>
</template>

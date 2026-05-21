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

  <!-- Streak hero -->
  <div class="streak-hero">
    <div class="streak-flame-wrap">
      <span class="streak-flame">🔥</span>
    </div>
    <div class="streak-main">
      <div class="streak-number">{{ stats.streak_days || 0 }}</div>
      <div class="streak-label">天连续学习</div>
    </div>
    <div v-if="stats.best_streak > 0" class="streak-best">
      最高记录: {{ stats.best_streak }} 天
    </div>
  </div>

  <!-- Stats cards -->
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-icon-wrap"><span>📖</span></div>
      <div class="stat-value">{{ stats.total_words || 0 }}</div>
      <div class="stat-label">总词汇量</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon-wrap"><span>💪</span></div>
      <div class="stat-value">{{ stats.mastered_count || 0 }}</div>
      <div class="stat-label">已掌握</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon-wrap"><span>✍</span></div>
      <div class="stat-value">{{ stats.learning_count || 0 }}</div>
      <div class="stat-label">学习中</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon-wrap"><span>❌</span></div>
      <div class="stat-value">{{ stats.wrong_count || 0 }}</div>
      <div class="stat-label">错题数</div>
    </div>
  </div>

  <!-- Category progress -->
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

<style scoped>
.streak-hero {
  background: var(--gradient-hero);
  border-radius: var(--radius-xl);
  padding: 32px 24px;
  margin-bottom: 20px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(99,102,241,0.25);
  position: relative;
  overflow: hidden;
}

.streak-hero::before {
  content: '';
  position: absolute;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: rgba(255,255,255,0.06);
  top: -60px;
  right: -40px;
}

.streak-flame-wrap {
  margin-bottom: 8px;
}

.streak-flame {
  font-size: 48px;
  display: inline-block;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

.streak-main {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 8px;
}

.streak-number {
  font-size: 48px;
  font-weight: 900;
  color: white;
  letter-spacing: -2px;
  line-height: 1;
}

.streak-label {
  font-size: 16px;
  color: rgba(255,255,255,0.85);
  font-weight: 600;
}

.streak-best {
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  margin-top: 8px;
  font-weight: 500;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.stat-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--primary);
  letter-spacing: -0.5px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}
</style>

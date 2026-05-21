<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const stats = ref({})
const pct = ref(0)
const plan = ref(null)
const planWords = ref([])
const completedIds = ref([])
const calendarData = ref({})
const calendarYear = ref(new Date().getFullYear())
const calendarMonth = ref(new Date().getMonth() + 1)
const dueReview = ref(0)

// Day detail modal
const dayDetail = ref(null)
const dayDetailDate = ref('')

onMounted(loadDashboard)
watch(() => route.path, (val) => { if (val === '/dashboard') loadDashboard() })

async function loadDashboard() {
  stats.value = await api('learning/stats')
  pct.value = stats.value.today_total > 0
    ? Math.round(stats.value.today_completed / stats.value.today_total * 100)
    : 0
  dueReview.value = stats.value.due_review || 0

  const planData = await api('plan/today')
  plan.value = planData.plan
  planWords.value = planData.words || []
  completedIds.value = JSON.parse(planData.plan?.completed_ids || '[]')

  await loadCalendar(calendarYear.value, calendarMonth.value)
}

async function generatePlan() {
  await api('plan/generate', { method: 'POST' })
  await loadDashboard()
}

async function clearTodayPlan() {
  if (!confirm('确定要清空今日计划吗？')) return
  await api(`learning/day-progress?date=${today}`, { method: 'DELETE' })
  await loadDashboard()
}

async function clearAllPlans() {
  if (!confirm('确定要清空所有计划吗？此操作不可撤销！')) return
  await api('learning/all-plans', { method: 'DELETE' })
  await loadDashboard()
}

// Calendar
async function loadCalendar(year, month) {
  const data = await api(`learning/calendar?year=${year}&month=${month}`)
  calendarData.value = data.days || {}
}

const monthNames = ['', '一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']

const calendarDays = computed(() => {
  const year = calendarYear.value
  const month = calendarMonth.value
  const firstDay = new Date(year, month - 1, 1).getDay()
  const daysInMonth = new Date(year, month, 0).getDate()
  const days = []
  for (let i = 0; i < firstDay; i++) days.push(null)
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    days.push({ day: d, date: dateStr, ...calendarData.value[dateStr] })
  }
  return days
})

const today = new Date().toISOString().slice(0, 10)

function prevMonth() {
  if (calendarMonth.value === 1) { calendarMonth.value = 12; calendarYear.value-- }
  else calendarMonth.value--
  loadCalendar(calendarYear.value, calendarMonth.value)
}

function nextMonth() {
  if (calendarMonth.value === 12) { calendarMonth.value = 1; calendarYear.value++ }
  else calendarMonth.value++
  loadCalendar(calendarYear.value, calendarMonth.value)
}

async function openDayDetail(date) {
  dayDetailDate.value = date
  const data = await api(`learning/day-detail?date=${date}`)
  dayDetail.value = data
}

function closeDayDetail() {
  dayDetail.value = null
}

// Ring progress
const ringOffset = computed(() => {
  const circumference = 2 * Math.PI * 42
  return circumference - (circumference * pct.value / 100)
})
</script>

<template>
  <div class="dash-page">
    <!-- Hero banner -->
    <div class="hero-card">
      <div class="hero-content">
        <div class="hero-greeting">Hi, {{ auth.username }}</div>
        <div class="hero-streak" :class="{ zero: !stats.streak_days }">
          <span class="streak-flame">🔥</span>
          <span v-if="stats.streak_days">连续 <strong>{{ stats.streak_days }}</strong> 天</span>
          <span v-else>开始你的连续学习之旅</span>
          <span v-if="stats.best_streak > 0" class="streak-best">最高 {{ stats.best_streak }} 天</span>
        </div>
      </div>
      <!-- Quick actions on mobile -->
      <div class="hero-actions">
        <button v-if="dueReview > 0" class="hero-action-btn review" @click="router.push({ name: 'review' })">
          <span class="hero-action-icon">🔄</span>
          <span>复习 {{ dueReview }}</span>
        </button>
        <button class="hero-action-btn stats" @click="router.push({ name: 'stats' })">
          <span class="hero-action-icon">📊</span>
          <span>统计</span>
        </button>
      </div>
    </div>

    <!-- Stats grid -->
    <div class="stats-grid">
      <div class="stat-card" style="--accent: var(--primary)">
        <div class="stat-icon-wrap primary"><span>📋</span></div>
        <div class="stat-value">{{ stats.today_total || 0 }}</div>
        <div class="stat-label">今日单词</div>
      </div>
      <div class="stat-card" style="--accent: var(--success)">
        <div class="stat-icon-wrap success"><span>✅</span></div>
        <div class="stat-value">{{ stats.today_completed || 0 }}</div>
        <div class="stat-label">已完成</div>
      </div>
      <div class="stat-card" style="--accent: var(--warning)">
        <div class="stat-icon-wrap warning"><span>💪</span></div>
        <div class="stat-value">{{ stats.mastered_count || 0 }}</div>
        <div class="stat-label">已掌握</div>
      </div>
      <div class="stat-card" style="--accent: var(--danger)">
        <div class="stat-icon-wrap danger"><span>🔄</span></div>
        <div class="stat-value">{{ stats.due_review || 0 }}</div>
        <div class="stat-label">待复习</div>
      </div>
    </div>

    <!-- Progress ring -->
    <div class="section">
      <div class="section-header"><h3>学习进度</h3></div>
      <div class="ring-progress-wrap">
        <svg class="ring-svg" viewBox="0 0 100 100">
          <circle class="ring-bg" cx="50" cy="50" r="42" />
          <circle class="ring-fill" cx="50" cy="50" r="42" :stroke-dashoffset="ringOffset" />
        </svg>
        <div class="ring-text">
          <span class="ring-pct">{{ pct }}</span>
          <span class="ring-label">%</span>
        </div>
      </div>
    </div>

    <!-- Today's plan -->
    <div class="section">
      <div class="section-header">
        <h3>今日计划</h3>
        <div class="section-actions">
          <button v-if="!plan" class="btn btn-primary btn-small" @click="generatePlan">生成今日计划</button>
          <template v-if="plan">
            <button class="link-btn" @click="clearTodayPlan">清空今日</button>
            <button class="link-btn danger" @click="clearAllPlans">清空所有</button>
          </template>
        </div>
      </div>
      <div class="plan-words-list">
        <span
          v-for="w in planWords"
          :key="w.id"
          class="plan-word-chip"
          :class="{ done: completedIds.includes(w.id) }"
        >{{ completedIds.includes(w.id) ? '✓ ' : '' }}{{ w.word }}</span>
      </div>
    </div>

    <!-- Overall progress -->
    <div class="section">
      <h3>总体进度</h3>
      <div class="overall-bar">
        <div class="overall-fill new-fill" :style="{ width: (stats.unlearned || 0) / Math.max(stats.unlearned + stats.learning_count + stats.mastered_count, 1) * 100 + '%' }"></div>
        <div class="overall-fill learning-fill" :style="{ width: (stats.learning_count || 0) / Math.max(stats.unlearned + stats.learning_count + stats.mastered_count, 1) * 100 + '%' }"></div>
        <div class="overall-fill mastered-fill" :style="{ width: (stats.mastered_count || 0) / Math.max(stats.unlearned + stats.learning_count + stats.mastered_count, 1) * 100 + '%' }"></div>
      </div>
      <div class="overall-legend">
        <span class="legend-item"><span class="dot new"></span>未学习 {{ stats.unlearned || 0 }}</span>
        <span class="legend-item"><span class="dot learning"></span>学习中 {{ stats.learning_count || 0 }}</span>
        <span class="legend-item"><span class="dot mastered"></span>已掌握 {{ stats.mastered_count || 0 }}</span>
        <span class="legend-item" v-if="stats.wrong_count"><span class="dot wrong"></span>错题 {{ stats.wrong_count }}</span>
      </div>
    </div>

    <!-- Calendar -->
    <div class="section">
      <div class="section-header"><h3>学习日历</h3></div>
      <div class="cal-nav">
        <button class="cal-nav-btn" @click="prevMonth">&lt;</button>
        <span class="cal-month">{{ calendarYear }}年{{ monthNames[calendarMonth] }}</span>
        <button class="cal-nav-btn" @click="nextMonth">&gt;</button>
      </div>
      <div class="cal-weekdays">
        <span v-for="d in ['日','一','二','三','四','五','六']" :key="d" class="cal-wd">{{ d }}</span>
      </div>
      <div class="cal-grid">
        <div
          v-for="(cell, i) in calendarDays" :key="i"
          class="cal-cell"
          :class="{
            empty: !cell,
            today: cell?.date === today,
            done: cell?.completed > 0,
            all: cell?.completed > 0 && cell?.completed >= cell?.total,
            clickable: cell
          }"
          @click="cell && openDayDetail(cell.date)"
        >
          <span v-if="cell" class="cal-day">{{ cell.day }}</span>
          <span v-if="cell?.completed > 0" class="cal-dot"></span>
        </div>
      </div>
    </div>

    <!-- Day detail modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="dayDetail" class="dd-overlay" @click.self="closeDayDetail">
          <div class="dd-card">
            <button class="dd-close" @click="closeDayDetail">&times;</button>
            <div class="dd-date">{{ dayDetailDate }}</div>
            <div class="dd-stats">
              <div class="dd-stat">
                <span class="dd-stat-val">{{ dayDetail.total }}</span>
                <span class="dd-stat-label">计划</span>
              </div>
              <div class="dd-stat done">
                <span class="dd-stat-val">{{ dayDetail.completed }}</span>
                <span class="dd-stat-label">完成</span>
              </div>
              <div class="dd-stat review">
                <span class="dd-stat-val">{{ dayDetail.reviewed_count }}</span>
                <span class="dd-stat-label">复习</span>
              </div>
            </div>
            <div class="dd-progress-bar" v-if="dayDetail.total > 0">
              <div class="dd-progress-fill" :style="{ width: Math.round(dayDetail.completed / dayDetail.total * 100) + '%' }"></div>
            </div>
            <div v-if="dayDetail.words && dayDetail.words.length" class="dd-words">
              <div v-for="w in dayDetail.words" :key="w.id" class="dd-word-item" :class="{ done: w.completed }">
                <span class="dd-word">{{ w.word }}</span>
                <span class="dd-meaning">{{ w.meaning_cn || (w.meanings && w.meanings[0]?.meaning_cn) || '' }}</span>
                <span class="dd-status">{{ w.completed ? '✓' : '...' }}</span>
              </div>
            </div>
            <div v-else class="dd-empty">当天没有学习记录</div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.dash-page {
  animation: fadeInUp 0.3s ease;
}

/* Hero card */
.hero-card {
  background: var(--gradient-hero);
  border-radius: var(--radius-xl);
  padding: 24px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 20px rgba(99,102,241,0.25);
  position: relative;
  overflow: hidden;
}

.hero-card::before {
  content: '';
  position: absolute;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: rgba(255,255,255,0.06);
  top: -40px;
  right: -20px;
}

.hero-content { position: relative; z-index: 1; }

.hero-greeting {
  font-size: 22px;
  font-weight: 800;
  color: white;
  margin-bottom: 6px;
  letter-spacing: -0.3px;
}

.hero-streak {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: rgba(255,255,255,0.9);
  font-weight: 600;
}

.hero-streak.zero { color: rgba(255,255,255,0.7); }
.streak-flame { font-size: 20px; }
.streak-best { margin-left: 8px; font-size: 12px; color: rgba(255,255,255,0.6); }

.hero-actions {
  display: flex;
  gap: 8px;
  position: relative;
  z-index: 1;
}

.hero-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 12px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(8px);
}

.hero-action-btn.review {
  background: rgba(255,255,255,0.2);
  color: white;
}

.hero-action-btn.stats {
  background: rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.9);
}

.hero-action-btn:active { transform: scale(0.95); }
.hero-action-icon { font-size: 16px; }

/* Stats grid */
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
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  margin-bottom: 2px;
}

.stat-icon-wrap.primary { background: rgba(99,102,241,0.08); }
.stat-icon-wrap.success { background: rgba(16,185,129,0.08); }
.stat-icon-wrap.warning { background: rgba(245,158,11,0.08); }
.stat-icon-wrap.danger { background: rgba(239,68,68,0.08); }

/* Ring progress */
.ring-progress-wrap {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}

.ring-svg {
  width: 120px;
  height: 120px;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: var(--border);
  stroke-width: 8;
}

.ring-fill {
  fill: none;
  stroke: url(#ringGrad);
  stroke: var(--primary);
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 2 * 3.14159 * 42;
  transition: stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.ring-text {
  position: absolute;
  display: flex;
  align-items: baseline;
  justify-content: center;
}

.ring-progress-wrap {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px 0;
}

.ring-pct {
  font-size: 32px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -1px;
}

.ring-label {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-left: 2px;
}

/* Link buttons */
.link-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.15s;
}

.link-btn:hover { color: var(--primary); background: rgba(99,102,241,0.06); }
.link-btn.danger:hover { color: var(--danger); background: rgba(239,68,68,0.06); }

/* Overall bar */
.overall-bar {
  display: flex;
  height: 10px;
  border-radius: 5px;
  overflow: hidden;
  background: var(--border);
  margin-bottom: 12px;
}

.overall-fill { height: 100%; transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
.new-fill { background: var(--border); }
.learning-fill { background: var(--gradient-warm); }
.mastered-fill { background: var(--gradient-success); }

.overall-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.dot.wrong { background: var(--danger); }

/* Calendar */
.cal-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.cal-nav-btn {
  width: 32px; height: 32px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.cal-nav-btn:active { background: var(--bg); transform: scale(0.95); }

.cal-month { font-size: 15px; font-weight: 700; color: var(--text); }

.cal-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  margin-bottom: 4px;
}

.cal-wd { font-size: 12px; color: var(--text-tertiary); font-weight: 700; }

.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.cal-cell {
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  position: relative;
  font-size: 13px;
  transition: all 0.15s;
}

.cal-cell.clickable { cursor: pointer; }
.cal-cell.clickable:hover { background: rgba(99,102,241,0.06); }
.cal-cell.today { background: rgba(99,102,241,0.1); font-weight: 700; color: var(--primary); box-shadow: inset 0 0 0 2px var(--primary); border-radius: 10px; }
.cal-cell.today:hover { background: rgba(99,102,241,0.15); }
.cal-cell.done { background: rgba(16,185,129,0.06); }
.cal-cell.all { background: rgba(16,185,129,0.12); }

.cal-day { line-height: 1; }

.cal-dot {
  width: 4px; height: 4px;
  border-radius: 50%;
  background: var(--success);
  margin-top: 3px;
}

/* Day detail modal */
.dd-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 20px;
}

.dd-card {
  background: var(--surface);
  border-radius: var(--radius-xl);
  padding: 24px;
  max-width: 400px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
  box-shadow: var(--shadow-lg);
}

.dd-close {
  position: absolute;
  top: 12px;
  right: 14px;
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  line-height: 1;
  padding: 4px;
  transition: color 0.2s;
}

.dd-close:hover { color: var(--text); }

.dd-date {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 16px;
}

.dd-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.dd-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  padding: 12px;
  background: var(--bg);
  border-radius: var(--radius-sm);
}

.dd-stat-val { font-size: 22px; font-weight: 800; color: var(--text); }
.dd-stat.done .dd-stat-val { color: var(--success); }
.dd-stat.review .dd-stat-val { color: var(--primary); }
.dd-stat-label { font-size: 12px; color: var(--text-secondary); margin-top: 2px; font-weight: 500; }

.dd-progress-bar {
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 16px;
}

.dd-progress-fill {
  height: 100%;
  background: var(--gradient-success);
  border-radius: 3px;
  transition: width 0.3s;
}

.dd-words {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dd-word-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg);
  border-radius: var(--radius-sm);
  font-size: 14px;
}

.dd-word-item.done { opacity: 0.7; }

.dd-word {
  font-weight: 600;
  color: var(--text);
  min-width: 60px;
}

.dd-meaning {
  flex: 1;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.dd-status {
  font-size: 13px;
  flex-shrink: 0;
}

.dd-word-item.done .dd-status { color: var(--success); }

.dd-empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 20px;
  font-size: 14px;
}

/* Modal transition */
.modal-enter-active { transition: opacity 0.2s; }
.modal-leave-active { transition: opacity 0.15s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .dd-card { animation: modalIn 0.25s ease; }
.modal-leave-active .dd-card { animation: modalOut 0.15s ease; }

@keyframes modalIn {
  from { transform: scale(0.95) translateY(8px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}

@keyframes modalOut {
  from { transform: scale(1); opacity: 1; }
  to { transform: scale(0.95); opacity: 0; }
}

/* Fade in up */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .hero-card { flex-direction: column; gap: 12px; align-items: flex-start; }
  .hero-actions { width: 100%; }
  .hero-action-btn { flex: 1; justify-content: center; }
}
</style>

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

async function loadCalendar(year, month) {
  const data = await api(`learning/calendar?year=${year}&month=${month}`)
  calendarData.value = data.days || {}
}

const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

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

const totalWords = computed(() => (stats.value.unlearned || 0) + (stats.value.learning_count || 0) + (stats.value.mastered_count || 0))
const masteredPct = computed(() => totalWords.value > 0 ? Math.round((stats.value.mastered_count || 0) / totalWords.value * 100) : 0)
const learningPct = computed(() => totalWords.value > 0 ? Math.round((stats.value.learning_count || 0) / totalWords.value * 100) : 0)

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
function closeDayDetail() { dayDetail.value = null }

const ringOffset = computed(() => {
  const circumference = 2 * Math.PI * 46
  return circumference - (circumference * pct.value / 100)
})

function getGreeting() {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
}

const weekDays = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
</script>

<template>
  <div class="dash-page">
    <!-- Greeting header -->
    <div class="greet-bar">
      <div class="greet-left">
        <h2 class="greet-text">{{ getGreeting() }}，{{ auth.username }}</h2>
        <div class="greet-streak" :class="{ active: stats.streak_days }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>
          <span v-if="stats.streak_days">连续 <strong>{{ stats.streak_days }}</strong> 天</span>
          <span v-else>尚未开始连续学习</span>
          <span v-if="stats.best_streak > 0" class="streak-max">最高 {{ stats.best_streak }}天</span>
        </div>
      </div>
      <div class="greet-actions">
        <button v-if="dueReview > 0" class="action-pill review" @click="router.push({ name: 'review' })">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
          复习 {{ dueReview }}
        </button>
        <button class="action-pill learn" @click="router.push({ name: 'learn' })">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          开始学习
        </button>
      </div>
    </div>

    <!-- Stats cards row -->
    <div class="stat-row">
      <div class="stat-card">
        <div class="sc-top">
          <div class="sc-icon today-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
          </div>
          <span class="sc-label">今日任务</span>
        </div>
        <div class="sc-value-row">
          <span class="sc-num">{{ stats.today_completed || 0 }}</span>
          <span class="sc-divider">/</span>
          <span class="sc-total">{{ stats.today_total || 0 }}</span>
        </div>
        <div class="sc-bar"><div class="sc-bar-fill" :style="{ width: pct + '%' }"></div></div>
      </div>

      <div class="stat-card">
        <div class="sc-top">
          <div class="sc-icon mastered-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          </div>
          <span class="sc-label">已掌握</span>
        </div>
        <div class="sc-value-row">
          <span class="sc-num green">{{ stats.mastered_count || 0 }}</span>
        </div>
        <div class="sc-bar"><div class="sc-bar-fill green-fill" :style="{ width: masteredPct + '%' }"></div></div>
      </div>

      <div class="stat-card">
        <div class="sc-top">
          <div class="sc-icon review-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
          </div>
          <span class="sc-label">待复习</span>
        </div>
        <div class="sc-value-row">
          <span class="sc-num" :class="{ orange: dueReview > 0 }">{{ dueReview }}</span>
        </div>
        <div class="sc-bar"><div class="sc-bar-fill" :class="{ 'orange-fill': dueReview > 0 }" :style="{ width: Math.min(dueReview * 5, 100) + '%' }"></div></div>
      </div>

      <div class="stat-card">
        <div class="sc-top">
          <div class="sc-icon vocab-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          </div>
          <span class="sc-label">学习中</span>
        </div>
        <div class="sc-value-row">
          <span class="sc-num purple">{{ stats.learning_count || 0 }}</span>
        </div>
        <div class="sc-bar"><div class="sc-bar-fill purple-fill" :style="{ width: learningPct + '%' }"></div></div>
      </div>
    </div>

    <!-- Two column layout: progress + calendar -->
    <div class="main-grid">
      <!-- Left: Progress & Plan -->
      <div class="col-left">
        <!-- Today's progress -->
        <div class="card">
          <div class="card-header">
            <h3>今日进度</h3>
            <span class="card-badge" :class="{ complete: pct >= 100 }">{{ pct }}%</span>
          </div>
          <div class="progress-ring-wrap">
            <svg class="ring-svg" viewBox="0 0 100 100">
              <defs>
                <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style="stop-color:#6366f1"/>
                  <stop offset="100%" style="stop-color:#8b5cf6"/>
                </linearGradient>
              </defs>
              <circle class="ring-bg" cx="50" cy="50" r="46" />
              <circle class="ring-fill" cx="50" cy="50" r="46" :stroke-dashoffset="ringOffset" stroke="url(#ringGrad)" />
            </svg>
            <div class="ring-center">
              <span class="ring-pct">{{ pct }}</span>
              <span class="ring-unit">%</span>
            </div>
          </div>
          <div v-if="pct < 100 && stats.today_total > 0" class="ring-hint">
            还需完成 <strong>{{ (stats.today_total || 0) - (stats.today_completed || 0) }}</strong> 个单词
          </div>
          <div v-else-if="pct >= 100" class="ring-hint done">今日目标已完成</div>
        </div>

        <!-- Overall progress -->
        <div class="card">
          <div class="card-header">
            <h3>词库总览</h3>
            <span class="card-sub">{{ totalWords }} 词</span>
          </div>
          <div class="overall-bar">
            <div class="ob-fill mastered" :style="{ width: masteredPct + '%' }"></div>
            <div class="ob-fill learning" :style="{ width: learningPct + '%' }"></div>
          </div>
          <div class="overall-legend">
            <div class="ol-item">
              <span class="ol-dot mastered"></span>
              <span class="ol-text">已掌握</span>
              <span class="ol-num">{{ stats.mastered_count || 0 }}</span>
            </div>
            <div class="ol-item">
              <span class="ol-dot learning"></span>
              <span class="ol-text">学习中</span>
              <span class="ol-num">{{ stats.learning_count || 0 }}</span>
            </div>
            <div class="ol-item">
              <span class="ol-dot fresh"></span>
              <span class="ol-text">未学习</span>
              <span class="ol-num">{{ stats.unlearned || 0 }}</span>
            </div>
            <div class="ol-item" v-if="stats.wrong_count">
              <span class="ol-dot wrong"></span>
              <span class="ol-text">错题</span>
              <span class="ol-num">{{ stats.wrong_count }}</span>
            </div>
          </div>
        </div>

        <!-- Today's plan -->
        <div class="card">
          <div class="card-header">
            <h3>今日计划</h3>
            <div class="card-actions">
              <button v-if="!plan" class="pill-btn primary" @click="generatePlan">生成计划</button>
              <template v-if="plan">
                <button class="text-btn" @click="clearTodayPlan">清空今日</button>
                <button class="text-btn warn" @click="clearAllPlans">清空所有</button>
              </template>
            </div>
          </div>
          <div v-if="planWords.length" class="plan-list">
            <span
              v-for="w in planWords"
              :key="w.id"
              class="plan-chip"
              :class="{ done: completedIds.includes(w.id) }"
            >
              <svg v-if="completedIds.includes(w.id)" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              {{ w.word }}
            </span>
          </div>
          <div v-else class="plan-empty">
            <span>暂无学习计划</span>
          </div>
        </div>
      </div>

      <!-- Right: Calendar -->
      <div class="col-right">
        <div class="card calendar-card">
          <div class="card-header">
            <h3>学习日历</h3>
            <div class="cal-nav">
              <button class="nav-arrow" @click="prevMonth">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
              </button>
              <span class="cal-label">{{ monthNames[calendarMonth - 1] }} {{ calendarYear }}</span>
              <button class="nav-arrow" @click="nextMonth">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
              </button>
            </div>
          </div>
          <div class="cal-weekdays">
            <span v-for="d in weekDays" :key="d" class="cw">{{ d }}</span>
          </div>
          <div class="cal-grid">
            <div
              v-for="(cell, i) in calendarDays" :key="i"
              class="cc"
              :class="{
                empty: !cell,
                today: cell?.date === today,
                done: cell?.completed > 0 && cell?.completed < cell?.total,
                all: cell?.completed > 0 && cell?.completed >= cell?.total,
                clickable: cell
              }"
              @click="cell && openDayDetail(cell.date)"
            >
              <span v-if="cell" class="cc-num">{{ cell.day }}</span>
              <span v-if="cell?.completed > 0 && cell?.total > 0" class="cc-bar">
                <span class="cc-bar-fill" :style="{ width: Math.round(cell.completed / cell.total * 100) + '%' }"></span>
              </span>
            </div>
          </div>
          <div class="cal-footer">
            <span class="cf-legend"><span class="cf-dot today-dot"></span> 今天</span>
            <span class="cf-legend"><span class="cf-dot done-dot"></span> 已学习</span>
            <span class="cf-legend"><span class="cf-dot all-dot"></span> 已完成</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Day detail modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="dayDetail" class="dd-overlay" @click.self="closeDayDetail">
          <div class="dd-card">
            <button class="dd-close" @click="closeDayDetail">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
            <div class="dd-date">{{ dayDetailDate }}</div>
            <div class="dd-stats">
              <div class="dd-stat"><span class="dd-val">{{ dayDetail.total }}</span><span class="dd-lbl">计划</span></div>
              <div class="dd-stat done"><span class="dd-val">{{ dayDetail.completed }}</span><span class="dd-lbl">完成</span></div>
              <div class="dd-stat review"><span class="dd-val">{{ dayDetail.reviewed_count }}</span><span class="dd-lbl">复习</span></div>
            </div>
            <div class="dd-bar" v-if="dayDetail.total > 0">
              <div class="dd-bar-fill" :style="{ width: Math.round(dayDetail.completed / dayDetail.total * 100) + '%' }"></div>
            </div>
            <div v-if="dayDetail.words && dayDetail.words.length" class="dd-words">
              <div v-for="w in dayDetail.words" :key="w.id" class="dd-word" :class="{ done: w.completed }">
                <span class="dd-w-check">
                  <svg v-if="w.completed" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                  <span v-else class="dd-w-circle"></span>
                </span>
                <span class="dd-w-text">{{ w.word }}</span>
                <span class="dd-w-meaning">{{ w.meaning_cn || (w.meanings && w.meanings[0]?.meaning_cn) || '' }}</span>
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
.dash-page { animation: fadeIn 0.35s ease; }

/* ===== Greeting ===== */
.greet-bar {
  display: flex; align-items: flex-end; justify-content: space-between;
  margin-bottom: 24px; flex-wrap: wrap; gap: 12px;
}
.greet-text { font-size: 24px; font-weight: 800; color: var(--text); letter-spacing: -0.5px; }
.greet-streak {
  display: flex; align-items: center; gap: 6px; font-size: 13px;
  color: var(--text-tertiary); font-weight: 500; margin-top: 4px;
}
.greet-streak.active { color: var(--warning); }
.greet-streak svg { flex-shrink: 0; }
.greet-streak strong { font-weight: 700; }
.streak-max { font-size: 12px; color: var(--text-tertiary); margin-left: 4px; }

.greet-actions { display: flex; gap: 8px; }
.action-pill {
  display: inline-flex; align-items: center; gap: 6px; padding: 9px 18px;
  border-radius: 10px; border: none; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
}
.action-pill.review {
  background: rgba(245,158,11,0.08); color: var(--warning);
  border: 1px solid rgba(245,158,11,0.15);
}
.action-pill.review:hover { background: rgba(245,158,11,0.14); }
.action-pill.learn {
  background: var(--gradient-primary); color: white;
  box-shadow: 0 2px 8px rgba(99,102,241,0.25);
}
.action-pill.learn:hover { box-shadow: 0 4px 16px rgba(99,102,241,0.35); transform: translateY(-1px); }

/* ===== Stat cards ===== */
.stat-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;
}
.stat-card {
  background: var(--surface); border-radius: 16px; padding: 18px;
  border: 1px solid var(--border); transition: all 0.2s;
}
.stat-card:hover { border-color: rgba(99,102,241,0.15); box-shadow: var(--shadow); }

.sc-top { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.sc-icon {
  width: 32px; height: 32px; border-radius: 8px; display: flex;
  align-items: center; justify-content: center;
}
.today-icon { background: rgba(99,102,241,0.08); color: var(--primary); }
.mastered-icon { background: rgba(16,185,129,0.08); color: var(--success); }
.review-icon { background: rgba(245,158,11,0.08); color: var(--warning); }
.vocab-icon { background: rgba(139,92,246,0.08); color: #8b5cf6; }
.sc-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }

.sc-value-row { display: flex; align-items: baseline; gap: 2px; margin-bottom: 10px; }
.sc-num { font-size: 28px; font-weight: 800; color: var(--text); letter-spacing: -0.5px; }
.sc-num.green { color: var(--success); }
.sc-num.orange { color: var(--warning); }
.sc-num.purple { color: #8b5cf6; }
.sc-divider { font-size: 20px; color: var(--text-tertiary); font-weight: 300; margin: 0 2px; }
.sc-total { font-size: 18px; color: var(--text-tertiary); font-weight: 600; }

.sc-bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
.sc-bar-fill { height: 100%; background: var(--gradient-primary); border-radius: 2px; transition: width 0.6s cubic-bezier(0.4,0,0.2,1); }
.sc-bar-fill.green-fill { background: var(--gradient-success); }
.sc-bar-fill.orange-fill { background: var(--gradient-warm); }
.sc-bar-fill.purple-fill { background: linear-gradient(135deg, #8b5cf6, #a78bfa); }

/* ===== Main grid ===== */
.main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.card {
  background: var(--surface); border-radius: 16px; padding: 20px;
  border: 1px solid var(--border); margin-bottom: 16px;
}
.card:last-child { margin-bottom: 0; }

.card-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.card-header h3 { font-size: 16px; font-weight: 700; color: var(--text); }
.card-badge {
  font-size: 13px; font-weight: 700; color: var(--primary);
  background: rgba(99,102,241,0.08); padding: 3px 10px; border-radius: 8px;
}
.card-badge.complete { background: rgba(16,185,129,0.08); color: var(--success); }
.card-sub { font-size: 13px; color: var(--text-tertiary); font-weight: 500; }
.card-actions { display: flex; gap: 6px; }

/* ===== Progress ring ===== */
.progress-ring-wrap {
  position: relative; display: flex; justify-content: center; align-items: center;
  padding: 12px 0;
}
.ring-svg { width: 140px; height: 140px; transform: rotate(-90deg); }
.ring-bg { fill: none; stroke: var(--border); stroke-width: 6; }
.ring-fill {
  fill: none; stroke-width: 6; stroke-linecap: round;
  stroke-dasharray: 2 * 3.14159 * 46;
  transition: stroke-dashoffset 0.8s cubic-bezier(0.4,0,0.2,1);
}
.ring-center { position: absolute; display: flex; align-items: baseline; }
.ring-pct { font-size: 36px; font-weight: 800; color: var(--text); letter-spacing: -1px; }
.ring-unit { font-size: 16px; font-weight: 600; color: var(--text-secondary); margin-left: 2px; }

.ring-hint { text-align: center; font-size: 13px; color: var(--text-secondary); margin-top: 8px; }
.ring-hint strong { color: var(--primary); font-weight: 700; }
.ring-hint.done { color: var(--success); }

/* ===== Overall bar ===== */
.overall-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--border); margin-bottom: 16px; }
.ob-fill { height: 100%; transition: width 0.5s cubic-bezier(0.4,0,0.2,1); }
.ob-fill.mastered { background: var(--gradient-success); border-radius: 4px 0 0 4px; }
.ob-fill.learning { background: linear-gradient(135deg, #8b5cf6, #a78bfa); }

.overall-legend { display: flex; flex-wrap: wrap; gap: 16px; }
.ol-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-secondary); }
.ol-dot { width: 8px; height: 8px; border-radius: 3px; flex-shrink: 0; }
.ol-dot.mastered { background: var(--success); }
.ol-dot.learning { background: #8b5cf6; }
.ol-dot.fresh { background: var(--border); }
.ol-dot.wrong { background: var(--danger); }
.ol-text { font-weight: 500; }
.ol-num { font-weight: 700; color: var(--text); margin-left: 2px; }

/* ===== Plan ===== */
.pill-btn {
  padding: 6px 14px; border-radius: 8px; border: none; font-size: 12px;
  font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.pill-btn.primary { background: var(--gradient-primary); color: white; }
.pill-btn.primary:hover { box-shadow: 0 2px 8px rgba(99,102,241,0.3); }

.text-btn {
  background: none; border: none; color: var(--text-secondary); font-size: 12px;
  font-weight: 600; cursor: pointer; padding: 4px 8px; border-radius: 6px; transition: all 0.15s;
}
.text-btn:hover { color: var(--primary); background: rgba(99,102,241,0.04); }
.text-btn.warn:hover { color: var(--danger); background: rgba(239,68,68,0.04); }

.plan-list { display: flex; flex-wrap: wrap; gap: 6px; }
.plan-chip {
  display: inline-flex; align-items: center; gap: 4px; padding: 5px 14px;
  border-radius: 8px; font-size: 13px; font-weight: 500;
  background: var(--bg); color: var(--text-secondary); border: 1px solid transparent;
  transition: all 0.15s;
}
.plan-chip.done {
  background: rgba(16,185,129,0.06); color: var(--success);
  border-color: rgba(16,185,129,0.15);
}
.plan-chip:not(.done):hover { border-color: var(--primary); color: var(--primary); }
.plan-empty { font-size: 13px; color: var(--text-tertiary); padding: 12px 0; text-align: center; }

/* ===== Calendar ===== */
.calendar-card { height: 100%; display: flex; flex-direction: column; }
.cal-nav { display: flex; align-items: center; gap: 8px; }
.nav-arrow {
  width: 28px; height: 28px; border-radius: 8px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text-secondary); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all 0.15s;
}
.nav-arrow:hover { border-color: var(--primary); color: var(--primary); }
.cal-label { font-size: 14px; font-weight: 600; color: var(--text); min-width: 90px; text-align: center; }

.cal-weekdays { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; margin-bottom: 6px; }
.cw { font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; padding: 4px 0; }

.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; }
.cc {
  aspect-ratio: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; border-radius: 10px; position: relative; transition: all 0.15s;
}
.cc.clickable { cursor: pointer; }
.cc.clickable:hover { background: var(--bg); }
.cc.today {
  background: rgba(99,102,241,0.08); box-shadow: inset 0 0 0 1.5px var(--primary);
}
.cc.today .cc-num { color: var(--primary); font-weight: 700; }
.cc.done { background: rgba(16,185,129,0.06); }
.cc.all { background: rgba(16,185,129,0.12); }

.cc-num { font-size: 13px; color: var(--text); line-height: 1; font-weight: 500; }

.cc-bar {
  width: 16px; height: 3px; background: var(--border); border-radius: 1.5px;
  margin-top: 3px; overflow: hidden;
}
.cc-bar-fill { height: 100%; background: var(--gradient-primary); border-radius: 1.5px; }
.cc.all .cc-bar-fill { background: var(--gradient-success); }

.cal-footer {
  display: flex; gap: 16px; margin-top: 12px; padding-top: 12px;
  border-top: 1px solid var(--border);
}
.cf-legend { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-tertiary); font-weight: 500; }
.cf-dot { width: 8px; height: 8px; border-radius: 3px; }
.cf-dot.today-dot { border: 1.5px solid var(--primary); background: rgba(99,102,241,0.15); }
.cf-dot.done-dot { background: rgba(16,185,129,0.3); }
.cf-dot.all-dot { background: var(--success); }

/* ===== Day detail modal ===== */
.dd-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.35);
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  z-index: 200; padding: 20px;
}
.dd-card {
  background: var(--surface); border-radius: 20px; padding: 24px;
  max-width: 400px; width: 100%; max-height: 80vh; overflow-y: auto;
  position: relative; box-shadow: var(--shadow-lg);
}
.dd-close {
  position: absolute; top: 12px; right: 12px; background: none; border: none;
  color: var(--text-tertiary); cursor: pointer; padding: 4px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; transition: all 0.15s;
}
.dd-close:hover { color: var(--text); background: var(--bg); }

.dd-date { font-size: 18px; font-weight: 800; color: var(--text); margin-bottom: 16px; }
.dd-stats { display: flex; gap: 10px; margin-bottom: 12px; }
.dd-stat {
  flex: 1; text-align: center; padding: 12px 8px; background: var(--bg); border-radius: 10px;
}
.dd-val { display: block; font-size: 22px; font-weight: 800; color: var(--text); }
.dd-stat.done .dd-val { color: var(--success); }
.dd-stat.review .dd-val { color: var(--primary); }
.dd-lbl { font-size: 11px; color: var(--text-secondary); font-weight: 500; margin-top: 2px; }

.dd-bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; margin-bottom: 16px; }
.dd-bar-fill { height: 100%; background: var(--gradient-success); border-radius: 2px; transition: width 0.3s; }

.dd-words { display: flex; flex-direction: column; gap: 4px; }
.dd-word {
  display: flex; align-items: center; gap: 10px; padding: 8px 12px;
  background: var(--bg); border-radius: 8px; font-size: 14px;
}
.dd-word.done { opacity: 0.65; }
.dd-w-check { width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; color: var(--success); flex-shrink: 0; }
.dd-w-circle { width: 12px; height: 12px; border-radius: 50%; border: 1.5px solid var(--border); }
.dd-w-text { font-weight: 600; color: var(--text); min-width: 60px; }
.dd-w-meaning { flex: 1; font-size: 13px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dd-empty { text-align: center; color: var(--text-secondary); padding: 20px; font-size: 14px; }

/* ===== Transitions ===== */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.modal-enter-active { transition: opacity 0.2s; }
.modal-leave-active { transition: opacity 0.15s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .dd-card { animation: modalIn 0.2s ease; }
.modal-leave-active .dd-card { animation: modalOut 0.15s ease; }
@keyframes modalIn { from { transform: scale(0.96) translateY(8px); opacity: 0; } to { transform: scale(1) translateY(0); opacity: 1; } }
@keyframes modalOut { from { transform: scale(1); opacity: 1; } to { transform: scale(0.96); opacity: 0; } }

/* ===== Responsive ===== */
@media (max-width: 900px) {
  .main-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .greet-bar { flex-direction: column; align-items: flex-start; }
  .greet-text { font-size: 20px; }
  .stat-row { grid-template-columns: repeat(2, 1fr); }
  .sc-num { font-size: 24px; }
}
</style>
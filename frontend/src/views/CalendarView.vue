<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

const year = ref(new Date().getFullYear())
const month = ref(new Date().getMonth() + 1)
const calendarData = ref({ days: {} })
const selectedDate = ref(null)
const dayDetail = ref(null)
const isMobile = ref(false)

onMounted(() => {
  loadCalendar()
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

function checkMobile() {
  isMobile.value = window.innerWidth <= 768
}

async function loadCalendar() {
  calendarData.value = await api(`learning/calendar?year=${year.value}&month=${month.value}`)
  dayDetail.value = null
}

function prev() {
  month.value--
  if (month.value < 1) { month.value = 12; year.value-- }
  loadCalendar()
}

function next() {
  month.value++
  if (month.value > 12) { month.value = 1; year.value++ }
  loadCalendar()
}

function getFirstDay() {
  return new Date(calendarData.value.year || year.value, (calendarData.value.month || month.value) - 1, 1).getDay()
}

function getDaysInMonth() {
  return new Date(calendarData.value.year || year.value, calendarData.value.month || month.value, 0).getDate()
}

function isToday(dateStr) {
  const now = new Date()
  return dateStr === `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`
}

function getDayClass(d) {
  const dateStr = `${calendarData.value.year}-${String(calendarData.value.month).padStart(2,'0')}-${String(d).padStart(2,'0')}`
  const dayData = calendarData.value.days?.[dateStr]
  let cls = 'calendar-day'
  if (isToday(dateStr)) cls += ' today'
  if (selectedDate.value === dateStr) cls += ' selected'
  if (dayData) {
    const pct = dayData.total > 0 ? Math.round(dayData.completed / dayData.total * 100) : 0
    cls += pct >= 100 ? ' all-done' : ' has-data'
  }
  return cls
}

function getDayPct(d) {
  const dateStr = `${calendarData.value.year}-${String(calendarData.value.month).padStart(2,'0')}-${String(d).padStart(2,'0')}`
  const dayData = calendarData.value.days?.[dateStr]
  return dayData ? (dayData.total > 0 ? Math.round(dayData.completed / dayData.total * 100) : 0) : 0
}

function getDayData(d) {
  const dateStr = `${calendarData.value.year}-${String(calendarData.value.month).padStart(2,'0')}-${String(d).padStart(2,'0')}`
  return calendarData.value.days?.[dateStr]
}

async function selectDate(d) {
  const dateStr = `${calendarData.value.year}-${String(calendarData.value.month).padStart(2,'0')}-${String(d).padStart(2,'0')}`
  selectedDate.value = dateStr
  await loadCalendar()
  dayDetail.value = await api(`learning/day-detail?date=${dateStr}`)
}

async function clearDayProgress(date) {
  if (!confirm(`确定清空 ${date} 的学习进度？`)) return
  await api(`learning/day-progress?date=${date}`, { method: 'DELETE' })
  await loadCalendar()
  dayDetail.value = null
  selectedDate.value = null
}

async function clearAllPlans() {
  if (!confirm('确定清空所有学习计划？此操作不可恢复。')) return
  await api('learning/all-plans', { method: 'DELETE' })
  await loadCalendar()
  dayDetail.value = null
  selectedDate.value = null
}

function closeDayDetail() {
  dayDetail.value = null
  selectedDate.value = null
}
</script>

<template>
  <h2 class="page-title">学习日历</h2>

  <div class="calendar-layout">
    <div class="calendar">
      <div class="calendar-header">
        <button class="btn btn-outline btn-small" @click="prev">&lt;</button>
        <span class="calendar-title">{{ calendarData.year }}年{{ calendarData.month }}月</span>
        <button class="btn btn-outline btn-small" @click="next">&gt;</button>
      </div>
      <div class="calendar-weekdays">
        <span>日</span><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span>
      </div>
      <div class="calendar-grid">
        <div v-for="i in getFirstDay()" :key="'e'+i" class="calendar-day empty"></div>
        <div
          v-for="d in getDaysInMonth()"
          :key="d"
          :class="getDayClass(d)"
          @click="selectDate(d)"
        >
          <span class="cal-day-num">{{ d }}</span>
          <div v-if="getDayData(d)" class="cal-mini-bar">
            <div class="cal-mini-fill" :style="{ width: getDayPct(d) + '%' }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- PC: side panel -->
    <div v-if="dayDetail && !isMobile" class="day-detail">
      <div class="day-detail-header">
        <h3>{{ dayDetail.date }}</h3>
      </div>
      <div class="day-detail-stats">
        <div class="day-stat">
          <div class="day-stat-value done">{{ dayDetail.completed }}</div>
          <div class="day-stat-label">已完成</div>
        </div>
        <div class="day-stat">
          <div class="day-stat-value remain">{{ dayDetail.total - dayDetail.completed }}</div>
          <div class="day-stat-label">未完成</div>
        </div>
        <div class="day-stat">
          <div class="day-stat-value reviewed">{{ dayDetail.reviewed_count }}</div>
          <div class="day-stat-label">已复习</div>
        </div>
      </div>
      <div class="day-detail-words">
        <div v-for="w in dayDetail.words" :key="w.word" class="day-word-item" :class="w.completed ? 'completed' : 'pending'">
          <span class="day-word-status" :class="w.completed ? 'done' : 'pending'">{{ w.completed ? '✓' : '' }}</span>
          <span class="day-word-text">{{ w.word }}</span>
          <span class="day-word-meaning">{{ w.meaning_cn }}</span>
        </div>
        <div v-if="!dayDetail.words?.length" class="day-detail-empty">该日无学习计划</div>
      </div>
      <div class="day-detail-actions">
        <button v-if="dayDetail.total > 0" class="btn btn-danger btn-small" @click="clearDayProgress(dayDetail.date)">清空当日进度</button>
        <button class="btn btn-danger btn-small" @click="clearAllPlans">清空所有计划</button>
      </div>
    </div>
  </div>

  <!-- Mobile: bottom sheet modal -->
  <Teleport to="body">
    <div v-if="dayDetail && isMobile" class="day-detail-overlay" @click.self="closeDayDetail">
      <div class="day-detail-sheet">
        <div class="day-detail-sheet-handle"></div>
        <div class="day-detail-sheet-header">
          <h3>{{ dayDetail.date }}</h3>
          <button class="day-detail-close" @click="closeDayDetail">&times;</button>
        </div>
        <div class="day-detail-stats">
          <div class="day-stat">
            <div class="day-stat-value done">{{ dayDetail.completed }}</div>
            <div class="day-stat-label">已完成</div>
          </div>
          <div class="day-stat">
            <div class="day-stat-value remain">{{ dayDetail.total - dayDetail.completed }}</div>
            <div class="day-stat-label">未完成</div>
          </div>
          <div class="day-stat">
            <div class="day-stat-value reviewed">{{ dayDetail.reviewed_count }}</div>
            <div class="day-stat-label">已复习</div>
          </div>
        </div>
        <div class="day-detail-words">
          <div v-for="w in dayDetail.words" :key="w.word" class="day-word-item" :class="w.completed ? 'completed' : 'pending'">
            <span class="day-word-status" :class="w.completed ? 'done' : 'pending'">{{ w.completed ? '✓' : '' }}</span>
            <span class="day-word-text">{{ w.word }}</span>
            <span class="day-word-meaning">{{ w.meaning_cn }}</span>
          </div>
          <div v-if="!dayDetail.words?.length" class="day-detail-empty">该日无学习计划</div>
        </div>
        <div class="day-detail-actions">
          <button v-if="dayDetail.total > 0" class="btn btn-danger btn-small" @click="clearDayProgress(dayDetail.date)">清空当日进度</button>
          <button class="btn btn-danger btn-small" @click="clearAllPlans">清空所有计划</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.calendar-layout { display: flex; gap: 24px; align-items: flex-start; }

/* Day Detail Sheet (mobile) */
.day-detail-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  z-index: 300;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.day-detail-sheet {
  background: var(--surface);
  border-radius: 16px 16px 0 0;
  width: 100%;
  max-height: 70vh;
  overflow-y: auto;
  padding: 12px 20px 28px;
  animation: slideUp 0.25s ease-out;
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.day-detail-sheet-handle {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: var(--border);
  margin: 0 auto 12px;
}

.day-detail-sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.day-detail-sheet-header h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.day-detail-close {
  font-size: 24px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 4px 8px;
}

@media (max-width: 768px) {
  .calendar-layout { flex-direction: column; }
  .calendar { flex: none; width: 100%; }
}
</style>

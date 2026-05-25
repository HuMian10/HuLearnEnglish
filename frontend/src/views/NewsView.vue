<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const newsList = ref([])
const loading = ref(true)
const fetching = ref(false)
const fetchMsg = ref('')
const imgErrors = reactive({})

const selectedDate = ref('')
const availableDates = ref([])
const showDatePicker = ref(false)

const unreadCount = computed(() => newsList.value.filter(n => !n.is_read).length)

onMounted(async () => {
  await loadDates()
  await loadNews()
})

async function loadDates() {
  try {
    const data = await api('news/dates')
    availableDates.value = data.dates || []
  } catch (e) { console.error(e) }
}

async function loadNews() {
  loading.value = true
  try {
    const dateParam = selectedDate.value ? `&date=${selectedDate.value}` : ''
    const data = await api(`news/list?${dateParam}`)
    newsList.value = data.news || []
  } catch (e) { console.error(e) }
  loading.value = false
}

async function manualFetch() {
  fetching.value = true
  fetchMsg.value = ''
  try {
    const data = await api('news/fetch', { method: 'POST' })
    fetchMsg.value = data.message || `已抓取 ${data.count} 条新闻`
    if (data.count > 0) { await loadDates(); await loadNews() }
  } catch (e) { fetchMsg.value = '抓取失败' }
  fetching.value = false
  setTimeout(() => { fetchMsg.value = '' }, 3000)
}

function openDetail(id) { router.push({ name: 'news-detail', params: { id } }) }

function selectDate(date) { selectedDate.value = date; showDatePicker.value = false; loadNews() }
function clearDate() { selectedDate.value = ''; showDatePicker.value = false; loadNews() }
function toggleDatePicker() { showDatePicker.value = !showDatePicker.value }

function handleDateClickOutside(e) {
  if (showDatePicker.value && !e.target.closest('.date-picker-wrap')) showDatePicker.value = false
}

function fixUrl(url) {
  if (!url) return ''
  if (url.startsWith('//')) return 'https:' + url
  if (url.startsWith('http://')) return url.replace('http://', 'https://')
  return url
}

function onImgError(id) { imgErrors[id] = true }

function formatTime(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  if (isNaN(d.getTime())) return timeStr
  const now = new Date()
  const diffMs = now - d
  const diffHours = Math.floor(diffMs / 3600000)
  if (diffHours < 1) return '刚刚'
  if (diffHours < 24) return `${diffHours}h`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d`
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function formatDateLabel(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const today = new Date().toISOString().slice(0, 10)
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  if (dateStr === today) return 'Today'
  if (dateStr === yesterday) return 'Yesterday'
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

// First item with image gets featured layout
const featuredItem = computed(() => {
  if (selectedDate.value) return null
  return newsList.value.find(n => fixUrl(n.photo_url) && !imgErrors[n.id])
})
const listItems = computed(() => {
  if (selectedDate.value || !featuredItem.value) return newsList.value
  return newsList.value.filter(n => n.id !== featuredItem.value.id)
})
</script>

<template>
  <div class="news-page" @click="handleDateClickOutside">
    <!-- Header -->
    <div class="news-header">
      <div class="header-top">
        <h2 class="header-title">AI News</h2>
        <div class="header-actions">
          <div class="date-picker-wrap">
            <button class="icon-btn" :class="{ active: selectedDate }" @click.stop="toggleDatePicker" title="选择日期">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            </button>
            <Transition name="dropdown">
              <div v-if="showDatePicker" class="date-dropdown" @click.stop>
                <div class="dd-item" :class="{ active: !selectedDate }" @click="clearDate">全部</div>
                <div v-for="d in availableDates" :key="d.date" class="dd-item" :class="{ active: selectedDate === d.date }" @click="selectDate(d.date)">
                  <span>{{ formatDateLabel(d.date) }}</span>
                  <span class="dd-count">{{ d.count }}</span>
                </div>
              </div>
            </Transition>
          </div>
          <button class="icon-btn fetch-btn" :disabled="fetching" @click="manualFetch" title="抓取新闻">
            <svg :class="{ spinning: fetching }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
          </button>
        </div>
      </div>
      <div class="header-bar">
        <span class="bar-label" v-if="selectedDate">{{ formatDateLabel(selectedDate) }}</span>
        <span class="bar-label" v-else>Latest</span>
        <span class="bar-stat">{{ newsList.length }} 篇<template v-if="unreadCount"> · {{ unreadCount }} 未读</template></span>
      </div>
    </div>

    <!-- Toast -->
    <Transition name="toast">
      <div v-if="fetchMsg" class="toast">{{ fetchMsg }}</div>
    </Transition>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="loading-skeleton" v-for="i in 4" :key="i">
        <div class="sk-img"></div>
        <div class="sk-text"><div class="sk-line w80"></div><div class="sk-line w60"></div></div>
      </div>
    </div>

    <!-- Empty -->
    <div v-else-if="!newsList.length" class="empty-state">
      <div class="empty-icon">📭</div>
      <p>{{ selectedDate ? '该日期暂无新闻' : '暂无新闻' }}</p>
      <button class="action-btn" @click="manualFetch">抓取今日新闻</button>
    </div>

    <!-- News list -->
    <template v-else>
      <!-- Featured card (first item with image) -->
      <div v-if="featuredItem" class="featured-card" @click="openDetail(featuredItem.id)">
        <div class="featured-img-wrap">
          <img :src="fixUrl(featuredItem.photo_url)" class="featured-img" alt="" @error="onImgError(featuredItem.id)" />
          <div class="featured-overlay"></div>
          <div class="featured-body">
            <div v-if="!featuredItem.is_read" class="read-badge">NEW</div>
            <h3 class="featured-title">{{ featuredItem.title }}</h3>
            <span class="featured-time">{{ formatTime(featuredItem.source_time) }}</span>
          </div>
        </div>
      </div>

      <!-- Date filter tag -->
      <div v-if="selectedDate" class="filter-tag">
        <span>{{ formatDateLabel(selectedDate) }}</span>
        <button class="filter-clear" @click="clearDate">×</button>
      </div>

      <!-- List -->
      <div class="news-list">
        <div
          v-for="item in listItems"
          :key="item.id"
          class="news-card"
          :class="{ unread: !item.is_read }"
          @click="openDetail(item.id)"
        >
          <div v-if="fixUrl(item.photo_url) && !imgErrors[item.id]" class="card-img-wrap">
            <img :src="fixUrl(item.photo_url)" class="card-img" alt="" @error="onImgError(item.id)" />
          </div>
          <div class="card-body">
            <div class="card-title-row">
              <span v-if="!item.is_read" class="dot-new"></span>
              <h4 class="card-title" :class="{ dim: item.is_read }">{{ item.title }}</h4>
            </div>
            <div class="card-meta">
              <span class="meta-source">AIBase</span>
              <span class="meta-dot">·</span>
              <span class="meta-time">{{ formatTime(item.source_time) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.news-page { animation: fadeIn 0.4s ease; }

/* ===== Header ===== */
.news-header { margin-bottom: 20px; }
.header-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.header-title { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; color: var(--text); }
.header-actions { display: flex; gap: 6px; }

.icon-btn {
  width: 36px; height: 36px; border-radius: 10px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text-secondary); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all 0.2s;
}
.icon-btn:hover { border-color: var(--primary); color: var(--primary); background: rgba(99,102,241,0.04); }
.icon-btn.active { border-color: var(--primary); color: var(--primary); background: rgba(99,102,241,0.08); }
.fetch-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.header-bar { display: flex; align-items: baseline; gap: 8px; }
.bar-label { font-size: 14px; font-weight: 700; color: var(--text); }
.bar-stat { font-size: 13px; color: var(--text-tertiary); font-weight: 500; }

/* ===== Date dropdown ===== */
.date-picker-wrap { position: relative; }
.date-dropdown {
  position: absolute; top: calc(100% + 6px); right: 0; z-index: 200;
  background: var(--surface); border-radius: 14px; box-shadow: var(--shadow-lg);
  border: 1px solid var(--border); min-width: 150px; padding: 6px;
}
.dd-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 9px 14px; border-radius: 8px; cursor: pointer;
  font-size: 14px; font-weight: 500; color: var(--text); transition: all 0.15s;
}
.dd-item:hover { background: var(--bg); }
.dd-item.active { background: rgba(99,102,241,0.08); color: var(--primary); font-weight: 600; }
.dd-count { font-size: 12px; color: var(--text-tertiary); font-weight: 500; }

/* ===== Toast ===== */
.toast {
  position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 500;
  background: var(--text); color: white; padding: 10px 20px; border-radius: 10px;
  font-size: 13px; font-weight: 600; box-shadow: var(--shadow-lg);
}

/* ===== Loading skeleton ===== */
.loading-state { display: flex; flex-direction: column; gap: 12px; }
.loading-skeleton { display: flex; gap: 12px; padding: 16px; background: var(--surface); border-radius: 16px; }
.sk-img { width: 100px; height: 70px; border-radius: 10px; background: var(--bg); flex-shrink: 0; }
.sk-text { flex: 1; display: flex; flex-direction: column; gap: 10px; padding-top: 6px; }
.sk-line { height: 14px; border-radius: 4px; background: var(--bg); }
.w80 { width: 80%; } .w60 { width: 60%; }

/* ===== Empty ===== */
.empty-state { text-align: center; padding: 80px 20px; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { font-size: 15px; color: var(--text-secondary); margin-bottom: 20px; }
.action-btn {
  padding: 10px 24px; border-radius: 10px; border: none; font-size: 14px; font-weight: 600;
  background: var(--gradient-primary); color: white; cursor: pointer;
  box-shadow: 0 2px 8px rgba(99,102,241,0.3); transition: all 0.2s;
}
.action-btn:hover { box-shadow: 0 4px 16px rgba(99,102,241,0.4); transform: translateY(-1px); }

/* ===== Featured card ===== */
.featured-card { margin-bottom: 16px; cursor: pointer; border-radius: 20px; overflow: hidden; }
.featured-img-wrap { position: relative; height: 220px; background: var(--bg); }
.featured-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.featured-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.1) 60%, transparent 100%);
}
.featured-body { position: absolute; bottom: 0; left: 0; right: 0; padding: 20px 24px; }
.read-badge {
  display: inline-block; padding: 2px 10px; border-radius: 6px;
  background: var(--primary); color: white; font-size: 11px; font-weight: 700;
  letter-spacing: 0.5px; margin-bottom: 8px;
}
.featured-title {
  font-size: 20px; font-weight: 700; color: white; line-height: 1.35;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  margin-bottom: 6px;
}
.featured-time { font-size: 13px; color: rgba(255,255,255,0.7); font-weight: 500; }

/* ===== Filter tag ===== */
.filter-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 20px; background: rgba(99,102,241,0.08);
  color: var(--primary); font-size: 13px; font-weight: 600; margin-bottom: 12px;
}
.filter-clear {
  width: 18px; height: 18px; border-radius: 50%; border: none;
  background: rgba(99,102,241,0.15); color: var(--primary); font-size: 12px;
  cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s;
}
.filter-clear:hover { background: var(--primary); color: white; }

/* ===== News list ===== */
.news-list { display: flex; flex-direction: column; gap: 10px; }
.news-card {
  display: flex; gap: 14px; padding: 14px; background: var(--surface);
  border-radius: 16px; cursor: pointer; transition: all 0.2s; border: 1px solid transparent;
}
.news-card:hover { border-color: var(--border); box-shadow: var(--shadow); transform: translateY(-1px); }
.news-card.unread { background: rgba(99,102,241,0.02); border-color: rgba(99,102,241,0.08); }

.card-img-wrap { width: 88px; height: 64px; border-radius: 10px; overflow: hidden; flex-shrink: 0; background: var(--bg); }
.card-img { width: 100%; height: 100%; object-fit: cover; display: block; }

.card-body { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; }
.card-title-row { display: flex; align-items: flex-start; gap: 6px; }
.dot-new {
  width: 7px; height: 7px; border-radius: 50%; background: var(--primary);
  flex-shrink: 0; margin-top: 7px;
}
.card-title {
  font-size: 15px; font-weight: 600; color: var(--text); line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; flex: 1;
}
.card-title.dim { font-weight: 500; color: var(--text-secondary); }

.card-meta { display: flex; align-items: center; gap: 4px; margin-top: 6px; }
.meta-source { font-size: 12px; color: var(--primary); font-weight: 600; }
.meta-dot { font-size: 12px; color: var(--text-tertiary); }
.meta-time { font-size: 12px; color: var(--text-tertiary); font-weight: 500; }

/* ===== Transitions ===== */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.dropdown-enter-active { transition: all 0.15s ease; }
.dropdown-leave-active { transition: all 0.1s ease; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-6px); }
.toast-enter-active { transition: all 0.25s ease; }
.toast-leave-active { transition: all 0.15s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(-12px); }

/* ===== Mobile ===== */
@media (max-width: 768px) {
  .header-title { font-size: 22px; }
  .featured-img-wrap { height: 180px; }
  .featured-title { font-size: 17px; }
  .featured-body { padding: 16px; }
  .card-img-wrap { width: 72px; height: 52px; }
  .card-title { font-size: 14px; }
}
</style>
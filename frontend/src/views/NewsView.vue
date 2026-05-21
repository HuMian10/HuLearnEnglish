<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const newsList = ref([])
const loading = ref(true)
const fetching = ref(false)
const fetchMsg = ref('')
const imgErrors = reactive({})

onMounted(loadNews)

async function loadNews() {
  loading.value = true
  try {
    const data = await api('news/list')
    newsList.value = data.news || []
  } catch (e) {
    console.error(e)
  }
  loading.value = false
}

async function manualFetch() {
  fetching.value = true
  fetchMsg.value = ''
  try {
    const data = await api('news/fetch', { method: 'POST' })
    fetchMsg.value = data.message || `已抓取 ${data.count} 条新闻`
    if (data.count > 0) {
      await loadNews()
    }
  } catch (e) {
    fetchMsg.value = '抓取失败'
  }
  fetching.value = false
}

function openDetail(id) {
  router.push({ name: 'news-detail', params: { id } })
}

function fixUrl(url) {
  if (!url) return ''
  if (url.startsWith('//')) return 'https:' + url
  if (url.startsWith('http://')) return url.replace('http://', 'https://')
  return url
}

function onImgError(id) {
  imgErrors[id] = true
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  if (isNaN(d.getTime())) return timeStr
  const now = new Date()
  const diffMs = now - d
  const diffHours = Math.floor(diffMs / 3600000)
  if (diffHours < 1) return '刚刚'
  if (diffHours < 24) return `${diffHours}小时前`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}天前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<template>
  <div class="news-page">
    <div class="page-title">
      <span>📰 AI 新闻</span>
    </div>

    <div class="news-toolbar">
      <span class="news-count">{{ newsList.length }} 条新闻</span>
      <button class="btn btn-primary btn-small" :disabled="fetching" @click="manualFetch">
        {{ fetching ? '抓取中...' : '手动抓取' }}
      </button>
    </div>
    <div v-if="fetchMsg" class="fetch-msg">{{ fetchMsg }}</div>

    <div v-if="loading" class="empty-state">加载中...</div>
    <div v-else-if="!newsList.length" class="empty-state">
      <p>暂无新闻</p>
      <button class="btn btn-primary" @click="manualFetch">抓取今日新闻</button>
    </div>

    <div v-else class="news-list">
      <div
        v-for="item in newsList"
        :key="item.id"
        class="news-item"
        @click="openDetail(item.id)"
      >
        <div class="news-item-header">
          <div v-if="fixUrl(item.photo_url) && !imgErrors[item.id]" class="news-thumb-wrap">
            <img :src="fixUrl(item.photo_url)" class="news-thumb" alt="" @error="onImgError(item.id)" />
          </div>
          <div v-else class="news-thumb-placeholder">📰</div>
          <div class="news-item-info">
            <div class="news-title">{{ item.title }}</div>
            <div class="news-meta">
              <span class="news-source">AIBase</span>
              <span class="news-dot">·</span>
              <span class="news-time">{{ formatTime(item.source_time) }}</span>
            </div>
          </div>
          <span class="news-arrow">›</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.news-page {
  animation: fadeInUp 0.3s ease;
}

.news-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.news-count {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 600;
}

.fetch-msg {
  font-size: 13px;
  color: var(--success);
  margin-bottom: 12px;
  padding: 8px 12px;
  background: rgba(16,185,129,0.06);
  border-radius: var(--radius-sm);
}

.news-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.news-item {
  background: var(--surface);
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow);
  cursor: pointer;
  transition: all 0.2s;
}

.news-item:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.news-item.expanded {
  box-shadow: var(--shadow-md);
}

.news-item-header {
  display: flex;
  gap: 12px;
  align-items: center;
}

.news-thumb-wrap {
  width: 100px;
  height: 70px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--bg);
}

.news-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.news-thumb-placeholder {
  width: 100px;
  height: 70px;
  background: var(--bg);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}

.news-item-info {
  flex: 1;
  min-width: 0;
}

.news-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.news-meta {
  display: flex;
  gap: 4px;
  align-items: center;
  margin-top: 6px;
}

.news-source {
  font-size: 12px;
  color: var(--primary);
  font-weight: 600;
}

.news-dot {
  font-size: 12px;
  color: var(--text-tertiary);
}

.news-time {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.news-arrow {
  font-size: 20px;
  color: var(--text-tertiary);
  flex-shrink: 0;
  margin-left: 4px;
  transition: transform 0.2s;
}

.news-item:hover .news-arrow {
  transform: translateX(3px);
  color: var(--primary);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .news-thumb-wrap, .news-thumb-placeholder {
    width: 80px;
    height: 56px;
  }
  .news-title {
    font-size: 14px;
  }
}
</style>
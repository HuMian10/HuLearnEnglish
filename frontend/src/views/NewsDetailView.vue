<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()

const article = ref(null)
const loading = ref(true)
const imgError = ref(false)

// Selection popup state
const popup = ref(null) // { type: 'word' | 'translate', x, y, data, loading }
let mousePos = { x: 0, y: 0 }
let lastTouchPos = { x: 0, y: 0 }
let selectionDebounce = null

onMounted(() => {
  loadDetail()
  // Desktop: track mouse position + close popup on click outside
  document.addEventListener('mouseup', handleMouseUp)
  document.addEventListener('mousedown', handleMouseDown)
  document.addEventListener('mousemove', handleMouseMove)
  // Mobile: track touch position
  document.addEventListener('touchstart', handleTouchStart, { passive: true })
  document.addEventListener('touchmove', handleTouchMove, { passive: true })
  // Cross-platform: detect text selection changes
  document.addEventListener('selectionchange', handleSelectionChange)
  // Safari: prevent system context menu on long press
  document.addEventListener('contextmenu', handleContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('mouseup', handleMouseUp)
  document.removeEventListener('mousedown', handleMouseDown)
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('touchstart', handleTouchStart)
  document.removeEventListener('touchmove', handleTouchMove)
  document.removeEventListener('selectionchange', handleSelectionChange)
  document.removeEventListener('contextmenu', handleContextMenu)
})

async function loadDetail() {
  loading.value = true
  try {
    const data = await api(`news/detail?id=${route.params.id}`)
    if (data.ok) {
      article.value = data.news
    }
  } catch (e) {
    console.error(e)
  }
  loading.value = false
}

function goBack() {
  router.push({ name: 'news' })
}

function onImgError() {
  imgError.value = true
}

function fixUrl(url) {
  if (!url) return ''
  if (url.startsWith('//')) return 'https:' + url
  if (url.startsWith('http://')) return url.replace('http://', 'https://')
  return url
}

function formatDate(timeStr) {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  if (isNaN(d.getTime())) return timeStr
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

// --- Text selection logic ---
function handleMouseMove(e) {
  mousePos.x = e.clientX
  mousePos.y = e.clientY
}

function handleTouchStart(e) {
  const t = e.touches[0]
  if (t) {
    lastTouchPos.x = t.clientX
    lastTouchPos.y = t.clientY
  }
  // Close popup if tapping outside it
  if (popup.value && !e.target.closest('.lookup-popup')) {
    popup.value = null
  }
}

function handleTouchMove(e) {
  const t = e.touches[0]
  if (t) {
    lastTouchPos.x = t.clientX
    lastTouchPos.y = t.clientY
  }
}

function handleMouseDown(e) {
  // Close popup if clicking outside it
  if (popup.value && !e.target.closest('.lookup-popup')) {
    popup.value = null
  }
}

function handleMouseUp(e) {
  // Small delay to let the selection finalize
  setTimeout(() => {
    checkSelection()
  }, 100)
}

function handleSelectionChange() {
  // Debounce: selectionchange fires many times during drag-select
  if (selectionDebounce) clearTimeout(selectionDebounce)
  selectionDebounce = setTimeout(() => {
    checkSelection()
  }, 300)
}

function handleContextMenu(e) {
  // Prevent Safari/iOS system popup on text selection
  const contentEl = document.querySelector('.article-content')
  const titleEl = document.querySelector('.article-title')
  if ((contentEl && contentEl.contains(e.target)) || (titleEl && titleEl.contains(e.target))) {
    e.preventDefault()
  }
}

function checkSelection() {
  const sel = window.getSelection()
  const text = sel?.toString().trim()
  if (!text) return

  // Make sure selection is inside article content or title
  const contentEl = document.querySelector('.article-content')
  const titleEl = document.querySelector('.article-title')
  const inContent = contentEl && contentEl.contains(sel.anchorNode)
  const inTitle = titleEl && titleEl.contains(sel.anchorNode)
  if (!inContent && !inTitle) return

  // Determine single word vs multi-word
  const words = text.split(/\s+/).filter(w => w.length > 0)
  const isSingleWord = words.length === 1 && /[a-zA-Z]/.test(text)

  if (isSingleWord) {
    const cleanWord = text.replace(/[^a-zA-Z'-]/g, '').toLowerCase()
    lookupWord(cleanWord)
  } else {
    translateText(text)
  }
}

async function lookupWord(word) {
  popup.value = { type: 'word', x: 0, y: 0, loading: true, data: null, error: '', word }

  await nextTick()
  positionPopup()

  try {
    const data = await api(`news/lookup-word?word=${encodeURIComponent(word)}`)
    if (data.found) {
      popup.value.data = data.word
      popup.value.loading = false
    } else {
      popup.value.loading = false
      popup.value.error = '词库中暂无此词'
    }
  } catch (e) {
    popup.value.loading = false
    popup.value.error = '查询失败'
  }
  positionPopup()
}

async function translateText(text) {
  popup.value = { type: 'translate', x: 0, y: 0, loading: true, data: null, error: '', text }

  await nextTick()
  positionPopup()

  try {
    const data = await api('news/translate', {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
    if (data.ok) {
      popup.value.data = data.data
      popup.value.loading = false
    } else {
      popup.value.loading = false
      popup.value.error = data.error || '翻译失败'
    }
  } catch (e) {
    popup.value.loading = false
    popup.value.error = '翻译请求失败'
  }
  positionPopup()
}

function positionPopup() {
  if (!popup.value) return
  // Use touch position on mobile, mouse position on desktop
  const posX = lastTouchPos.x || mousePos.x
  const posY = lastTouchPos.y || mousePos.y
  // Try to get position from selection range
  const sel = window.getSelection()
  let rangeX = 0, rangeY = 0
  if (sel && sel.rangeCount > 0) {
    const range = sel.getRangeAt(0)
    const rect = range.getBoundingClientRect()
    // Position popup below the selection
    rangeX = rect.left + rect.width / 2
    rangeY = rect.bottom + 8
  }
  // Prefer selection-based position, fallback to pointer position
  const x = rangeX || Math.min(posX + 12, window.innerWidth - 340)
  const y = rangeY || Math.min(posY + 12, window.innerHeight - 300)
  // Clamp to viewport
  popup.value.x = Math.max(8, Math.min(x - 120, window.innerWidth - 340))
  popup.value.y = Math.min(y, window.innerHeight - 300)
  if (popup.value.y < 8) popup.value.y = 8
}

function closePopup() {
  popup.value = null
  window.getSelection()?.removeAllRanges()
}

function playAudio(url) {
  if (!url) return
  const audio = new Audio(url)
  audio.play()
}
</script>

<template>
  <div class="detail-page">
    <div v-if="loading" class="empty-state">加载中...</div>
    <div v-else-if="!article" class="empty-state">
      <p>新闻不存在</p>
      <button class="btn btn-primary" @click="goBack">返回新闻列表</button>
    </div>

    <article v-else class="article">
      <!-- Back button -->
      <button class="back-btn" @click="goBack">
        <span class="back-arrow">←</span>
        <span>返回列表</span>
      </button>

      <!-- Hero image -->
      <div v-if="fixUrl(article.photo_url) && !imgError" class="article-hero">
        <img :src="fixUrl(article.photo_url)" alt="" class="hero-img" @error="onImgError" />
      </div>

      <!-- Title -->
      <h1 class="article-title">{{ article.title }}</h1>

      <!-- Meta -->
      <div class="article-meta">
        <span class="meta-item">
          <span class="meta-icon">🕐</span>
          {{ formatDate(article.source_time) }}
        </span>
        <span class="meta-item">
          <span class="meta-icon">📡</span>
          AIBase
        </span>
      </div>

      <!-- Hint -->
      <div class="select-hint">💡 选中单词可查词，选中短语/句子可翻译</div>

      <!-- Content (summary may contain HTML, use v-html) -->
      <div class="article-content" v-html="article.content"></div>

      <!-- Bottom actions -->
      <div class="article-bottom">
        <button class="btn btn-outline" @click="goBack">← 返回新闻列表</button>
      </div>
    </article>

    <!-- Lookup popup (teleported to body) -->
    <Teleport to="body">
      <Transition name="popup">
        <div
          v-if="popup"
          class="lookup-popup"
          :style="{ left: popup.x + 'px', top: popup.y + 'px' }"
        >
          <button class="popup-close" @click="closePopup">×</button>

          <!-- Loading -->
          <div v-if="popup.loading" class="popup-loading">
            <span class="popup-spinner"></span>
            <span>{{ popup.type === 'word' ? '查词中...' : '翻译中...' }}</span>
          </div>

          <!-- Word lookup result -->
          <template v-else-if="popup.type === 'word' && popup.data">
            <div class="popup-word-header">
              <span class="popup-word">{{ popup.data.word }}</span>
              <span class="popup-phonetic" v-if="popup.data.phonetic_us">{{ popup.data.phonetic_us }}</span>
              <button
                v-if="popup.data.audio_us"
                class="popup-play-btn"
                @click="playAudio(popup.data.audio_us)"
                title="播放发音"
              >▶</button>
            </div>
            <div class="popup-meanings" v-if="popup.data.meanings?.length">
              <div v-for="(m, i) in popup.data.meanings" :key="i" class="popup-meaning-item">
                <span class="popup-pos" v-if="m.pos">{{ m.pos }}</span>
                <span class="popup-meaning-text">{{ m.meaning_cn }}</span>
              </div>
            </div>
            <div v-if="popup.data.example_en" class="popup-example">
              <div class="popup-example-en">{{ popup.data.example_en }}</div>
              <div class="popup-example-cn" v-if="popup.data.example_cn">{{ popup.data.example_cn }}</div>
            </div>
          </template>

          <!-- Translate result -->
          <template v-else-if="popup.type === 'translate' && popup.data">
            <div class="popup-translate-label">翻译</div>
            <div class="popup-translation">{{ popup.data.translation }}</div>
            <div v-if="popup.data.key_words?.length" class="popup-key-words">
              <div class="popup-kw-label">关键词</div>
              <div class="popup-kw-list">
                <span v-for="(kw, i) in popup.data.key_words" :key="i" class="popup-kw-item">
                  <span class="popup-kw-word">{{ kw.word }}</span>
                  <span class="popup-kw-meaning">{{ kw.meaning }}</span>
                </span>
              </div>
            </div>
          </template>

          <!-- Error / Not found -->
          <template v-else-if="popup.error">
            <div class="popup-error">{{ popup.error }}</div>
          </template>

          <!-- Word not in DB -->
          <template v-else-if="popup.type === 'word' && !popup.data">
            <div class="popup-not-found">
              <span class="popup-word">{{ popup.word }}</span>
              <span class="popup-nf-text">词库中暂无此词</span>
            </div>
          </template>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.detail-page {
  animation: fadeInUp 0.3s ease;
  max-width: 720px;
  margin: 0 auto;
}

.article {
  background: var(--surface);
  border-radius: var(--radius-xl);
  padding: 28px 32px;
  box-shadow: var(--shadow);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: var(--primary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
  margin-bottom: 20px;
}

.back-btn:hover {
  background: rgba(99,102,241,0.06);
}

.back-arrow {
  font-size: 18px;
  transition: transform 0.2s;
}

.back-btn:hover .back-arrow {
  transform: translateX(-3px);
}

.article-hero {
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 24px;
  background: var(--bg);
}

.hero-img {
  width: 100%;
  max-height: 360px;
  object-fit: cover;
  display: block;
}

.article-title {
  font-size: 24px;
  font-weight: 800;
  color: var(--text);
  line-height: 1.4;
  letter-spacing: -0.3px;
  margin-bottom: 16px;
  -webkit-touch-callout: none;
}

.article-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.meta-icon {
  font-size: 14px;
}

.select-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 16px;
  padding: 6px 12px;
  background: var(--bg);
  border-radius: var(--radius-sm);
  text-align: center;
}

.article-content {
  font-size: 16px;
  line-height: 1.85;
  color: var(--text);
  word-break: break-word;
  text-align: justify;
  hyphens: auto;
  cursor: text;
  user-select: text;
  -webkit-touch-callout: none;
  -webkit-user-select: text;
}

.article-content :deep(p) {
  margin-bottom: 14px;
  text-indent: 2em;
}

.article-content :deep(p:last-child) {
  margin-bottom: 0;
}

.article-content :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-sm);
  margin: 12px 0;
}

.article-content :deep(a) {
  color: var(--primary);
  text-decoration: none;
}

.article-content :deep(a:hover) {
  text-decoration: underline;
}

.article-content :deep(strong),
.article-content :deep(b) {
  font-weight: 700;
}

.article-content :deep(em),
.article-content :deep(i) {
  font-style: italic;
}

.article-bottom {
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: center;
}

/* ===== Lookup Popup ===== */
.lookup-popup {
  position: fixed;
  z-index: 300;
  min-width: 240px;
  max-width: 320px;
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 16px;
  border: 1px solid var(--border);
}

.popup-close {
  position: absolute;
  top: 8px;
  right: 10px;
  background: none;
  border: none;
  font-size: 18px;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  line-height: 1;
  transition: all 0.15s;
}

.popup-close:hover {
  color: var(--text);
  background: var(--bg);
}

.popup-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  padding: 8px 0;
}

.popup-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Word result */
.popup-word-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.popup-word {
  font-size: 20px;
  font-weight: 800;
  color: var(--text);
}

.popup-phonetic {
  font-size: 13px;
  color: var(--text-secondary);
}

.popup-play-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1.5px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  font-size: 10px;
  color: var(--primary);
  transition: all 0.15s;
  padding: 0;
}

.popup-play-btn:hover {
  border-color: var(--primary);
  background: rgba(99,102,241,0.06);
}

.popup-meanings {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.popup-meaning-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 14px;
}

.popup-pos {
  display: inline-block;
  background: rgba(99,102,241,0.08);
  color: var(--primary);
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.popup-meaning-text {
  color: var(--text);
  font-weight: 500;
}

.popup-example {
  padding-top: 8px;
  border-top: 1px solid var(--border);
  font-size: 13px;
  line-height: 1.5;
}

.popup-example-en {
  color: var(--text);
  font-weight: 500;
}

.popup-example-cn {
  color: var(--text-secondary);
  margin-top: 2px;
}

/* Translate result */
.popup-translate-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.popup-translation {
  font-size: 15px;
  color: var(--text);
  line-height: 1.6;
  font-weight: 500;
  margin-bottom: 12px;
}

.popup-kw-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-tertiary);
  margin-bottom: 6px;
}

.popup-kw-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.popup-kw-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--bg);
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.popup-kw-word {
  color: var(--primary);
  font-weight: 600;
}

.popup-kw-meaning {
  color: var(--text-secondary);
}

/* Not found */
.popup-not-found {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.popup-nf-text {
  font-size: 13px;
  color: var(--text-tertiary);
}

.popup-error {
  font-size: 13px;
  color: var(--danger);
}

/* Popup transition */
.popup-enter-active { transition: opacity 0.15s, transform 0.15s; }
.popup-leave-active { transition: opacity 0.1s; }
.popup-enter-from { opacity: 0; transform: scale(0.95); }
.popup-leave-to { opacity: 0; }

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .article {
    padding: 20px 16px;
    border-radius: var(--radius-lg);
  }
  .article-title {
    font-size: 20px;
  }
  .article-content {
    font-size: 15px;
    line-height: 1.75;
  }
  .hero-img {
    max-height: 220px;
  }
  .article-meta {
    gap: 12px;
    flex-wrap: wrap;
  }
  .lookup-popup {
    min-width: 200px;
    max-width: 280px;
  }
}
</style>
<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()

const article = ref(null)
const loading = ref(true)
const imgError = ref(false)
const showBackTop = ref(false)

// Selection toolbar & result popup state
const toolbar = ref(null) // { x, y, text }
const popup = ref(null)   // { type: 'word'|'translate', x, y, loading, data, error, word/text }
let mousePos = { x: 0, y: 0 }
let lastTouchPos = { x: 0, y: 0 }
let selectionDebounce = null
let isProcessing = false  // prevent double-trigger

onMounted(() => {
  loadDetail()
  document.addEventListener('mouseup', handleMouseUp)
  document.addEventListener('mousedown', handleMouseDown)
  document.addEventListener('mousemove', handleMouseMove, { passive: true })
  document.addEventListener('touchstart', handleTouchStart, { passive: true })
  document.addEventListener('touchmove', handleTouchMove, { passive: true })
  document.addEventListener('touchend', handleTouchEnd)
  document.addEventListener('selectionchange', handleSelectionChange)
  document.addEventListener('contextmenu', handleContextMenu)
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  document.removeEventListener('mouseup', handleMouseUp)
  document.removeEventListener('mousedown', handleMouseDown)
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('touchstart', handleTouchStart)
  document.removeEventListener('touchmove', handleTouchMove)
  document.removeEventListener('touchend', handleTouchEnd)
  document.removeEventListener('selectionchange', handleSelectionChange)
  document.removeEventListener('contextmenu', handleContextMenu)
  window.removeEventListener('scroll', handleScroll)
})

function handleScroll() { showBackTop.value = window.scrollY > 400 }

async function loadDetail() {
  loading.value = true
  try {
    const data = await api(`news/detail?id=${route.params.id}`)
    if (data.ok) article.value = data.news
  } catch (e) { console.error(e) }
  loading.value = false
}

function goBack() { router.push({ name: 'news' }) }
function onImgError() { imgError.value = true }
function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }) }

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
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`
}

function formatReadTime(content) {
  if (!content) return '1 min'
  const text = content.replace(/<[^>]+>/g, '')
  const words = text.split(/\s+/).length
  return `${Math.max(1, Math.round(words / 200))} min read`
}

// --- Get selected text, verify it's inside article ---
function getSelectedArticleText() {
  const sel = window.getSelection()
  const text = sel?.toString().trim()
  if (!text || !/[a-zA-Z]/.test(text)) return null
  const contentEl = document.querySelector('.article-content')
  const titleEl = document.querySelector('.article-title')
  if (!(contentEl?.contains(sel.anchorNode) || titleEl?.contains(sel.anchorNode))) return null
  return text
}

// Reliable cross-browser copy that works in HTTP and HTTPS
function copyTextToClipboard(text) {
  // Try modern API first
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text).catch(() => fallbackCopy(text))
  }
  return fallbackCopy(text)
}

function fallbackCopy(text) {
  const ta = document.createElement('textarea')
  ta.value = text
  // Style to be invisible but functional
  ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;pointer-events:none'
  ta.setAttribute('readonly', '') // prevent iOS keyboard popup
  document.body.appendChild(ta)
  // iOS Safari needs special selection handling
  const range = document.createRange()
  range.selectNodeContents(ta)
  const sel = window.getSelection()
  sel.removeAllRanges()
  sel.addRange(range)
  ta.setSelectionRange(0, text.length) // fallback for iOS
  let ok = false
  try { ok = document.execCommand('copy') } catch (e) { ok = false }
  sel.removeAllRanges()
  document.body.removeChild(ta)
  return ok
}

function isSingleWord(text) {
  const words = text.split(/\s+/).filter(w => w.length > 0)
  return words.length === 1 && /[a-zA-Z]/.test(text)
}

// --- Selection detection: show toolbar, NOT auto-query ---
function handleMouseMove(e) { mousePos.x = e.clientX; mousePos.y = e.clientY }

function handleTouchStart(e) {
  const t = e.touches[0]
  if (t) { lastTouchPos.x = t.clientX; lastTouchPos.y = t.clientY }
  // Close toolbar/popup if tapping outside them
  if (!e.target.closest('.sel-toolbar') && !e.target.closest('.lookup-popup')) {
    closeAll()
  }
}

function handleTouchMove(e) {
  const t = e.touches[0]
  if (t) { lastTouchPos.x = t.clientX; lastTouchPos.y = t.clientY }
}

function handleTouchEnd() {
  // Small delay to let the selection finalize on mobile
  setTimeout(() => showToolbarIfNeeded(), 200)
}

function handleMouseDown(e) {
  // Close toolbar/popup if clicking outside them
  if (!e.target.closest('.sel-toolbar') && !e.target.closest('.lookup-popup')) {
    closeAll()
  }
}

function handleMouseUp() {
  setTimeout(() => showToolbarIfNeeded(), 80)
}

function handleSelectionChange() {
  if (isProcessing) return
  if (selectionDebounce) clearTimeout(selectionDebounce)
  selectionDebounce = setTimeout(() => showToolbarIfNeeded(), 300)
}

// Completely suppress browser native context menu everywhere on this page
function handleContextMenu(e) {
  // Block on entire detail page to prevent Safari system menu
  e.preventDefault()
}

function showToolbarIfNeeded() {
  if (isProcessing) return
  const text = getSelectedArticleText()
  if (!text) {
    // Selection cleared → hide toolbar (but keep popup if open)
    if (!popup.value) toolbar.value = null
    return
  }
  // Show toolbar above the selection
  const sel = window.getSelection()
  let x = 0, y = 0
  if (sel && sel.rangeCount > 0) {
    const rect = sel.getRangeAt(0).getBoundingClientRect()
    x = rect.left + rect.width / 2
    y = rect.top - 8  // above the selection
  }
  // Fallback to pointer position
  if (!x || !y) {
    const px = lastTouchPos.x || mousePos.x
    const py = lastTouchPos.y || mousePos.y
    x = px; y = py - 20
  }
  toolbar.value = { x, y, text }
}

// --- Toolbar actions ---
function doTranslate() {
  if (!toolbar.value) return
  const text = toolbar.value.text
  toolbar.value = null // hide toolbar
  isProcessing = true

  // Auto-detect: single word → lookup DB, multi-word → LLM translate
  if (isSingleWord(text)) {
    const cleanWord = text.replace(/[^a-zA-Z'-]/g, '').toLowerCase()
    lookupWord(cleanWord)
  } else {
    translateText(text)
  }
}

function doCopy() {
  if (!toolbar.value) return
  const textToCopy = toolbar.value.text
  toolbar.value = null // hide toolbar first
  window.getSelection()?.removeAllRanges() // clear selection to prevent system menu
  copyTextToClipboard(textToCopy)
  showToast('已复制')
}

// Simple toast
const toastMsg = ref('')
let toastTimer = null
function showToast(msg) {
  toastMsg.value = msg
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, 1500)
}

async function lookupWord(word) {
  popup.value = { type: 'word', x: 0, y: 0, loading: true, data: null, error: '', word }
  await nextTick(); positionPopup()
  try {
    const data = await api(`news/lookup-word?word=${encodeURIComponent(word)}`)
    if (data.found) { popup.value.data = data.word; popup.value.loading = false }
    else { popup.value.loading = false; popup.value.error = '词库中暂无此词' }
  } catch (e) { popup.value.loading = false; popup.value.error = '查询失败' }
  isProcessing = false
  positionPopup()
}

async function translateText(text) {
  popup.value = { type: 'translate', x: 0, y: 0, loading: true, data: null, error: '', text }
  await nextTick(); positionPopup()
  try {
    const data = await api('news/translate', { method: 'POST', body: JSON.stringify({ text }) })
    if (data.ok) { popup.value.data = data.data; popup.value.loading = false }
    else { popup.value.loading = false; popup.value.error = data.error || '翻译失败' }
  } catch (e) { popup.value.loading = false; popup.value.error = '翻译请求失败' }
  isProcessing = false
  positionPopup()
}

function positionPopup() {
  if (!popup.value) return
  // Position below the selection
  const sel = window.getSelection()
  let rangeX = 0, rangeY = 0
  if (sel && sel.rangeCount > 0) {
    const rect = sel.getRangeAt(0).getBoundingClientRect()
    rangeX = rect.left + rect.width / 2
    rangeY = rect.bottom + 8
  }
  const posX = lastTouchPos.x || mousePos.x
  const posY = lastTouchPos.y || mousePos.y
  const x = rangeX || Math.min(posX + 12, window.innerWidth - 340)
  const y = rangeY || Math.min(posY + 12, window.innerHeight - 300)
  popup.value.x = Math.max(8, Math.min(x - 140, window.innerWidth - 340))
  popup.value.y = Math.min(y, window.innerHeight - 300)
  if (popup.value.y < 8) popup.value.y = 8
}

function closePopup() { popup.value = null; window.getSelection()?.removeAllRanges() }
function closeAll() { toolbar.value = null; popup.value = null }
function playAudio(url) { if (!url) return; new Audio(url).play() }
</script>

<template>
  <div class="detail-page">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="ld-hero"></div>
      <div class="ld-body"><div class="ld-line w70"></div><div class="ld-line w50"></div><div class="ld-line w90"></div></div>
    </div>

    <!-- Empty -->
    <div v-else-if="!article" class="empty-state">
      <div class="empty-icon">😕</div>
      <p>新闻不存在</p>
      <button class="action-btn" @click="goBack">返回新闻列表</button>
    </div>

    <!-- Article -->
    <article v-else class="article">
      <div class="top-bar">
        <button class="back-btn" @click="goBack">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          <span>返回</span>
        </button>
        <div class="top-hint">选中文字可查词/翻译</div>
      </div>

      <div v-if="fixUrl(article.photo_url) && !imgError" class="hero-wrap">
        <img :src="fixUrl(article.photo_url)" alt="" class="hero-img" @error="onImgError" />
      </div>

      <div class="title-area">
        <h1 class="article-title">{{ article.title }}</h1>
        <div class="title-meta">
          <div class="meta-left">
            <span class="meta-source">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
              AIBase
            </span>
            <span class="meta-sep">·</span>
            <span class="meta-date">{{ formatDate(article.source_time) }}</span>
            <span class="meta-sep">·</span>
            <span class="meta-read">{{ formatReadTime(article.content) }}</span>
          </div>
        </div>
      </div>

      <div class="divider-accent"></div>

      <div class="article-content" v-html="article.content"></div>

      <div class="article-footer">
        <button class="footer-back" @click="goBack">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          返回新闻列表
        </button>
      </div>
    </article>

    <!-- Back to top -->
    <Transition name="fade">
      <button v-if="showBackTop" class="back-top" @click="scrollToTop" title="回到顶部">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>
      </button>
    </Transition>

    <!-- Selection toolbar (floating above selection) -->
    <Teleport to="body">
      <Transition name="toolbar">
        <div v-if="toolbar" class="sel-toolbar" :style="{ left: toolbar.x + 'px', top: toolbar.y + 'px' }">
          <button class="tb-btn" @click="doTranslate" title="查词/翻译">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8l6 6"/><path d="M4 14l6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="M22 22l-5-10-5 10"/><path d="M14 18h6"/></svg>
            <span>翻译</span>
          </button>
          <div class="tb-divider"></div>
          <button class="tb-btn" @click="doCopy" title="复制">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            <span>复制</span>
          </button>
        </div>
      </Transition>
    </Teleport>

    <!-- Result popup -->
    <Teleport to="body">
      <Transition name="popup">
        <div v-if="popup" class="lookup-popup" :style="{ left: popup.x + 'px', top: popup.y + 'px' }">
          <button class="popup-close" @click="closePopup">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>

          <!-- Loading -->
          <div v-if="popup.loading" class="popup-loading">
            <div class="spinner"></div>
            <span>{{ popup.type === 'word' ? '查词中...' : '翻译中...' }}</span>
          </div>

          <!-- Word lookup -->
          <template v-else-if="popup.type === 'word' && popup.data">
            <div class="pw-header">
              <span class="pw-word">{{ popup.data.word }}</span>
              <span class="pw-phonetic" v-if="popup.data.phonetic_us">{{ popup.data.phonetic_us }}</span>
              <button v-if="popup.data.audio_us" class="pw-play" @click="playAudio(popup.data.audio_us)" title="播放发音">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
              </button>
            </div>
            <div class="pw-meanings" v-if="popup.data.meanings?.length">
              <div v-for="(m, i) in popup.data.meanings" :key="i" class="pw-m-item">
                <span class="pw-pos" v-if="m.pos">{{ m.pos }}</span>
                <span class="pw-meaning">{{ m.meaning_cn }}</span>
              </div>
            </div>
            <div v-if="popup.data.example_en" class="pw-example">
              <div class="pw-ex-en">{{ popup.data.example_en }}</div>
              <div class="pw-ex-cn" v-if="popup.data.example_cn">{{ popup.data.example_cn }}</div>
            </div>
          </template>

          <!-- Translate -->
          <template v-else-if="popup.type === 'translate' && popup.data">
            <div class="pt-label">翻译</div>
            <div class="pt-translation">{{ popup.data.translation }}</div>
            <div v-if="popup.data.key_words?.length" class="pt-keywords">
              <span class="pt-kw-label">关键词</span>
              <div class="pt-kw-list">
                <span v-for="(kw, i) in popup.data.key_words" :key="i" class="pt-kw">
                  <b>{{ kw.word }}</b> {{ kw.meaning }}
                </span>
              </div>
            </div>
          </template>

          <!-- Error -->
          <template v-else-if="popup.error">
            <div class="popup-error">{{ popup.error }}</div>
          </template>

          <!-- Not found -->
          <template v-else-if="popup.type === 'word' && !popup.data">
            <div class="pw-notfound">
              <span class="pw-word">{{ popup.word }}</span>
              <span class="pw-nf">词库中暂无此词</span>
            </div>
          </template>
        </div>
      </Transition>
    </Teleport>

    <!-- Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toastMsg" class="copy-toast">{{ toastMsg }}</div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.detail-page {
  animation: fadeIn 0.35s ease;
  max-width: 720px;
  margin: 0 auto;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
}

/* ===== Loading ===== */
.loading-state { padding: 0; }
.ld-hero { height: 260px; background: var(--bg); border-radius: 20px; margin-bottom: 24px; }
.ld-body { padding: 0 4px; }
.ld-line { height: 16px; border-radius: 6px; background: var(--bg); margin-bottom: 14px; }
.w70 { width: 70%; } .w50 { width: 50%; } .w90 { width: 90%; }

/* ===== Empty ===== */
.empty-state { text-align: center; padding: 80px 20px; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { font-size: 15px; color: var(--text-secondary); margin-bottom: 20px; }
.action-btn {
  padding: 10px 24px; border-radius: 12px; border: none; font-size: 14px; font-weight: 600;
  background: var(--gradient-primary); color: white; cursor: pointer;
  box-shadow: 0 2px 8px rgba(99,102,241,0.3); transition: all 0.2s;
}
.action-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(99,102,241,0.4); }

/* ===== Top bar ===== */
.top-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.back-btn {
  display: inline-flex; align-items: center; gap: 5px; background: none; border: none;
  color: var(--primary); font-size: 14px; font-weight: 600; cursor: pointer;
  padding: 8px 12px; border-radius: 10px; transition: all 0.15s;
}
.back-btn:hover { background: rgba(99,102,241,0.06); }
.top-hint { font-size: 12px; color: var(--text-tertiary); font-weight: 500; }

/* ===== Hero ===== */
.hero-wrap { border-radius: 20px; overflow: hidden; margin-bottom: 28px; background: var(--bg); }
.hero-img { width: 100%; max-height: 380px; object-fit: cover; display: block; }

/* ===== Title ===== */
.title-area { padding: 0 4px; margin-bottom: 20px; }
.article-title {
  font-size: 28px; font-weight: 800; color: var(--text); line-height: 1.35;
  letter-spacing: -0.5px; margin-bottom: 14px; -webkit-touch-callout: none;
}
.title-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 2px; }
.meta-left { display: flex; align-items: center; gap: 6px; }
.meta-source {
  display: inline-flex; align-items: center; gap: 4px; font-size: 13px;
  color: var(--primary); font-weight: 600;
}
.meta-source svg { opacity: 0.7; }
.meta-sep { font-size: 13px; color: var(--text-tertiary); }
.meta-date { font-size: 13px; color: var(--text-tertiary); font-weight: 500; }
.meta-read { font-size: 13px; color: var(--text-tertiary); font-weight: 500; }

.divider-accent {
  width: 48px; height: 3px; border-radius: 2px; background: var(--primary);
  margin-bottom: 24px; opacity: 0.6;
}

/* ===== Content ===== */
.article-content {
  font-size: 17px; line-height: 1.9; color: var(--text);
  word-break: break-word; text-align: justify; hyphens: auto;
  cursor: text; user-select: text; -webkit-touch-callout: none; -webkit-user-select: text;
  padding: 0 4px;
}
.article-content :deep(p) { margin-bottom: 18px; text-indent: 2em; }
.article-content :deep(p:last-child) { margin-bottom: 0; }
.article-content :deep(img) { max-width: 100%; border-radius: 12px; margin: 16px 0; }
.article-content :deep(a) { color: var(--primary); text-decoration: none; border-bottom: 1px solid rgba(99,102,241,0.3); }
.article-content :deep(a:hover) { border-bottom-color: var(--primary); }
.article-content :deep(strong), .article-content :deep(b) { font-weight: 700; color: var(--text); }
.article-content :deep(em), .article-content :deep(i) { font-style: italic; }
.article-content :deep(blockquote) {
  margin: 16px 0; padding: 12px 20px; border-left: 3px solid var(--primary);
  background: rgba(99,102,241,0.04); border-radius: 0 10px 10px 0; font-style: italic;
}

/* ===== Footer ===== */
.article-footer {
  margin-top: 40px; padding-top: 24px; border-top: 1px solid var(--border); text-align: center;
}
.footer-back {
  display: inline-flex; align-items: center; gap: 6px; background: none; border: 1px solid var(--border);
  color: var(--text-secondary); font-size: 14px; font-weight: 600; cursor: pointer;
  padding: 10px 24px; border-radius: 12px; transition: all 0.2s;
}
.footer-back:hover { border-color: var(--primary); color: var(--primary); background: rgba(99,102,241,0.04); }

/* ===== Back to top ===== */
.back-top {
  position: fixed; bottom: 24px; right: 24px; z-index: 200;
  width: 44px; height: 44px; border-radius: 14px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text-secondary); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all 0.2s;
  box-shadow: var(--shadow);
}
.back-top:hover { color: var(--primary); border-color: var(--primary); transform: translateY(-2px); }

/* ===== Selection Toolbar ===== */
.sel-toolbar {
  position: fixed; z-index: 400;
  display: flex; align-items: center; gap: 2px;
  background: var(--text); border-radius: 10px; padding: 4px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
  transform: translateX(-50%);
  /* Arrow pointing down */
}
.sel-toolbar::after {
  content: ''; position: absolute; bottom: -6px; left: 50%; transform: translateX(-50%);
  width: 0; height: 0; border-left: 6px solid transparent; border-right: 6px solid transparent;
  border-top: 6px solid var(--text);
}

.tb-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 7px 14px; border: none; border-radius: 7px;
  background: transparent; color: rgba(255,255,255,0.85); font-size: 13px;
  font-weight: 600; cursor: pointer; transition: all 0.12s; white-space: nowrap;
}
.tb-btn:hover { background: rgba(255,255,255,0.12); color: white; }
.tb-btn:active { transform: scale(0.95); }

.tb-divider { width: 1px; height: 20px; background: rgba(255,255,255,0.2); flex-shrink: 0; }

/* ===== Lookup Popup ===== */
.lookup-popup {
  position: fixed; z-index: 300; min-width: 260px; max-width: 340px;
  background: var(--surface); border-radius: 16px; padding: 18px;
  border: 1px solid var(--border); box-shadow: var(--shadow-lg);
  backdrop-filter: blur(20px);
}
.popup-close {
  position: absolute; top: 8px; right: 8px; background: none; border: none;
  color: var(--text-tertiary); cursor: pointer; padding: 4px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center; transition: all 0.15s;
}
.popup-close:hover { color: var(--text); background: var(--bg); }

.popup-loading { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--text-secondary); padding: 8px 0; }
.spinner {
  width: 16px; height: 16px; border: 2px solid var(--border); border-top-color: var(--primary);
  border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Word result */
.pw-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.pw-word { font-size: 22px; font-weight: 800; color: var(--text); }
.pw-phonetic { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.pw-play {
  width: 28px; height: 28px; border-radius: 50%; border: none; cursor: pointer;
  background: rgba(99,102,241,0.08); color: var(--primary); display: flex;
  align-items: center; justify-content: center; transition: all 0.15s;
}
.pw-play:hover { background: rgba(99,102,241,0.15); }

.pw-meanings { display: flex; flex-direction: column; gap: 7px; margin-bottom: 12px; }
.pw-m-item { display: flex; align-items: baseline; gap: 8px; font-size: 14px; }
.pw-pos {
  display: inline-block; background: rgba(99,102,241,0.08); color: var(--primary);
  padding: 2px 10px; border-radius: 8px; font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.pw-meaning { color: var(--text); font-weight: 500; }

.pw-example { padding-top: 10px; border-top: 1px solid var(--border); font-size: 13px; line-height: 1.55; }
.pw-ex-en { color: var(--text); font-weight: 500; }
.pw-ex-cn { color: var(--text-secondary); margin-top: 3px; }

/* Translate result */
.pt-label { font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.pt-translation { font-size: 15px; color: var(--text); line-height: 1.65; font-weight: 500; margin-bottom: 14px; }
.pt-keywords { margin-top: 4px; }
.pt-kw-label { font-size: 11px; font-weight: 600; color: var(--text-tertiary); margin-bottom: 6px; display: block; }
.pt-kw-list { display: flex; flex-wrap: wrap; gap: 6px; }
.pt-kw {
  display: inline-flex; gap: 4px; background: var(--bg); padding: 4px 12px;
  border-radius: 10px; font-size: 12px; color: var(--text-secondary);
}
.pt-kw b { color: var(--primary); font-weight: 600; }

/* Not found */
.pw-notfound { display: flex; flex-direction: column; gap: 4px; }
.pw-nf { font-size: 13px; color: var(--text-tertiary); }

.popup-error { font-size: 13px; color: var(--danger); font-weight: 500; }

/* ===== Copy Toast ===== */
.copy-toast {
  position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); z-index: 500;
  background: var(--text); color: white; padding: 10px 20px; border-radius: 10px;
  font-size: 13px; font-weight: 600; box-shadow: var(--shadow-lg);
}

/* ===== Transitions ===== */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.toolbar-enter-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.toolbar-leave-active { transition: opacity 0.08s ease; }
.toolbar-enter-from { opacity: 0; transform: translateX(-50%) translateY(4px); }
.toolbar-leave-to { opacity: 0; }

.popup-enter-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.popup-leave-active { transition: opacity 0.1s ease; }
.popup-enter-from { opacity: 0; transform: scale(0.96) translateY(4px); }
.popup-leave-to { opacity: 0; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s, transform 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(8px); }

.toast-enter-active { transition: all 0.2s ease; }
.toast-leave-active { transition: all 0.12s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(8px); }

/* ===== Mobile ===== */
@media (max-width: 768px) {
  .article-title { font-size: 22px; }
  .article-content { font-size: 15px; line-height: 1.8; }
  .hero-wrap { border-radius: 16px; }
  .hero-img { max-height: 220px; }
  .lookup-popup { min-width: 220px; max-width: 290px; }
  .back-top { bottom: 16px; right: 16px; }
  .title-area { padding: 0; }
  .article-content { padding: 0; }
  .tb-btn { padding: 6px 12px; font-size: 12px; }
}
</style>
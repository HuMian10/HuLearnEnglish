<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'
import { useRoute } from 'vue-router'

const route = useRoute()

const words = ref([])
const index = ref(0)
const current = ref(null)
const empty = ref(true)
const finished = ref(false)
const wordMastered = ref(false)

// Favorites
const isFav = ref(false)

// LLM
const showChat = ref(false)
const chatMessages = ref([])
const chatInput = ref('')
const llmOutput = ref('')

// Phase: front → answer
const phase = ref('front')
const initialChoice = ref('') // 'known' or 'unknown'

// Stats
const correctCount = ref(0)
const wrongCount = ref(0)

const progress = computed(() =>
  words.value.length > 0 ? Math.round((index.value / words.value.length) * 100) : 0
)

onMounted(() => loadReview())
watch(() => route.path, (val) => { if (val === '/review') loadReview() })

async function loadReview() {
  const data = await api('learning/due-review')
  if (!data.words || data.words.length === 0) {
    empty.value = true
    finished.value = false
    current.value = null
    return
  }
  empty.value = false
  finished.value = false
  words.value = data.words
  index.value = 0
  correctCount.value = 0
  wrongCount.value = 0
  showWord()
}

function showWord() {
  if (index.value >= words.value.length) {
    finished.value = true
    current.value = null
    return
  }
  current.value = words.value[index.value]
  phase.value = 'front'
  initialChoice.value = ''
  wordMastered.value = false
  showChat.value = false
  llmOutput.value = ''
  chatMessages.value = []
  checkFavorite()
}

function playAudio(url) {
  if (!url) return
  new Audio(url).play().catch(() => {})
}

function hasForms(w) {
  return w.plural || w.past_tense || w.past_participle || w.present_participle || w.comparative || w.superlative || w.third_person
}

function getMeaningText(w) {
  if (!w) return ''
  if (w.meanings?.length) return w.meanings.map(m => m.meaning_cn).join('；')
  return w.meaning_cn || ''
}

function onKnow() {
  initialChoice.value = 'known'
  phase.value = 'answer'
}

function onDontKnow() {
  initialChoice.value = 'unknown'
  phase.value = 'answer'
}

async function markCorrect() {
  correctCount.value++
  await submitReview(true)
}

async function markWrong() {
  wrongCount.value++
  await submitReview(false)
}

async function submitReview(correct) {
  if (!words.value[index.value]) return
  await api('learning/review', {
    method: 'POST',
    body: JSON.stringify({ word_id: words.value[index.value].id, correct }),
  })
  index.value++
  showWord()
}

async function markMastered() {
  if (!words.value[index.value] || wordMastered.value) return
  wordMastered.value = true
  await api('learning/master', {
    method: 'POST',
    body: JSON.stringify({ word_id: words.value[index.value].id }),
  })
  correctCount.value++
  index.value++
  showWord()
}

async function llmQuickAction(action) {
  if (!current.value) return
  llmOutput.value = '<div style="color:var(--text-secondary);text-align:center;padding:8px">加载中...</div>'
  showChat.value = false
  try {
    const result = await api(`llm/quick-actions/${current.value.id}?action=${action}`, { method: 'POST' })
    if (!result.ok) {
      llmOutput.value = `<div style="color:var(--danger)">${result.error || '请求失败'}</div>`
      return
    }
    llmOutput.value = `<pre style="white-space:pre-wrap;font-size:13px;line-height:1.6;color:var(--text);background:var(--bg);padding:12px;border-radius:8px;overflow-x:auto">${JSON.stringify(result.data, null, 2)}</pre>`
  } catch (e) {
    llmOutput.value = `<div style="color:var(--danger)">${e.message}</div>`
  }
}

async function sendChat() {
  if (!chatInput.value.trim() || !current.value) return
  chatMessages.value.push({ role: 'user', text: chatInput.value })
  const msg = chatInput.value
  chatInput.value = ''
  try {
    const res = await fetch(`/api/llm/chat/${current.value.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
      credentials: 'include',
    })
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const assistantIdx = chatMessages.value.length
    chatMessages.value.push({ role: 'assistant', text: '' })
    while (true) {
      const { done: rd, value } = await reader.read()
      if (rd) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') break
          try {
            const parsed = JSON.parse(data)
            if (parsed.content) chatMessages.value[assistantIdx].text += parsed.content
          } catch {}
        }
      }
    }
  } catch (e) {
    chatMessages.value.push({ role: 'assistant', text: 'Error: ' + e.message })
  }
}

async function loadMore() {
  const data = await api('learning/due-review')
  if (data.words && data.words.length > 0) {
    words.value = data.words
    index.value = 0
    correctCount.value = 0
    wrongCount.value = 0
    finished.value = false
    showWord()
  }
}

async function checkFavorite() {
  if (!current.value) return
  try {
    const data = await api(`learning/favorites/check/${current.value.id}`)
    isFav.value = data.is_favorite
  } catch {
    isFav.value = false
  }
}

async function toggleFavorite() {
  if (!current.value) return
  try {
    if (isFav.value) {
      await api(`learning/favorites/${current.value.id}`, { method: 'DELETE' })
      isFav.value = false
    } else {
      await api(`learning/favorites/${current.value.id}`, { method: 'POST' })
      isFav.value = true
    }
  } catch {}
}
</script>

<template>
  <h2 class="page-title">单词复习</h2>

  <div v-if="empty" class="empty-state">
    <div class="empty-icon">🎉</div>
    <p>没有需要复习的单词</p>
    <p class="empty-hint">所有学过的单词都在记忆周期内，稍后再来吧</p>
  </div>

  <template v-else-if="finished">
    <div class="summary-card">
      <div class="summary-title">复习完成!</div>
      <div class="summary-stats">
        <div class="summary-stat">
          <span class="stat-value">{{ correctCount + wrongCount }}</span>
          <span class="stat-label">总复习</span>
        </div>
        <div class="summary-stat correct">
          <span class="stat-value">{{ correctCount }}</span>
          <span class="stat-label">认识</span>
        </div>
        <div class="summary-stat wrong">
          <span class="stat-value">{{ wrongCount }}</span>
          <span class="stat-label">不认识</span>
        </div>
      </div>
      <div class="summary-bar">
        <div class="summary-bar-fill" :style="{ width: words.length > 0 ? (correctCount / words.length * 100) + '%' : '0%' }"></div>
      </div>
      <p class="summary-rate">正确率 {{ words.length > 0 ? Math.round(correctCount / words.length * 100) : 0 }}%</p>
      <button class="btn btn-primary" @click="loadMore">继续复习</button>
    </div>
  </template>

  <template v-else-if="current">
    <!-- Progress bar -->
    <div class="review-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <span class="progress-text">{{ index + 1 }} / {{ words.length }}</span>
    </div>

    <!-- Word toolbar — always visible across all phases -->
    <div class="word-toolbar">
      <button class="toolbar-btn" :class="{ active: isFav }" @click="toggleFavorite" title="收藏">
        <span style="font-size:14px">{{ isFav ? '⭐' : '☆' }}</span>
        <span>{{ isFav ? '已收藏' : '收藏' }}</span>
      </button>
      <button class="toolbar-btn" :class="{ active: wordMastered }" @click="markMastered" title="已掌握">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        <span>已掌握</span>
      </button>
    </div>

    <!-- Phase: front — show word, user judges -->
    <template v-if="phase === 'front'">
      <div class="word-card-container">
        <div class="word-card">
          <div class="card-face">
            <div class="card-word">{{ current.word }}</div>
            <div class="card-phonetic-row">
              <span v-if="current.phonetic_uk" class="card-phonetic-item">🇬🇧 {{ current.phonetic_uk }}<button v-if="current.audio_uk" class="card-play-btn mini" @click.stop="playAudio(current.audio_uk)"><span class="play-icon">&#9654;</span></button></span>
              <span v-if="current.phonetic_us" class="card-phonetic-item">🇺🇸 {{ current.phonetic_us }}<button v-if="current.audio_us" class="card-play-btn mini" @click.stop="playAudio(current.audio_us)"><span class="play-icon">&#9654;</span></button></span>
              <span v-if="!current.phonetic_uk && !current.phonetic_us && current.phonetic" class="card-phonetic-item">{{ current.phonetic }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="learn-actions">
        <button class="btn btn-danger" @click="onDontKnow">✗ 不认识</button>
        <button class="btn btn-success" @click="onKnow">✓ 认识</button>
      </div>
    </template>

    <!-- Phase: answer — reveal full card -->
    <template v-if="phase === 'answer'">
      <Transition name="card" mode="out-in">
        <div class="word-card-container" :key="'answer'">
          <div class="word-card">
            <div class="card-face">
              <div class="card-word">{{ current.word }}</div>
              <div class="card-phonetic-row">
                <span v-if="current.phonetic_uk" class="card-phonetic-item">🇬🇧 {{ current.phonetic_uk }}<button v-if="current.audio_uk" class="card-play-btn mini" @click.stop="playAudio(current.audio_uk)"><span class="play-icon">&#9654;</span></button></span>
                <span v-if="current.phonetic_us" class="card-phonetic-item">🇺🇸 {{ current.phonetic_us }}<button v-if="current.audio_us" class="card-play-btn mini" @click.stop="playAudio(current.audio_us)"><span class="play-icon">&#9654;</span></button></span>
                <span v-if="!current.phonetic_uk && !current.phonetic_us && current.phonetic" class="card-phonetic-item">{{ current.phonetic }}</span>
              </div>
              <div class="card-meanings">
                <div v-for="(m, i) in (current.meanings || [])" :key="i" class="card-meaning-item">
                  <span class="card-pos">{{ m.pos }}</span>
                  <span class="card-meaning-text">{{ m.meaning_cn }}</span>
                </div>
                <div v-if="!current.meanings?.length && current.meaning_cn" class="card-meaning-item">
                  <span class="card-pos">{{ current.pos }}</span>
                  <span class="card-meaning-text">{{ current.meaning_cn }}</span>
                </div>
              </div>
              <div class="card-forms" v-if="hasForms(current)">
                <span v-if="current.plural" class="card-form-tag">复数: {{ current.plural }}</span>
                <span v-if="current.past_tense" class="card-form-tag">过去式: {{ current.past_tense }}</span>
                <span v-if="current.past_participle" class="card-form-tag">过去分词: {{ current.past_participle }}</span>
                <span v-if="current.present_participle" class="card-form-tag">现在分词: {{ current.present_participle }}</span>
                <span v-if="current.comparative" class="card-form-tag">比较级: {{ current.comparative }}</span>
                <span v-if="current.superlative" class="card-form-tag">最高级: {{ current.superlative }}</span>
                <span v-if="current.third_person" class="card-form-tag">三单: {{ current.third_person }}</span>
              </div>
              <div class="card-example" v-if="current.example_en">{{ current.example_en }}<br>{{ current.example_cn }}</div>
            </div>
          </div>
        </div>
      </Transition>

      <!-- User initially said "认识" — confirm or correct -->
      <div v-if="initialChoice === 'known'" class="learn-actions">
        <button class="btn btn-danger" @click="markWrong">不记得了</button>
        <button class="btn btn-success" @click="markCorrect">记得，下一个</button>
      </div>

      <!-- User initially said "不认识" — just acknowledge and move on -->
      <div v-else class="learn-actions">
        <button class="btn btn-primary" @click="markWrong">下一个</button>
      </div>

      <div class="learn-llm">
        <div class="llm-quick-actions">
          <button class="btn btn-small" @click="llmQuickAction('examples')">生成例句</button>
          <button class="btn btn-small" @click="llmQuickAction('explain')">详细解释</button>
          <button class="btn btn-small" @click="llmQuickAction('quiz')">小测验</button>
          <button class="btn btn-small" @click="showChat = !showChat">自由对话</button>
        </div>
        <div v-html="llmOutput"></div>
        <div v-if="showChat" class="llm-chat">
          <div class="chat-messages">
            <div v-for="(msg, i) in chatMessages" :key="i" class="chat-msg" :class="msg.role">{{ msg.text }}</div>
          </div>
          <div class="chat-input">
            <input v-model="chatInput" placeholder="问关于这个单词的问题..." @keydown.enter="sendChat">
            <button class="btn btn-primary btn-small" @click="sendChat">发送</button>
          </div>
        </div>
      </div>
    </template>
  </template>
</template>

<style scoped>
/* Progress bar */
.review-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--gradient-primary);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
  min-width: 48px;
  text-align: right;
  font-weight: 600;
}

/* Empty state */
.empty-icon { font-size: 56px; margin-bottom: 8px; }
.empty-hint { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

/* Summary card */
.summary-card {
  max-width: 400px;
  margin: 40px auto;
  background: var(--surface);
  border-radius: var(--radius-xl);
  padding: 32px;
  box-shadow: var(--shadow-md);
  text-align: center;
}

.summary-title {
  font-size: 24px;
  font-weight: 800;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 24px;
}

.summary-stats {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-bottom: 20px;
}

.summary-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.5px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
  font-weight: 500;
}

.summary-stat.correct .stat-value { color: var(--success); }
.summary-stat.wrong .stat-value { color: var(--danger); }

.summary-bar {
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.summary-bar-fill {
  height: 100%;
  background: var(--gradient-success);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.summary-rate {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 20px;
  font-weight: 600;
}

.summary-card .btn { width: 100%; justify-content: center; }

/* Card styles */
.card-face {
  background: var(--surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px;
}

/* Transition */
.card-enter-active { transition: all 0.3s ease; }
.card-leave-active { transition: all 0.15s ease; }
.card-enter-from { opacity: 0; transform: translateY(12px); }
.card-leave-to { opacity: 0; transform: translateY(-8px); }

/* Word toolbar */
.word-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  padding: 8px 4px;
  margin-bottom: 4px;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: 1.5px solid var(--border);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1;
}

.toolbar-btn:hover {
  color: var(--success);
  border-color: var(--success);
  background: rgba(16,185,129,0.06);
}

.toolbar-btn.active {
  color: var(--success);
  border-color: var(--success);
  background: rgba(16,185,129,0.08);
}

.toolbar-btn svg { flex-shrink: 0; }

@media (max-width: 768px) {
  .summary-card { padding: 24px 16px; margin: 20px auto; }
  .summary-stats { gap: 20px; }
  .stat-value { font-size: 24px; }
  .card-face { padding: 16px; }
}
</style>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const words = ref([])
const total = ref(0)
const page = ref(1)
const empty = ref(true)

onMounted(loadWrongWords)
watch(() => route.path, (val) => { if (val === '/wrong-words') loadWrongWords() })

async function loadWrongWords() {
  const data = await api(`learning/wrong-words?page=${page.value}`)
  words.value = data.words || []
  total.value = data.total || 0
  empty.value = total.value === 0
}

function playAudio(url) {
  if (!url) return
  new Audio(url).play().catch(() => {})
}

function getMeaningText(w) {
  if (!w) return ''
  if (w.meanings?.length) return w.meanings.map(m => m.meaning_cn).join('；')
  return w.meaning_cn || ''
}

async function removeFromWrong(wordId) {
  await api(`learning/wrong-words/${wordId}`, { method: 'DELETE' })
  await loadWrongWords()
}

async function reviewWord(word) {
  // Navigate to review page - the word will appear in due reviews
  router.push({ name: 'review' })
}
</script>

<template>
  <h2 class="page-title">错题本</h2>

  <div v-if="empty" class="empty-state">
    <div class="empty-icon">✨</div>
    <p>没有错题记录</p>
    <p class="empty-hint">答错的单词会自动收录在这里</p>
  </div>

  <template v-else>
    <div class="wrong-count">共 {{ total }} 个错题</div>

    <div class="wrong-list">
      <div v-for="w in words" :key="w.id" class="wrong-card">
        <div class="wrong-card-main">
          <div class="wrong-word-row">
            <span class="wrong-word">{{ w.word }}</span>
            <span v-if="w.phonetic_us" class="wrong-phonetic">🇺🇸 {{ w.phonetic_us }}
              <button v-if="w.audio_us" class="card-play-btn mini" @click="playAudio(w.audio_us)"><span class="play-icon">&#9654;</span></button>
            </span>
          </div>
          <div class="wrong-meaning">{{ getMeaningText(w) }}</div>
          <div class="wrong-meta">
            <span class="wrong-count-tag">错 {{ w.wrong_count }} 次</span>
            <span v-if="w.last_wrong_at" class="wrong-time">{{ w.last_wrong_at.split(' ')[0] }}</span>
          </div>
        </div>
        <div class="wrong-card-actions">
          <button class="btn btn-small" @click="removeFromWrong(w.id)" title="移出错题本">移除</button>
        </div>
      </div>
    </div>
  </template>
</template>

<style scoped>
.empty-icon { font-size: 48px; margin-bottom: 8px; }
.empty-hint { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

.wrong-count {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.wrong-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wrong-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--surface);
  border-radius: 12px;
  box-shadow: var(--shadow);
  gap: 12px;
}

.wrong-card-main { flex: 1; min-width: 0; }

.wrong-word-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.wrong-word {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.wrong-phonetic {
  font-size: 13px;
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.wrong-meaning {
  font-size: 14px;
  color: var(--text);
  margin-top: 4px;
  line-height: 1.5;
}

.wrong-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}

.wrong-count-tag {
  font-size: 11px;
  font-weight: 600;
  color: var(--danger);
  background: #fef2f2;
  padding: 2px 8px;
  border-radius: 10px;
}

.wrong-time {
  font-size: 11px;
  color: var(--text-secondary);
}

.wrong-card-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .wrong-card { padding: 12px; }
  .wrong-word { font-size: 16px; }
}
</style>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'

const route = useRoute()
const words = ref([])
const total = ref(0)
const page = ref(1)
const empty = ref(true)

onMounted(loadFavorites)
watch(() => route.path, (val) => { if (val === '/favorites') loadFavorites() })

async function loadFavorites() {
  const data = await api(`learning/favorites?page=${page.value}`)
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

async function unfavorite(wordId) {
  await api(`learning/favorites/${wordId}`, { method: 'DELETE' })
  await loadFavorites()
}
</script>

<template>
  <h2 class="page-title">收藏单词</h2>

  <div v-if="empty" class="empty-state">
    <div class="empty-icon">⭐</div>
    <p>还没有收藏的单词</p>
    <p class="empty-hint">在学习时点击收藏按钮来添加</p>
  </div>

  <template v-else>
    <div class="fav-count">共 {{ total }} 个收藏</div>

    <div class="fav-list">
      <div v-for="w in words" :key="w.id" class="fav-card">
        <div class="fav-card-main">
          <div class="fav-word-row">
            <span class="fav-word">{{ w.word }}</span>
            <span v-if="w.phonetic_us" class="fav-phonetic">🇺🇸 {{ w.phonetic_us }}
              <button v-if="w.audio_us" class="card-play-btn mini" @click="playAudio(w.audio_us)"><span class="play-icon">&#9654;</span></button>
            </span>
          </div>
          <div class="fav-meaning">{{ getMeaningText(w) }}</div>
        </div>
        <button class="fav-unfav-btn" @click="unfavorite(w.id)" title="取消收藏">⭐</button>
      </div>
    </div>
  </template>
</template>

<style scoped>
.empty-icon { font-size: 48px; margin-bottom: 8px; }
.empty-hint { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

.fav-count {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.fav-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.fav-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--surface);
  border-radius: 12px;
  box-shadow: var(--shadow);
  gap: 12px;
}

.fav-card-main { flex: 1; min-width: 0; }

.fav-word-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.fav-word {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.fav-phonetic {
  font-size: 13px;
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.fav-meaning {
  font-size: 14px;
  color: var(--text);
  margin-top: 4px;
  line-height: 1.5;
}

.fav-unfav-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  flex-shrink: 0;
  padding: 4px;
  transition: transform 0.15s;
}

.fav-unfav-btn:active { transform: scale(0.85); }

@media (max-width: 768px) {
  .fav-card { padding: 12px; }
  .fav-word { font-size: 16px; }
}
</style>

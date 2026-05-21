<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { useWordBooksStore } from '../stores/wordBooks'

const route = useRoute()
const wordBooks = useWordBooksStore()

// Tabs
const activeTab = ref('favorites')
const tabs = [
  { key: 'favorites', label: '收藏', icon: '⭐' },
  { key: 'wrong', label: '错题', icon: '❌' },
  { key: 'books', label: '单词本', icon: '📚' },
]

// Search
const search = ref('')

// Favorites data
const favWords = ref([])
const favTotal = ref(0)

// Wrong words data
const wrongWords = ref([])
const wrongTotal = ref(0)

// Word books data
const books = ref([])
const selectedBookId = ref(0)
const bookWords = ref([])

// Word detail modal
const showModal = ref(false)
const modalWord = ref(null)
const modalIsFav = ref(false)
const modalLlmOutput = ref('')

onMounted(loadTab)
watch(() => route.path, (val) => { if (val === '/word-bank') loadTab() })
watch(activeTab, () => { search.value = ''; loadTab() })

async function loadTab() {
  if (activeTab.value === 'favorites') await loadFavorites()
  else if (activeTab.value === 'wrong') await loadWrongWords()
  else await loadBooks()
}

// ── Favorites ──

async function loadFavorites() {
  const data = await api('learning/favorites?page=1&page_size=500')
  favWords.value = data.words || []
  favTotal.value = data.total || 0
}

async function toggleFavorite(wordId) {
  try {
    if (modalIsFav.value) {
      await api(`learning/favorites/${wordId}`, { method: 'DELETE' })
      modalIsFav.value = false
    } else {
      await api(`learning/favorites/${wordId}`, { method: 'POST' })
      modalIsFav.value = true
    }
  } catch {}
  if (activeTab.value === 'favorites') await loadFavorites()
}

// ── Wrong Words ──

async function loadWrongWords() {
  const data = await api('learning/wrong-words?page=1&page_size=500')
  wrongWords.value = data.words || []
  wrongTotal.value = data.total || 0
}

async function removeFromWrong(wordId) {
  await api(`learning/wrong-words/${wordId}`, { method: 'DELETE' })
  await loadWrongWords()
  closeModal()
}

async function clearAllWrong() {
  if (!confirm('确定要清空全部错题吗？')) return
  await api('learning/wrong-words', { method: 'DELETE' })
  await loadWrongWords()
}

// ── Word Books ──

async function loadBooks() {
  const data = await api('word-books')
  books.value = data.books || []
  if (books.value.length > 0 && !selectedBookId.value) {
    selectedBookId.value = books.value.find(b => b.is_active)?.id || books.value[0].id
  }
  if (selectedBookId.value) await loadBookWords()
}

async function loadBookWords() {
  if (!selectedBookId.value) return
  const data = await api(`words/all-by-book?word_book_id=${selectedBookId.value}`)
  bookWords.value = data.words || []
}

function selectBook(id) {
  selectedBookId.value = id
  loadBookWords()
}

// ── Current word list for the active tab ──

const currentWords = computed(() => {
  if (activeTab.value === 'favorites') return favWords.value
  if (activeTab.value === 'wrong') return wrongWords.value
  return bookWords.value
})

const filteredWords = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return currentWords.value
  return currentWords.value.filter(w =>
    w.word.toLowerCase().includes(q) ||
    getMeaningText(w).toLowerCase().includes(q)
  )
})

const grouped = computed(() => {
  const list = filteredWords.value
  const groups = []
  let curLetter = ''
  let curGroup = null
  for (const w of list) {
    const letter = w.word[0]?.toUpperCase() || '#'
    if (letter !== curLetter) {
      curLetter = letter
      curGroup = { letter, words: [] }
      groups.push(curGroup)
    }
    curGroup.words.push(w)
  }
  return groups
})

const letters = computed(() => grouped.value.map(g => g.letter))

function scrollTo(letter) {
  const el = document.getElementById('wb-letter-' + letter)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// ── Word Detail Modal ──

function getMeaningText(w) {
  if (!w) return ''
  if (w.meanings?.length) return w.meanings.map(m => m.meaning_cn).join('；')
  return w.meaning_cn || ''
}

function playAudio(url) {
  if (!url) return
  new Audio(url).play().catch(() => {})
}

async function openDetail(word) {
  const data = await api('words/' + word.id)
  modalWord.value = data
  modalLlmOutput.value = ''
  // Check favorite status
  try {
    const fav = await api(`learning/favorites/check/${word.id}`)
    modalIsFav.value = fav.is_favorite
  } catch {
    modalIsFav.value = false
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  modalWord.value = null
}

async function llmAction(id, action) {
  modalLlmOutput.value = '<div style="color:var(--text-secondary);text-align:center;padding:8px">加载中...</div>'
  try {
    const result = await api(`llm/quick-actions/${id}?action=${action}`, { method: 'POST' })
    if (!result.ok) {
      modalLlmOutput.value = `<div style="color:var(--danger)">${result.error || '请求失败'}</div>`
      return
    }
    modalLlmOutput.value = renderLLMData(result.action, result.data, modalWord.value?.word)
  } catch (e) {
    modalLlmOutput.value = `<div style="color:var(--danger)">${e.message}</div>`
  }
}

function escHtml(str) {
  if (!str) return ''
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')
}

function highlightWord(text, word) {
  if (!word) return text
  const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(new RegExp(`(${escaped})`, 'gi'), '<span style="color:var(--primary);font-weight:600">$1</span>')
}

function renderLLMData(action, data, word) {
  if (action === 'examples') {
    const examples = data.examples || []
    if (!examples.length) return '<div style="color:var(--danger)">未生成例句</div>'
    return `<div style="display:flex;flex-direction:column;gap:10px">${examples.map(ex => `
      <div style="padding:10px 12px;background:var(--bg);border-radius:8px">
        <div style="font-size:14px;line-height:1.6">${highlightWord(escHtml(ex.en), word)}</div>
        <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">${escHtml(ex.cn)}</div>
      </div>`).join('')}</div>`
  }
  if (action === 'explain') {
    let html = '<div style="display:flex;flex-direction:column;gap:12px">'
    if (data.meaning) html += `<div><div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px">释义</div><div style="font-size:14px;line-height:1.6">${escHtml(data.meaning)}</div></div>`
    if (data.nuances) html += `<div><div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px">细微差别</div><div style="font-size:14px;line-height:1.6">${escHtml(data.nuances)}</div></div>`
    if (data.collocations?.length) html += `<div><div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px">常见搭配</div><div style="display:flex;gap:6px;flex-wrap:wrap">${data.collocations.map(c => `<span style="background:#eef2ff;color:#4f46e5;padding:3px 10px;border-radius:12px;font-size:13px">${escHtml(c)}</span>`).join('')}</div></div>`
    if (data.common_mistakes) html += `<div><div style="font-size:12px;font-weight:600;color:var(--text-secondary);margin-bottom:4px">常见错误</div><div style="font-size:14px;line-height:1.6;color:var(--danger)">${escHtml(data.common_mistakes)}</div></div>`
    html += '</div>'
    return html
  }
  if (action === 'quiz') {
    const quizzes = data.quizzes || []
    if (!quizzes.length) return '<div style="color:var(--danger)">未生成测验</div>'
    return `<div style="display:flex;flex-direction:column;gap:12px">${quizzes.map((q, i) => {
      if (q.type === 'fill_blank') return `<div style="padding:10px 12px;background:var(--bg);border-radius:8px">
        <div style="font-size:12px;color:var(--primary);font-weight:600;margin-bottom:6px">填空题</div>
        <div style="font-size:14px;margin-bottom:8px">${escHtml(q.question)}</div>
        <div style="font-size:13px;color:var(--text-secondary)">答案: ${escHtml(q.answer)}</div>
      </div>`
      if (q.type === 'choice') return `<div style="padding:10px 12px;background:var(--bg);border-radius:8px">
        <div style="font-size:12px;color:var(--primary);font-weight:600;margin-bottom:6px">选择题</div>
        <div style="font-size:14px;margin-bottom:8px">${escHtml(q.question)}</div>
        <div style="font-size:13px">${(q.options||[]).map(o => `<div style="padding:3px 0">${escHtml(o)}</div>`).join('')}</div>
        <div style="font-size:13px;color:var(--success);margin-top:6px">正确答案: ${escHtml(q.answer)}</div>
      </div>`
      return ''
    }).join('')}</div>`
  }
  return `<pre style="white-space:pre-wrap;font-size:13px">${JSON.stringify(data, null, 2)}</pre>`
}
</script>

<template>
  <h2 class="page-title">词库</h2>

  <!-- Tabs -->
  <div class="wb-tabs">
    <button
      v-for="tab in tabs" :key="tab.key"
      class="wb-tab" :class="{ active: activeTab === tab.key }"
      @click="activeTab = tab.key"
    >
      <span class="wb-tab-icon">{{ tab.icon }}</span>
      <span>{{ tab.label }}</span>
      <span v-if="tab.key === 'favorites' && favTotal" class="wb-tab-badge">{{ favTotal }}</span>
      <span v-if="tab.key === 'wrong' && wrongTotal" class="wb-tab-badge wrong">{{ wrongTotal }}</span>
    </button>
  </div>

  <!-- Search -->
  <input v-model="search" placeholder="搜索单词或释义..." class="wb-search">

  <!-- ── Favorites Tab ── -->
  <template v-if="activeTab === 'favorites'">
    <div v-if="favTotal === 0" class="wb-empty">
      <div class="wb-empty-icon">⭐</div>
      <p>还没有收藏的单词</p>
      <p class="wb-empty-hint">在学习时点击收藏按钮来添加</p>
    </div>
    <div v-else class="wb-body">
      <div class="wb-list">
        <div v-for="group in grouped" :key="group.letter" class="wb-group">
          <div :id="'wb-letter-' + group.letter" class="wb-letter-header">{{ group.letter }}</div>
          <div v-for="w in group.words" :key="w.id" class="wb-word-item" @click="openDetail(w)">
            <span class="wb-word">{{ w.word }}</span>
            <span class="wb-meaning">{{ getMeaningText(w) }}</span>
          </div>
        </div>
        <div v-if="grouped.length === 0" class="wb-no-match">没有匹配的单词</div>
      </div>
      <div class="wb-alpha-bar" v-if="letters.length > 0">
        <span v-for="l in letters" :key="l" class="wb-alpha-item" @click="scrollTo(l)">{{ l }}</span>
      </div>
    </div>
  </template>

  <!-- ── Wrong Words Tab ── -->
  <template v-if="activeTab === 'wrong'">
    <div v-if="wrongTotal > 0" class="wb-clear-bar">
      <span class="wb-clear-text">共 {{ wrongTotal }} 个错题</span>
      <button class="wb-clear-btn" @click="clearAllWrong">清空全部错题</button>
    </div>
    <div v-if="wrongTotal === 0" class="wb-empty">
      <div class="wb-empty-icon">✨</div>
      <p>没有错题记录</p>
      <p class="wb-empty-hint">答错的单词会自动收录在这里</p>
    </div>
    <div v-else class="wb-body">
      <div class="wb-list">
        <div v-for="group in grouped" :key="group.letter" class="wb-group">
          <div :id="'wb-letter-' + group.letter" class="wb-letter-header">{{ group.letter }}</div>
          <div v-for="w in group.words" :key="w.id" class="wb-word-item wrong" @click="openDetail(w)">
            <div class="wb-word-main">
              <span class="wb-word">{{ w.word }}</span>
              <span class="wb-wrong-tag">错{{ w.wrong_count }}次</span>
            </div>
            <span class="wb-meaning">{{ getMeaningText(w) }}</span>
          </div>
        </div>
        <div v-if="grouped.length === 0" class="wb-no-match">没有匹配的单词</div>
      </div>
      <div class="wb-alpha-bar" v-if="letters.length > 0">
        <span v-for="l in letters" :key="l" class="wb-alpha-item" @click="scrollTo(l)">{{ l }}</span>
      </div>
    </div>
  </template>

  <!-- ── Word Books Tab ── -->
  <template v-if="activeTab === 'books'">
    <!-- Book selector -->
    <div class="wb-book-chips">
      <button
        v-for="book in books" :key="book.id"
        class="wb-book-chip" :class="{ active: selectedBookId === book.id }"
        @click="selectBook(book.id)"
      >
        <span>{{ book.icon }}</span>
        <span>{{ book.name }}</span>
        <span class="wb-book-count">{{ book.word_count }}</span>
      </button>
    </div>

    <div v-if="bookWords.length === 0" class="wb-empty">
      <div class="wb-empty-icon">📚</div>
      <p>选择一个单词本查看</p>
    </div>
    <div v-else class="wb-body">
      <div class="wb-list">
        <div v-for="group in grouped" :key="group.letter" class="wb-group">
          <div :id="'wb-letter-' + group.letter" class="wb-letter-header">{{ group.letter }}</div>
          <div v-for="w in group.words" :key="w.id" class="wb-word-item" @click="openDetail(w)">
            <span class="wb-word">{{ w.word }}</span>
            <span class="wb-meaning">{{ getMeaningText(w) }}</span>
          </div>
        </div>
        <div v-if="grouped.length === 0" class="wb-no-match">没有匹配的单词</div>
      </div>
      <div class="wb-alpha-bar" v-if="letters.length > 0">
        <span v-for="l in letters" :key="l" class="wb-alpha-item" @click="scrollTo(l)">{{ l }}</span>
      </div>
    </div>
  </template>

  <!-- ── Word Detail Modal ── -->
  <Teleport to="body">
    <div v-if="showModal && modalWord" class="wb-modal-overlay" @click.self="closeModal">
      <div class="wb-modal-card">
        <button class="wb-modal-close" @click="closeModal">&times;</button>

        <!-- Favorite button -->
        <div class="wb-modal-fav">
          <button class="wb-fav-btn" :class="{ active: modalIsFav }" @click="toggleFavorite(modalWord.id)">
            {{ modalIsFav ? '⭐ 已收藏' : '☆ 收藏' }}
          </button>
          <!-- Remove from wrong words (only show in wrong tab) -->
          <button v-if="activeTab === 'wrong'" class="wb-remove-btn" @click="removeFromWrong(modalWord.id)">移出错题本</button>
        </div>

        <div class="wb-modal-word">{{ modalWord.word }}</div>
        <div class="wb-modal-phonetics">
          <span v-if="modalWord.phonetic_uk">🇬🇧 {{ modalWord.phonetic_uk }}
            <button v-if="modalWord.audio_uk" class="card-play-btn mini" @click="playAudio(modalWord.audio_uk)"><span class="play-icon">&#9654;</span></button>
          </span>
          <span v-if="modalWord.phonetic_us">🇺🇸 {{ modalWord.phonetic_us }}
            <button v-if="modalWord.audio_us" class="card-play-btn mini" @click="playAudio(modalWord.audio_us)"><span class="play-icon">&#9654;</span></button>
          </span>
        </div>

        <div class="wb-modal-meanings">
          <div v-for="(m, i) in (modalWord.meanings || [])" :key="i" class="wb-modal-m">
            <span class="card-pos">{{ m.pos }}</span>
            <span class="wb-modal-m-text">{{ m.meaning_cn }}</span>
          </div>
          <div v-if="!modalWord.meanings?.length && modalWord.meaning_cn" class="wb-modal-m">
            <span class="card-pos">{{ modalWord.pos }}</span>
            <span class="wb-modal-m-text">{{ modalWord.meaning_cn }}</span>
          </div>
        </div>

        <div v-if="modalWord.plural || modalWord.past_tense || modalWord.past_participle || modalWord.present_participle || modalWord.comparative || modalWord.superlative || modalWord.third_person" class="wb-modal-forms">
          <span v-if="modalWord.plural" class="card-form-tag">复数: {{ modalWord.plural }}</span>
          <span v-if="modalWord.past_tense" class="card-form-tag">过去式: {{ modalWord.past_tense }}</span>
          <span v-if="modalWord.past_participle" class="card-form-tag">过去分词: {{ modalWord.past_participle }}</span>
          <span v-if="modalWord.present_participle" class="card-form-tag">现在分词: {{ modalWord.present_participle }}</span>
          <span v-if="modalWord.comparative" class="card-form-tag">比较级: {{ modalWord.comparative }}</span>
          <span v-if="modalWord.superlative" class="card-form-tag">最高级: {{ modalWord.superlative }}</span>
          <span v-if="modalWord.third_person" class="card-form-tag">三单: {{ modalWord.third_person }}</span>
        </div>

        <div v-if="modalWord.example_en" class="wb-modal-example">
          {{ modalWord.example_en }}<br>{{ modalWord.example_cn }}
        </div>

        <div class="wb-modal-actions">
          <button class="btn btn-small" @click="llmAction(modalWord.id, 'examples')">生成例句</button>
          <button class="btn btn-small" @click="llmAction(modalWord.id, 'explain')">详细解释</button>
          <button class="btn btn-small" @click="llmAction(modalWord.id, 'quiz')">小测验</button>
        </div>
        <div v-html="modalLlmOutput" style="margin-top:12px"></div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* ── Tabs ── */
.wb-tabs {
  display: flex;
  gap: 3px;
  background: var(--bg);
  border-radius: var(--radius);
  padding: 3px;
  margin-bottom: 16px;
}

.wb-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.wb-tab:hover { color: var(--text); }
.wb-tab.active {
  background: var(--surface);
  color: var(--primary);
  box-shadow: var(--shadow);
  font-weight: 700;
}

.wb-tab-icon { font-size: 16px; }

.wb-tab-badge {
  font-size: 10px;
  font-weight: 700;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  background: var(--primary);
  color: white;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}

.wb-tab-badge.wrong { background: var(--danger); }

/* ── Search ── */
.wb-search {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  outline: none;
  background: var(--surface);
  color: var(--text);
  margin-bottom: 16px;
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.wb-search:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }

/* ── Empty ── */
.wb-empty { text-align: center; padding: 40px 20px; }
.wb-empty-icon { font-size: 56px; margin-bottom: 8px; }
.wb-empty-hint { font-size: 13px; color: var(--text-secondary); margin-top: 4px; font-weight: 500; }

/* ── Clear bar ── */
.wb-clear-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.wb-clear-text { font-size: 13px; color: var(--text-secondary); font-weight: 500; }

.wb-clear-btn {
  padding: 5px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--danger);
  background: transparent;
  color: var(--danger);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.wb-clear-btn:hover { background: rgba(239,68,68,0.04); }

/* ── Word list body ── */
.wb-body { display: flex; gap: 0; min-height: 0; }
.wb-list { flex: 1; overflow-y: auto; min-width: 0; }
.wb-group { margin-bottom: 2px; }

.wb-letter-header {
  position: sticky;
  top: 0;
  background: var(--bg);
  font-size: 13px;
  font-weight: 700;
  color: var(--primary);
  padding: 6px 0 4px;
  z-index: 1;
}

.wb-word-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 4px;
  border-bottom: 1px solid rgba(0,0,0,0.04);
  cursor: pointer;
  transition: background 0.12s;
}

.wb-word-item:active { background: rgba(99,102,241,0.04); }

.wb-word-item.wrong { flex-direction: column; align-items: flex-start; gap: 2px; }

.wb-word-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wb-word {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  flex-shrink: 0;
  min-width: 80px;
}

.wb-meaning {
  font-size: 13px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wb-wrong-tag {
  font-size: 10px;
  font-weight: 600;
  color: var(--danger);
  background: rgba(239,68,68,0.08);
  padding: 1px 6px;
  border-radius: 8px;
}

.wb-no-match {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 14px;
}

/* ── Alphabet bar ── */
.wb-alpha-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 2px;
  gap: 0;
  flex-shrink: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.wb-alpha-item {
  font-size: 10px;
  font-weight: 600;
  color: var(--primary);
  padding: 1px 5px;
  cursor: pointer;
  line-height: 1.3;
  border-radius: 4px;
  transition: background 0.15s;
}

.wb-alpha-item:active { background: rgba(99,102,241,0.1); }

/* ── Book chips ── */
.wb-book-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.wb-book-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s;
}

.wb-book-chip:hover { border-color: var(--primary); }
.wb-book-chip.active { border-color: var(--primary); background: rgba(99,102,241,0.06); color: var(--primary); font-weight: 700; }

.wb-book-count {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg);
  padding: 1px 6px;
  border-radius: 8px;
}

/* ── Modal ── */
.wb-modal-overlay {
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

.wb-modal-card {
  background: var(--surface);
  border-radius: var(--radius-xl);
  padding: 24px;
  max-width: 420px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  position: relative;
  box-shadow: var(--shadow-lg);
  animation: fadeInUp 0.2s ease;
}

.wb-modal-close {
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

.wb-modal-close:hover { color: var(--text); }

.wb-modal-fav {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.wb-fav-btn {
  padding: 5px 14px;
  border-radius: 20px;
  border: 1.5px solid var(--border);
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
}

.wb-fav-btn.active { border-color: #f59e0b; background: rgba(245,158,11,0.06); color: #b45309; }

.wb-remove-btn {
  padding: 5px 14px;
  border-radius: 20px;
  border: 1.5px solid var(--danger);
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: var(--danger);
  transition: all 0.2s;
}

.wb-remove-btn:hover { background: rgba(239,68,68,0.04); }

.wb-modal-word {
  font-size: 28px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 8px;
  letter-spacing: -0.3px;
}

.wb-modal-phonetics {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}

.wb-modal-meanings {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.wb-modal-m {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.wb-modal-m-text {
  font-size: 15px;
  font-weight: 500;
  color: var(--text);
}

.wb-modal-forms {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.wb-modal-example {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
  margin-top: 8px;
}

.wb-modal-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .wb-tab { padding: 8px 8px; font-size: 13px; }
  .wb-modal-card { max-width: 100%; border-radius: var(--radius-lg); }
}
</style>

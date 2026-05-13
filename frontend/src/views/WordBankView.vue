<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { useWordBooksStore } from '../stores/wordBooks'

const wordBooks = useWordBooksStore()

const words = ref([])
const categories = ref([])
const search = ref('')
const category = ref('')
const selectedBookId = ref(0)
const page = ref(1)
const totalPages = ref(1)

const modalWord = ref(null)
const showModal = ref(false)
const modalLlmOutput = ref('')

onMounted(loadWordBank)

async function loadWordBank() {
  await wordBooks.fetchMyBooks()
  await loadCategories()
  await loadWordList()
}

async function loadCategories() {
  const params = new URLSearchParams()
  if (selectedBookId.value) params.set('word_book_id', selectedBookId.value)
  const cats = await api('words/categories?' + params)
  categories.value = cats
}

async function loadWordList() {
  const params = new URLSearchParams({
    page: page.value,
    page_size: 50,
    category: category.value,
    search: search.value,
  })
  if (selectedBookId.value) params.set('word_book_id', selectedBookId.value)
  const data = await api('words?' + params)
  words.value = data.words
  totalPages.value = Math.ceil(data.total / data.page_size)
}

function doSearch() { page.value = 1; loadWordList() }
function filterCategory(cat) { category.value = cat; page.value = 1; loadWordList() }

function selectBook(bookId) {
  selectedBookId.value = bookId
  category.value = ''
  page.value = 1
  loadCategories()
  loadWordList()
}

async function showWordDetail(id) {
  const word = await api('words/' + id)
  modalWord.value = word
  modalLlmOutput.value = ''
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function modalLLMAction(id, action) {
  modalLlmOutput.value = '<div class="llm-loading">加载中...</div>'
  try {
    const result = await api(`llm/quick-actions/${id}?action=${action}`, { method: 'POST' })
    if (!result.ok) {
      modalLlmOutput.value = `<div class="llm-error">${result.error || '请求失败'}</div>`
      return
    }
    modalLlmOutput.value = `<pre>${JSON.stringify(result.data, null, 2)}</pre>`
  } catch (e) {
    modalLlmOutput.value = `<div class="llm-error">${e.message}</div>`
  }
}

function playAudio(url) {
  if (!url) return
  new Audio(url).play().catch(() => {})
}
</script>

<template>
  <h2 class="page-title">词库</h2>

  <!-- Word book selector -->
  <div class="wordbook-chips" v-if="wordBooks.myBooks.length > 0">
    <span class="chip" :class="{ active: !selectedBookId }" @click="selectBook(0)">全部</span>
    <span
      v-for="book in wordBooks.myBooks"
      :key="book.id"
      class="chip"
      :class="{ active: selectedBookId === book.id }"
      @click="selectBook(book.id)"
    >{{ book.icon }} {{ book.name }}</span>
  </div>

  <div class="wordbank-controls">
    <input v-model="search" placeholder="搜索单词或释义..." @input="doSearch">
    <select v-model="category" @change="filterCategory(category)">
      <option value="">全部分类</option>
      <option v-for="c in categories" :key="c.category" :value="c.category">{{ c.category }} ({{ c.count }})</option>
    </select>
  </div>

  <div class="category-chips">
    <span class="chip" :class="{ active: !category }" @click="filterCategory('')">全部</span>
    <span v-for="c in categories" :key="c.category" class="chip" :class="{ active: category === c.category }" @click="filterCategory(c.category)">{{ c.category }}</span>
  </div>

  <div class="word-list">
    <div v-for="w in words" :key="w.id" class="word-item" @click="showWordDetail(w.id)">
      <span class="wi-word">{{ w.word }}</span><span class="wi-pos">{{ (w.meanings && w.meanings[0]?.pos) || w.pos }}</span>
      <div class="wi-meaning">{{ (w.meanings && w.meanings[0]?.meaning_cn) || w.meaning_cn }}</div>
    </div>
  </div>

  <div class="pagination" v-if="totalPages > 1">
    <button v-for="p in Math.min(totalPages, 10)" :key="p" class="btn btn-small" :class="p === page ? 'btn-primary' : 'btn-outline'" @click="page = p; loadWordList()">{{ p }}</button>
  </div>

  <!-- Word Detail Modal -->
  <div v-if="showModal" class="modal active" @click.self="closeModal">
    <div class="modal-content" v-if="modalWord">
      <button class="modal-close" @click="closeModal">&times;</button>
      <h2 style="font-size:28px;font-weight:700;margin-bottom:8px">{{ modalWord.word }}</h2>
      <div style="margin-bottom:8px;display:flex;gap:12px;align-items:center;flex-wrap:wrap">
        <span v-if="modalWord.phonetic_uk" class="modal-phonetic">🇬🇧 {{ modalWord.phonetic_uk }}<button v-if="modalWord.audio_uk" class="card-play-btn mini" @click="playAudio(modalWord.audio_uk)"><span class="play-icon">&#9654;</span></button></span>
        <span v-if="modalWord.phonetic_us" class="modal-phonetic">🇺🇸 {{ modalWord.phonetic_us }}<button v-if="modalWord.audio_us" class="card-play-btn mini" @click="playAudio(modalWord.audio_us)"><span class="play-icon">&#9654;</span></button></span>
        <span v-if="!modalWord.phonetic_uk && !modalWord.phonetic_us && modalWord.phonetic" style="color:#64748b;font-size:14px">{{ modalWord.phonetic }}</span>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">
        <span v-for="(m, i) in (modalWord.meanings || [])" :key="i" style="display:inline-flex;align-items:center;gap:4px">
          <span style="display:inline-block;background:#eef2ff;color:#4f46e5;padding:2px 10px;border-radius:12px;font-size:13px">{{ m.pos }}</span>
          <span style="font-size:15px;font-weight:500">{{ m.meaning_cn }}</span>
        </span>
        <span v-if="!modalWord.meanings?.length && modalWord.meaning_cn" style="display:inline-flex;align-items:center;gap:4px">
          <span style="display:inline-block;background:#eef2ff;color:#4f46e5;padding:2px 10px;border-radius:12px;font-size:13px">{{ modalWord.pos }}</span>
          <span style="font-size:15px;font-weight:500">{{ modalWord.meaning_cn }}</span>
        </span>
      </div>
      <span style="display:inline-block;background:#fef3c7;color:#92400e;padding:2px 10px;border-radius:12px;font-size:13px">{{ modalWord.category }}</span>
      <div v-if="modalWord.plural || modalWord.past_tense || modalWord.past_participle || modalWord.present_participle || modalWord.comparative || modalWord.superlative || modalWord.third_person" style="margin-top:12px;display:flex;gap:6px;flex-wrap:wrap">
        <span v-if="modalWord.plural" class="modal-form-tag">复数: {{ modalWord.plural }}</span>
        <span v-if="modalWord.past_tense" class="modal-form-tag">过去式: {{ modalWord.past_tense }}</span>
        <span v-if="modalWord.past_participle" class="modal-form-tag">过去分词: {{ modalWord.past_participle }}</span>
        <span v-if="modalWord.present_participle" class="modal-form-tag">现在分词: {{ modalWord.present_participle }}</span>
        <span v-if="modalWord.comparative" class="modal-form-tag">比较级: {{ modalWord.comparative }}</span>
        <span v-if="modalWord.superlative" class="modal-form-tag">最高级: {{ modalWord.superlative }}</span>
        <span v-if="modalWord.third_person" class="modal-form-tag">三单: {{ modalWord.third_person }}</span>
      </div>
      <p v-if="modalWord.example_en" style="margin-top:12px;color:#64748b;font-size:14px;line-height:1.6">{{ modalWord.example_en }}<br>{{ modalWord.example_cn }}</p>
      <div style="margin-top:20px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-small" @click="modalLLMAction(modalWord.id, 'examples')">生成例句</button>
        <button class="btn btn-small" @click="modalLLMAction(modalWord.id, 'explain')">详细解释</button>
        <button class="btn btn-small" @click="modalLLMAction(modalWord.id, 'quiz')">小测验</button>
      </div>
      <div v-html="modalLlmOutput" style="margin-top:16px"></div>
    </div>
  </div>
</template>

<style scoped>
.wordbook-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.modal-phonetic { color: #64748b; font-size: 14px; }
.modal-form-tag { display: inline-block; background: #f0f4ff; color: #4f46e5; padding: 2px 10px; border-radius: 12px; font-size: 13px; }
</style>

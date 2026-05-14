<script setup>
import { ref, watch, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useLearningStore } from '../stores/learning'
import { useWordBooksStore } from '../stores/wordBooks'
import { api } from '../api'

const auth = useAuthStore()
const learning = useLearningStore()
const wordBooks = useWordBooksStore()

const show = ref(false)
const pageStack = ref([]) // ['menu'] or ['menu', 'user-info'] etc.

const currentPage = computed(() => {
  const stack = pageStack.value
  return stack.length > 0 ? stack[stack.length - 1] : 'menu'
})

// Email form state
const emailInput = ref('')
const emailDisabled = ref(true)
const emailBtnText = ref('换绑')
const emailBtnMode = ref('change')
const emailSaved = ref(false)
const emailSavedMsg = ref('')

// Learning settings
const dailyWords = ref(10)
const recognizeModes = ref(['direct'])
const learnModes = ref(['flip'])
const recognizeModeOptions = [
  { value: 'direct', label: '直接标记', desc: '不验证' },
  { value: 'select_meaning', label: '选释义', desc: '看单词选释义' },
  { value: 'select_word', label: '选单词', desc: '看释义选单词' },
  { value: 'spell', label: '拼写', desc: '看释义拼写' },
  { value: 'dictation', label: '听写', desc: '听音频拼写' },
]
const learnModeOptions = [
  { value: 'flip', label: '翻卡查看', desc: '翻转查看详情' },
  { value: 'select_meaning', label: '选释义', desc: '看单词选释义' },
  { value: 'select_word', label: '选单词', desc: '看释义选单词' },
  { value: 'spell', label: '拼写', desc: '看释义拼写' },
  { value: 'dictation', label: '听写', desc: '听音频拼写' },
]
const learningSaved = ref(false)

// LLM settings
const llmUrl = ref('')
const llmKey = ref('')
const llmModel = ref('')
const llmSaved = ref(false)

// Word list page
const wlBookId = ref(0)
const wlBookName = ref('')
const wlWords = ref([])
const wlSearch = ref('')
const wlDetailWord = ref(null)
const wlShowDetail = ref(false)
const wlLlmOutput = ref('')

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])

watch(() => props.modelValue, (val) => {
  show.value = val
  if (val) pageStack.value = ['menu']
})

watch(show, (val) => {
  emit('update:modelValue', val)
})

const pageTitles = {
  menu: '设置',
  'user-info': '用户信息',
  'learning-settings': '学习设置',
  'word-books': '单词本',
  'word-list': '单词列表',
  'llm-settings': 'LLM 配置',
}

const navTitle = computed(() => pageTitles[currentPage.value] || '设置')

function pushPage(page) {
  pageStack.value.push(page)
  if (page === 'user-info') loadUserInfo()
  if (page === 'learning-settings') loadLearningSettings()
  if (page === 'word-books') loadWordBooks()
  if (page === 'llm-settings') loadLLMSettings()
}

function popPage() {
  if (pageStack.value.length > 1) {
    pageStack.value.pop()
  } else {
    show.value = false
  }
}

async function loadUserInfo() {
  const data = await api('auth/me')
  emailInput.value = data.email || ''
  const hasEmail = !!data.email
  emailDisabled.value = hasEmail
  emailBtnText.value = hasEmail ? '换绑' : '绑定'
  emailBtnMode.value = hasEmail ? 'change' : 'bind'
}

async function loadLearningSettings() {
  await learning.fetchSettings()
  dailyWords.value = learning.settings?.daily_words || 10
  const rm = learning.settings?.recognize_mode || 'direct'
  recognizeModes.value = rm.includes(',') ? rm.split(',') : [rm]
  const lm = learning.settings?.learn_mode || 'flip'
  learnModes.value = lm.includes(',') ? lm.split(',') : [lm]
}

function toggleRecognizeMode(val) {
  const idx = recognizeModes.value.indexOf(val)
  if (idx >= 0) {
    if (recognizeModes.value.length > 1) recognizeModes.value.splice(idx, 1)
  } else {
    recognizeModes.value.push(val)
  }
}

function toggleLearnMode(val) {
  const idx = learnModes.value.indexOf(val)
  if (idx >= 0) {
    if (learnModes.value.length > 1) learnModes.value.splice(idx, 1)
  } else {
    learnModes.value.push(val)
  }
}

async function loadWordBooks() {
  await wordBooks.fetchAllBooks()
}

async function loadLLMSettings() {
  await learning.fetchSettings()
  llmUrl.value = learning.settings?.llm_api_url || ''
  llmKey.value = learning.settings?.llm_api_key || ''
  llmModel.value = learning.settings?.llm_model || ''
}

function handleEmailBtn() {
  if (emailBtnMode.value === 'change' && emailDisabled.value) {
    emailDisabled.value = false
    emailInput.value = ''
    emailBtnText.value = '保存'
    emailBtnMode.value = 'save'
    return
  }
  bindEmail()
}

async function bindEmail() {
  try {
    await auth.updateEmail(emailInput.value.trim())
    const hasEmail = !!emailInput.value.trim()
    emailDisabled.value = hasEmail
    emailBtnText.value = hasEmail ? '换绑' : '绑定'
    emailBtnMode.value = hasEmail ? 'change' : 'bind'
    emailSavedMsg.value = hasEmail ? '邮箱换绑成功!' : '邮箱绑定成功!'
    emailSaved.value = true
    setTimeout(() => emailSaved.value = false, 2000)
  } catch (e) {
    alert(e.message)
  }
}

async function saveLearningSettings() {
  await learning.saveSetting('daily_words', dailyWords.value)
  await learning.saveSetting('recognize_mode', recognizeModes.value.join(','))
  await learning.saveSetting('learn_mode', learnModes.value.join(','))
  learning.recognizeMode = recognizeModes.value.join(',')
  learning.learnMode = learnModes.value.join(',')
  learningSaved.value = true
  setTimeout(() => learningSaved.value = false, 2000)
}

async function toggleBook(book) {
  if (book.is_active) return
  await wordBooks.activateBook(book.id)
}

async function openWordList(book) {
  wlBookId.value = book.id
  wlBookName.value = book.name
  wlSearch.value = ''
  wlDetailWord.value = null
  wlShowDetail.value = false
  pushPage('word-list')
  const data = await api(`words/all-by-book?word_book_id=${book.id}`)
  wlWords.value = data.words || []
}

const wlFiltered = computed(() => {
  const q = wlSearch.value.trim().toLowerCase()
  if (!q) return wlWords.value
  return wlWords.value.filter(w =>
    w.word.toLowerCase().includes(q) ||
    (w.meaning_cn && w.meaning_cn.toLowerCase().includes(q))
  )
})

const wlGrouped = computed(() => {
  const list = wlFiltered.value
  const groups = []
  let currentLetter = ''
  let currentGroup = null
  for (const w of list) {
    const letter = w.word[0]?.toUpperCase() || '#'
    if (letter !== currentLetter) {
      currentLetter = letter
      currentGroup = { letter, words: [] }
      groups.push(currentGroup)
    }
    currentGroup.words.push(w)
  }
  return groups
})

const wlLetters = computed(() => wlGrouped.value.map(g => g.letter))

function wlScrollTo(letter) {
  const el = document.getElementById('wl-letter-' + letter)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function wlShowWordDetail(id) {
  const word = await api('words/' + id)
  wlDetailWord.value = word
  wlLlmOutput.value = ''
  wlShowDetail.value = true
}

async function wlLLMAction(id, action) {
  wlLlmOutput.value = '<div style="color:var(--text-secondary);text-align:center;padding:8px">加载中...</div>'
  try {
    const result = await api(`llm/quick-actions/${id}?action=${action}`, { method: 'POST' })
    if (!result.ok) {
      wlLlmOutput.value = `<div style="color:var(--danger)">${result.error || '请求失败'}</div>`
      return
    }
    wlLlmOutput.value = `<pre style="white-space:pre-wrap;font-size:13px;line-height:1.6;color:var(--text);background:var(--bg);padding:12px;border-radius:8px;overflow-x:auto">${JSON.stringify(result.data, null, 2)}</pre>`
  } catch (e) {
    wlLlmOutput.value = `<div style="color:var(--danger)">${e.message}</div>`
  }
}

function playAudio(url) {
  if (!url) return
  new Audio(url).play().catch(() => {})
}

async function saveLLMSettings() {
  await learning.saveSetting('llm_api_url', llmUrl.value)
  await learning.saveSetting('llm_api_key', llmKey.value)
  await learning.saveSetting('llm_model', llmModel.value)
  llmSaved.value = true
  setTimeout(() => llmSaved.value = false, 2000)
}

function closeOnOverlay(e) {
  if (e.target === e.currentTarget) show.value = false
}
</script>

<template>
  <div v-if="show" class="modal active" @click="closeOnOverlay">
    <div class="s-panel" @click.stop>
      <!-- Navbar -->
      <div class="s-navbar">
        <button class="s-back-btn" @click="popPage">
          <svg v-if="pageStack.length > 1" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
        <span class="s-nav-title">{{ navTitle }}</span>
        <span class="s-nav-spacer"></span>
      </div>

      <!-- Page content -->
      <div class="s-pages">
        <Transition :name="pageStack.length > 1 ? 's-push' : 's-pop'" mode="out-in">

          <!-- MENU page -->
          <div v-if="currentPage === 'menu'" key="menu" class="s-page">
            <div class="s-page-scroll">
              <!-- Profile card -->
              <div class="s-profile" @click="pushPage('user-info')">
                <span class="popup-avatar s-avatar">{{ auth.initial }}</span>
                <div class="s-profile-text">
                  <div class="s-profile-name">{{ auth.username }}</div>
                  <div class="s-profile-email">{{ auth.user?.email || '未绑定邮箱' }}</div>
                </div>
                <svg class="s-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
              </div>

              <!-- Menu group -->
              <div class="s-group">
                <div class="s-item" @click="pushPage('learning-settings')">
                  <div class="s-item-icon" style="background:#eef2ff;color:#4f46e5;">⚙</div>
                  <div class="s-item-body">
                    <div class="s-item-label">学习设置</div>
                    <div class="s-item-sub">每日 {{ dailyWords }} 词 · {{ recognizeModeOptions.find(o => o.value === recognizeMode)?.label }}</div>
                  </div>
                  <svg class="s-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
                </div>
                <div class="s-item" @click="pushPage('word-books')">
                  <div class="s-item-icon" style="background:#fef3c7;color:#92400e;">📚</div>
                  <div class="s-item-body">
                    <div class="s-item-label">单词本</div>
                    <div class="s-item-sub">管理你的词库</div>
                  </div>
                  <svg class="s-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
                </div>
                <div class="s-item" @click="pushPage('llm-settings')">
                  <div class="s-item-icon" style="background:#f0fdf4;color:#166534;">🤖</div>
                  <div class="s-item-body">
                    <div class="s-item-label">LLM 配置</div>
                    <div class="s-item-sub">{{ llmModel || '未配置' }}</div>
                  </div>
                  <svg class="s-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
                </div>
              </div>
            </div>
          </div>

          <!-- USER INFO page -->
          <div v-else-if="currentPage === 'user-info'" key="user-info" class="s-page">
            <div class="s-page-scroll">
              <div class="s-section">
                <div class="s-row">
                  <span class="s-row-label">用户名</span>
                  <span class="s-row-value muted">{{ auth.username }}</span>
                </div>
                <div class="s-row">
                  <span class="s-row-label">邮箱</span>
                  <div class="s-row-input">
                    <input type="email" v-model="emailInput" :disabled="emailDisabled" placeholder="输入邮箱" class="s-input-sm">
                    <button class="s-btn-sm" :class="emailBtnMode === 'bind' ? 'primary' : 'outline'" @click="handleEmailBtn">{{ emailBtnText }}</button>
                  </div>
                </div>
                <div class="s-row">
                  <span class="s-row-label">注册时间</span>
                  <span class="s-row-value muted">{{ auth.user?.created_at }}</span>
                </div>
              </div>
              <Transition name="s-fade">
                <div v-if="emailSaved" class="s-msg success">{{ emailSavedMsg }}</div>
              </Transition>
            </div>
          </div>

          <!-- LEARNING SETTINGS page -->
          <div v-else-if="currentPage === 'learning-settings'" key="learning-settings" class="s-page">
            <div class="s-page-scroll">
              <div class="s-section">
                <div class="s-row">
                  <span class="s-row-label">每日学习单词</span>
                  <div class="s-row-stepper">
                    <button class="s-stepper-btn" @click="dailyWords = Math.max(1, dailyWords - 5)">−</button>
                    <span class="s-stepper-val">{{ dailyWords }}</span>
                    <button class="s-stepper-btn" @click="dailyWords = Math.min(50, dailyWords + 5)">+</button>
                  </div>
                </div>
              </div>

              <div class="s-section-title">认识验证模式 <span class="s-section-hint">可多选，随机出题</span></div>
              <div class="s-chip-group">
                <button v-for="opt in recognizeModeOptions" :key="opt.value"
                  class="s-chip" :class="{ on: recognizeModes.includes(opt.value) }"
                  @click="toggleRecognizeMode(opt.value)">
                  <span class="s-chip-label">{{ opt.label }}</span>
                  <span class="s-chip-desc">{{ opt.desc }}</span>
                </button>
              </div>

              <div class="s-section-title">不认识练习模式 <span class="s-section-hint">可多选，随机出题</span></div>
              <div class="s-chip-group">
                <button v-for="opt in learnModeOptions" :key="opt.value"
                  class="s-chip" :class="{ on: learnModes.includes(opt.value) }"
                  @click="toggleLearnMode(opt.value)">
                  <span class="s-chip-label">{{ opt.label }}</span>
                  <span class="s-chip-desc">{{ opt.desc }}</span>
                </button>
              </div>

              <button class="s-action-btn" @click="saveLearningSettings">保存设置</button>
              <Transition name="s-fade">
                <div v-if="learningSaved" class="s-msg success">设置已保存!</div>
              </Transition>
            </div>
          </div>

          <!-- WORD BOOKS page -->
          <div v-else-if="currentPage === 'word-books'" key="word-books" class="s-page">
            <div class="s-page-scroll">
              <div class="s-book-list">
                <div v-for="book in wordBooks.allBooks" :key="book.id" class="s-book" :class="{ on: book.is_active }">
                  <div class="s-book-left" @click="openWordList(book)">
                    <span class="s-book-emoji">{{ book.icon }}</span>
                    <div class="s-book-body">
                      <div class="s-book-name">{{ book.name }}</div>
                      <div class="s-book-desc">{{ book.description }}</div>
                      <div class="s-book-count">{{ book.word_count }} 个单词</div>
                    </div>
                  </div>
                  <button class="s-book-toggle" :class="{ on: book.is_active }" @click.stop="toggleBook(book)">
                    {{ book.is_active ? '使用中' : '切换' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- WORD LIST page -->
          <div v-else-if="currentPage === 'word-list'" key="word-list" class="s-page">
            <div class="s-page-scroll wl-page">
              <input v-model="wlSearch" placeholder="搜索单词或释义..." class="wl-search">
              <div class="wl-body">
                <div class="wl-list">
                  <div v-for="group in wlGrouped" :key="group.letter" class="wl-group">
                    <div :id="'wl-letter-' + group.letter" class="wl-letter-header">{{ group.letter }}</div>
                    <div v-for="w in group.words" :key="w.id" class="wl-word-item" @click="wlShowWordDetail(w.id)">
                      <span class="wl-word">{{ w.word }}</span>
                      <span class="wl-meaning">{{ (w.meanings && w.meanings[0]?.meaning_cn) || w.meaning_cn }}</span>
                    </div>
                  </div>
                  <div v-if="wlGrouped.length === 0" class="wl-empty">没有找到匹配的单词</div>
                </div>
                <div class="wl-alpha-bar" v-if="wlLetters.length > 0">
                  <span v-for="l in wlLetters" :key="l" class="wl-alpha-item" @click="wlScrollTo(l)">{{ l }}</span>
                </div>
              </div>
            </div>
            <!-- Word detail popup -->
            <div v-if="wlShowDetail && wlDetailWord" class="wl-detail-overlay" @click.self="wlShowDetail = false">
              <div class="wl-detail-card">
                <button class="wl-detail-close" @click="wlShowDetail = false">&times;</button>
                <div class="wl-detail-word">{{ wlDetailWord.word }}</div>
                <div class="wl-detail-phonetics">
                  <span v-if="wlDetailWord.phonetic_uk" class="wl-phonetic">🇬🇧 {{ wlDetailWord.phonetic_uk }}<button v-if="wlDetailWord.audio_uk" class="card-play-btn mini" @click="playAudio(wlDetailWord.audio_uk)"><span class="play-icon">&#9654;</span></button></span>
                  <span v-if="wlDetailWord.phonetic_us" class="wl-phonetic">🇺🇸 {{ wlDetailWord.phonetic_us }}<button v-if="wlDetailWord.audio_us" class="card-play-btn mini" @click="playAudio(wlDetailWord.audio_us)"><span class="play-icon">&#9654;</span></button></span>
                  <span v-if="!wlDetailWord.phonetic_uk && !wlDetailWord.phonetic_us && wlDetailWord.phonetic" class="wl-phonetic">{{ wlDetailWord.phonetic }}</span>
                </div>
                <div class="wl-detail-meanings">
                  <div v-for="(m, i) in (wlDetailWord.meanings || [])" :key="i" class="wl-detail-m">
                    <span class="card-pos">{{ m.pos }}</span>
                    <span class="wl-detail-m-text">{{ m.meaning_cn }}</span>
                  </div>
                  <div v-if="!wlDetailWord.meanings?.length && wlDetailWord.meaning_cn" class="wl-detail-m">
                    <span class="card-pos">{{ wlDetailWord.pos }}</span>
                    <span class="wl-detail-m-text">{{ wlDetailWord.meaning_cn }}</span>
                  </div>
                </div>
                <div class="wl-detail-forms" v-if="wlDetailWord.plural || wlDetailWord.past_tense || wlDetailWord.past_participle || wlDetailWord.present_participle || wlDetailWord.comparative || wlDetailWord.superlative || wlDetailWord.third_person">
                  <span v-if="wlDetailWord.plural" class="card-form-tag">复数: {{ wlDetailWord.plural }}</span>
                  <span v-if="wlDetailWord.past_tense" class="card-form-tag">过去式: {{ wlDetailWord.past_tense }}</span>
                  <span v-if="wlDetailWord.past_participle" class="card-form-tag">过去分词: {{ wlDetailWord.past_participle }}</span>
                  <span v-if="wlDetailWord.present_participle" class="card-form-tag">现在分词: {{ wlDetailWord.present_participle }}</span>
                  <span v-if="wlDetailWord.comparative" class="card-form-tag">比较级: {{ wlDetailWord.comparative }}</span>
                  <span v-if="wlDetailWord.superlative" class="card-form-tag">最高级: {{ wlDetailWord.superlative }}</span>
                  <span v-if="wlDetailWord.third_person" class="card-form-tag">三单: {{ wlDetailWord.third_person }}</span>
                </div>
                <div v-if="wlDetailWord.example_en" class="wl-detail-example">{{ wlDetailWord.example_en }}<br>{{ wlDetailWord.example_cn }}</div>
                <div class="wl-detail-actions">
                  <button class="s-btn-sm" @click="wlLLMAction(wlDetailWord.id, 'examples')">生成例句</button>
                  <button class="s-btn-sm" @click="wlLLMAction(wlDetailWord.id, 'explain')">详细解释</button>
                  <button class="s-btn-sm" @click="wlLLMAction(wlDetailWord.id, 'quiz')">小测验</button>
                </div>
                <div v-html="wlLlmOutput" style="margin-top:12px"></div>
              </div>
            </div>
          </div>

          <!-- LLM SETTINGS page -->
          <div v-else-if="currentPage === 'llm-settings'" key="llm-settings" class="s-page">
            <div class="s-page-scroll">
              <div class="s-section">
                <div class="s-row stack">
                  <span class="s-row-label">API 地址</span>
                  <input type="text" v-model="llmUrl" placeholder="https://api.deepseek.com/v1/chat/completions" class="s-input-full">
                </div>
                <div class="s-row stack">
                  <span class="s-row-label">API Key</span>
                  <input type="password" v-model="llmKey" placeholder="输入你的 API Key" class="s-input-full">
                </div>
                <div class="s-row stack">
                  <span class="s-row-label">模型名称</span>
                  <input type="text" v-model="llmModel" placeholder="deepseek-chat" class="s-input-full">
                </div>
              </div>
              <button class="s-action-btn" @click="saveLLMSettings">保存配置</button>
              <Transition name="s-fade">
                <div v-if="llmSaved" class="s-msg success">配置已保存!</div>
              </Transition>
            </div>
          </div>

        </Transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ==================== Panel ==================== */
.s-panel {
  background: var(--bg);
  max-width: 480px;
  width: 92%;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  max-height: 88vh;
  overflow: hidden;
}

/* ==================== Navbar ==================== */
.s-navbar {
  display: flex;
  align-items: center;
  padding: 12px 10px;
  background: var(--surface);
  flex-shrink: 0;
  border-bottom: 1px solid var(--border);
}

.s-back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  transition: background 0.2s;
  flex-shrink: 0;
}

.s-back-btn:hover { background: var(--bg); }
.s-back-btn:active { background: var(--border); }

.s-nav-title {
  flex: 1;
  text-align: center;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.3px;
}

.s-nav-spacer { width: 38px; flex-shrink: 0; }

/* ==================== Pages container ==================== */
.s-pages {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.s-page {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
}

.s-page-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px 16px 32px;
  -webkit-overflow-scrolling: touch;
}

/* ==================== Profile card ==================== */
.s-profile {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  background: var(--surface);
  border-radius: 14px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
  margin-bottom: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.s-profile:active { transform: scale(0.98); }

.s-avatar { width: 54px; height: 54px; font-size: 24px; flex-shrink: 0; }

.s-profile-text { flex: 1; min-width: 0; }
.s-profile-name { font-size: 17px; font-weight: 700; color: var(--text); }
.s-profile-email {
  font-size: 13px; color: var(--text-secondary); margin-top: 3px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.s-chevron { color: #c0c8d4; flex-shrink: 0; }

/* ==================== Menu group ==================== */
.s-group {
  background: var(--surface);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.s-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid #f1f5f9;
}

.s-item:last-child { border-bottom: none; }
.s-item:active { background: #f8fafc; }

.s-item-icon {
  width: 36px; height: 36px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 17px; flex-shrink: 0;
}

.s-item-body { flex: 1; min-width: 0; }
.s-item-label { font-size: 15px; font-weight: 600; color: var(--text); }
.s-item-sub { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }

/* ==================== Section & rows ==================== */
.s-section {
  background: var(--surface);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  margin-bottom: 8px;
}

.s-section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 16px 0 6px;
}

.s-section-hint {
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  font-size: 11px;
  opacity: 0.7;
}

/* Chip group */
.s-chip-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.s-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 16px;
  border: 1.5px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  cursor: pointer;
  transition: all 0.2s;
  min-width: 72px;
}

.s-chip:hover { border-color: #c7d2fe; background: #fafaff; }

.s-chip.on {
  border-color: var(--primary);
  background: #eef2ff;
  box-shadow: 0 0 0 1px var(--primary);
}

.s-chip-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.s-chip.on .s-chip-label { color: var(--primary); }

.s-chip-desc {
  font-size: 10px;
  color: var(--text-secondary);
  line-height: 1.2;
}

.s-chip.on .s-chip-desc { color: var(--primary-light); }

.s-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  gap: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.s-row:last-child { border-bottom: none; }

.s-row.clickable { cursor: pointer; transition: background 0.12s; }
.s-row.clickable:active { background: #f8fafc; }

.s-row.stack { flex-direction: column; align-items: stretch; }

.s-row-label {
  font-size: 15px;
  color: var(--text);
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.s-row-value { font-size: 14px; color: var(--text); font-weight: 500; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.s-row-value.muted { color: var(--text-secondary); font-weight: 400; }

/* Email row inline */
.s-row-input { display: flex; align-items: center; gap: 8px; }

.s-input-sm {
  padding: 7px 10px;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  width: 150px;
  background: var(--surface);
  color: var(--text);
  transition: border-color 0.2s;
}

.s-input-sm:focus { border-color: var(--primary); }
.s-input-sm:disabled { background: var(--bg); color: var(--text-secondary); }

.s-btn-sm {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  border: 1.5px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
}

.s-btn-sm.primary {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.s-btn-sm:hover { opacity: 0.85; }

/* Full-width input */
.s-input-full {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  background: var(--surface);
  color: var(--text);
  margin-top: 6px;
  transition: border-color 0.2s;
}

.s-input-full:focus { border-color: var(--primary); }

/* Check mark */
.s-check {
  color: var(--primary);
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

/* Stepper */
.s-row-stepper {
  display: flex;
  align-items: center;
  gap: 2px;
  background: var(--bg);
  border-radius: 10px;
  overflow: hidden;
}

.s-stepper-btn {
  width: 36px; height: 36px;
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.s-stepper-btn:active { background: var(--border); }

.s-stepper-val {
  min-width: 36px;
  text-align: center;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

/* Action button */
.s-action-btn {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 12px;
  background: var(--primary);
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
  margin-top: 8px;
}

.s-action-btn:active { transform: scale(0.98); opacity: 0.9; }

/* Toast message */
.s-msg {
  text-align: center;
  padding: 10px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  margin-top: 8px;
}

.s-msg.success { color: var(--success); }

/* ==================== Word Books ==================== */
.s-book-list { display: flex; flex-direction: column; gap: 12px; }

.s-book {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: var(--surface);
  border-radius: 14px;
  border: 1.5px solid #f1f5f9;
  transition: all 0.25s;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  gap: 12px;
}

.s-book.on { border-color: #bbf7d0; background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%); }

.s-book-left { display: flex; align-items: center; gap: 14px; flex: 1; min-width: 0; }
.s-book-emoji { font-size: 30px; flex-shrink: 0; }
.s-book-body { min-width: 0; }
.s-book-name { font-size: 15px; font-weight: 600; color: var(--text); }
.s-book-desc { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.s-book-count { font-size: 11px; color: var(--text-secondary); margin-top: 3px; }

.s-book-toggle {
  padding: 7px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  border: 1.5px solid var(--primary);
  background: transparent;
  color: var(--primary);
  cursor: pointer;
  transition: all 0.25s;
  white-space: nowrap;
  flex-shrink: 0;
}

.s-book-toggle:hover { background: #eef2ff; }

.s-book-toggle.on {
  background: var(--success);
  color: white;
  border-color: var(--success);
  cursor: default;
}

.s-book-left { cursor: pointer; }

/* ==================== Word List ==================== */
.wl-page { display: flex; flex-direction: column; }

.wl-search {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid var(--border);
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  background: var(--surface);
  color: var(--text);
  margin-bottom: 12px;
  box-sizing: border-box;
}

.wl-search:focus { border-color: var(--primary); }

.wl-body { display: flex; gap: 0; flex: 1; min-height: 0; }

.wl-list { flex: 1; overflow-y: auto; min-width: 0; }

.wl-group { margin-bottom: 4px; }

.wl-letter-header {
  position: sticky;
  top: 0;
  background: var(--bg);
  font-size: 13px;
  font-weight: 700;
  color: var(--primary);
  padding: 6px 0 4px;
  z-index: 1;
}

.wl-word-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 9px 4px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
  transition: background 0.12s;
}

.wl-word-item:active { background: #f8fafc; }

.wl-word {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  flex-shrink: 0;
  min-width: 80px;
}

.wl-meaning {
  font-size: 13px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wl-empty {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 14px;
}

/* Alphabet bar */
.wl-alpha-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px 2px;
  gap: 0;
  flex-shrink: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.wl-alpha-item {
  font-size: 10px;
  font-weight: 600;
  color: var(--primary);
  padding: 1px 5px;
  cursor: pointer;
  line-height: 1.3;
  border-radius: 4px;
  transition: background 0.15s;
}

.wl-alpha-item:active { background: #eef2ff; }

/* Word detail overlay */
.wl-detail-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  padding: 20px;
}

.wl-detail-card {
  background: var(--surface);
  border-radius: 16px;
  padding: 24px;
  max-width: 380px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.wl-detail-close {
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
}

.wl-detail-word {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.wl-detail-phonetics {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.wl-phonetic {
  color: #64748b;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.wl-detail-meanings {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.wl-detail-m {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.wl-detail-m-text {
  font-size: 15px;
  font-weight: 500;
  color: var(--text);
}

.wl-detail-forms {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.wl-detail-example {
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
  margin-top: 8px;
}

.wl-detail-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
}

/* ==================== Transitions ==================== */
.s-push-enter-active { transition: transform 0.3s cubic-bezier(0.16,1,0.3,1), opacity 0.3s ease; }
.s-push-leave-active { transition: transform 0.2s ease, opacity 0.15s ease; }
.s-push-enter-from { transform: translateX(60px); opacity: 0; }
.s-push-leave-to { transform: translateX(-20px); opacity: 0.5; }

.s-pop-enter-active { transition: transform 0.3s cubic-bezier(0.16,1,0.3,1), opacity 0.3s ease; }
.s-pop-leave-active { transition: transform 0.2s ease, opacity 0.15s ease; }
.s-pop-enter-from { transform: translateX(-20px); opacity: 0.5; }
.s-pop-leave-to { transform: translateX(60px); opacity: 0; }

.s-fade-enter-active { transition: opacity 0.3s ease; }
.s-fade-leave-active { transition: opacity 0.2s ease; }
.s-fade-enter-from, .s-fade-leave-to { opacity: 0; }

/* ==================== Mobile ==================== */
@media (max-width: 768px) {
  .s-panel {
    max-width: 100%;
    width: 100%;
    max-height: 100vh;
    max-height: 100dvh;
    border-radius: 0;
    height: 100vh;
    height: 100dvh;
  }

  .s-navbar {
    padding-top: calc(8px + env(safe-area-inset-top));
  }

  .s-input-sm { width: 130px; }
}
</style>

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
const recognizeMode = ref('direct')
const learnMode = ref('flip')
const recognizeModeOptions = [
  { value: 'direct', label: '直接标记' },
  { value: 'select_meaning', label: '选释义' },
  { value: 'spell', label: '拼写' },
  { value: 'select_word', label: '选单词' },
  { value: 'dictation', label: '听写' },
]
const learnModeOptions = [
  { value: 'flip', label: '翻卡查看' },
  { value: 'select_meaning', label: '选释义' },
  { value: 'spell', label: '拼写' },
  { value: 'select_word', label: '选单词' },
  { value: 'dictation', label: '听写' },
]
const learningSaved = ref(false)

// LLM settings
const llmUrl = ref('')
const llmKey = ref('')
const llmModel = ref('')
const llmSaved = ref(false)

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
  recognizeMode.value = learning.settings?.recognize_mode || 'direct'
  learnMode.value = learning.settings?.learn_mode || 'flip'
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
  await learning.saveSetting('recognize_mode', recognizeMode.value)
  await learning.saveSetting('learn_mode', learnMode.value)
  learning.recognizeMode = recognizeMode.value
  learning.learnMode = learnMode.value
  learningSaved.value = true
  setTimeout(() => learningSaved.value = false, 2000)
}

async function toggleBook(book) {
  if (book.is_active) {
    await wordBooks.deactivateBook(book.id)
  } else {
    await wordBooks.activateBook(book.id)
  }
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

              <div class="s-section-title">认识验证模式</div>
              <div class="s-section">
                <div v-for="opt in recognizeModeOptions" :key="opt.value" class="s-row clickable" @click="recognizeMode = opt.value">
                  <span class="s-row-label">{{ opt.label }}</span>
                  <div v-if="recognizeMode === opt.value" class="s-check">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </div>
                </div>
              </div>

              <div class="s-section-title">不认识练习模式</div>
              <div class="s-section">
                <div v-for="opt in learnModeOptions" :key="opt.value" class="s-row clickable" @click="learnMode = opt.value">
                  <span class="s-row-label">{{ opt.label }}</span>
                  <div v-if="learnMode === opt.value" class="s-check">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </div>
                </div>
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
                  <div class="s-book-left">
                    <span class="s-book-emoji">{{ book.icon }}</span>
                    <div class="s-book-body">
                      <div class="s-book-name">{{ book.name }}</div>
                      <div class="s-book-desc">{{ book.description }}</div>
                      <div class="s-book-count">{{ book.word_count }} 个单词</div>
                    </div>
                  </div>
                  <button class="s-book-toggle" :class="{ on: book.is_active }" @click="toggleBook(book)">
                    {{ book.is_active ? '已激活' : '激活' }}
                  </button>
                </div>
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
  padding: 16px 16px 6px;
}

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
  border: 1.5px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.25s;
  white-space: nowrap;
  flex-shrink: 0;
}

.s-book-toggle.on {
  background: var(--success);
  color: white;
  border-color: var(--success);
  box-shadow: 0 2px 8px rgba(16,185,129,0.3);
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

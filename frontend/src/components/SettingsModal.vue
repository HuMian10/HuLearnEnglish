<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useLearningStore } from '../stores/learning'
import { useWordBooksStore } from '../stores/wordBooks'
import { api } from '../api'

const auth = useAuthStore()
const learning = useLearningStore()
const wordBooks = useWordBooksStore()

const show = ref(false)
const activeTab = ref('user-info')

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
  if (val) switchTab('user-info')
})

watch(show, (val) => {
  emit('update:modelValue', val)
})

function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'user-info') loadUserInfo()
  if (tab === 'learning-settings') loadLearningSettings()
  if (tab === 'word-books') loadWordBooks()
  if (tab === 'llm-settings') loadLLMSettings()
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
    <div class="settings-modal-content">
      <button class="modal-close" @click="show = false">&times;</button>

      <div class="settings-modal-header">
        <span class="popup-avatar settings-modal-avatar">{{ auth.initial }}</span>
        <div class="settings-modal-header-text">
          <div class="settings-modal-username">{{ auth.username }}</div>
          <div class="settings-modal-email">{{ auth.user?.email || '未绑定邮箱' }}</div>
        </div>
      </div>

      <div class="settings-modal-tabs">
        <button class="settings-tab" :class="{ active: activeTab === 'user-info' }" @click="switchTab('user-info')">👤 用户信息</button>
        <button class="settings-tab" :class="{ active: activeTab === 'learning-settings' }" @click="switchTab('learning-settings')">⚙ 学习设置</button>
        <button class="settings-tab" :class="{ active: activeTab === 'word-books' }" @click="switchTab('word-books')">📚 单词本</button>
        <button class="settings-tab" :class="{ active: activeTab === 'llm-settings' }" @click="switchTab('llm-settings')">🤖 LLM 配置</button>
      </div>

      <div class="settings-modal-body">
        <!-- User Info -->
        <div v-if="activeTab === 'user-info'">
          <div class="setting-item">
            <label>用户名</label>
            <input type="text" :value="auth.username" disabled>
          </div>
          <div class="setting-item">
            <label>邮箱</label>
            <div class="email-row">
              <input type="email" v-model="emailInput" :disabled="emailDisabled" placeholder="输入邮箱地址">
              <button
                class="btn email-action-btn"
                :class="emailBtnMode === 'bind' ? 'btn-primary' : 'btn-outline'"
                @click="handleEmailBtn"
              >{{ emailBtnText }}</button>
            </div>
          </div>
          <div class="setting-item">
            <label>注册时间</label>
            <input type="text" :value="auth.user?.created_at" disabled>
          </div>
          <div v-if="emailSaved" class="success-msg">{{ emailSavedMsg }}</div>
        </div>

        <!-- Learning Settings -->
        <div v-if="activeTab === 'learning-settings'">
          <div class="setting-item">
            <label>每日学习单词数</label>
            <input type="number" v-model.number="dailyWords" min="1" max="50">
          </div>
          <div class="setting-item">
            <label>认识验证模式 <span style="font-weight:400;color:#94a3b8">(点击"认识"后的验证方式)</span></label>
            <select v-model="recognizeMode">
              <option v-for="opt in recognizeModeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <div class="setting-item">
            <label>不认识练习模式 <span style="font-weight:400;color:#94a3b8">(点击"不认识"后的练习方式)</span></label>
            <select v-model="learnMode">
              <option v-for="opt in learnModeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <button class="btn btn-primary settings-save-btn" @click="saveLearningSettings">保存</button>
          <div v-if="learningSaved" class="success-msg">设置已保存!</div>
        </div>

        <!-- LLM Settings -->
        <div v-if="activeTab === 'llm-settings'">
          <div class="setting-item">
            <label>API 地址</label>
            <input type="text" v-model="llmUrl" placeholder="https://api.deepseek.com/v1/chat/completions">
          </div>
          <div class="setting-item">
            <label>API Key</label>
            <input type="password" v-model="llmKey" placeholder="输入你的 API Key">
          </div>
          <div class="setting-item">
            <label>模型名称</label>
            <input type="text" v-model="llmModel" placeholder="deepseek-chat">
          </div>
          <button class="btn btn-primary settings-save-btn" @click="saveLLMSettings">保存</button>
          <div v-if="llmSaved" class="success-msg">配置已保存!</div>
        </div>

        <!-- Word Books -->
        <div v-if="activeTab === 'word-books'">
          <div class="word-book-list">
            <div v-for="book in wordBooks.allBooks" :key="book.id" class="word-book-card" :class="{ active: book.is_active }">
              <div class="word-book-icon">{{ book.icon }}</div>
              <div class="word-book-info">
                <div class="word-book-name">{{ book.name }}</div>
                <div class="word-book-desc">{{ book.description }}</div>
                <div class="word-book-count">{{ book.word_count }} 个单词</div>
              </div>
              <button
                class="btn btn-small word-book-toggle"
                :class="book.is_active ? 'btn-success' : 'btn-outline'"
                @click="toggleBook(book)"
              >{{ book.is_active ? '已激活' : '激活' }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-modal-content {
  background: var(--surface);
  border-radius: var(--radius);
  max-width: 520px;
  width: 90%;
  position: relative;
  max-height: 85vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.settings-modal-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--border);
}

.settings-modal-avatar {
  width: 48px;
  height: 48px;
  font-size: 22px;
  flex-shrink: 0;
}

.settings-modal-header-text { flex: 1; min-width: 0; }
.settings-modal-username { font-size: 18px; font-weight: 700; color: var(--text); }
.settings-modal-email { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }

.settings-modal-tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
  padding: 0 16px;
}

.settings-tab {
  padding: 12px 16px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.2s;
  white-space: nowrap;
}

.settings-tab:hover { color: var(--primary); }
.settings-tab.active { color: var(--primary); border-bottom-color: var(--primary); font-weight: 600; }

.settings-modal-body {
  padding: 24px;
  flex: 1;
  overflow-y: auto;
}

.settings-save-btn {
  width: 100%;
  justify-content: center;
  margin-top: 8px;
}

@media (max-width: 768px) {
  .settings-modal-content {
    max-width: 100%;
    width: 100%;
    max-height: 100vh;
    border-radius: 0;
    height: 100vh;
  }
  .settings-modal-tabs { overflow-x: auto; }
}

.word-book-list { display: flex; flex-direction: column; gap: 12px; }

.word-book-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid var(--border);
  transition: all 0.2s;
}

.word-book-card.active { border-color: var(--success); background: #f0fdf4; }

.word-book-icon { font-size: 28px; flex-shrink: 0; }

.word-book-info { flex: 1; min-width: 0; }

.word-book-name { font-size: 15px; font-weight: 600; color: var(--text); }

.word-book-desc { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }

.word-book-count { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }

.word-book-toggle { flex-shrink: 0; }

.setting-item select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  background: var(--surface);
  color: var(--text);
  appearance: auto;
}
.setting-item select:focus { border-color: var(--primary); }

</style>

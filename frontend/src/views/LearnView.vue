<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'
import { useLearningStore } from '../stores/learning'
import { useRoute } from 'vue-router'

const learning = useLearningStore()
const route = useRoute()

const words = ref([])
const index = ref(0)
const current = ref(null)
const done = ref(false)

// Phase: front → recognize_quiz → show_answer → practice_quiz
const phase = ref('front')
const wordMastered = ref(false)
// After show_answer, which action to show
const answerAction = ref('') // 'mark_known' | 'practice'
const showChat = ref(false)
const chatMessages = ref([])
const chatInput = ref('')
const llmOutput = ref('')

// Quiz state
const quizType = ref('')
const quizOptions = ref([])
const spellInput = ref('')
const dictationInput = ref('')
const showHint = ref(false)
const answered = ref(false)
const selectedIdx = ref(null)
const answerCorrect = ref(null)
const distractors = ref([])

const QUIZ_ORDER = ['select_meaning', 'select_word', 'spell', 'dictation']

const recognizeModes = computed(() => {
  const raw = learning.recognizeMode || 'direct'
  const modes = raw.includes(',') ? raw.split(',') : [raw]
  return sortByOrder(modes)
})
const learnModes = computed(() => {
  const raw = learning.learnMode || 'flip'
  const modes = raw.includes(',') ? raw.split(',') : [raw]
  return sortByOrder(modes)
})

function sortByOrder(modes) {
  const special = modes.filter(m => !QUIZ_ORDER.includes(m))
  const quizModes = QUIZ_ORDER.filter(o => modes.includes(o))
  return [...special, ...quizModes]
}

// Queue of quiz types to go through for the current word
const quizQueue = ref([])
const quizQueueIndex = ref(0)

const isLastInQueue = computed(() => quizQueueIndex.value >= quizQueue.value.length - 1)

onMounted(async () => {
  await learning.fetchSettings()
  loadLearn()
})

watch(() => route.path, (val) => { if (val === '/learn') loadLearn() })

async function loadLearn() {
  const plan = await api('plan/today')
  if (!plan.plan || !plan.remaining || plan.remaining.length === 0) {
    done.value = true
    return
  }
  words.value = plan.remaining
  index.value = 0
  done.value = false
  showWord()
}

async function continueLearn() {
  const plan = await api('plan/continue', { method: 'POST' })
  if (!plan.remaining || plan.remaining.length === 0) {
    done.value = true
    return
  }
  words.value = plan.remaining
  index.value = 0
  done.value = false
  showWord()
}

function showWord() {
  if (index.value >= words.value.length) {
    done.value = true
    return
  }
  current.value = words.value[index.value]
  phase.value = 'front'
  answerAction.value = ''
  wordMastered.value = false
  showChat.value = false
  llmOutput.value = ''
  chatMessages.value = []
  resetQuiz()
  distractors.value = []
  fetchDistractors()
}

function resetQuiz() {
  quizType.value = ''
  quizOptions.value = []
  spellInput.value = ''
  dictationInput.value = ''
  showHint.value = false
  answered.value = false
  selectedIdx.value = null
  answerCorrect.value = null
}

async function fetchDistractors() {
  if (!current.value) return
  try {
    const data = await api(`words/distractors?word_id=${current.value.id}&count=3`)
    distractors.value = data
  } catch {
    distractors.value = []
  }
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

function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

function buildOptionList(type) {
  if (!current.value || distractors.value.length === 0) return []
  const correct = type === 'meaning'
    ? { text: getMeaningText(current.value), correct: true }
    : { text: current.value.word, correct: true }
  const wrongList = distractors.value.map(d => ({
    text: type === 'meaning' ? getMeaningText(d) : d.word,
    correct: false,
  }))
  return shuffleArray([correct, ...wrongList])
}

// === Flow ===

function onRecognize() {
  const modes = recognizeModes.value.filter(m => m !== 'direct')
  if (modes.length === 0) {
    answerAction.value = 'mark_known'
    phase.value = 'show_answer'
    return
  }
  quizQueue.value = [...modes]
  quizQueueIndex.value = 0
  startQuiz(quizQueue.value[0])
  phase.value = 'recognize_quiz'
}

function onDontKnow() {
  const practiceModes = learnModes.value.filter(m => m !== 'flip')
  answerAction.value = practiceModes.length > 0 ? 'practice' : 'mark_unknown'
  phase.value = 'show_answer'
}

function startPractice() {
  resetQuiz()
  const practiceModes = learnModes.value.filter(m => m !== 'flip')
  quizQueue.value = [...practiceModes]
  quizQueueIndex.value = 0
  startQuiz(quizQueue.value[0])
  phase.value = 'practice_quiz'
}

function nextInQueue() {
  quizQueueIndex.value++
  if (quizQueueIndex.value < quizQueue.value.length) {
    resetQuiz()
    startQuiz(quizQueue.value[quizQueueIndex.value])
    return true
  }
  return false
}

function startQuiz(type) {
  quizType.value = type
  answered.value = false
  selectedIdx.value = null
  answerCorrect.value = null
  spellInput.value = ''
  dictationInput.value = ''
  showHint.value = false
  if (type === 'select_meaning') {
    quizOptions.value = buildOptionList('meaning')
  } else if (type === 'select_word') {
    quizOptions.value = buildOptionList('word')
  } else {
    quizOptions.value = []
  }
  if (type === 'dictation') {
    setTimeout(() => autoPlayAudio(), 300)
  }
}

function autoPlayAudio() {
  if (!current.value) return
  const url = current.value.audio_us || current.value.audio_uk
  if (url) new Audio(url).play().catch(() => {})
}

function replayAudio() {
  autoPlayAudio()
}

function checkDictation() {
  if (answered.value || !current.value) return
  answered.value = true
  const correct = dictationInput.value.trim().toLowerCase() === current.value.word.toLowerCase()
  answerCorrect.value = correct
  afterQuizAnswer(correct)
}

function handleOptionSelect(opt, idx) {
  if (answered.value) return
  answered.value = true
  selectedIdx.value = idx
  answerCorrect.value = opt.correct
  afterQuizAnswer(opt.correct)
}

function checkSpell() {
  if (answered.value || !current.value) return
  answered.value = true
  const correct = spellInput.value.trim().toLowerCase() === current.value.word.toLowerCase()
  answerCorrect.value = correct
  afterQuizAnswer(correct)
}

function afterQuizAnswer(correct) {
  // Just record the result, don't auto-advance.
  // User clicks a button to proceed (handled by onQuizNext).
}

function onQuizNext() {
  if (phase.value === 'recognize_quiz') {
    if (!answerCorrect.value) {
      const practiceModes = learnModes.value.filter(m => m !== 'flip')
      answerAction.value = practiceModes.length > 0 ? 'practice' : 'mark_unknown'
      phase.value = 'show_answer'
      return
    }
    const hasMore = nextInQueue()
    if (!hasMore) {
      answerAction.value = 'mark_known'
      phase.value = 'show_answer'
    }
  } else if (phase.value === 'practice_quiz') {
    const hasMore = nextInQueue()
    if (!hasMore) {
      answerAction.value = 'mark_known'
      phase.value = 'show_answer'
    }
  }
}

async function markWord(correct) {
  if (!current.value) return
  await api('learning/review', {
    method: 'POST',
    body: JSON.stringify({ word_id: current.value.id, correct }),
  })
  index.value++
  showWord()
}

async function markMastered() {
  if (!current.value || wordMastered.value) return
  wordMastered.value = true
  await api('learning/master', {
    method: 'POST',
    body: JSON.stringify({ word_id: current.value.id }),
  })
  index.value++
  showWord()
}

// === LLM ===

async function llmQuickAction(action) {
  if (!current.value) return
  llmOutput.value = '<div class="llm-loading">加载中...</div>'
  showChat.value = false
  try {
    const result = await api(`llm/quick-actions/${current.value.id}?action=${action}`, { method: 'POST' })
    if (!result.ok) {
      llmOutput.value = `<div class="llm-error">${result.error || '请求失败'}</div>`
      return
    }
    llmOutput.value = renderLLMData(result.action, result.data, current.value.word)
  } catch (e) {
    llmOutput.value = `<div class="llm-error">${e.message}</div>`
  }
}

function escHtml(str) {
  if (!str) return ''
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')
}

function highlightWord(text, word) {
  if (!word) return text
  const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(new RegExp(`(${escaped})`, 'gi'), '<span class="llm-highlight">$1</span>')
}

function renderLLMData(action, data, word) {
  if (action === 'examples') return renderExamples(data, word)
  if (action === 'explain') return renderExplain(data)
  if (action === 'quiz') return renderQuiz(data, word)
  return `<pre>${JSON.stringify(data, null, 2)}</pre>`
}

function renderExamples(data, word) {
  const examples = data.examples || []
  if (!examples.length) return '<div class="llm-error">未生成例句</div>'
  return `<div class="llm-examples">${examples.map(ex => `
    <div class="llm-example-item">
      <div class="llm-example-en">${highlightWord(escHtml(ex.en), word)}</div>
      <div class="llm-example-cn">${escHtml(ex.cn)}</div>
    </div>`).join('')}</div>`
}

function renderExplain(data) {
  let html = '<div class="llm-explain">'
  if (data.meaning) html += `<div class="llm-explain-section"><div class="llm-explain-label">释义</div><div class="llm-explain-text">${escHtml(data.meaning)}</div></div>`
  if (data.nuances) html += `<div class="llm-explain-section"><div class="llm-explain-label">细微差别</div><div class="llm-explain-text">${escHtml(data.nuances)}</div></div>`
  if (data.collocations?.length) html += `<div class="llm-explain-section"><div class="llm-explain-label">常见搭配</div><div class="llm-explain-tags">${data.collocations.map(c => `<span class="llm-collocation-tag">${escHtml(c)}</span>`).join('')}</div></div>`
  if (data.common_mistakes) html += `<div class="llm-explain-section"><div class="llm-explain-label">常见错误</div><div class="llm-explain-text">${escHtml(data.common_mistakes)}</div></div>`
  html += '</div>'
  return html
}

function renderQuiz(data, word) {
  const quizzes = data.quizzes || []
  if (!quizzes.length) return '<div class="llm-error">未生成测验</div>'
  const quizId = 'q' + Date.now()
  return `<div class="llm-quiz">${quizzes.map((q, i) => {
    if (q.type === 'fill_blank') return renderFillBlank(q, i, quizId)
    if (q.type === 'choice') return renderChoice(q, i, quizId)
    return ''
  }).join('')}</div>`
}

function renderFillBlank(q, idx, prefix) {
  const inputId = `${prefix}-fill-${idx}`
  const resultId = `${prefix}-fill-result-${idx}`
  return `<div class="llm-quiz-item">
    <div class="llm-quiz-type">填空题</div>
    <div class="llm-quiz-question">${escHtml(q.question)}</div>
    <div class="llm-quiz-fill-row">
      <input type="text" class="llm-quiz-fill-input" id="${inputId}" placeholder="${escHtml(q.hint || '输入答案')}">
      <button class="btn btn-primary btn-small" onclick="(function(){var i=document.getElementById('${inputId}'),r=document.getElementById('${resultId}'),a='${q.answer}'.toLowerCase(),v=i.value.trim().toLowerCase();if(v===a){i.classList.add('correct');i.classList.remove('wrong');r.textContent='正确! ✓';r.style.color='#10b981'}else{i.classList.add('wrong');i.classList.remove('correct');r.textContent='正确答案: ${q.answer}';r.style.color='#ef4444'}})()">检查</button>
    </div>
    <div class="llm-quiz-answer-reveal" id="${resultId}"></div>
  </div>`
}

function renderChoice(q, idx, prefix) {
  const explId = `${prefix}-choice-expl-${idx}`
  const optFn = `${prefix}_checkChoice_${idx}`
  const script = `
  window.${optFn} = function(btn, optIdx) {
    var answer = '${q.answer}';
    var buttons = btn.parentElement.querySelectorAll('.llm-quiz-option');
    var selectedLetter = String.fromCharCode(65 + optIdx);
    var isCorrect = selectedLetter === answer;
    buttons.forEach(function(ob, i) {
      ob.classList.add('disabled');
      var letter = String.fromCharCode(65 + i);
      if (letter === answer) ob.classList.add('correct');
    });
    if (!isCorrect) btn.classList.add('wrong');
    var expl = document.getElementById('${explId}');
    if (expl) expl.style.display = '';
  }`
  return `<div class="llm-quiz-item">
    <div class="llm-quiz-type">选择题</div>
    <div class="llm-quiz-question">${escHtml(q.question)}</div>
    <div class="llm-quiz-options">
      ${(q.options || []).map((opt, oi) =>
        `<button class="llm-quiz-option" onclick="${optFn}(this,${oi})">${escHtml(opt)}</button>`
      ).join('')}
    </div>
    <div class="llm-quiz-explanation" id="${explId}" style="display:none">${escHtml(q.explanation || '')}</div>
    <script>${script}<\/script>
  </div>`
}

async function sendChat() {
  const msg = chatInput.value.trim()
  if (!msg || !current.value) return
  chatInput.value = ''
  chatMessages.value.push({ role: 'user', text: msg })

  try {
    const resp = await fetch('/api/llm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ word: current.value.word, message: msg }),
      credentials: 'include',
    })
    const reader = resp.body.getReader()
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
</script>

<template>
  <h2 class="page-title">单词学习</h2>

  <div v-if="done" class="empty-state">
    <p>本批单词已全部学习!</p>
    <button class="btn btn-primary" @click="continueLearn">继续下一批</button>
  </div>

  <template v-else-if="current">
    <div class="learn-progress">
      <span>{{ index + 1 }}</span> / <span>{{ words.length }}</span>
    </div>

    <!-- Word toolbar — always visible across all phases -->
    <div class="word-toolbar">
      <button class="toolbar-btn" :class="{ active: wordMastered }" @click="markMastered" title="已掌握">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        <span>熟</span>
      </button>
    </div>

    <!-- Phase: front — word card front + 认识/不认识 -->
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
        <button class="btn btn-success" @click="onRecognize">✓ 认识</button>
      </div>
    </template>

    <!-- Phase: recognize_quiz — quiz overlay while word stays on front -->
    <template v-if="phase === 'recognize_quiz'">
      <div class="quiz-card">
        <div class="quiz-card-badge recognize">认识验证 <span v-if="quizQueue.length > 1" class="quiz-step">{{ quizQueueIndex + 1 }}/{{ quizQueue.length }}</span></div>

        <template v-if="quizType === 'select_meaning'">
          <div class="quiz-prompt-word">{{ current.word }}</div>
          <div class="card-phonetic-row" style="justify-content:center;margin-bottom:16px">
            <span v-if="current.phonetic_uk" class="card-phonetic-item">🇬🇧 {{ current.phonetic_uk }}<button v-if="current.audio_uk" class="card-play-btn mini" @click.stop="playAudio(current.audio_uk)"><span class="play-icon">&#9654;</span></button></span>
            <span v-if="current.phonetic_us" class="card-phonetic-item">🇺🇸 {{ current.phonetic_us }}<button v-if="current.audio_us" class="card-play-btn mini" @click.stop="playAudio(current.audio_us)"><span class="play-icon">&#9654;</span></button></span>
          </div>
          <div class="quiz-label">选择正确释义：</div>
          <div class="quiz-options">
            <button v-for="(opt, i) in quizOptions" :key="i" class="quiz-option-btn"
              :class="{ correct: answered && opt.correct, wrong: answered && selectedIdx === i && !opt.correct, disabled: answered }"
              @click="handleOptionSelect(opt, i)">{{ opt.text }}</button>
          </div>
        </template>

        <template v-if="quizType === 'spell'">
          <div class="quiz-prompt-meaning">{{ getMeaningText(current) }}</div>
          <div class="quiz-prompt-phonetic" v-if="current.phonetic_us || current.phonetic_uk">
            <span v-if="current.phonetic_uk">🇬🇧 {{ current.phonetic_uk }}</span>
            <span v-if="current.phonetic_us">🇺🇸 {{ current.phonetic_us }}</span>
          </div>
          <div class="quiz-label">拼写这个单词：</div>
          <div class="quiz-spell-row">
            <input v-model="spellInput" class="quiz-spell-input"
              :class="{ correct: answered && answerCorrect, wrong: answered && !answerCorrect }"
              placeholder="输入单词拼写..." :disabled="answered" @keydown.enter="checkSpell">
            <button v-if="!answered" class="btn btn-primary btn-small" @click="checkSpell">确认</button>
          </div>
          <div v-if="answered && !answerCorrect" class="quiz-answer-reveal">正确答案: {{ current.word }}</div>
        </template>

        <template v-if="quizType === 'select_word'">
          <div class="quiz-prompt-meaning">{{ getMeaningText(current) }}</div>
          <div class="quiz-label">选择对应的单词：</div>
          <div class="quiz-options">
            <button v-for="(opt, i) in quizOptions" :key="i" class="quiz-option-btn"
              :class="{ correct: answered && opt.correct, wrong: answered && selectedIdx === i && !opt.correct, disabled: answered }"
              @click="handleOptionSelect(opt, i)">{{ opt.text }}</button>
          </div>
        </template>

        <template v-if="quizType === 'dictation'">
          <div class="quiz-label">听音频，拼写你听到的单词：</div>
          <button class="dictation-play-btn" @click="replayAudio" :disabled="!current.audio_us && !current.audio_uk">
            <span class="dictation-play-icon">&#9654;</span>
            <span>播放音频</span>
          </button>
          <button class="btn btn-small dictation-hint-btn" @click="showHint = !showHint" :disabled="answered">
            {{ showHint ? '隐藏提示' : '提示' }}
          </button>
          <div v-if="showHint" class="dictation-hint">
            <span v-if="current.phonetic_uk">🇬🇧 {{ current.phonetic_uk }}</span>
            <span v-if="current.phonetic_us">🇺🇸 {{ current.phonetic_us }}</span>
            <span v-if="!current.phonetic_uk && !current.phonetic_us && current.phonetic">{{ current.phonetic }}</span>
          </div>
          <div class="quiz-spell-row">
            <input v-model="dictationInput" class="quiz-spell-input"
              :class="{ correct: answered && answerCorrect, wrong: answered && !answerCorrect }"
              placeholder="输入你听到的单词..." :disabled="answered" @keydown.enter="checkDictation">
            <button v-if="!answered" class="btn btn-primary btn-small" @click="checkDictation">确认</button>
          </div>
          <div v-if="answered && !answerCorrect" class="quiz-answer-reveal">正确答案: {{ current.word }}</div>
        </template>

        <div v-if="answered" class="quiz-result" :class="{ correct: answerCorrect, wrong: !answerCorrect }">
          {{ answerCorrect ? '回答正确! ✓' : '回答错误 ✗' }}
        </div>
        <div v-if="answered" class="quiz-actions-row">
          <button class="btn btn-primary quiz-next-btn" @click="onQuizNext">{{ isLastInQueue ? '下一个单词' : '下一题' }}</button>
        </div>
      </div>
    </template>

    <!-- Phase: show_answer — flipped card showing definition + action -->
    <template v-if="phase === 'show_answer'">
      <div class="word-card-container">
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
      <div class="learn-actions">
        <button v-if="answerAction === 'mark_known'" class="btn btn-success" @click="markWord(true)">✓ 认识，下一个</button>
        <button v-if="answerAction === 'mark_unknown'" class="btn btn-primary" @click="markWord(false)">下一个</button>
        <button v-if="answerAction === 'practice'" class="btn btn-primary" @click="startPractice">开始练习</button>
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

    <!-- Phase: practice_quiz — practice quiz card -->
    <template v-if="phase === 'practice_quiz'">
      <div class="quiz-card">
        <div class="quiz-card-badge practice">练习模式 <span v-if="quizQueue.length > 1" class="quiz-step">{{ quizQueueIndex + 1 }}/{{ quizQueue.length }}</span></div>

        <template v-if="quizType === 'select_meaning'">
          <div class="quiz-prompt-word">{{ current.word }}</div>
          <div class="card-phonetic-row" style="justify-content:center;margin-bottom:16px">
            <span v-if="current.phonetic_uk" class="card-phonetic-item">🇬🇧 {{ current.phonetic_uk }}<button v-if="current.audio_uk" class="card-play-btn mini" @click.stop="playAudio(current.audio_uk)"><span class="play-icon">&#9654;</span></button></span>
            <span v-if="current.phonetic_us" class="card-phonetic-item">🇺🇸 {{ current.phonetic_us }}<button v-if="current.audio_us" class="card-play-btn mini" @click.stop="playAudio(current.audio_us)"><span class="play-icon">&#9654;</span></button></span>
          </div>
          <div class="quiz-label">选择正确释义：</div>
          <div class="quiz-options">
            <button v-for="(opt, i) in quizOptions" :key="i" class="quiz-option-btn"
              :class="{ correct: answered && opt.correct, wrong: answered && selectedIdx === i && !opt.correct, disabled: answered }"
              @click="handleOptionSelect(opt, i)">{{ opt.text }}</button>
          </div>
        </template>

        <template v-if="quizType === 'spell'">
          <div class="quiz-prompt-meaning">{{ getMeaningText(current) }}</div>
          <div class="quiz-prompt-phonetic" v-if="current.phonetic_us || current.phonetic_uk">
            <span v-if="current.phonetic_uk">🇬🇧 {{ current.phonetic_uk }}</span>
            <span v-if="current.phonetic_us">🇺🇸 {{ current.phonetic_us }}</span>
          </div>
          <div class="quiz-label">拼写这个单词：</div>
          <div class="quiz-spell-row">
            <input v-model="spellInput" class="quiz-spell-input"
              :class="{ correct: answered && answerCorrect, wrong: answered && !answerCorrect }"
              placeholder="输入单词拼写..." :disabled="answered" @keydown.enter="checkSpell">
            <button v-if="!answered" class="btn btn-primary btn-small" @click="checkSpell">确认</button>
          </div>
          <div v-if="answered && !answerCorrect" class="quiz-answer-reveal">正确答案: {{ current.word }}</div>
        </template>

        <template v-if="quizType === 'select_word'">
          <div class="quiz-prompt-meaning">{{ getMeaningText(current) }}</div>
          <div class="quiz-label">选择对应的单词：</div>
          <div class="quiz-options">
            <button v-for="(opt, i) in quizOptions" :key="i" class="quiz-option-btn"
              :class="{ correct: answered && opt.correct, wrong: answered && selectedIdx === i && !opt.correct, disabled: answered }"
              @click="handleOptionSelect(opt, i)">{{ opt.text }}</button>
          </div>
        </template>

        <template v-if="quizType === 'dictation'">
          <div class="quiz-label">听音频，拼写你听到的单词：</div>
          <button class="dictation-play-btn" @click="replayAudio" :disabled="!current.audio_us && !current.audio_uk">
            <span class="dictation-play-icon">&#9654;</span>
            <span>播放音频</span>
          </button>
          <button class="btn btn-small dictation-hint-btn" @click="showHint = !showHint" :disabled="answered">
            {{ showHint ? '隐藏提示' : '提示' }}
          </button>
          <div v-if="showHint" class="dictation-hint">
            <span v-if="current.phonetic_uk">🇬🇧 {{ current.phonetic_uk }}</span>
            <span v-if="current.phonetic_us">🇺🇸 {{ current.phonetic_us }}</span>
            <span v-if="!current.phonetic_uk && !current.phonetic_us && current.phonetic">{{ current.phonetic }}</span>
          </div>
          <div class="quiz-spell-row">
            <input v-model="dictationInput" class="quiz-spell-input"
              :class="{ correct: answered && answerCorrect, wrong: answered && !answerCorrect }"
              placeholder="输入你听到的单词..." :disabled="answered" @keydown.enter="checkDictation">
            <button v-if="!answered" class="btn btn-primary btn-small" @click="checkDictation">确认</button>
          </div>
          <div v-if="answered && !answerCorrect" class="quiz-answer-reveal">正确答案: {{ current.word }}</div>
        </template>

        <div v-if="answered" class="quiz-result" :class="{ correct: answerCorrect, wrong: !answerCorrect }">
          {{ answerCorrect ? '回答正确! ✓' : '回答错误 ✗' }}
        </div>
        <div v-if="answered" class="quiz-actions-row">
          <button class="btn btn-primary quiz-next-btn" @click="onQuizNext">{{ isLastInQueue ? '下一个单词' : '下一题' }}</button>
        </div>
      </div>
    </template>
  </template>
</template>

<style scoped>
/* Word toolbar — persistent across all phases */
.word-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  padding: 8px 4px;
  margin-bottom: 4px;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 5px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1;
}

.toolbar-btn:hover {
  color: var(--success);
  border-color: var(--success);
  background: #f0fdf4;
}

.toolbar-btn.active {
  color: var(--success);
  border-color: var(--success);
  background: #f0fdf4;
}

.toolbar-btn svg {
  flex-shrink: 0;
}

.card-face {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.quiz-card {
  max-width: 460px;
  margin: 0 auto;
  background: var(--surface);
  border-radius: var(--radius);
  padding: 28px 24px;
  box-shadow: var(--shadow);
  text-align: center;
}

.quiz-card-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  margin-bottom: 20px;
}

.quiz-step {
  font-size: 11px;
  font-weight: 500;
  opacity: 0.7;
}

.quiz-card-badge.recognize {
  background: #eef2ff;
  color: var(--primary);
}

.quiz-card-badge.practice {
  background: #fef3c7;
  color: #92400e;
}

.quiz-prompt-word {
  font-size: 32px;
  font-weight: 700;
  color: var(--text);
}

.quiz-prompt-meaning {
  font-size: 20px;
  font-weight: 500;
  color: var(--text);
  line-height: 1.5;
  margin-bottom: 4px;
}

.quiz-prompt-phonetic {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
  justify-content: center;
}

.quiz-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 16px 0 12px;
  text-align: center;
}

.quiz-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quiz-option-btn {
  padding: 12px 16px;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--surface);
  text-align: left;
  color: var(--text);
}

.quiz-option-btn:hover:not(.disabled) {
  border-color: var(--primary);
  background: #eef2ff;
}

.quiz-option-btn.correct {
  border-color: var(--success);
  background: #ecfdf5;
  color: #065f46;
}

.quiz-option-btn.wrong {
  border-color: var(--danger);
  background: #fef2f2;
  color: #991b1b;
}

.quiz-option-btn.disabled {
  pointer-events: none;
  opacity: 0.7;
}

.quiz-spell-row {
  display: flex;
  gap: 8px;
  max-width: 360px;
  margin: 0 auto;
}

.quiz-spell-input {
  flex: 1;
  padding: 12px 16px;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  font-size: 16px;
  outline: none;
  text-align: center;
}

.quiz-spell-input:focus { border-color: var(--primary); }
.quiz-spell-input.correct { border-color: var(--success); background: #ecfdf5; }
.quiz-spell-input.wrong { border-color: var(--danger); background: #fef2f2; }

.quiz-answer-reveal {
  font-size: 14px;
  color: var(--danger);
  margin-top: 8px;
}

.quiz-result {
  margin-top: 16px;
  font-size: 15px;
  font-weight: 600;
}

.quiz-result.correct { color: var(--success); }
.quiz-result.wrong { color: var(--danger); }

.quiz-actions-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.quiz-next-btn {
  padding: 10px 32px;
  font-size: 15px;
  border-radius: 10px;
}

.dictation-play-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  border: 2px solid var(--primary);
  border-radius: 50px;
  background: var(--surface);
  color: var(--primary);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 16px;
}

.dictation-play-btn:hover:not(:disabled) {
  background: var(--primary);
  color: white;
}

.dictation-play-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.dictation-play-icon {
  font-size: 18px;
}

.dictation-hint-btn {
  margin-bottom: 12px;
}

.dictation-hint {
  display: flex;
  gap: 12px;
  justify-content: center;
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding: 8px 16px;
  background: #f8fafc;
  border-radius: 8px;
}

@media (max-width: 768px) {
  .quiz-card { padding: 20px 16px; }
  .quiz-prompt-word { font-size: 26px; }
  .quiz-prompt-meaning { font-size: 18px; }
  .quiz-option-btn { padding: 10px 14px; font-size: 14px; }
  .quiz-spell-input { padding: 10px 14px; font-size: 14px; }
  .card-face { padding: 16px; }
}
</style>

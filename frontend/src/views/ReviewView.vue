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
  background: var(--primary);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
  min-width: 48px;
  text-align: right;
}

/* Empty state */
.empty-icon { font-size: 48px; margin-bottom: 8px; }
.empty-hint { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

/* Summary card */
.summary-card {
  max-width: 400px;
  margin: 40px auto;
  background: var(--surface);
  border-radius: var(--radius);
  padding: 32px;
  box-shadow: var(--shadow);
  text-align: center;
}

.summary-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
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
  font-weight: 700;
  color: var(--text);
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
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
  background: var(--success);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.summary-rate {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.summary-card .btn { width: 100%; justify-content: center; }

/* Card styles */
.card-face {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  min-height: 280px;
}

/* Transition */
.card-enter-active { transition: all 0.3s ease; }
.card-leave-active { transition: all 0.15s ease; }
.card-enter-from { opacity: 0; transform: translateY(12px); }
.card-leave-to { opacity: 0; transform: translateY(-8px); }

@media (max-width: 768px) {
  .summary-card { padding: 24px 16px; margin: 20px auto; }
  .summary-stats { gap: 20px; }
  .stat-value { font-size: 24px; }
  .card-face { padding: 20px; min-height: 220px; }
}
</style>

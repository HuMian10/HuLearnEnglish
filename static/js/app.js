// ===== State =====
let isLoggedIn = false;
let currentUser = null;
let currentPage = 'dashboard';
let learnWords = [];
let learnIndex = 0;
let reviewWords = [];
let reviewIndex = 0;
let currentWord = null;
let currentModalWord = null;
let calendarYear, calendarMonth, selectedDate = null;
let wordBankPage = 1;
let wordBankCategory = '';

// ===== Auth =====
async function checkAuth() {
    try {
        const resp = await fetch('/api/auth/me', { credentials: 'include' });
        const data = await resp.json();
        if (data.ok) {
            isLoggedIn = true;
            currentUser = data;
            showApp();
        } else {
            isLoggedIn = false;
            currentUser = null;
            showLogin();
        }
    } catch (e) {
        showLogin();
    }
}

function showLogin() {
    document.getElementById('loginPage').style.display = '';
    document.getElementById('appContainer').style.display = 'none';
}

function showApp() {
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('appContainer').style.display = '';
    document.getElementById('userName').textContent = currentUser.username;
    document.getElementById('userAvatar').textContent = currentUser.username[0].toUpperCase();
    document.getElementById('mobileAvatar').textContent = currentUser.username[0].toUpperCase();
    loadDashboard();
}

function switchLoginTab(tab) {
    document.querySelectorAll('.login-tab').forEach(t => t.classList.remove('active'));
    if (tab === 'login') {
        document.getElementById('loginForm').style.display = '';
        document.getElementById('registerForm').style.display = 'none';
        document.querySelectorAll('.login-tab')[0].classList.add('active');
    } else {
        document.getElementById('loginForm').style.display = 'none';
        document.getElementById('registerForm').style.display = '';
        document.querySelectorAll('.login-tab')[1].classList.add('active');
    }
    document.getElementById('login-error').textContent = '';
    document.getElementById('reg-error').textContent = '';
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    document.getElementById('login-error').textContent = '';

    try {
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
            credentials: 'include',
        });
        const data = await resp.json();
        if (data.ok) {
            isLoggedIn = true;
            currentUser = data;
            showApp();
        } else {
            document.getElementById('login-error').textContent = data.error || '登录失败';
        }
    } catch (e) {
        document.getElementById('login-error').textContent = '网络错误';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    const password2 = document.getElementById('reg-password2').value;
    const email = document.getElementById('reg-email').value.trim();
    document.getElementById('reg-error').textContent = '';

    if (password !== password2) {
        document.getElementById('reg-error').textContent = '两次密码不一致';
        return;
    }

    try {
        const resp = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, email }),
            credentials: 'include',
        });
        const data = await resp.json();
        if (data.ok) {
            isLoggedIn = true;
            currentUser = data;
            showApp();
        } else {
            document.getElementById('reg-error').textContent = data.error || '注册失败';
        }
    } catch (e) {
        document.getElementById('reg-error').textContent = '网络错误';
    }
}

async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    isLoggedIn = false;
    currentUser = null;
    showLogin();
}

// ===== Navigation =====
function showPage(page) {
    if (!isLoggedIn) return;
    currentPage = page;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');

    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll(`.nav-item[data-page="${page}"]`).forEach(n => n.classList.add('active'));

    document.querySelectorAll('.mobile-nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll(`.mobile-nav-item[data-page="${page}"]`).forEach(n => n.classList.add('active'));

    if (page === 'dashboard') loadDashboard();
    if (page === 'learn') loadLearnPage();
    if (page === 'review') loadReviewPage();
    if (page === 'wordbank') loadWordBank();
    if (page === 'stats') loadStats();
    if (page === 'calendar') loadCalendar();
}

// Sidebar nav clicks
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => showPage(item.dataset.page));
});

// ===== API Helpers =====
async function api(path, options = {}) {
    const resp = await fetch('/api/' + path, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        ...options,
    });
    if (resp.status === 401) {
        isLoggedIn = false;
        currentUser = null;
        showLogin();
        throw new Error('Unauthorized');
    }
    return resp.json();
}

// ===== Dashboard =====
async function loadDashboard() {
    const stats = await api('learning/stats');
    document.getElementById('stat-today-total').textContent = stats.today_total;
    document.getElementById('stat-today-done').textContent = stats.today_completed;
    document.getElementById('stat-mastered').textContent = stats.mastered_count;
    document.getElementById('stat-due-review').textContent = stats.due_review;
    document.getElementById('stat-unlearned').textContent = stats.unlearned;
    document.getElementById('stat-learning').textContent = stats.learning_count;
    document.getElementById('stat-mastered-total').textContent = stats.mastered_count;

    const pct = stats.today_total > 0 ? Math.round(stats.today_completed / stats.today_total * 100) : 0;
    document.getElementById('dashboard-progress').style.width = pct + '%';
    document.getElementById('dashboard-progress-text').textContent = pct + '%';

    const plan = await api('plan/today');
    const container = document.getElementById('dashboard-plan-words');
    if (plan.plan) {
        const completedIds = JSON.parse(plan.plan.completed_ids || '[]');
        container.innerHTML = (plan.words || []).map(w =>
            `<span class="plan-word-chip ${completedIds.includes(w.id) ? 'done' : ''}" onclick="showPage('learn')">${w.word}</span>`
        ).join('');
        document.getElementById('btn-generate-plan').style.display = 'none';
    } else {
        container.innerHTML = '';
        document.getElementById('btn-generate-plan').style.display = '';
    }
}

async function generatePlan() {
    const result = await api('plan/generate', { method: 'POST' });
    if (currentPage === 'dashboard') loadDashboard();
    if (currentPage === 'learn') loadLearnPage();
}

// ===== Learn Page =====
async function loadLearnPage() {
    const plan = await api('plan/today');
    const emptyEl = document.getElementById('learn-empty');
    const contentEl = document.getElementById('learn-content');

    if (!plan.plan || !plan.remaining || plan.remaining.length === 0) {
        emptyEl.style.display = '';
        contentEl.style.display = 'none';
        return;
    }

    emptyEl.style.display = 'none';
    contentEl.style.display = '';
    learnWords = plan.remaining;
    learnIndex = 0;
    showLearnWord();
}

function showLearnWord() {
    if (learnIndex >= learnWords.length) {
        document.getElementById('learn-content').innerHTML =
            '<div class="empty-state"><p>今日单词已全部学习!</p><button class="btn btn-primary" onclick="loadLearnPage()">继续</button></div>';
        return;
    }

    currentWord = learnWords[learnIndex];
    document.getElementById('learn-current').textContent = learnIndex + 1;
    document.getElementById('learn-total').textContent = learnWords.length;

    document.getElementById('card-word').textContent = currentWord.word;
    document.getElementById('card-phonetic').textContent = currentWord.phonetic || '';
    document.getElementById('card-word-back').textContent = currentWord.word;
    document.getElementById('card-phonetic-back').textContent = currentWord.phonetic || '';
    document.getElementById('card-pos').textContent = currentWord.pos;
    document.getElementById('card-meaning').textContent = currentWord.meaning_cn;

    const exEn = currentWord.example_en || '';
    const exCn = currentWord.example_cn || '';
    document.getElementById('card-example').textContent =
        exEn ? `${exEn}\n${exCn}` : '';

    document.getElementById('wordCard').classList.remove('flipped');
    document.getElementById('chatMessages').innerHTML = '';
    document.getElementById('llmChat').style.display = 'none';
    document.getElementById('llmStructuredOutput').innerHTML = '';
}

function flipCard() {
    document.getElementById('wordCard').classList.toggle('flipped');
}

async function markWord(correct) {
    if (!currentWord) return;
    await api('learning/review', {
        method: 'POST',
        body: JSON.stringify({ word_id: currentWord.id, correct }),
    });
    learnIndex++;
    showLearnWord();
}

// ===== LLM Chat =====
function toggleLLMChat() {
    const el = document.getElementById('llmChat');
    el.style.display = el.style.display === 'none' ? '' : 'none';
}

async function sendChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg || !currentWord) return;
    input.value = '';

    const container = document.getElementById('chatMessages');
    container.innerHTML += `<div class="chat-msg user">${msg}</div>`;

    const respDiv = document.createElement('div');
    respDiv.className = 'chat-msg assistant';
    container.appendChild(respDiv);
    container.scrollTop = container.scrollHeight;

    try {
        const resp = await fetch('/api/llm/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word: currentWord.word, message: msg }),
            credentials: 'include',
        });

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') break;
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.error) respDiv.textContent += '\n[Error: ' + parsed.error + ']';
                        else if (parsed.content) respDiv.textContent += parsed.content;
                    } catch (e) {}
                }
            }
            container.scrollTop = container.scrollHeight;
        }
    } catch (e) {
        respDiv.textContent = 'Error: ' + e.message;
    }
}

// ===== LLM Quick Actions (structured JSON) =====
async function llmQuickAction(action) {
    if (!currentWord) return;
    const outputEl = document.getElementById('llmStructuredOutput');
    outputEl.innerHTML = '<div class="llm-loading">加载中...</div>';

    // Hide chat when showing structured output
    document.getElementById('llmChat').style.display = 'none';

    try {
        const result = await api(`llm/quick-actions/${currentWord.id}?action=${action}`, {
            method: 'POST',
        });
        if (!result.ok) {
            outputEl.innerHTML = `<div class="llm-error">${result.error || '请求失败'}</div>`;
            return;
        }
        outputEl.innerHTML = renderLLMData(result.action, result.data, currentWord.word);
    } catch (e) {
        outputEl.innerHTML = `<div class="llm-error">${e.message}</div>`;
    }
}

function renderLLMData(action, data, word) {
    if (action === 'examples') return renderExamples(data, word);
    if (action === 'explain') return renderExplain(data);
    if (action === 'quiz') return renderQuiz(data);
    return `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

function highlightWord(text, word) {
    if (!word) return text;
    const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return text.replace(new RegExp(`(${escaped})`, 'gi'), '<span class="llm-highlight">$1</span>');
}

function renderExamples(data, word) {
    const examples = data.examples || [];
    if (!examples.length) return '<div class="llm-error">未生成例句</div>';
    return `<div class="llm-examples">${examples.map(ex => `
        <div class="llm-example-item">
            <div class="llm-example-en">${highlightWord(escHtml(ex.en), word)}</div>
            <div class="llm-example-cn">${escHtml(ex.cn)}</div>
        </div>
    `).join('')}</div>`;
}

function renderExplain(data) {
    let html = '<div class="llm-explain">';
    if (data.meaning) {
        html += `<div class="llm-explain-section">
            <div class="llm-explain-label">释义</div>
            <div class="llm-explain-text">${escHtml(data.meaning)}</div>
        </div>`;
    }
    if (data.nuances) {
        html += `<div class="llm-explain-section">
            <div class="llm-explain-label">细微差别</div>
            <div class="llm-explain-text">${escHtml(data.nuances)}</div>
        </div>`;
    }
    if (data.collocations && data.collocations.length) {
        html += `<div class="llm-explain-section">
            <div class="llm-explain-label">常见搭配</div>
            <div class="llm-explain-tags">${data.collocations.map(c =>
                `<span class="llm-collocation-tag">${escHtml(c)}</span>`
            ).join('')}</div>
        </div>`;
    }
    if (data.common_mistakes) {
        html += `<div class="llm-explain-section">
            <div class="llm-explain-label">常见错误</div>
            <div class="llm-explain-text">${escHtml(data.common_mistakes)}</div>
        </div>`;
    }
    html += '</div>';
    return html;
}

function renderQuiz(data) {
    const quizzes = data.quizzes || [];
    if (!quizzes.length) return '<div class="llm-error">未生成测验</div>';

    return `<div class="llm-quiz">${quizzes.map((q, i) => {
        if (q.type === 'fill_blank') return renderFillBlank(q, i);
        if (q.type === 'choice') return renderChoice(q, i);
        return '';
    }).join('')}</div>`;
}

function renderFillBlank(q, idx) {
    return `<div class="llm-quiz-item">
        <div class="llm-quiz-type">填空题</div>
        <div class="llm-quiz-question">${escHtml(q.question)}</div>
        <div class="llm-quiz-fill-row">
            <input type="text" class="llm-quiz-fill-input" id="fill-${idx}" placeholder="${escHtml(q.hint || '输入答案')}" onkeydown="if(event.key==='Enter')checkFillBlank(${idx},'${escAttr(q.answer)}')">
            <button class="btn btn-primary btn-small" onclick="checkFillBlank(${idx},'${escAttr(q.answer)}')">检查</button>
        </div>
        <div class="llm-quiz-answer-reveal" id="fill-result-${idx}"></div>
    </div>`;
}

function renderChoice(q, idx) {
    return `<div class="llm-quiz-item">
        <div class="llm-quiz-type">选择题</div>
        <div class="llm-quiz-question">${escHtml(q.question)}</div>
        <div class="llm-quiz-options">
            ${(q.options || []).map((opt, oi) =>
                `<button class="llm-quiz-option" onclick="checkChoice(this,${oi},'${q.answer}',${idx})">${escHtml(opt)}</button>`
            ).join('')}
        </div>
        <div class="llm-quiz-explanation" id="choice-expl-${idx}" style="display:none">${escHtml(q.explanation || '')}</div>
    </div>`;
}

function checkFillBlank(idx, answer) {
    const input = document.getElementById(`fill-${idx}`);
    const result = document.getElementById(`fill-result-${idx}`);
    if (!input) return;
    const userAnswer = input.value.trim().toLowerCase();
    const correct = answer.toLowerCase();
    if (userAnswer === correct) {
        input.classList.add('correct');
        input.classList.remove('wrong');
        result.textContent = '正确! ✓';
        result.style.color = '#10b981';
    } else {
        input.classList.add('wrong');
        input.classList.remove('correct');
        result.textContent = `正确答案: ${answer}`;
        result.style.color = '#ef4444';
    }
}

function checkChoice(btn, optIdx, answer, quizIdx) {
    // answer is like "A", "B" etc.
    const optionButtons = btn.parentElement.querySelectorAll('.llm-quiz-option');
    const selectedLetter = String.fromCharCode(65 + optIdx); // 0->A, 1->B...
    const isCorrect = selectedLetter === answer;

    optionButtons.forEach((ob, i) => {
        ob.classList.add('disabled');
        const letter = String.fromCharCode(65 + i);
        if (letter === answer) ob.classList.add('correct');
    });

    if (!isCorrect) btn.classList.add('wrong');

    const expl = document.getElementById(`choice-expl-${quizIdx}`);
    if (expl) expl.style.display = '';
}

function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escAttr(str) {
    if (!str) return '';
    return String(str).replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// ===== Review Page =====
async function loadReviewPage() {
    const stats = await api('learning/stats');
    const emptyEl = document.getElementById('review-empty');
    const contentEl = document.getElementById('review-content');

    if (stats.due_review === 0) {
        emptyEl.style.display = '';
        contentEl.style.display = 'none';
        return;
    }

    emptyEl.style.display = 'none';
    contentEl.style.display = '';

    const plan = await api('plan/today');
    if (plan.remaining && plan.remaining.length > 0) {
        reviewWords = plan.remaining;
        reviewIndex = 0;
        document.getElementById('review-count').textContent = reviewWords.length;
        showReviewWord();
    }
}

function showReviewWord() {
    if (reviewIndex >= reviewWords.length) {
        document.getElementById('review-content').innerHTML =
            '<div class="empty-state"><p>复习完成!</p></div>';
        return;
    }

    const word = reviewWords[reviewIndex];
    document.getElementById('review-word').textContent = word.word;
    document.getElementById('review-phonetic').textContent = word.phonetic || '';
    document.getElementById('review-word-back').textContent = word.word;
    document.getElementById('review-phonetic-back').textContent = word.phonetic || '';
    document.getElementById('review-pos').textContent = word.pos;
    document.getElementById('review-meaning').textContent = word.meaning_cn;

    const exEn = word.example_en || '';
    const exCn = word.example_cn || '';
    document.getElementById('review-example').textContent =
        exEn ? `${exEn}\n${exCn}` : '';

    document.getElementById('reviewCard').classList.remove('flipped');
}

function flipReviewCard() {
    document.getElementById('reviewCard').classList.toggle('flipped');
}

async function reviewMark(correct) {
    if (!reviewWords[reviewIndex]) return;
    await api('learning/review', {
        method: 'POST',
        body: JSON.stringify({ word_id: reviewWords[reviewIndex].id, correct }),
    });
    reviewIndex++;
    showReviewWord();
}

// ===== Word Bank =====
async function loadWordBank() {
    const cats = await api('words/categories');
    const select = document.getElementById('categoryFilter');
    const chipsEl = document.getElementById('categoryChips');

    if (select.options.length <= 1) {
        cats.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.category;
            opt.textContent = `${c.category} (${c.count})`;
            select.appendChild(opt);
        });
    }

    chipsEl.innerHTML = `<span class="chip ${!wordBankCategory ? 'active' : ''}" onclick="setCategory('')">全部</span>`;
    cats.forEach(c => {
        chipsEl.innerHTML += `<span class="chip ${wordBankCategory === c.category ? 'active' : ''}" onclick="setCategory('${c.category}')">${c.category}</span>`;
    });

    loadWordList();
}

async function loadWordList() {
    const search = document.getElementById('wordSearch').value;
    const params = new URLSearchParams({
        page: wordBankPage,
        page_size: 50,
        category: wordBankCategory,
        search: search,
    });
    const data = await api('words?' + params);

    const listEl = document.getElementById('wordList');
    listEl.innerHTML = data.words.map(w =>
        `<div class="word-item" onclick="showWordDetail(${w.id})">
            <span class="wi-word">${w.word}</span><span class="wi-pos">${w.pos}</span>
            <div class="wi-meaning">${w.meaning_cn}</div>
        </div>`
    ).join('');

    const pagEl = document.getElementById('wordPagination');
    const totalPages = Math.ceil(data.total / data.page_size);
    pagEl.innerHTML = '';
    if (totalPages > 1) {
        for (let i = 1; i <= totalPages && i <= 10; i++) {
            pagEl.innerHTML += `<button class="btn btn-small ${i === wordBankPage ? 'btn-primary' : 'btn-outline'}" onclick="wordBankPage=${i};loadWordList()">${i}</button>`;
        }
    }
}

function searchWords() { wordBankPage = 1; loadWordList(); }
function filterByCategory() {
    wordBankCategory = document.getElementById('categoryFilter').value;
    wordBankPage = 1;
    loadWordList();
}
function setCategory(cat) {
    wordBankCategory = cat;
    document.getElementById('categoryFilter').value = cat;
    wordBankPage = 1;
    loadWordList();
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    document.querySelectorAll(`.chip`).forEach(c => {
        if (c.textContent.trim() === (cat || '全部')) c.classList.add('active');
    });
}

// ===== Word Detail Modal =====
async function showWordDetail(id) {
    const word = await api('words/' + id);
    if (!word) return;
    currentModalWord = word;

    const modal = document.getElementById('wordModal');
    const detail = document.getElementById('modal-word-detail');

    detail.innerHTML = `
        <h2 style="font-size:28px;font-weight:700;margin-bottom:8px">${word.word}</h2>
        <p style="color:#64748b;margin-bottom:4px">${word.phonetic || ''}</p>
        <span style="display:inline-block;background:#eef2ff;color:#4f46e5;padding:2px 10px;border-radius:12px;font-size:13px">${word.pos}</span>
        <span style="display:inline-block;background:#fef3c7;color:#92400e;padding:2px 10px;border-radius:12px;font-size:13px;margin-left:6px">${word.category}</span>
        <p style="font-size:18px;margin-top:16px;font-weight:600">${word.meaning_cn}</p>
        ${word.example_en ? `<p style="margin-top:12px;color:#64748b;font-size:14px;line-height:1.6">${word.example_en}<br>${word.example_cn || ''}</p>` : ''}
        <div style="margin-top:20px;display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn btn-small" onclick="modalLLMAction(${word.id},'examples','生成例句')">生成例句</button>
            <button class="btn btn-small" onclick="modalLLMAction(${word.id},'explain','详细解释')">详细解释</button>
            <button class="btn btn-small" onclick="modalLLMAction(${word.id},'quiz','小测验')">小测验</button>
        </div>
        <div id="modal-llm-output" style="margin-top:16px"></div>
    `;

    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('wordModal').classList.remove('active');
}

async function modalLLMAction(id, action, label) {
    const output = document.getElementById('modal-llm-output');
    output.innerHTML = '<div class="llm-loading">加载中...</div>';

    try {
        const result = await api(`llm/quick-actions/${id}?action=${action}`, {
            method: 'POST',
        });
        if (!result.ok) {
            output.innerHTML = `<div class="llm-error">${result.error || '请求失败'}</div>`;
            return;
        }
        output.innerHTML = renderLLMData(result.action, result.data, currentModalWord?.word);
    } catch (e) {
        output.innerHTML = `<div class="llm-error">${e.message}</div>`;
    }
}

// ===== Stats =====
async function loadStats() {
    const stats = await api('learning/stats');
    document.getElementById('stats-total-words').textContent = stats.total_words;
    document.getElementById('stats-mastered').textContent = stats.mastered_count;
    document.getElementById('stats-learning').textContent = stats.learning_count;
    document.getElementById('stats-new').textContent = stats.new_count;

    const cats = await api('words/categories');
    const container = document.getElementById('category-progress');
    container.innerHTML = '';

    for (const cat of cats) {
        const pct = stats.total_words > 0
            ? Math.round(stats.mastered_count / stats.total_words * 100)
            : 0;

        container.innerHTML += `
            <div class="cat-progress-item">
                <span class="cat-progress-name">${cat.category}</span>
                <div class="cat-progress-bar">
                    <div class="cat-progress-fill" style="width:${pct}%"></div>
                </div>
                <span class="cat-progress-text">${pct}%</span>
            </div>
        `;
    }
}

// ===== User Popup =====
function toggleUserPopup(e) {
    if (e) e.stopPropagation();
    const popup = document.getElementById('userPopup');
    if (popup.classList.contains('active')) {
        closeUserPopup();
    } else {
        popup.classList.add('active');
        showPopupView('popup-menu');
        updatePopupSummary();
    }
}

function closeUserPopup() {
    const popup = document.getElementById('userPopup');
    popup.classList.remove('active');
}

function showPopupView(viewId) {
    // Legacy — menu view only
    document.querySelectorAll('#userPopup .popup-view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

function updatePopupSummary() {
    if (!currentUser) return;
    document.getElementById('popupAvatar').textContent = currentUser.username[0].toUpperCase();
    document.getElementById('popupUsername').textContent = currentUser.username;
    document.getElementById('popupEmailPreview').textContent = currentUser.email || '未绑定邮箱';
}

// Click outside to close popup
document.addEventListener('click', (e) => {
    const popup = document.getElementById('userPopup');
    if (!popup) return;
    if (!popup.classList.contains('active')) return;
    if (popup.contains(e.target)) return;
    if (e.target.closest('.user-info') || e.target.closest('.mobile-header-avatar')) return;
    closeUserPopup();
});

// ===== Popup Loaders =====
async function loadUserInfo() {
    const userInfo = await api('auth/me');
    document.getElementById('profile-username').value = userInfo.username || '';
    document.getElementById('profile-created-at').value = userInfo.created_at || '';

    const emailInput = document.getElementById('profile-email');
    const emailBtn = document.getElementById('email-action-btn');
    const hasEmail = !!userInfo.email;
    emailInput.value = userInfo.email || '';
    emailInput.disabled = hasEmail;
    emailInput.placeholder = '输入邮箱地址';
    emailBtn.textContent = hasEmail ? '换绑' : '绑定';
    emailBtn.className = hasEmail ? 'btn btn-outline btn-small email-action-btn' : 'btn btn-primary btn-small email-action-btn';
    emailBtn.dataset.mode = hasEmail ? 'change' : 'bind';
}

async function loadLearningSettings() {
    const settings = await api('learning/settings');
    document.getElementById('setting-daily-words').value = settings.daily_words || '10';
}

async function loadLLMSettings() {
    const settings = await api('learning/settings');
    document.getElementById('setting-llm-url').value = settings.llm_api_url || '';
    document.getElementById('setting-llm-key').value = settings.llm_api_key || '';
    document.getElementById('setting-llm-model').value = settings.llm_model || '';
}

async function bindEmail() {
    const emailInput = document.getElementById('profile-email');
    const emailBtn = document.getElementById('email-action-btn');

    // If in "change" mode, unlock input for editing first
    if (emailBtn.dataset.mode === 'change' && emailInput.disabled) {
        emailInput.disabled = false;
        emailInput.value = '';
        emailInput.focus();
        emailBtn.textContent = '保存';
        emailBtn.className = 'btn btn-primary btn-small email-action-btn';
        emailBtn.dataset.mode = 'save';
        return;
    }

    const email = emailInput.value.trim();
    try {
        const data = await api('auth/email', {
            method: 'PUT',
            body: JSON.stringify({ email }),
        });
        if (data.ok) {
            currentUser.email = email;
            updatePopupSummary();
            document.getElementById('settingsModalEmail').textContent = email || '未绑定邮箱';
            emailInput.value = email;
            emailInput.disabled = !!email;
            emailBtn.textContent = email ? '换绑' : '绑定';
            emailBtn.className = email ? 'btn btn-outline btn-small email-action-btn' : 'btn btn-primary btn-small email-action-btn';
            emailBtn.dataset.mode = email ? 'change' : 'bind';
            const msg = document.getElementById('email-saved');
            msg.textContent = email ? '邮箱换绑成功!' : '邮箱绑定成功!';
            msg.style.display = '';
            setTimeout(() => msg.style.display = 'none', 2000);
        } else {
            alert(data.error || '绑定失败');
        }
    } catch (e) {
        alert('网络错误');
    }
}

async function saveLearningSettings() {
    await api('learning/settings', {
        method: 'POST',
        body: JSON.stringify({ key: 'daily_words', value: document.getElementById('setting-daily-words').value }),
    });
    const msg = document.getElementById('learning-settings-saved');
    msg.style.display = '';
    setTimeout(() => msg.style.display = 'none', 2000);
}

async function saveLLMSettings() {
    const pairs = [
        ['llm_api_url', document.getElementById('setting-llm-url').value],
        ['llm_api_key', document.getElementById('setting-llm-key').value],
        ['llm_model', document.getElementById('setting-llm-model').value],
    ];
    for (const [key, value] of pairs) {
        await api('learning/settings', {
            method: 'POST',
            body: JSON.stringify({ key, value }),
        });
    }
    const msg = document.getElementById('llm-settings-saved');
    msg.style.display = '';
    setTimeout(() => msg.style.display = 'none', 2000);
}

// ===== Calendar =====
async function loadCalendar() {
    const now = new Date();
    if (calendarYear === undefined) {
        calendarYear = now.getFullYear();
        calendarMonth = now.getMonth() + 1;
    }
    const data = await api(`learning/calendar?year=${calendarYear}&month=${calendarMonth}`);
    renderCalendar(data);
}

function calendarPrev() {
    calendarMonth--;
    if (calendarMonth < 1) { calendarMonth = 12; calendarYear--; }
    loadCalendar();
}

function calendarNext() {
    calendarMonth++;
    if (calendarMonth > 12) { calendarMonth = 1; calendarYear++; }
    loadCalendar();
}

function renderCalendar(data) {
    document.getElementById('calendarTitle').textContent = `${data.year}年${data.month}月`;

    const grid = document.getElementById('calendarGrid');
    const days = data.days || {};
    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;

    // First day of month and total days
    const firstDay = new Date(data.year, data.month - 1, 1).getDay();
    const daysInMonth = new Date(data.year, data.month, 0).getDate();

    let html = '';
    // Empty cells before first day
    for (let i = 0; i < firstDay; i++) {
        html += '<div class="calendar-day empty"></div>';
    }
    // Day cells
    for (let d = 1; d <= daysInMonth; d++) {
        const dateStr = `${data.year}-${String(data.month).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
        const dayData = days[dateStr];
        const isToday = dateStr === todayStr;
        const isSelected = dateStr === selectedDate;
        let cls = 'calendar-day';
        if (isToday) cls += ' today';
        if (isSelected) cls += ' selected';

        if (dayData) {
            const pct = dayData.total > 0 ? Math.round(dayData.completed / dayData.total * 100) : 0;
            if (pct >= 100) cls += ' all-done';
            else cls += ' has-data';
            html += `<div class="${cls}" onclick="selectDate('${dateStr}')">
                <span class="cal-day-num">${d}</span>
                <div class="cal-mini-bar"><div class="cal-mini-fill" style="width:${pct}%"></div></div>
            </div>`;
        } else {
            html += `<div class="${cls}" onclick="selectDate('${dateStr}')">
                <span class="cal-day-num">${d}</span>
            </div>`;
        }
    }
    grid.innerHTML = html;
}

async function selectDate(date) {
    selectedDate = date;
    // Re-render calendar to update selection
    const data = await api(`learning/calendar?year=${calendarYear}&month=${calendarMonth}`);
    renderCalendar(data);

    // Load day detail
    const detail = await api(`learning/day-detail?date=${date}`);
    renderDayDetail(detail);
}

function renderDayDetail(detail) {
    const el = document.getElementById('dayDetail');
    el.style.display = '';

    document.getElementById('dayDetailDate').textContent = detail.date;

    const remain = detail.total - detail.completed;
    document.getElementById('dayDetailStats').innerHTML = `
        <div class="day-stat">
            <div class="day-stat-value done">${detail.completed}</div>
            <div class="day-stat-label">已完成</div>
        </div>
        <div class="day-stat">
            <div class="day-stat-value remain">${remain}</div>
            <div class="day-stat-label">未完成</div>
        </div>
        <div class="day-stat">
            <div class="day-stat-value reviewed">${detail.reviewed_count}</div>
            <div class="day-stat-label">已复习</div>
        </div>
    `;

    const wordsEl = document.getElementById('dayDetailWords');
    if (detail.words && detail.words.length > 0) {
        wordsEl.innerHTML = detail.words.map(w => `
            <div class="day-word-item ${w.completed ? 'completed' : 'pending'}">
                <span class="day-word-status ${w.completed ? 'done' : 'pending'}">${w.completed ? '&#10003;' : ''}</span>
                <span class="day-word-text">${escHtml(w.word)}</span>
                <span class="day-word-meaning">${escHtml(w.meaning_cn)}</span>
            </div>
        `).join('');
    } else {
        wordsEl.innerHTML = '<div class="day-detail-empty">该日无学习计划</div>';
    }

    const actionsEl = document.getElementById('dayDetailActions');
    if (detail.total > 0) {
        actionsEl.innerHTML = `
            <button class="btn btn-danger btn-small" onclick="clearDayProgress('${detail.date}')">清空当日进度</button>
            <button class="btn btn-danger btn-small" onclick="clearAllPlans()">清空所有计划</button>
        `;
    } else {
        actionsEl.innerHTML = `
            <button class="btn btn-danger btn-small" onclick="clearAllPlans()">清空所有计划</button>
        `;
    }
}

async function clearDayProgress(date) {
    if (!confirm(`确定清空 ${date} 的学习进度？清空后可重新学习。`)) return;
    await api(`learning/day-progress?date=${date}`, { method: 'DELETE' });
    await loadCalendar();
    document.getElementById('dayDetail').style.display = 'none';
    selectedDate = null;
}

async function clearAllPlans() {
    if (!confirm('确定清空所有学习计划？此操作不可恢复。')) return;
    await api('learning/all-plans', { method: 'DELETE' });
    await loadCalendar();
    document.getElementById('dayDetail').style.display = 'none';
    selectedDate = null;
}

// ===== Settings Modal =====
function openSettingsModal(tab) {
    closeUserPopup();
    const modal = document.getElementById('settingsModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    // Update header
    if (currentUser) {
        document.getElementById('settingsModalAvatar').textContent = currentUser.username[0].toUpperCase();
        document.getElementById('settingsModalUsername').textContent = currentUser.username;
        document.getElementById('settingsModalEmail').textContent = currentUser.email || '未绑定邮箱';
    }

    switchSettingsTab(tab || 'user-info');
}

function closeSettingsModal() {
    document.getElementById('settingsModal').classList.remove('active');
    document.body.style.overflow = '';
}

function switchSettingsTab(tab) {
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.settings-tab-pane').forEach(p => p.classList.remove('active'));

    const tabBtn = document.querySelector(`.settings-tab[data-tab="${tab}"]`);
    const pane = document.getElementById('settings-tab-' + tab);
    if (tabBtn) tabBtn.classList.add('active');
    if (pane) pane.classList.add('active');

    if (tab === 'user-info') loadUserInfo();
    if (tab === 'learning-settings') loadLearningSettings();
    if (tab === 'llm-settings') loadLLMSettings();
}

// ESC key to close settings modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('settingsModal');
        if (modal.classList.contains('active')) closeSettingsModal();
    }
});

// ===== Init =====
checkAuth();

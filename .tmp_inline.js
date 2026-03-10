
const API_BASE = '/api/v1';
const AUTH_HEADER = 'Bearer access_token_user_123';
let currentSubject = 'math';
let currentDifficulty = 'medium';
let messageCount = 0;
let emotionHistory = [];
let sessionId = 'session_' + Date.now();
let currentSchedule = null;
let blockTimers = {};

function apiCall(endpoint, method='GET', body=null) {
    const opts = {
        method,
        headers: {'Content-Type':'application/json','Authorization': AUTH_HEADER}
    };
    if (body) opts.body = JSON.stringify(body);
    return fetch(API_BASE + endpoint, opts).then(r => r.ok ? r.json() : null).catch(() => null);
}

const SUBJ_ICONS = {math:'math',reading:'reading',writing:'pencil',science:'science',social_studies:'globe',break:'sparkle',review:'sync',enrichment:'rocket'};
const SUBJ_COLORS = {math:'var(--cyan)',reading:'var(--magenta)',writing:'var(--purple)',science:'var(--lime)',social_studies:'#ffa500',break:'var(--text-muted)',review:'var(--cyan)',enrichment:'var(--purple)'};
const DAY_NAMES = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];

function getTimeGreeting() {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
}

async function loadDailySchedule() {
    const data = await apiCall('/schedule/today');
    if (!data || !data.blocks) {
        const container = document.getElementById('scheduleBlocks');
        if (container) container.innerHTML = '<div style="text-align:center;padding:30px;color:var(--text-muted)">Could not load today\'s schedule. <span style="color:var(--cyan);cursor:pointer;text-decoration:underline" onclick="loadDailySchedule()">Retry</span></div>';
        return;
    }
    currentSchedule = data;

    const saved = localStorage.getItem('ob_profile');
    let userName = 'Learner';
    try { userName = JSON.parse(saved).name; } catch(e) {}

    const greetEl = document.getElementById('scheduleGreeting');
    if (greetEl) greetEl.textContent = getTimeGreeting() + ', ' + userName + '!';

    const dateEl = document.getElementById('scheduleDate');
    if (dateEl) {
        const d = new Date();
        dateEl.textContent = d.toLocaleDateString('en-US', {weekday:'long',month:'long',day:'numeric',year:'numeric'});
    }

    renderScheduleBlocks(data.blocks);
    updateScheduleProgress(data);
    loadWeekView();
    loadTimeStats();
    initChatFeatures();
}

function renderScheduleBlocks(blocks) {
    const container = document.getElementById('scheduleBlocks');
    if (!container) return;

    const firstIncomplete = blocks.findIndex(b => !b.completed);

    container.innerHTML = blocks.map((b, i) => {
        const isBreak = ['break','review','enrichment'].includes(b.subject);
        const isCurrent = i === firstIncomplete;
        const statusClass = b.completed ? 'completed' : (isCurrent ? 'current' : '');
        const breakClass = isBreak ? 'is-break' : '';
        const iconName = SUBJ_ICONS[b.subject] || 'book';
        const statusIcon = b.completed ? icon('check', 14) : (isCurrent ? icon('play', 14) : (i + 1));
        const statusType = b.completed ? 'done' : (isCurrent ? 'active' : 'upcoming');
        const tagClass = b.activity_type === 'game' ? 'game' : b.activity_type === 'video' ? 'video' : b.activity_type === 'writing' ? 'writing' : b.activity_type === 'creative' ? 'creative' : '';
        const timeSpent = b.time_spent_seconds > 0 ? ' \u2022 ' + Math.round(b.time_spent_seconds / 60) + 'min spent' : '';

        return `<div class="schedule-block ${statusClass} ${breakClass}" onclick="${isBreak && b.completed ? '' : 'startBlock(' + i + ')'}" data-block="${i}">
            <div class="sb-icon ${b.subject}">${icon(iconName, 22)}</div>
            <div class="sb-info">
                <div class="sb-title">${b.title}</div>
                <div class="sb-meta">
                    <span class="sb-tag ${tagClass}">${b.activity_label || b.activity_type}</span>
                    <span>${b.subject_label || b.subject}${timeSpent}</span>
                </div>
            </div>
            <div class="sb-duration">${icon('clock', 12)} ${b.duration_minutes}min</div>
            <div class="sb-status ${statusType}">${statusIcon}</div>
        </div>`;
    }).join('');
}

function updateScheduleProgress(data) {
    const blocks = data.blocks || [];
    const done = blocks.filter(b => b.completed).length;
    const total = blocks.length;
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;

    const bar = document.getElementById('scheduleProgressBar');
    const text = document.getElementById('scheduleProgressText');
    if (bar) bar.style.width = pct + '%';
    if (text) text.textContent = done + ' / ' + total + ' blocks';
}

async function loadWeekView() {
    const data = await apiCall('/schedule/week');
    if (!data || !data.days) return;
    const container = document.getElementById('scheduleWeek');
    if (!container) return;

    container.innerHTML = data.days.map((d, i) => {
        let cls = '';
        if (d.is_today) cls = 'today';
        else if (d.has_schedule && d.completed_blocks >= d.total_blocks && d.total_blocks > 0) cls = 'completed';
        else if (d.has_schedule && d.completed_blocks > 0) cls = 'partial';
        const dayDate = new Date(d.date + 'T12:00:00');
        const dayNum = dayDate.getDate();
        return `<div class="schedule-week-day ${cls}">
            <div class="swd-name">${DAY_NAMES[i]}</div>
            <div class="swd-num">${dayNum}</div>
        </div>`;
    }).join('');
}

async function loadTimeStats() {
    const data = await apiCall('/schedule/time-log?period=week');
    if (!data) return;
    const container = document.getElementById('scheduleStats');
    if (!container) return;

    const subjects = ['math','reading','writing','science','social_studies'];
    const labels = {math:'Math',reading:'Reading',writing:'Writing',science:'Science',social_studies:'Social Studies'};
    let html = '';
    subjects.forEach(s => {
        const hrs = (data.by_subject && data.by_subject[s]) || 0;
        html += `<div class="schedule-stat">
            <div class="schedule-stat-val" style="color:${SUBJ_COLORS[s]}">${hrs}h</div>
            <div class="schedule-stat-label">${labels[s]}</div>
        </div>`;
    });
    html += `<div class="schedule-stat">
        <div class="schedule-stat-val">${data.total_hours || 0}h</div>
        <div class="schedule-stat-label">Total This Week</div>
    </div>`;
    container.innerHTML = html;
}

function startBlock(index) {
    if (!currentSchedule || !currentSchedule.blocks) return;
    const block = currentSchedule.blocks[index];
    if (!block || block.completed) return;

    blockTimers[index] = Date.now();

    const activityType = block.activity_type;

    if (activityType === 'game') {
        switchTab('games');
        showToast(icon('gamepad', 20), 'Game Time!', 'Playing: ' + block.title);
        setTimeout(() => showCompleteBlockPrompt(index), 1000);
    } else if (activityType === 'video') {
        openLesson(index, block);
    } else {
        openLesson(index, block);
    }
}

async function openLesson(index, block) {
    const overlay = document.getElementById('lessonOverlay');
    const viewer = document.getElementById('lessonViewer');
    overlay.classList.add('active');
    overlay.scrollTop = 0;

    const subjLabels = {math:'Mathematics',reading:'Reading',writing:'Writing',science:'Science',social_studies:'Social Studies',review:'Review',enrichment:'Enrichment',break:'Break'};
    const subjLabel = subjLabels[block.subject] || block.subject;

    viewer.innerHTML = `
        <div class="lv-header">
            <div class="lv-back" onclick="closeLesson()">${icon('chevron-left', 18)}</div>
            <div class="lv-header-info">
                <div class="lv-subject-tag ${block.subject}">${subjLabel}</div>
                <div class="lv-title">${block.title}</div>
                <div class="lv-meta"><span>${icon('clock', 12)} ${block.duration_minutes} min</span><span>${block.activity_label || block.activity_type}</span></div>
            </div>
        </div>
        <div class="lv-loading">
            <div class="lv-loading-spinner"></div>
            <div class="lv-loading-text">Preparing your lesson...</div>
        </div>`;

    try {
        const lesson = await apiCall('/schedule/lesson', 'POST', { block_index: index });
        if (lesson) {
            renderLesson(lesson, index, block);
        } else {
            renderFallbackLesson(index, block);
        }
    } catch (e) {
        renderFallbackLesson(index, block);
    }
}

const CURATED_VIDEOS = {
    math: {
        tiny: {id:'PKxVBFdFEZo',title:'Learn to Count 1-10'},
        junior: {id:'_AzFxPxjbJM',title:'Introduction to Multiplication'},
        rising: {id:'WnEPB-bX8HQ',title:'Understanding Fractions'},
    },
    reading: {
        tiny: {id:'36IBDpTRVNE',title:'Phonics Song for Kids'},
        junior: {id:'Wn7UXmENkJo',title:'Reading Comprehension'},
        rising: {id:'yzivtV1x_4A',title:'Story Elements'},
    },
    science: {
        tiny: {id:'6v9LbmGaKXo',title:'Animals for Kids'},
        junior: {id:'e4kCBs9Bwxk',title:'States of Matter'},
        rising: {id:'URUJD5NEXC8',title:'The Solar System'},
    },
    writing: {
        tiny: {id:'WJmKa4Gy6vk',title:'Learn to Write Letters'},
        junior: {id:'4UArfm9eHx4',title:'Writing a Paragraph'},
        rising: {id:'dDIq3F0PBHA',title:'Essay Writing'},
    },
    social_studies: {
        tiny: {id:'9i7SsGqJON0',title:'Community Helpers'},
        junior: {id:'MkUrtGYgMC8',title:'Maps and Geography'},
        rising: {id:'W8OkSAj6rJE',title:'Ancient Civilizations'},
    }
};

function getVideoForLesson(subject) {
    const ag = getAgeGroup();
    const subj = CURATED_VIDEOS[subject];
    if (!subj) return null;
    return subj[ag] || subj.junior || null;
}

function renderLesson(lesson, blockIndex, block) {
    const viewer = document.getElementById('lessonViewer');
    const subjLabels = {math:'Mathematics',reading:'Reading',writing:'Writing',science:'Science',social_studies:'Social Studies',review:'Review',enrichment:'Enrichment',break:'Break'};
    const subjLabel = subjLabels[block.subject] || block.subject;
    const missionIcons = {math:'🔢',reading:'📖',science:'🔬',writing:'✏️',social_studies:'🌍',review:'🔄',enrichment:'⭐',break:'☕'};
    const totalSteps = (lesson.sections ? lesson.sections.length : 0) + (lesson.check_understanding ? 1 : 0);
    const video = getVideoForLesson(block.subject);
    novaReact('lessonStart');

    let html = `
        <div class="lv-header">
            <div class="lv-back" onclick="closeLesson()">${icon('chevron-left', 18)}</div>
            <div class="lv-header-info">
                <div class="lv-subject-tag ${block.subject}">${subjLabel}</div>
                <div class="lv-title">${lesson.title || block.title}</div>
                <div class="lv-meta"><span>${icon('clock', 12)} ${block.duration_minutes} min</span><span>${block.activity_label || block.activity_type}</span></div>
            </div>
            <div class="lv-read-btn" onclick="readLessonAloud(this)" id="readAloudBtn">🔊 Read to Me</div>
        </div>`;

    html += `<div class="lv-mission-header ${block.subject}">
        <div class="lv-mission-title"><span class="mission-icon">${missionIcons[block.subject] || '📚'}</span> Mission</div>
        <div class="lv-mission-name">${lesson.title || block.title}</div>
    </div>`;

    if (totalSteps > 1) {
        html += `<div class="lv-adventure-progress" id="lessonProgress">
            ${Array.from({length: totalSteps}, (_, i) => `
                <div class="lv-step-dot ${i === 0 ? 'active' : ''}" onclick="scrollToLessonStep(${i})" id="stepDot${i}">${i + 1}</div>
                ${i < totalSteps - 1 ? '<div class="lv-step-line" id="stepLine' + i + '"></div>' : ''}
            `).join('')}
        </div>`;
    }

    html += `<div class="lv-nova-inline">
        <img src="/assets/nova-mascot.png" alt="Nova" onerror="this.style.display='none'">
        <div class="nova-text">${lesson.intro ? formatLessonText(lesson.intro) : 'Let\'s explore ' + (lesson.title || block.title) + ' together! I\'ll guide you step by step.'}</div>
    </div>`;

    if (video) {
        html += `<div class="lv-video-section">
            <iframe src="https://www.youtube.com/embed/${video.id}?rel=0&modestbranding=1" allowfullscreen loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe>
            <div class="lv-video-label">🎬 ${escapeHtml(video.title)}</div>
        </div>`;
    }

    if (lesson.objectives && lesson.objectives.length > 0) {
        html += `<div class="lv-objectives">
            <div class="lv-objectives-title">${icon('check', 14)} What You'll Learn</div>
            <div class="lv-obj-list">${lesson.objectives.map(o =>
                `<div class="lv-obj"><div class="lv-obj-check">${icon('check', 10)}</div><span>${o}</span></div>`
            ).join('')}</div>
        </div>`;
    }

    if (lesson.sections) {
        lesson.sections.forEach((s, i) => {
            html += `<div class="lv-section" id="lessonStep${i}" data-step="${i}">
                <div class="lv-section-head">${s.heading}</div>
                <div class="lv-section-content">${formatLessonText(s.content)}</div>
                ${s.example ? `<div class="lv-example">${formatLessonText(s.example)}</div>` : ''}
                ${s.tip ? `<div class="lv-tip">${formatLessonText(s.tip)}</div>` : ''}
                ${generateTryItExercise(s, i, block.subject)}
            </div>`;
        });
    }

    if (lesson.key_vocabulary && lesson.key_vocabulary.length > 0) {
        html += `<div class="lv-vocab">
            <div class="lv-vocab-title">${icon('book', 14)} Key Vocabulary</div>
            <div class="lv-vocab-grid">${lesson.key_vocabulary.map(v =>
                `<div class="lv-vocab-card"><div class="lv-vocab-term">${escapeHtml(v.term)}</div><div class="lv-vocab-def">${escapeHtml(v.definition)}</div></div>`
            ).join('')}</div>
        </div>`;
    }

    if (lesson.check_understanding && lesson.check_understanding.length > 0) {
        const quizStep = lesson.sections ? lesson.sections.length : 0;
        html += `<div class="lv-check" id="lessonStep${quizStep}" data-step="${quizStep}">
            <div class="lv-check-title">${icon('brain', 14)} Check Your Understanding</div>
            ${lesson.check_understanding.map((q, qi) => {
                const safeQ = escapeHtml(q.question);
                const safeOpts = Array.isArray(q.options) ? q.options : [];
                const correctIdx = Math.max(0, Math.min(parseInt(q.correct) || 0, safeOpts.length - 1));
                const safeExpl = escapeHtml(q.explanation || '').replace(/'/g, "\\'");
                return `<div class="lv-quiz-q" id="lvq${qi}">
                    <div class="lv-quiz-question">${safeQ}</div>
                    <div class="lv-quiz-opts">${safeOpts.map((o, oi) =>
                        `<div class="lv-quiz-opt" onclick="checkLessonQuiz(${qi},${oi},${correctIdx},'${safeExpl}')">${escapeHtml(o)}</div>`
                    ).join('')}</div>
                    <div class="lv-quiz-explain" id="lvqe${qi}"></div>
                </div>`;
            }).join('')}
        </div>`;
    }

    if (lesson.summary) {
        html += `<div class="lv-summary">
            <div class="lv-summary-title">${icon('check', 14)} Summary</div>
            <div class="lv-summary-text">${formatLessonText(lesson.summary)}</div>
        </div>`;
    }

    if (lesson.challenge) {
        html += `<div class="lv-challenge">
            <div class="lv-challenge-title">🏆 Challenge</div>
            <div class="lv-challenge-text">${formatLessonText(lesson.challenge)}</div>
        </div>`;
    }

    html += `<div class="lv-actions">
        <button class="lv-btn primary" onclick="completeLessonBlock(${blockIndex})">🎉 Complete Mission!</button>
        <button class="lv-btn secondary" onclick="askNovaAboutLesson('${(lesson.title||block.title).replace(/'/g,"\\'")}')">${icon('robot', 16)} Ask Nova</button>
        <button class="lv-btn secondary" onclick="closeLesson()">${icon('chevron-left', 16)} Back</button>
    </div>`;

    viewer.innerHTML = html;
    setupLessonStepObserver(totalSteps);
}

function generateTryItExercise(section, idx, subject) {
    const heading = (section.heading || '').toLowerCase();
    let q, opts, correct;
    if (subject === 'math' || heading.includes('number') || heading.includes('add') || heading.includes('multiply')) {
        const a = Math.floor(Math.random() * 10) + 1;
        const b = Math.floor(Math.random() * 10) + 1;
        q = `Quick! What is ${a} + ${b}?`;
        correct = a + b;
        opts = [correct, correct + 1, correct - 1, correct + 2].sort(() => Math.random() - 0.5);
    } else if (subject === 'science' || heading.includes('experiment') || heading.includes('observe')) {
        const qs = [{q:'True or False: The sun is a star',opts:['True','False'],c:0},{q:'What do plants need to grow?',opts:['Water & Light','TV','Toys'],c:0}];
        const pick = qs[Math.floor(Math.random() * qs.length)];
        q = pick.q; opts = pick.opts; correct = pick.c;
    } else {
        return '';
    }
    const safeOpts = (Array.isArray(opts) ? opts : []).map(o => String(o));
    const correctVal = typeof correct === 'number' && correct > 100 ? String(correct) : (typeof correct === 'number' && correct < safeOpts.length ? safeOpts[correct] : String(correct));
    return `<div class="lv-tryit">
        <div class="lv-tryit-title">🧪 Try It!</div>
        <div class="lv-tryit-question">${q}</div>
        <div class="lv-tryit-opts">${safeOpts.map((o, oi) =>
            `<div class="lv-tryit-opt" onclick="checkTryIt(this, '${String(o).replace(/'/g,"\\'")}', '${String(correctVal).replace(/'/g,"\\'")}')">${o}</div>`
        ).join('')}</div>
        <div class="lv-tryit-feedback" id="tryitFb${idx}"></div>
    </div>`;
}

function checkTryIt(el, chosen, correct) {
    const parent = el.closest('.lv-tryit');
    parent.querySelectorAll('.lv-tryit-opt').forEach(o => o.classList.add('disabled'));
    if (String(chosen) === String(correct)) {
        el.classList.add('correct');
        novaReact('correct');
        showFloatingXP(10, el.getBoundingClientRect().left, el.getBoundingClientRect().top);
    } else {
        el.classList.add('wrong');
        parent.querySelectorAll('.lv-tryit-opt').forEach(o => { if (o.textContent == correct) o.classList.add('correct'); });
    }
}

function setupLessonStepObserver(totalSteps) {
    if (totalSteps <= 1) return;
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const step = parseInt(entry.target.dataset.step);
                for (let i = 0; i <= step; i++) {
                    const dot = document.getElementById('stepDot' + i);
                    if (dot) dot.classList.add(i < step ? 'complete' : 'active');
                    if (i < step) { const line = document.getElementById('stepLine' + i); if (line) line.classList.add('complete'); }
                }
            }
        });
    }, {threshold: 0.3});
    for (let i = 0; i < totalSteps; i++) {
        const el = document.getElementById('lessonStep' + i);
        if (el) observer.observe(el);
    }
}

function scrollToLessonStep(step) {
    const el = document.getElementById('lessonStep' + step);
    if (el) el.scrollIntoView({behavior: 'smooth', block: 'start'});
}

function readLessonAloud(btn) {
    const viewer = document.getElementById('lessonViewer');
    const text = viewer.innerText.slice(0, 500);
    if (btn.classList.contains('playing')) {
        window.speechSynthesis && window.speechSynthesis.cancel();
        btn.classList.remove('playing');
        btn.textContent = '🔊 Read to Me';
        return;
    }
    if (!window.speechSynthesis) {
        return;
    }
    btn.classList.add('playing');
    btn.textContent = '⏹️ Stop';
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 0.9;
    utter.onend = () => { btn.classList.remove('playing'); btn.textContent = '🔊 Read to Me'; };
    utter.onerror = () => { btn.classList.remove('playing'); btn.textContent = '🔊 Read to Me'; };
    window.speechSynthesis.speak(utter);
}

function renderFallbackLesson(blockIndex, block) {
    const viewer = document.getElementById('lessonViewer');
    const subjLabels = {math:'Mathematics',reading:'Reading',writing:'Writing',science:'Science',social_studies:'Social Studies',review:'Review',enrichment:'Enrichment',break:'Break'};
    const subjLabel = subjLabels[block.subject] || block.subject;
    const missionIcons = {math:'🔢',reading:'📖',science:'🔬',writing:'✏️',social_studies:'🌍',review:'🔄',enrichment:'⭐',break:'☕'};
    const video = getVideoForLesson(block.subject);
    novaReact('lessonStart');

    let html = `
        <div class="lv-header">
            <div class="lv-back" onclick="closeLesson()">${icon('chevron-left', 18)}</div>
            <div class="lv-header-info">
                <div class="lv-subject-tag ${block.subject}">${subjLabel}</div>
                <div class="lv-title">${block.title}</div>
                <div class="lv-meta"><span>${icon('clock', 12)} ${block.duration_minutes} min</span><span>${block.activity_label || block.activity_type}</span></div>
            </div>
        </div>
        <div class="lv-mission-header ${block.subject}">
            <div class="lv-mission-title"><span class="mission-icon">${missionIcons[block.subject] || '📚'}</span> Mission</div>
            <div class="lv-mission-name">${block.title}</div>
        </div>
        <div class="lv-nova-inline">
            <img src="/assets/nova-mascot.png" alt="Nova" onerror="this.style.display='none'">
            <div class="nova-text">Let's explore ${block.title} together! I'll guide you step by step.</div>
        </div>`;

    if (video) {
        html += `<div class="lv-video-section">
            <iframe src="https://www.youtube.com/embed/${video.id}?rel=0&modestbranding=1" allowfullscreen loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe>
            <div class="lv-video-label">🎬 ${escapeHtml(video.title)}</div>
        </div>`;
    }

    html += `
        <div class="lv-section">
            <div class="lv-section-head">About This Lesson</div>
            <div class="lv-section-content">
                <p>${block.description || 'In this lesson, you will explore ' + block.title + '.'}</p>
                <p>Watch the video above or click "Ask Nova" to start learning with your AI tutor!</p>
            </div>
        </div>
        <div class="lv-actions">
            <button class="lv-btn primary" onclick="completeLessonBlock(${blockIndex})">🎉 Complete Mission!</button>
            <button class="lv-btn secondary" onclick="askNovaAboutLesson('${block.title.replace(/'/g,"\\'")}')">${icon('robot', 16)} Ask Nova</button>
            <button class="lv-btn secondary" onclick="closeLesson()">${icon('chevron-left', 16)} Back</button>
        </div>`;

    viewer.innerHTML = html;
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function formatLessonText(text) {
    if (!text) return '';
    let safe = escapeHtml(text);
    return safe
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n- /g, '<br>• ')
        .replace(/\n/g, '<br>')
        .replace(/^- /g, '• ');
}

function checkLessonQuiz(qIndex, optIndex, correctIndex, explanation) {
    const qEl = document.getElementById('lvq' + qIndex);
    if (!qEl) return;
    correctIndex = Math.max(0, Math.min(correctIndex, 3));
    const opts = qEl.querySelectorAll('.lv-quiz-opt');
    opts.forEach(o => o.classList.add('disabled'));
    opts[correctIndex].classList.add('correct');
    if (optIndex === correctIndex) {
        showScreenFlash('correct');
        novaReact('correct');
        showFloatingXP(15);
    } else {
        opts[optIndex].classList.add('wrong');
        showScreenFlash('wrong');
    }
    const explainEl = document.getElementById('lvqe' + qIndex);
    if (explainEl && explanation) {
        explainEl.textContent = explanation;
        explainEl.classList.add('show');
    }
}

function closeLesson() {
    document.getElementById('lessonOverlay').classList.remove('active');
}

async function completeLessonBlock(blockIndex) {
    showCelebration('🎉 Mission Complete!');
    showFloatingXP(30);
    setTimeout(() => {
        closeLesson();
        completeBlock(blockIndex);
    }, 1500);
}

function askNovaAboutLesson(title) {
    closeLesson();
    switchTab('chat');
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = 'Help me learn about ' + title;
        chatInput.focus();
    }
}

function showCompleteBlockPrompt(index) {
    const block = currentSchedule.blocks[index];
    if (!block) return;

    const existing = document.getElementById('blockCompleteBar');
    if (existing) existing.remove();

    const bar = document.createElement('div');
    bar.id = 'blockCompleteBar';
    bar.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:1000;display:flex;align-items:center;gap:12px;padding:12px 20px;border-radius:14px;background:rgba(10,10,26,0.95);backdrop-filter:blur(20px);border:1px solid rgba(0,245,255,0.2);box-shadow:0 8px 32px rgba(0,0,0,0.5);animation:fadeSlide 0.3s ease';
    bar.innerHTML = `
        <span style="color:var(--text-secondary);font-size:13px">${icon(SUBJ_ICONS[block.subject] || 'book', 16)} ${block.title}</span>
        <button onclick="completeBlock(${index})" style="padding:8px 16px;border-radius:10px;border:none;background:linear-gradient(135deg,var(--cyan),var(--lime));color:#000;font-weight:700;font-size:13px;cursor:pointer">${icon('check', 14)} Mark Complete</button>
        <button onclick="this.parentElement.remove()" style="padding:8px 12px;border-radius:10px;border:1px solid var(--glass-border);background:transparent;color:var(--text-muted);cursor:pointer;font-size:12px">Later</button>
    `;
    document.body.appendChild(bar);
}

async function completeBlock(index) {
    const startTime = blockTimers[index] || Date.now();
    const timeSpent = Math.round((Date.now() - startTime) / 1000);

    const result = await apiCall('/schedule/complete-block', 'POST', {
        block_index: index,
        time_spent_seconds: Math.max(timeSpent, 60)
    });

    const bar = document.getElementById('blockCompleteBar');
    if (bar) bar.remove();

    if (result && (result.status === 'completed' || result.status === 'already_completed')) {
        currentSchedule.blocks[index].completed = true;
        currentSchedule.blocks[index].time_spent_seconds = timeSpent;
        renderScheduleBlocks(currentSchedule.blocks);
        updateScheduleProgress(currentSchedule);

        const dp = result.day_progress;
        if (dp && dp.completed === dp.total) {
            showToast(icon('trophy', 24), 'School Day Complete!', 'Amazing work! You finished all ' + dp.total + ' blocks today!');
        } else {
            showToast(icon('check', 20), 'Block Complete!', (dp ? dp.completed + ' of ' + dp.total : '') + ' blocks done');
        }
        loadTimeStats();
    } else {
        showToast(icon('warning', 20), 'Oops!', 'Could not save completion. Try again.');
    }
}

function toggleBrowse(forceShow) {
    const el = document.getElementById('browseContent');
    const btn = document.querySelector('.browse-toggle');
    if (!el) return;
    if (forceShow || !el.classList.contains('visible')) {
        el.classList.add('visible');
        if (btn) btn.textContent = 'Hide Resources';
    } else {
        el.classList.remove('visible');
        if (btn) btn.textContent = 'Show Resources';
    }
}

async function loadProgressReport() {
    const container = document.getElementById('progressReportContainer');
    if (!container) return;
    const data = await apiCall('/schedule/progress-report');
    if (!data) { container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted)">No progress data yet. Complete some schedule blocks to generate your report.</div>'; return; }

    const subjects = ['math','reading','writing','science','social_studies'];
    const labels = {math:'Mathematics',reading:'Reading',writing:'Writing',science:'Science',social_studies:'Social Studies'};
    const colors = {math:'var(--cyan)',reading:'var(--magenta)',writing:'var(--purple)',science:'var(--lime)',social_studies:'#ffa500'};

    let html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px">';
    subjects.forEach(s => {
        const eq = (data.grade_equivalencies && data.grade_equivalencies[s]) || 0;
        const hrs = (data.total_hours && data.total_hours[s]) || 0;
        html += `<div style="padding:14px;border-radius:12px;background:rgba(255,255,255,0.03);border:1px solid var(--glass-border);text-align:center">
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px">${labels[s]}</div>
            <div style="font-size:24px;font-weight:800;color:${colors[s]}">G${eq}</div>
            <div style="font-size:10px;color:var(--text-muted);margin-top:4px">${hrs}h this month</div>
        </div>`;
    });
    html += '</div>';

    if (data.ai_summary) {
        html += `<div style="padding:12px 16px;border-radius:10px;background:rgba(0,245,255,0.04);border:1px solid rgba(0,245,255,0.1);font-size:13px;color:var(--text-secondary);line-height:1.5">${data.ai_summary}</div>`;
    }

    const mastered = data.standards_mastered ? data.standards_mastered.length : 0;
    const inProg = data.standards_in_progress ? data.standards_in_progress.length : 0;
    html += `<div style="display:flex;gap:16px;margin-top:12px;font-size:12px;color:var(--text-muted)">
        <span>${icon('check', 12)} <strong style="color:var(--lime)">${mastered}</strong> standards mastered</span>
        <span>${icon('clock', 12)} <strong style="color:var(--cyan)">${inProg}</strong> in progress</span>
    </div>`;

    container.innerHTML = html;
}

async function loadTimeOnTask() {
    const container = document.getElementById('timeOnTaskContainer');
    if (!container) return;
    const data = await apiCall('/schedule/time-log?period=week');
    if (!data || !data.by_subject) { container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted)">No time data yet this week.</div>'; return; }

    const subjects = ['math','reading','writing','science','social_studies'];
    const labels = {math:'Math',reading:'Reading',writing:'Writing',science:'Science',social_studies:'Social Studies'};
    const colors = {math:'var(--cyan)',reading:'var(--magenta)',writing:'var(--purple)',science:'var(--lime)',social_studies:'#ffa500'};

    const maxHours = Math.max(...subjects.map(s => data.by_subject[s] || 0), 1);

    let html = '';
    subjects.forEach(s => {
        const hrs = data.by_subject[s] || 0;
        const pct = Math.round((hrs / maxHours) * 100);
        html += `<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
            <div style="width:90px;font-size:12px;color:var(--text-secondary);text-align:right">${labels[s]}</div>
            <div style="flex:1;height:20px;background:rgba(255,255,255,0.04);border-radius:6px;overflow:hidden">
                <div style="height:100%;width:${pct}%;background:${colors[s]};border-radius:6px;transition:width 0.5s ease;min-width:${hrs > 0 ? '2px' : '0'}"></div>
            </div>
            <div style="width:50px;font-size:12px;color:var(--text-muted);font-weight:600">${hrs}h</div>
        </div>`;
    });

    html += `<div style="text-align:right;margin-top:8px;font-size:13px;color:var(--cyan);font-weight:600">Total: ${data.total_hours || 0}h this week</div>`;
    container.innerHTML = html;
}

function switchTab(tab) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById('panel-' + tab).classList.add('active');
    document.querySelectorAll(`.tab-btn[data-tab="${tab}"]`).forEach(b => b.classList.add('active'));
    document.querySelectorAll(`.nav-item[data-tab="${tab}"]`).forEach(n => n.classList.add('active'));
    if (tab === 'knowledge') loadProgressDashboard();
    if (tab === 'games') connectGameWs();
    if (tab === 'learn') loadDailySchedule();
    if (tab === 'analytics') {
        setTimeout(renderCharts, 50);
        loadReviewSchedule();
        loadProgressReport();
        loadTimeOnTask();
    }
}

function setSubject(subject, btn) {
    currentSubject = subject;
    document.querySelectorAll('.subject-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const labels = {math:icon('math', 14)+' Math',science:icon('science', 14)+' Science',reading:icon('reading', 14)+' Reading',coding:icon('coding', 14)+' Coding'};
    document.getElementById('chatTopicTag').innerHTML = labels[subject] || subject;
}

function updateDifficulty() {
    currentDifficulty = document.getElementById('difficultySelect').value;
}

function renderMarkdown(text) {
    return text
        .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        .replace(/\n/g, '<br>');
}

const AGENT_LABELS = {
    domain_expert: 'Domain Expert',
    socratic_guide: 'Socratic Guide',
    metacog_coach: 'Metacog Coach',
    error_analyst: 'Error Analyst',
    orchestrator: 'Orchestrator'
};

function addMessage(text, isUser, meta=null) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `msg ${isUser ? 'user' : 'ai'}`;
    let metaHtml = '';
    let coachingHtml = '';
    if (meta) {
        metaHtml = '<div class="msg-meta">';
        if (meta.agent) {
            const label = AGENT_LABELS[meta.agent] || meta.agent;
            metaHtml += `<span class="agent-badge ${meta.agent}">${icon('robot', 10)} ${label}</span>`;
        }
        if (meta.model) {
            metaHtml += `<span class="agent-badge claude">${icon('zap', 10)} ${meta.model}</span>`;
        }
        if (meta.usedThinking) {
            metaHtml += `<span class="thinking-badge">${icon('brain', 10)} Deep Thinking</span>`;
        }
        if (meta.strategy) metaHtml += `<span class="meta-tag strategy">${icon('target', 12)} ${meta.strategy}</span>`;
        if (meta.emotion) metaHtml += `<span class="meta-tag emotion">${icon('heart', 12)} ${meta.emotion}</span>`;
        if (meta.concepts && meta.concepts.length) {
            meta.concepts.forEach(c => { metaHtml += `<span class="meta-tag concept">${icon('pin', 12)} ${c}</span>`; });
        }
        metaHtml += '</div>';
        if (meta.coaching) {
            coachingHtml = `<div class="coaching-tip"><strong>💡 Learning Tip</strong><br>${meta.coaching}</div>`;
        }
    }
    div.innerHTML = `
        <div class="msg-avatar">${isUser ? icon('avatar', 18) : icon('robot', 18)}</div>
        <div class="msg-body">
            <div class="msg-bubble">${renderMarkdown(text)}</div>
            ${coachingHtml}
            ${metaHtml}
        </div>`;
    container.appendChild(div);
    requestAnimationFrame(() => {
        div.scrollIntoView({behavior: 'smooth', block: 'end'});
    });
}

function showTyping() {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'typing-indicator';
    div.id = 'typingIndicator';
    div.innerHTML = `
        <div class="msg-avatar" style="background:linear-gradient(135deg,rgba(217,119,87,0.25),rgba(139,92,246,0.25));border:1.5px solid rgba(217,119,87,0.25);width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 0 12px rgba(217,119,87,0.15)">${icon('robot', 18)}</div>
        <div>
            <div class="typing-dots"><span></span><span></span><span></span></div>
            <div class="neural-processing"><div class="brain-pulse">${icon('brain', 18)}</div>Nova is reasoning with Claude AI...</div>
        </div>`;
    container.appendChild(div);
    requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
}

function hideTyping() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

function getStudentAge() {
    try {
        const saved = localStorage.getItem('ob_profile');
        if (saved) {
            const profile = JSON.parse(saved);
            if (profile.age) return parseInt(profile.age);
        }
    } catch(e) {}
    return 9;
}

function getStudentAgeGroup() {
    try {
        const saved = localStorage.getItem('ob_profile');
        if (saved) {
            const profile = JSON.parse(saved);
            if (profile.ageGroup) return profile.ageGroup;
        }
    } catch(e) {}
    return 'junior';
}

function updateChatSuggestedTopics() {
    const container = document.getElementById('chatSuggestedTopics');
    if (!container) return;
    const chips = [];
    if (currentSchedule && currentSchedule.blocks) {
        currentSchedule.blocks.forEach(b => {
            if (!b.completed && b.subject && !['break','review','enrichment'].includes(b.subject)) {
                const title = b.standard_title || b.title || '';
                if (title) {
                    const subj = b.subject.charAt(0).toUpperCase() + b.subject.slice(1);
                    chips.push({label: 'Help me with ' + title, subject: b.subject, message: 'Help me understand ' + title});
                }
            }
        });
    }
    if (chips.length === 0) {
        chips.push({label: 'Teach me something new', subject: 'math', message: 'Teach me something new and interesting!'});
        chips.push({label: 'Practice problems', subject: currentSubject, message: 'Give me some practice problems for ' + currentSubject});
        chips.push({label: 'Fun facts', subject: 'science', message: 'Tell me a fun science fact!'});
    }
    const uniqueChips = chips.slice(0, 4);
    container.innerHTML = '<div class="suggested-label">' + icon('sparkle', 10) + ' Suggested Topics</div>' +
        uniqueChips.map(c => '<button class="suggested-chip" onclick="useSuggestedTopic(\'' + c.message.replace(/'/g, "\\'") + '\')">' + c.label + '</button>').join('');
}

function useSuggestedTopic(message) {
    const input = document.getElementById('chatInput');
    if (input) {
        input.value = message;
        sendChatMessage();
    }
}

function quickAction(action) {
    const age = getStudentAge();
    let message = '';
    switch(action) {
        case 'quiz':
            message = 'Quiz me on ' + currentSubject + '! Give me a fun challenge.';
            break;
        case 'story':
            message = 'Tell me an educational story about ' + currentSubject + ' that would be great for someone my age.';
            break;
        case 'explain':
            message = 'Explain the current topic like I\'m ' + age + ' years old. Make it simple and fun!';
            break;
        case 'draw':
            message = 'Can you describe a visual diagram or drawing that would help me understand ' + currentSubject + ' better?';
            break;
    }
    if (message) {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = message;
            sendChatMessage();
        }
    }
}

function updateChatPlaceholder() {
    const input = document.getElementById('chatInput');
    if (!input) return;
    const age = getStudentAge();
    const ageGroup = getStudentAgeGroup();
    let placeholder = 'Ask me anything...';
    if (currentSchedule && currentSchedule.blocks) {
        const current = currentSchedule.blocks.find(b => !b.completed && !['break','review','enrichment'].includes(b.subject));
        if (current) {
            const title = current.standard_title || current.title || current.subject;
            if (ageGroup === 'tiny') {
                placeholder = 'Ask about ' + title + '! I\'m here to help ✨';
            } else if (ageGroup === 'rising') {
                placeholder = 'Ask about ' + title + ' or anything else...';
            } else {
                placeholder = 'Ask me about ' + title + '...';
            }
        }
    }
    input.placeholder = placeholder;
}

function initChatFeatures() {
    const age = getStudentAge();
    const explainBtn = document.getElementById('explainBtn');
    if (explainBtn) explainBtn.textContent = 'Explain Like I\'m ' + age;
    updateChatSuggestedTopics();
    updateChatPlaceholder();
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    addMessage(text, true);
    messageCount++;
    showTyping();

    const studentAge = getStudentAge();

    try {
        await apiCall('/ai-models/bkt/predict', 'POST', {
            skill_id: currentSubject, skill_name: currentSubject,
            attempts: messageCount, successes: Math.floor(messageCount*0.7), previous_mastery: 0.3
        });
    } catch(e) {}

    let chatResponse = null;
    try {
        chatResponse = await apiCall('/chat/message', 'POST', {
            message: text,
            context: {
                subject: currentSubject,
                difficulty: currentDifficulty,
                session_id: sessionId,
                student_age: studentAge,
                emotion: 'neutral'
            }
        });
    } catch(e) {}

    hideTyping();

    let responseText = '';
    let strategy = 'Socratic Questioning';
    let detectedEmotion = 'neutral';
    if (chatResponse && chatResponse.response) {
        responseText = chatResponse.response;
        strategy = chatResponse.teaching_strategy || strategy;
        detectedEmotion = chatResponse.emotion_analysis?.primary_emotion || chatResponse.detected_emotion || chatResponse.emotion || 'neutral';
        const emotionConf = chatResponse.emotion_analysis?.confidence;
        const coachingMeta = chatResponse.metacognitive_coaching;
        let coachingText = null;
        if (coachingMeta && coachingMeta.triggered && coachingMeta.strategy_tip) {
            coachingText = coachingMeta.strategy_tip;
        }
        addMessage(responseText, false, {
            strategy: strategy,
            emotion: detectedEmotion,
            concepts: chatResponse.concepts_covered || [],
            agent: chatResponse.agent_used || null,
            model: chatResponse.model || null,
            usedThinking: chatResponse.used_thinking || false,
            coaching: coachingText
        });
        if (chatResponse.difficulty_adjustment) {
            const sel = document.getElementById('difficultySelect');
            if (chatResponse.difficulty_adjustment === 'decrease') sel.value = 'easy';
            else if (chatResponse.difficulty_adjustment === 'increase') sel.value = 'hard';
        }
        if (emotionConf) {
            updateEmotionGauge(detectedEmotion, emotionConf);
        }
    } else {
        const fallbackResponses = {
            math: "That's an excellent math question! Let me think about this with you. What do you already know about this topic? Understanding what you know helps me guide you better. Try breaking the problem into smaller parts — what's the first step you'd take?",
            science: "What a fascinating science question! The natural world is full of wonders. Let's explore this together — can you tell me what you've observed about this? Science is all about observation and asking 'why'!",
            reading: "Great question about reading! Understanding text is like being a detective — we look for clues the author leaves us. What part of the text made you curious? Let's look at it together and find the key ideas.",
            coding: "Awesome coding question! Programming is like giving instructions to a very literal friend. Let's break this down step by step. What do you think the code should do first? Think about it like a recipe — each step builds on the last."
        };
        responseText = fallbackResponses[currentSubject] || fallbackResponses.math;
        addMessage(responseText, false, {
            strategy: 'Socratic Questioning',
            emotion: 'engaged',
            concepts: [currentSubject]
        });
    }

    if (detectedEmotion && detectedEmotion !== 'neutral') {
        updateEmotionGauge(detectedEmotion, 0.7);
    }

    avatarReact(strategy, detectedEmotion);

    if (autoReadEnabled && responseText) {
        speakText(responseText);
    }

    const lastMsg = document.querySelector('#chatMessages .msg.ai:last-child');
    if (lastMsg && responseText) {
        addSpeakerButton(lastMsg, responseText);
    }
}

function updateEmotionGauge(emotion, confidence) {
    const conf = Math.round((confidence || 0.65) * 100);
    const emojis = {engaged:'face-happy',confused:'face-sad',frustrated:'face-frustrated',excited:'face-excited',confident:'face-cool',bored:'face-neutral',neutral:'face-neutral',happy:'face-laughing',curious:'face-thinking'};
    const colors = {engaged:'var(--lime)',confused:'#ffaa00',frustrated:'#ff4444',excited:'var(--magenta)',confident:'var(--cyan)',bored:'var(--text-muted)',neutral:'var(--cyan)',happy:'var(--lime)',curious:'var(--purple)'};
    document.getElementById('emotionEmoji').innerHTML = icon(emojis[emotion] || 'face-happy', 28);
    document.getElementById('emotionPct').textContent = conf + '%';
    document.getElementById('emotionName').textContent = emotion ? emotion.charAt(0).toUpperCase() + emotion.slice(1) : 'Neutral';
    const fill = document.getElementById('emotionGaugeFill');
    const offset = 314 - (314 * conf / 100);
    fill.style.strokeDashoffset = offset;
    fill.style.stroke = colors[emotion] || 'var(--cyan)';

    emotionHistory.push(conf);
    if (emotionHistory.length > 20) emotionHistory.shift();
    drawSparkline();
}

function drawSparkline() {
    const canvas = document.getElementById('emotionSparkline');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.offsetWidth * 2;
    const h = canvas.height = canvas.offsetHeight * 2;
    ctx.clearRect(0, 0, w, h);
    if (emotionHistory.length < 2) return;
    ctx.strokeStyle = 'rgba(0,245,255,0.5)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    emotionHistory.forEach((v, i) => {
        const x = (i / (emotionHistory.length - 1)) * w;
        const y = h - (v / 100) * h;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(0,245,255,0.1)');
    grad.addColorStop(1, 'rgba(0,245,255,0)');
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.fillStyle = grad;
    ctx.fill();
}

function checkAnswer(el, result) {
    if (document.querySelector('.exercise-option.correct, .exercise-option.wrong')) return;
    el.classList.add(result);
    if (result === 'correct') {
        showToast(icon('confetti', 20), 'Correct!', '+50 XP earned!');
        animateXP(50);
    } else {
        const correct = el.parentElement.querySelector('[onclick*="correct"]');
        if (correct) setTimeout(() => correct.classList.add('correct'), 300);
        showToast(icon('muscle', 20), 'Not quite!', 'Keep trying — you\'re learning!');
    }
}

function animateXP(amount) {
    const bar = document.getElementById('xpBar');
    const current = parseFloat(bar.style.width) || 65;
    const newW = Math.min(current + amount / 100, 100);
    bar.style.width = newW + '%';
}

function showToast(icon, title, desc) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-text">
            <div class="toast-title">${title}</div>
            <div class="toast-desc">${desc}</div>
        </div>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function loadLesson(id) {
    showToast(icon('book', 20), 'Loading Lesson', 'Preparing your next lesson...');
}

let videoLibrary = [];
let currentVideo = null;
let videoQuizAnswers = {};
let videoPlayTimer = null;

async function loadVideoLibrary(subject) {
    const grid = document.getElementById('videoGrid');
    grid.innerHTML = '<div class="video-loading">Loading videos...</div>';
    let endpoint = '/videos/library';
    if (subject && subject !== 'all') endpoint += '?subject=' + subject;
    const data = await apiCall(endpoint);
    if (data && data.videos) {
        videoLibrary = data.videos;
        renderVideoGrid(data.videos);
        const stats = document.getElementById('videoStats');
        stats.innerHTML = `<span>${icon('video', 14)} ${data.total} videos</span><span>${icon('check', 14)} ${data.watched} watched</span>`;
    } else {
        grid.innerHTML = '<div class="video-loading">No videos available yet</div>';
    }
}

function renderVideoGrid(videos) {
    const grid = document.getElementById('videoGrid');
    if (!videos.length) {
        grid.innerHTML = '<div class="video-loading">No videos found</div>';
        return;
    }
    const subjColors = {math:'var(--cyan)',science:'var(--lime)',reading:'var(--magenta)',coding:'var(--purple)'};
    grid.innerHTML = videos.map(v => `
        <div class="video-card ${v.watched ? 'watched' : ''}" onclick="openVideoModal('${v.id}')">
            <div class="video-card-thumb">
                ${v.thumbnail_icon}
                <div class="video-card-duration">${v.duration_formatted}</div>
                ${v.watched ? '<div class="video-card-watched">' + icon('check', 12) + ' Watched</div>' : ''}
            </div>
            <div class="video-card-subj" style="color:${subjColors[v.subject]||'var(--cyan)'}">${v.subject}</div>
            <div class="video-card-title">${v.title}</div>
            <div class="video-card-desc">${v.description}</div>
            <div class="video-card-meta">
                <span>${icon('reading', 14)} ${v.topic}</span>
                <span>${icon('star', 14)} ${v.difficulty}</span>
                ${v.quiz_score !== null && v.quiz_score !== undefined ? `<span>${icon('pencil', 14)} ${Math.round(v.quiz_score*100)}%</span>` : ''}
            </div>
        </div>
    `).join('');
}

function filterVideos(subject, btn) {
    document.querySelectorAll('.video-filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadVideoLibrary(subject);
}

async function openVideoModal(videoId) {
    const data = await apiCall('/videos/' + videoId);
    if (!data) { showToast(icon('cross', 20),'Error','Could not load video'); return; }
    currentVideo = data;
    videoQuizAnswers = {};
    document.getElementById('videoModalTitle').textContent = data.title;
    document.getElementById('videoPlaceholderText').textContent = data.title;
    document.getElementById('videoPlaceholderDesc').textContent = data.topic + ' • ' + data.duration_formatted;
    document.getElementById('videoDetailDesc').textContent = data.description;
    document.getElementById('videoDetailMeta').innerHTML =
        `<span>${icon('reading', 14)} ${data.subject} — ${data.topic}</span>` +
        `<span>${icon('star', 14)} ${data.difficulty}</span>` +
        `<span>${icon('clock', 14)} ${data.duration_formatted}</span>` +
        `<span>${icon('magnifier', 14)} ${data.view_count} views</span>`;
    document.getElementById('videoPlaceholder').style.display = 'flex';
    document.getElementById('videoProgressBar').style.display = 'none';
    document.getElementById('videoProgressFill').style.width = '0%';
    document.getElementById('videoPlayBtn').style.display = '';
    document.getElementById('videoPlayBtn').innerHTML = icon('play', 16) + ' Play Video';
    document.getElementById('videoQuizArea').style.display = 'none';
    document.getElementById('videoModal').style.display = 'flex';
}

function closeVideoModal() {
    document.getElementById('videoModal').style.display = 'none';
    if (videoPlayTimer) { clearInterval(videoPlayTimer); videoPlayTimer = null; }
    currentVideo = null;
}

function simulateVideoPlay() {
    if (!currentVideo) return;
    const btn = document.getElementById('videoPlayBtn');
    btn.style.display = 'none';
    const bar = document.getElementById('videoProgressBar');
    bar.style.display = 'block';
    const fill = document.getElementById('videoProgressFill');
    const placeholderIcon = document.querySelector('.video-placeholder-icon');
    placeholderIcon.innerHTML = icon('play', 40);
    const duration = Math.min(currentVideo.duration_seconds, 10);
    let elapsed = 0;
    videoPlayTimer = setInterval(() => {
        elapsed += 0.1;
        const pct = Math.min((elapsed / duration) * 100, 100);
        fill.style.width = pct + '%';
        if (elapsed >= duration) {
            clearInterval(videoPlayTimer);
            videoPlayTimer = null;
            onVideoComplete();
        }
    }, 100);
}

async function onVideoComplete() {
    if (!currentVideo) return;
    document.querySelector('.video-placeholder-icon').innerHTML = icon('check', 40);
    document.querySelector('.video-placeholder-text').textContent = 'Video Complete!';
    if (currentVideo.quiz_data && currentVideo.quiz_data.questions && currentVideo.quiz_data.questions.length) {
        renderVideoQuiz(currentVideo.quiz_data.questions);
    } else {
        const res = await apiCall('/videos/' + currentVideo.id + '/complete', 'POST', {});
        if (res) {
            showToast(icon('film', 20), 'Video Complete!', '+' + res.xp_earned + ' XP earned!');
            animateXP(res.xp_earned);
        }
        loadVideoLibrary('all');
    }
}

function renderVideoQuiz(questions) {
    const area = document.getElementById('videoQuizArea');
    const container = document.getElementById('videoQuizQuestions');
    videoQuizAnswers = {};
    container.innerHTML = questions.map((q, i) => `
        <div class="video-quiz-q" data-qi="${i}">
            <div class="video-quiz-q-text">${i+1}. ${q.q}</div>
            <div class="video-quiz-opts">
                ${q.options.map((opt, oi) => `
                    <div class="video-quiz-opt" data-qi="${i}" data-oi="${oi}" onclick="selectVideoQuizOpt(this,${i},${oi})">${opt}</div>
                `).join('')}
            </div>
        </div>
    `).join('');
    document.getElementById('videoQuizSubmit').disabled = false;
    document.getElementById('videoQuizSubmit').textContent = 'Submit Answers';
    area.style.display = 'block';
}

function selectVideoQuizOpt(el, qi, oi) {
    document.querySelectorAll(`.video-quiz-opt[data-qi="${qi}"]`).forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
    videoQuizAnswers[qi] = oi;
}

async function submitVideoQuiz() {
    if (!currentVideo || !currentVideo.quiz_data) return;
    const questions = currentVideo.quiz_data.questions;
    let correct = 0;
    questions.forEach((q, i) => {
        const opts = document.querySelectorAll(`.video-quiz-opt[data-qi="${i}"]`);
        opts.forEach(o => {
            const oi = parseInt(o.dataset.oi);
            if (oi === q.answer) o.classList.add('correct');
            else if (videoQuizAnswers[i] === oi) o.classList.add('wrong');
            o.style.pointerEvents = 'none';
        });
        if (videoQuizAnswers[i] === q.answer) correct++;
    });
    const score = questions.length > 0 ? correct / questions.length : 0;
    const btn = document.getElementById('videoQuizSubmit');
    btn.disabled = true;
    btn.textContent = `Score: ${correct}/${questions.length} (${Math.round(score*100)}%)`;
    const resultDiv = document.createElement('div');
    resultDiv.className = 'video-quiz-result';
    resultDiv.style.background = score >= 0.7 ? 'rgba(0,255,136,0.1)' : 'rgba(255,165,0,0.1)';
    resultDiv.style.color = score >= 0.7 ? 'var(--lime)' : '#ffaa00';
    resultDiv.innerHTML = score >= 0.7 ? icon('confetti', 18) + ' Great job!' : icon('muscle', 18) + ' Keep practicing!';
    document.getElementById('videoQuizArea').appendChild(resultDiv);
    const res = await apiCall('/videos/' + currentVideo.id + '/complete', 'POST', { quiz_score: score });
    if (res) {
        showToast(icon('film', 20), 'Video Complete!', '+' + res.xp_earned + ' XP earned!');
        animateXP(res.xp_earned);
    }
    loadVideoLibrary('all');
}

let progressFilter = 'all';
let progressCurriculumData = null;
let progressReportData = null;

async function loadProgressDashboard() {
    const grid = document.getElementById('progressCardsGrid');
    if (!grid) return;

    renderProgressWeekHistory();

    const [currData, reportData] = await Promise.all([
        apiCall('/schedule/curriculum').catch(() => null),
        apiCall('/schedule/progress-report').catch(() => null)
    ]);

    progressCurriculumData = currData;
    progressReportData = reportData;

    if (reportData) {
        const mastered = reportData.standards_mastered ? reportData.standards_mastered.length : 0;
        const weekStreak = reportData.week_streak || 0;
        const el1 = document.getElementById('progressWeekStreak');
        const el2 = document.getElementById('progressDailyCount');
        if (el1) el1.textContent = '🔥 ' + weekStreak + ' week streak';
        if (el2) el2.textContent = '✅ ' + mastered + ' standards mastered';
    }

    renderProgressCards();
}

function renderProgressWeekHistory() {
    const container = document.getElementById('progressWeekHistory');
    if (!container) return;
    const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    const today = new Date();
    const dayOfWeek = (today.getDay() + 6) % 7;
    let html = '';
    days.forEach((d, i) => {
        let cls = 'progress-day-dot';
        if (i === dayOfWeek) cls += ' today';
        else if (i < dayOfWeek) cls += ' completed';
        html += '<div class="' + cls + '">' + d + '</div>';
    });
    container.innerHTML = html;
}

function renderProgressCards() {
    const grid = document.getElementById('progressCardsGrid');
    if (!grid) return;

    const subjects = ['math','reading','writing','science','social_studies'];
    const labels = {math:'Mathematics',reading:'Reading',writing:'Writing',science:'Science',social_studies:'Social Studies'};
    const icons = {math:'math',reading:'reading',writing:'pencil',science:'science',social_studies:'globe'};
    const colors = {math:'var(--cyan)',reading:'var(--magenta)',writing:'var(--purple)',science:'var(--lime)',social_studies:'#ffa500'};

    const filtered = progressFilter === 'all' ? subjects : subjects.filter(s => s === progressFilter);

    if (filtered.length === 0) {
        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-muted)">No subjects match this filter.</div>';
        return;
    }

    const standards = (progressCurriculumData && progressCurriculumData.standards) || [];
    const report = progressReportData || {};
    const masteredList = report.standards_mastered || [];
    const inProgressList = report.standards_in_progress || [];
    const gradeEq = report.grade_equivalencies || {};
    const totalHours = report.total_hours || {};

    let html = '';
    filtered.forEach(subj => {
        const subjStandards = standards.filter(s => s.subject === subj);
        const totalStd = subjStandards.length || 1;
        const masteredCount = masteredList.filter(s => {
            const found = standards.find(st => st.title === s || st.id === s);
            return found && found.subject === subj;
        }).length;
        const inProgCount = inProgressList.filter(s => {
            const found = standards.find(st => st.title === s || st.id === s);
            return found && found.subject === subj;
        }).length;
        const masteryPct = totalStd > 0 ? Math.round((masteredCount / totalStd) * 100) : 0;
        const circumference = Math.PI * 2 * 21;
        const offset = circumference - (circumference * masteryPct / 100);
        const currentStandard = subjStandards.find((s, i) => i >= masteredCount) || subjStandards[0];
        const ge = gradeEq[subj] || 0;
        const hrs = totalHours[subj] || 0;

        html += '<div class="progress-subject-card ' + subj + '">';
        html += '<div class="psc-header">';
        html += '<div class="psc-title"><span class="ic" data-i="' + icons[subj] + '" data-s="18"></span> ' + labels[subj] + '</div>';
        html += '<div class="psc-ring">';
        html += '<svg viewBox="0 0 52 52"><circle class="ring-bg" cx="26" cy="26" r="21"/>';
        html += '<circle class="ring-fill" cx="26" cy="26" r="21" stroke="' + colors[subj] + '" stroke-dasharray="' + circumference.toFixed(1) + '" stroke-dashoffset="' + offset.toFixed(1) + '"/></svg>';
        html += '<div class="psc-ring-label" style="color:' + colors[subj] + '">' + masteryPct + '%</div>';
        html += '</div></div>';

        if (currentStandard) {
            html += '<div class="psc-current">';
            html += '<div class="psc-current-label">Currently Working On</div>';
            html += '<div class="psc-current-title">' + (currentStandard.title || 'General Practice') + '</div>';
            html += '</div>';
        }

        html += '<div class="psc-stats">';
        html += '<div class="psc-stat"><div class="psc-stat-val" style="color:var(--lime)">' + masteredCount + '</div><div class="psc-stat-label">Mastered</div></div>';
        html += '<div class="psc-stat"><div class="psc-stat-val" style="color:var(--cyan)">' + inProgCount + '</div><div class="psc-stat-label">In Progress</div></div>';
        html += '<div class="psc-stat"><div class="psc-stat-val" style="color:var(--text-secondary)">' + totalStd + '</div><div class="psc-stat-label">Total</div></div>';
        if (ge) html += '<div class="psc-stat"><div class="psc-stat-val" style="color:' + colors[subj] + '">G' + ge + '</div><div class="psc-stat-label">Grade Eq.</div></div>';
        html += '</div>';

        html += '<div class="psc-mastery-bar"><div class="psc-mastery-fill" style="width:' + masteryPct + '%;background:' + colors[subj] + '"></div></div>';
        html += '<div class="psc-mastery-text"><span>' + masteredCount + '/' + totalStd + ' standards</span>';
        if (hrs) html += '<span>' + hrs + 'h logged</span>';
        html += '</div>';

        if (subjStandards.length > 0) {
            const listId = 'stdList_' + subj;
            html += '<button class="psc-standards-toggle" onclick="toggleStandardsList(\'' + listId + '\',this)">Standards Checklist ▼</button>';
            html += '<div class="psc-standards-list collapsed" id="' + listId + '">';
            subjStandards.forEach(std => {
                const isMastered = masteredList.includes(std.title) || masteredList.includes(std.id);
                const isInProg = inProgressList.includes(std.title) || inProgressList.includes(std.id);
                let checkCls = 'not-started';
                let checkIcon = '○';
                if (isMastered) { checkCls = 'mastered'; checkIcon = '✓'; }
                else if (isInProg) { checkCls = 'in-progress'; checkIcon = '◐'; }
                html += '<div class="psc-standard-item">';
                html += '<div class="std-check ' + checkCls + '">' + checkIcon + '</div>';
                html += '<div class="std-name">' + (std.title || 'Standard') + '</div>';
                html += '</div>';
            });
            html += '</div>';
        }

        html += '</div>';
    });

    grid.innerHTML = html;
    populateIcons();
}

function toggleStandardsList(id, btn) {
    const el = document.getElementById(id);
    if (!el) return;
    const isExpanded = el.classList.contains('expanded');
    el.classList.toggle('expanded', !isExpanded);
    el.classList.toggle('collapsed', isExpanded);
    btn.textContent = isExpanded ? 'Standards Checklist ▼' : 'Standards Checklist ▲';
}

function filterProgress(filter, btn) {
    document.querySelectorAll('.progress-filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    progressFilter = filter;
    renderProgressCards();
}

async function loadReviewSchedule() {
    const container = document.getElementById('reviewSchedule');
    if (!container) return;
    try {
        const data = await apiCall('/curriculum/review-schedule');
        if (data && data.schedule && data.schedule.length > 0) {
            container.innerHTML = '';
            data.schedule.forEach(item => {
                let urgencyColor;
                if (item.days_overdue > 0) urgencyColor = '#ff4444';
                else if (item.days_overdue > -1) urgencyColor = '#ffaa00';
                else if (item.days_overdue > -3) urgencyColor = 'var(--lime)';
                else urgencyColor = 'var(--cyan)';

                let dateText;
                if (item.days_overdue > 0) dateText = 'Overdue';
                else if (item.days_overdue > -0.01) dateText = 'Due today';
                else if (item.days_overdue > -1) dateText = 'Due tomorrow';
                else dateText = 'In ' + Math.abs(Math.round(item.days_overdue)) + ' days';

                const div = document.createElement('div');
                div.className = 'review-item';
                div.innerHTML = `<div class="ri-urgency" style="background:${urgencyColor}"></div><div class="ri-name">${item.skill_name} (${Math.round(item.mastery * 100)}%)</div><div class="ri-date">${dateText}</div>`;
                container.appendChild(div);
            });
            return;
        }
    } catch(e) {}
}

function renderCharts() {
    renderTimeChart();
    renderMasteryChart();
    renderEmotionChart();
}

function renderTimeChart() {
    const canvas = document.getElementById('chartTime');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.offsetWidth * 2;
    const h = canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    const cw = canvas.offsetWidth, ch = canvas.offsetHeight;
    ctx.clearRect(0, 0, cw, ch);

    const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    const data = [25, 40, 30, 55, 45, 20, 35];
    const maxVal = Math.max(...data) * 1.2;
    const padding = {top:20,right:20,bottom:30,left:40};
    const plotW = cw - padding.left - padding.right;
    const plotH = ch - padding.top - padding.bottom;

    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + (plotH / 4) * i;
        ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(cw - padding.right, y); ctx.stroke();
        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.font = '10px Inter';
        ctx.textAlign = 'right';
        ctx.fillText(Math.round(maxVal - (maxVal/4)*i) + 'm', padding.left - 5, y + 3);
    }

    days.forEach((d, i) => {
        const x = padding.left + (plotW / (days.length - 1)) * i;
        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.font = '10px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(d, x, ch - 8);
    });

    const grad = ctx.createLinearGradient(0, padding.top, 0, ch - padding.bottom);
    grad.addColorStop(0, 'rgba(0,245,255,0.2)');
    grad.addColorStop(1, 'rgba(0,245,255,0)');
    ctx.beginPath();
    data.forEach((v, i) => {
        const x = padding.left + (plotW / (data.length - 1)) * i;
        const y = padding.top + plotH - (v / maxVal) * plotH;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    const lastX = padding.left + plotW;
    ctx.lineTo(lastX, ch - padding.bottom);
    ctx.lineTo(padding.left, ch - padding.bottom);
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.beginPath();
    data.forEach((v, i) => {
        const x = padding.left + (plotW / (data.length - 1)) * i;
        const y = padding.top + plotH - (v / maxVal) * plotH;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = 'var(--cyan)';
    ctx.lineWidth = 2;
    ctx.stroke();

    data.forEach((v, i) => {
        const x = padding.left + (plotW / (data.length - 1)) * i;
        const y = padding.top + plotH - (v / maxVal) * plotH;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#0a0a1a';
        ctx.fill();
        ctx.strokeStyle = '#00f5ff';
        ctx.lineWidth = 2;
        ctx.stroke();
    });
}

function renderMasteryChart() {
    const canvas = document.getElementById('chartMastery');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.offsetWidth * 2;
    const h = canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    const cw = canvas.offsetWidth, ch = canvas.offsetHeight;
    ctx.clearRect(0, 0, cw, ch);

    const subjects = [{name:'Math',val:67,color:'#00f5ff'},{name:'Science',val:52,color:'#00ff88'},{name:'Reading',val:74,color:'#ff00ff'},{name:'Coding',val:38,color:'#8b5cf6'}];
    const padding = {top:20,right:20,bottom:30,left:50};
    const plotW = cw - padding.left - padding.right;
    const plotH = ch - padding.top - padding.bottom;
    const barW = plotW / subjects.length * 0.6;
    const gap = plotW / subjects.length;

    subjects.forEach((s, i) => {
        const x = padding.left + gap * i + (gap - barW) / 2;
        const barH = (s.val / 100) * plotH;
        const y = padding.top + plotH - barH;

        const grad = ctx.createLinearGradient(0, y, 0, y + barH);
        grad.addColorStop(0, s.color);
        grad.addColorStop(1, s.color + '33');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.roundRect(x, y, barW, barH, 4);
        ctx.fill();

        ctx.fillStyle = s.color;
        ctx.font = 'bold 12px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(s.val + '%', x + barW/2, y - 6);
        ctx.fillStyle = 'rgba(255,255,255,0.4)';
        ctx.font = '10px Inter';
        ctx.fillText(s.name, x + barW/2, ch - 8);
    });
}

function renderEmotionChart() {
    const canvas = document.getElementById('chartEmotion');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.offsetWidth * 2;
    const h = canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    const cw = canvas.offsetWidth, ch = canvas.offsetHeight;
    ctx.clearRect(0, 0, cw, ch);

    const emotions = [
        {name:'Engaged',val:0.7},{name:'Confident',val:0.5},{name:'Curious',val:0.6},
        {name:'Confused',val:0.15},{name:'Frustrated',val:0.08},{name:'Excited',val:0.45}
    ];
    const cx = cw / 2, cy = ch / 2;
    const maxR = Math.min(cx, cy) - 30;
    const n = emotions.length;

    for (let ring = 1; ring <= 4; ring++) {
        const r = (maxR / 4) * ring;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.05)';
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    emotions.forEach((e, i) => {
        const angle = (Math.PI * 2 / n) * i - Math.PI / 2;
        const x = cx + Math.cos(angle) * (maxR + 15);
        const y = cy + Math.sin(angle) * (maxR + 15);
        ctx.fillStyle = 'rgba(255,255,255,0.4)';
        ctx.font = '10px Inter';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(e.name, x, y);
    });

    ctx.beginPath();
    emotions.forEach((e, i) => {
        const angle = (Math.PI * 2 / n) * i - Math.PI / 2;
        const r = maxR * e.val;
        const x = cx + Math.cos(angle) * r;
        const y = cy + Math.sin(angle) * r;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle = 'rgba(0,245,255,0.1)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(0,245,255,0.6)';
    ctx.lineWidth = 2;
    ctx.stroke();

    emotions.forEach((e, i) => {
        const angle = (Math.PI * 2 / n) * i - Math.PI / 2;
        const r = maxR * e.val;
        const x = cx + Math.cos(angle) * r;
        const y = cy + Math.sin(angle) * r;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#00f5ff';
        ctx.fill();
    });
}

function getAgeGroup() {
    try { return ({3:'tiny',4:'tiny',5:'tiny',6:'junior',7:'junior',8:'junior'})[JSON.parse(localStorage.getItem('ob_profile')).age] || 'rising'; } catch(e) { return 'junior'; }
}
function getPlayerAge() {
    try { return JSON.parse(localStorage.getItem('ob_profile')).age || 8; } catch(e) { return 8; }
}

const NOVA_PHRASES = {
    correct: ['Awesome!','Great job!','You got it!','Brilliant!','Amazing!','Perfect!','Superstar!','Way to go!','Nailed it!','Fantastic!'],
    wrong: ['Try again!','Almost!','Keep going!','You can do it!','So close!','Nice try!','Don\'t give up!'],
    streak: ['On fire!','Unstoppable!','Streak master!','Keep it rolling!','Incredible run!'],
    gameStart: ['Let\'s go!','Ready? Go!','You\'ve got this!','Time to shine!','Adventure awaits!'],
    lessonStart: ['Let\'s learn!','Exciting stuff!','Ready to explore?','Knowledge time!'],
    complete: ['Champion!','You did it!','Mission complete!','Outstanding!','Legend!']
};

function novaReact(state, customMsg) {
    const img = document.getElementById('novaImg');
    const speech = document.getElementById('novaSpeech');
    if (!img || !speech) return;
    img.className = 'nova-img ' + state;
    const phrases = NOVA_PHRASES[state] || NOVA_PHRASES.correct;
    const msg = customMsg || phrases[Math.floor(Math.random() * phrases.length)];
    speech.textContent = msg;
    speech.classList.add('show');
    if (window._novaSpeechTimer) clearTimeout(window._novaSpeechTimer);
    window._novaSpeechTimer = setTimeout(() => {
        speech.classList.remove('show');
        img.className = 'nova-img idle';
    }, 2500);
}

function spawnConfetti(count = 50) {
    const container = document.getElementById('confettiContainer');
    if (!container) return;
    const frag = document.createDocumentFragment();
    const colors = ['#00f5ff','#ff00ff','#00ff88','#8b5cf6','#fbbf24','#ff416c','#06b6d4'];
    const shapes = ['circle','square','star'];
    for (let i = 0; i < count; i++) {
        const el = document.createElement('div');
        el.className = 'confetti-container';
        const piece = document.createElement('div');
        piece.className = 'confetti-piece ' + shapes[Math.floor(Math.random()*shapes.length)];
        piece.style.background = colors[Math.floor(Math.random()*colors.length)];
        piece.style.left = Math.random()*100 + '%';
        piece.style.top = '-10px';
        piece.style.width = (6 + Math.random()*8) + 'px';
        piece.style.height = (6 + Math.random()*8) + 'px';
        piece.style.setProperty('--fall-y', (60 + Math.random()*40) + 'vh');
        piece.style.setProperty('--spin', (360 + Math.random()*720) + 'deg');
        piece.style.setProperty('--fall-dur', (1.5 + Math.random()*2) + 's');
        piece.style.animationDelay = Math.random()*0.5 + 's';
        el.appendChild(piece);
        frag.appendChild(el);
    }
    container.appendChild(frag);
    setTimeout(() => { while(container.firstChild) container.removeChild(container.firstChild); }, 4000);
}

function showFloatingXP(amount, x, y) {
    const el = document.createElement('div');
    el.className = 'floating-xp';
    el.textContent = '+' + amount + ' XP';
    el.style.left = (x || window.innerWidth/2) + 'px';
    el.style.top = (y || window.innerHeight/2) + 'px';
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1300);
}

function showScreenFlash(type) {
    const el = document.getElementById('screenFlash');
    if (!el) return;
    el.className = 'screen-flash ' + type;
    setTimeout(() => { el.className = 'screen-flash'; }, 350);
}

function showStarburst(x, y) {
    const el = document.createElement('div');
    el.className = 'starburst';
    el.style.left = x + 'px';
    el.style.top = y + 'px';
    const rays = 8;
    for (let i = 0; i < rays; i++) {
        const ray = document.createElement('div');
        ray.className = 'starburst-ray';
        ray.style.setProperty('--ray-angle', (i * 360/rays) + 'deg');
        el.appendChild(ray);
    }
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 700);
}

function showCelebration(text) {
    spawnConfetti(80);
    novaReact('celebrating');
    const overlay = document.createElement('div');
    overlay.className = 'celebration-overlay active';
    overlay.innerHTML = `<div class="celebration-text">${text || '🎉 Amazing!'}</div>`;
    document.body.appendChild(overlay);
    setTimeout(() => { overlay.classList.remove('active'); setTimeout(() => overlay.remove(), 300); }, 2000);
}

function gameNovaHTML(msg) {
    return `<div class="gp-nova-float"><img src="/assets/nova-mascot.png" alt="Nova" onerror="this.style.display='none'"><div class="nova-bubble${msg ? ' show' : ''}">${msg || ''}</div></div>`;
}

const GAME_DEFS = [
    {id:'number_lab',title:'Number Lab',icon:'math',cat:'math',desc:'Explore numbers, solve puzzles, and discover math secrets in the lab!',descTiny:'Tap the right number! Count and match!',descRising:'Build equations, balance expressions, master operations.',tags:['Math','Interactive'],xp:50},
    {id:'word_forge',title:'Word Forge',icon:'reading',cat:'words',desc:'Craft words from letters, build your vocabulary, and become a word master!',descTiny:'Match letters! Build simple words!',descRising:'Vocabulary, word roots, and analogies.',tags:['Reading','Words'],xp:50},
    {id:'science_lab',title:'Science Explorer',icon:'science',cat:'science',desc:'Mix potions, run experiments, and discover how the world works!',descTiny:'Mix colors! Sort animals!',descRising:'Chemistry, physics, and ecosystem experiments.',tags:['Science','Discovery'],xp:50},
    {id:'pattern_quest',title:'Pattern Quest',icon:'brain',cat:'pattern',desc:'Find patterns, complete sequences, and train your brain!',descTiny:'What comes next? Spot the pattern!',descRising:'Complex sequences, logic puzzles, spatial reasoning.',tags:['Logic','Patterns'],xp:40},
    {id:'speed_challenge',title:'Speed Challenge',icon:'zap',cat:'speed',desc:'Race against the clock with math, spelling, science, and coding questions!',descTiny:'Quick quiz fun!',descRising:'Fast-paced trivia across all subjects.',tags:['Speed','All Subjects'],xp:60}
];

let gState = {game:null,round:0,total:10,score:0,streak:0,bestStreak:0,correct:0,timer:null,timerVal:0,answered:false,questions:[]};

const GAME_IMAGES = {number_lab:'/assets/game-number-lab.png',word_forge:'/assets/game-word-forge.png',science_lab:'/assets/game-science-lab.png',pattern_quest:'/assets/game-pattern-quest.png',speed_challenge:'/assets/game-speed-challenge.png'};

function renderGameSelect() {
    const sel = document.getElementById('gameSelect');
    const ag = getAgeGroup();
    sel.innerHTML = GAME_DEFS.map(g => {
        const desc = ag === 'tiny' ? g.descTiny : (ag === 'rising' ? g.descRising : g.desc);
        const hs = localStorage.getItem('hs_' + g.id);
        const img = GAME_IMAGES[g.id] || '';
        return `<div class="game-card" onclick="launchGame('${g.id}')">
            <div class="gc-glow ${g.cat}"></div>
            ${hs ? `<div class="gc-highscore">🏆 ${hs}</div>` : ''}
            <div class="gc-banner ${g.cat}">
                ${img ? `<img class="gc-banner-img" src="${img}" alt="" loading="lazy">` : ''}
                <div class="gc-icon">${icon(g.icon, 42)}</div>
            </div>
            <div class="gc-body">
                <div class="gc-title">${g.title}</div>
                <div class="gc-desc">${desc}</div>
                <div class="gc-tags">${g.tags.map(t => `<span class="gc-tag">${t}</span>`).join('')}<span class="gc-tag xp">+${g.xp} XP</span></div>
            </div>
        </div>`;
    }).join('');
}

function launchGame(gameId) {
    gState = {game:gameId,round:0,total:10,score:0,streak:0,bestStreak:0,correct:0,timer:null,timerVal:0,answered:false,questions:[]};
    const def = GAME_DEFS.find(g => g.id === gameId);
    document.getElementById('gameSelectView').style.display = 'none';
    document.getElementById('gamePlayArea').classList.add('active');
    document.getElementById('gpTitle').textContent = def ? def.title : 'Game';
    document.getElementById('gpScore').textContent = '0';
    document.getElementById('gpStreak').textContent = '';
    novaReact('gameStart');

    if (gameId === 'number_lab') setupNumberLab();
    else if (gameId === 'word_forge') setupWordForge();
    else if (gameId === 'science_lab') setupScienceLab();
    else if (gameId === 'pattern_quest') setupPatternQuest();
    else if (gameId === 'speed_challenge') setupSpeedChallenge();
}

function exitGame() {
    if (gState.timer) clearInterval(gState.timer);
    document.getElementById('gameSelectView').style.display = 'block';
    document.getElementById('gamePlayArea').classList.remove('active');
    renderGameSelect();
}

function updateGameHUD() {
    document.getElementById('gpRound').textContent = `${gState.round} / ${gState.total}`;
    document.getElementById('gpScore').textContent = gState.score;
    document.getElementById('gpStreak').textContent = gState.streak >= 2 ? `${icon('zap',12)} ${gState.streak}x` : '';
}

function startRoundTimer(sec) {
    if (gState.timer) clearInterval(gState.timer);
    gState.timerVal = sec;
    const el = document.getElementById('gpTimer');
    el.textContent = sec;
    el.style.color = 'var(--magenta)';
    gState.timer = setInterval(() => {
        gState.timerVal--;
        el.textContent = Math.max(0, gState.timerVal);
        if (gState.timerVal <= 5) el.style.color = '#ff4444';
        if (gState.timerVal <= 0) {
            clearInterval(gState.timer);
            if (!gState.answered) handleGameTimeout();
        }
    }, 1000);
}

function handleGameTimeout() {
    gState.answered = true;
    gState.streak = 0;
    document.querySelectorAll('.gp-option').forEach(o => o.classList.add('disabled'));
    setTimeout(() => advanceRound(), 1200);
}

function advanceRound() {
    gState.round++;
    if (gState.round > gState.total) {
        showGameComplete();
        return;
    }
    gState.answered = false;
    updateGameHUD();
    if (gState.game === 'number_lab') renderNumberLabRound();
    else if (gState.game === 'word_forge') renderWordForgeRound();
    else if (gState.game === 'science_lab') renderScienceLabRound();
    else if (gState.game === 'pattern_quest') renderPatternQuestRound();
    else if (gState.game === 'speed_challenge') renderSpeedRound();
}

function scoreAnswer(correct) {
    gState.answered = true;
    if (gState.timer) clearInterval(gState.timer);
    if (correct) {
        gState.correct++;
        gState.streak++;
        if (gState.streak > gState.bestStreak) gState.bestStreak = gState.streak;
        const bonus = gState.streak >= 3 ? 50 : 0;
        const timeBonus = Math.round(gState.timerVal * 3);
        gState.score += 100 + bonus + timeBonus;
        showScreenFlash('correct');
        novaReact(gState.streak >= 3 ? 'streak' : 'correct');
        if (gState.streak >= 3) showStarburst(window.innerWidth/2, window.innerHeight/2);
        showFloatingXP(100 + bonus + timeBonus);
    } else {
        gState.streak = 0;
        showScreenFlash('wrong');
        novaReact('wrong');
    }
    updateGameHUD();
    setTimeout(() => advanceRound(), correct ? 800 : 1200);
}

function showGameComplete() {
    if (gState.timer) clearInterval(gState.timer);
    const def = GAME_DEFS.find(g => g.id === gState.game);
    const xp = def ? def.xp : 40;
    const accuracy = gState.total > 0 ? Math.round((gState.correct / gState.total) * 100) : 0;

    const prev = parseInt(localStorage.getItem('hs_' + gState.game) || '0');
    const isNewHighScore = gState.score > prev;
    if (isNewHighScore) localStorage.setItem('hs_' + gState.game, gState.score);

    showCelebration(accuracy >= 80 ? '⭐ Amazing!' : accuracy >= 50 ? '🎉 Great Job!' : '💪 Keep Going!');
    showFloatingXP(xp);

    document.getElementById('gpContent').innerHTML = `
        <div class="gp-results">
            <div class="gpr-trophy">🏆</div>
            <div class="gpr-title">${accuracy >= 80 ? 'Amazing!' : accuracy >= 50 ? 'Great Effort!' : 'Keep Practicing!'}</div>
            ${isNewHighScore ? '<div style="font-size:14px;color:var(--magenta);font-weight:700;animation:pulse 1s ease infinite">🌟 New High Score!</div>' : ''}
            <div class="gpr-xp" style="animation:popIn 0.5s ease">+${xp} XP</div>
            <div class="gpr-stats">
                <div class="gpr-stat"><div class="gpr-stat-val" style="animation:countUp 0.5s ease">${gState.score}</div><div class="gpr-stat-lbl">Score</div></div>
                <div class="gpr-stat"><div class="gpr-stat-val" style="animation:countUp 0.5s ease 0.1s both">${accuracy}%</div><div class="gpr-stat-lbl">Accuracy</div></div>
                <div class="gpr-stat"><div class="gpr-stat-val" style="animation:countUp 0.5s ease 0.2s both">${gState.bestStreak}</div><div class="gpr-stat-lbl">Best Streak</div></div>
            </div>
            <div class="gpr-actions">
                <button class="gp-btn primary" onclick="launchGame('${gState.game}')">🔄 Play Again</button>
                <button class="gp-btn secondary" onclick="exitGame()">← Back to Games</button>
            </div>
        </div>`;
    document.getElementById('gpRound').textContent = 'Done!';
    document.getElementById('gpTimer').textContent = '';

    apiCall('/gamification/award-xp', 'POST', {xp_amount: xp, source: gState.game});
}

// === NUMBER LAB ===
const TAP_EMOJIS = ['⭐','🌟','🦋','🐱','🐶','🍎','🌸','🎈','🐠','🦄','🍊','🌺'];

function setupNumberLab() {
    const ag = getAgeGroup();
    gState.total = ag === 'tiny' ? 8 : 10;
    gState.round = 0;
    advanceRound();
}

function renderNumberLabRound() {
    const ag = getAgeGroup();
    const content = document.getElementById('gpContent');

    if (ag === 'tiny') {
        const target = Math.floor(Math.random() * 7) + 2;
        const emojis = [];
        for (let i = 0; i < target; i++) emojis.push(TAP_EMOJIS[Math.floor(Math.random() * TAP_EMOJIS.length)]);
        window._tapTarget = target;
        window._tapCount = 0;
        content.innerHTML = `
            ${gameNovaHTML('Tap each one to count!')}
            <div class="gp-question" style="font-size:22px">Tap to count them all!</div>
            <div style="display:flex;flex-wrap:wrap;gap:12px;justify-content:center;padding:16px">
                ${emojis.map((e, i) => `<div class="tap-object" onclick="tapToCount(this, ${i})" data-idx="${i}">${e}</div>`).join('')}
            </div>
            <div style="text-align:center;margin:12px 0">
                <span style="font-size:48px;font-weight:900;color:var(--cyan)" id="tapCounter">0</span>
                <span style="font-size:16px;color:var(--text-muted)"> / ${target}</span>
            </div>
            <div class="number-line" id="numLine" style="justify-content:center">
                ${Array.from({length: target}, (_, i) => `<div class="number-line-dot" id="nld${i}">${i+1}</div>`).join('')}
            </div>
            <div class="gp-hint">Tap each object to count! No wrong answers here!</div>`;
    } else if (ag === 'rising') {
        const steps = 3 + Math.floor(Math.random() * 2);
        const chain = [];
        let val = Math.floor(Math.random() * 10) + 5;
        chain.push({label: 'Start', value: val, op: '', input: false});
        for (let i = 0; i < steps; i++) {
            const ops = ['+', '-', '×'];
            const op = ops[Math.floor(Math.random() * ops.length)];
            let operand;
            if (op === '×') { operand = Math.floor(Math.random() * 5) + 2; val = val * operand; }
            else if (op === '-') { operand = Math.floor(Math.random() * Math.min(val, 10)) + 1; val = val - operand; }
            else { operand = Math.floor(Math.random() * 15) + 1; val = val + operand; }
            chain.push({label: `${op} ${operand}`, value: val, op, input: i === steps - 1});
        }
        window._pipelineAnswer = val;
        window._pipelineChain = chain;
        content.innerHTML = `
            ${gameNovaHTML('Solve the chain!')}
            <div class="gp-question">Follow the pipeline!</div>
            <div class="pipeline" id="pipelineZone">
                ${chain.map((s, i) => `
                    <div class="pipeline-step ${i === 0 ? 'complete' : ''}" id="ps${i}">
                        <div class="ps-label">${s.label}</div>
                        ${s.input ? `<input type="number" id="pipeInput" onkeydown="if(event.key==='Enter')checkPipelineAnswer()" placeholder="?">` : `<div class="ps-value">${i === 0 ? s.value : '?'}</div>`}
                    </div>
                    ${i < chain.length - 1 ? '<div class="pipeline-arrow">→</div>' : ''}
                `).join('')}
            </div>
            <button class="gp-btn primary" onclick="checkPipelineAnswer()" style="margin-top:16px">Check Answer</button>
            <div class="gp-hint">Each step transforms the number. Find the final result!</div>`;
        startRoundTimer(30);
    } else {
        const target = Math.floor(Math.random() * 20) + 5;
        const nums = [];
        const ops = ['+', '-', '×'];
        for (let i = 1; i <= 12; i++) nums.push(i);
        ops.forEach(o => nums.push(o));
        window._eqTarget = target;
        window._eqBuilt = [];
        content.innerHTML = `
            ${gameNovaHTML('Make the target!')}
            <div class="target-number" id="eqTarget">= ${target}</div>
            <div class="equation-builder" id="eqBuilder">
                <div class="gp-hint" style="width:100%">Tap orbs to build an equation!</div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;padding:12px">
                ${nums.map((n, i) => {
                    const isOp = typeof n === 'string';
                    return `<div class="orb ${isOp ? 'operator' : 'number'}" onclick="addToEquation(this, '${n}', ${isOp})" data-val="${n}">${n}</div>`;
                }).join('')}
            </div>
            <div style="display:flex;gap:8px;justify-content:center;margin-top:8px">
                <button class="gp-btn secondary" onclick="clearEquation()">Clear</button>
                <button class="gp-btn primary" onclick="checkEquation()">= Check</button>
            </div>
            <div class="gp-hint">Build an equation that equals ${target}! Multiple solutions work!</div>`;
        startRoundTimer(25);
    }
}

function tapToCount(el, idx) {
    if (el.classList.contains('tapped')) return;
    el.classList.add('tapped');
    window._tapCount++;
    document.getElementById('tapCounter').textContent = window._tapCount;
    const dot = document.getElementById('nld' + (window._tapCount - 1));
    if (dot) dot.classList.add('active');
    showFloatingXP(10, el.getBoundingClientRect().left + 30, el.getBoundingClientRect().top);
    if (window._tapCount >= window._tapTarget) {
        setTimeout(() => {
            novaReact('correct', 'You counted them all!');
            spawnConfetti(30);
            scoreAnswer(true);
        }, 400);
    }
}

function addToEquation(el, val, isOp) {
    if (gState.answered) return;
    const built = window._eqBuilt;
    const lastIsOp = built.length > 0 && typeof built[built.length-1] === 'string' && ['+','-','×'].includes(built[built.length-1]);
    if (isOp && (built.length === 0 || lastIsOp)) return;
    if (!isOp && built.length > 0 && !lastIsOp) return;
    built.push(val);
    const builder = document.getElementById('eqBuilder');
    builder.classList.add('has-items');
    builder.innerHTML = built.map(v => `<div class="orb ${['+','-','×'].includes(v) ? 'operator' : 'number'}" style="pointer-events:none">${v}</div>`).join('');
}

function clearEquation() {
    window._eqBuilt = [];
    const builder = document.getElementById('eqBuilder');
    builder.classList.remove('has-items');
    builder.innerHTML = '<div class="gp-hint" style="width:100%">Tap orbs to build an equation!</div>';
}

function checkEquation() {
    if (gState.answered) return;
    const built = window._eqBuilt;
    if (built.length < 3) return;
    const last = built[built.length-1];
    if (['+','-','×'].includes(last)) return;
    let expr = built.join(' ').replace(/×/g, '*');
    try {
        const result = Function('"use strict"; return (' + expr + ')')();
        if (Math.abs(result - window._eqTarget) < 0.001) {
            document.getElementById('eqBuilder').querySelectorAll('.orb').forEach(o => o.classList.add('correct-orb'));
            scoreAnswer(true);
        } else {
            novaReact('wrong', `That makes ${result}`);
            clearEquation();
        }
    } catch (e) {
        novaReact('wrong', 'Try different orbs!');
        clearEquation();
    }
}

function checkPipelineAnswer() {
    if (gState.answered) return;
    const input = document.getElementById('pipeInput');
    if (!input) return;
    const val = parseInt(input.value);
    if (isNaN(val)) return;
    const chain = window._pipelineChain;
    chain.forEach((s, i) => {
        const step = document.getElementById('ps' + i);
        if (step) {
            step.classList.add('complete');
            const valEl = step.querySelector('.ps-value');
            if (valEl) valEl.textContent = s.value;
        }
    });
    if (val === window._pipelineAnswer) {
        input.style.borderColor = 'var(--lime)';
        input.style.color = 'var(--lime)';
        scoreAnswer(true);
    } else {
        input.style.borderColor = '#ff4444';
        input.style.color = '#ff4444';
        novaReact('wrong', `Answer: ${window._pipelineAnswer}`);
        scoreAnswer(false);
    }
}

function checkMathAnswer(el, chosen, correct) {
    if (gState.answered) return;
    document.querySelectorAll('.gp-option').forEach(o => o.classList.add('disabled'));
    if (chosen === correct) {
        el.classList.add('correct');
        scoreAnswer(true);
    } else {
        el.classList.add('wrong');
        document.querySelectorAll('.gp-option').forEach(o => { if (o.textContent == correct) o.classList.add('correct'); });
        scoreAnswer(false);
    }
}

// === WORD FORGE ===
const WORDS_TINY = ['cat','dog','sun','hat','cup','red','big','run','sit','hop','map','pin','bug','fan','net'];
const LETTER_PICS = {a:'🍎',b:'🦋',c:'🐱',d:'🐶',e:'🥚',f:'🐸',g:'🍇',h:'🏠',i:'🍦',j:'🧃',k:'🪁',l:'🦁',m:'🌙',n:'🥜',o:'🐙',p:'🐧',q:'👑',r:'🌈',s:'⭐',t:'🌳',u:'☂️',v:'🎻',w:'🐳',x:'❌',y:'🧶',z:'⚡'};
const WORDS_JR_THEMES = {animals:['bear','fish','bird','deer','frog','duck','hawk','wolf','swan','goat'],food:['cake','milk','rice','plum','corn','bean','pear','lime','taco','soup'],nature:['rain','leaf','moon','wind','lake','sand','wave','hill','seed','vine']};
const WORDS_RISING = ['adventure','discovery','brilliant','telescope','challenge','essential','magnetic','equation','skeleton','architect','eloquent','peninsula','longitude','symbiotic','algorithm'];
const WORD_DEFS = {adventure:'An exciting experience',discovery:'Finding something new',brilliant:'Very bright or clever',telescope:'A tool to see far away',challenge:'Something hard to do',essential:'Absolutely necessary',magnetic:'Having power to attract',equation:'A math statement with equals',skeleton:'The bone structure of a body',architect:'A person who designs buildings',eloquent:'Fluent and persuasive speech',peninsula:'Land surrounded by water on three sides',longitude:'Distance east or west on a globe',symbiotic:'Living together beneficially',algorithm:'A step-by-step procedure'};

function setupWordForge() {
    const ag = getAgeGroup();
    gState.total = ag === 'tiny' ? 8 : 10;
    gState.round = 0;
    if (ag === 'junior') {
        const themes = Object.keys(WORDS_JR_THEMES);
        window._wfTheme = themes[Math.floor(Math.random() * themes.length)];
        window._wfFoundWords = [];
    }
    advanceRound();
}

function renderWordForgeRound() {
    const ag = getAgeGroup();
    const content = document.getElementById('gpContent');

    if (ag === 'tiny') {
        const letters = 'abcdefghijklmnopqrstuvwxyz';
        const idx = (gState.round - 1) % 26;
        const letter = letters[idx];
        const pic = LETTER_PICS[letter] || '❓';
        content.innerHTML = `
            ${gameNovaHTML('Tap the letter!')}
            <div class="gp-question" style="font-size:24px">Learn the letter!</div>
            <div style="text-align:center;margin:20px 0">
                <div style="font-size:100px;line-height:1;cursor:pointer;animation:novaFloat 2s ease-in-out infinite" onclick="tinyLetterTap(this, '${letter}')" id="bigLetter">${letter.toUpperCase()}</div>
                <div style="font-size:14px;color:var(--text-muted);margin-top:8px">Tap the letter!</div>
            </div>
            <div style="text-align:center;font-size:64px;margin:12px 0">${pic}</div>
            <div style="text-align:center;font-size:18px;font-weight:700;color:var(--cyan);text-transform:uppercase;letter-spacing:4px">${letter} is for ${Object.entries(LETTER_PICS).find(([k]) => k === letter)?.[1] || '?'}</div>
            <div style="display:flex;gap:12px;justify-content:center;margin-top:16px">
                ${(() => {
                    const pool = new Set([letter]);
                    while (pool.size < 4) pool.add(letters[Math.floor(Math.random() * 26)]);
                    return [...pool].sort(() => Math.random() - 0.5).map(l => {
                        const isCorrect = l === letter;
                        return `<div class="tap-object" onclick="tinyLetterMatch(this, '${l}', ${isCorrect})" style="font-size:24px;font-weight:800">${l.toUpperCase()}</div>`;
                    }).join('');
                })()}
            </div>
            <div class="gp-hint">Find the matching letter below! No wrong answers!</div>`;
    } else if (ag === 'rising') {
        const word = WORDS_RISING[(gState.round - 1) % WORDS_RISING.length];
        const def = WORD_DEFS[word] || 'A word to discover';
        const letters = word.split('');
        const shown = letters.map((l, i) => i === 0 ? l : (Math.random() > 0.6 ? l : '_'));
        if (shown.every(l => l !== '_')) shown[shown.length - 1] = '_';
        const missing = [];
        letters.forEach((l, i) => { if (shown[i] === '_') missing.push(l); });
        const extras = 'aeioulnrstd'.split('').filter(c => !missing.includes(c)).slice(0, 3);
        const choices = [...missing, ...extras].sort(() => Math.random() - 0.5);

        content.innerHTML = `
            ${gameNovaHTML('Complete it!')}
            <div class="gp-question">Complete the word!</div>
            <div class="gp-hint" style="margin-bottom:16px">${def}</div>
            <div class="gp-answer-slots" id="wordSlots">${shown.map(l => `<div class="gp-slot ${l !== '_' ? 'filled prefilled' : ''}">${l !== '_' ? l.toUpperCase() : ''}</div>`).join('')}</div>
            <div class="gp-drag-zone" id="wordTiles">${choices.map((l,i) => `<div class="gp-tile" onclick="placeWordLetter(this)" data-letter="${l}" data-idx="${i}">${l.toUpperCase()}</div>`).join('')}</div>
            <div style="text-align:center;margin-top:12px"><button class="gp-btn secondary" onclick="undoWordLetter()" style="padding:6px 16px;font-size:12px">${icon('chevron-left',12)} Undo</button></div>`;
        window._wordTarget = word;
        window._wordProgress = [...shown];
        window._wordTileUsed = [];
        window._wordSlotMap = [];
        startRoundTimer(30);
    } else {
        const theme = window._wfTheme || 'animals';
        const pool = WORDS_JR_THEMES[theme] || WORDS_JR_THEMES.animals;
        const allLetters = pool.join('').split('');
        const unique = [...new Set(allLetters)].sort(() => Math.random() - 0.5).slice(0, 12);
        window._wfPool = pool;
        window._wfLetters = unique;
        window._wfBuilding = '';

        content.innerHTML = `
            ${gameNovaHTML(`Theme: ${theme}!`)}
            <div class="gp-question">Word Smithing: <span style="color:var(--magenta);text-transform:capitalize">${theme}</span></div>
            <div style="text-align:center;margin:8px 0">
                <span style="font-size:13px;color:var(--text-muted)">Found: </span>
                <span id="wfFoundList" style="font-size:13px;color:var(--lime);font-weight:600">${window._wfFoundWords.join(', ') || 'none yet'}</span>
            </div>
            <div class="gp-answer-slots" id="wfBuildZone" style="min-height:48px;justify-content:center"></div>
            <div class="gp-drag-zone" id="wfTiles" style="margin-top:12px">
                ${unique.map((l,i) => `<div class="gp-tile" onclick="wfAddLetter(this)" data-letter="${l}" data-idx="${i}" style="font-size:22px">${l.toUpperCase()}</div>`).join('')}
            </div>
            <div style="display:flex;gap:8px;justify-content:center;margin-top:12px">
                <button class="gp-btn secondary" onclick="wfClear()">Clear</button>
                <button class="gp-btn primary" onclick="wfSubmitWord()">⚒️ Forge!</button>
            </div>
            <div class="gp-hint">Build ${theme} words from the letters! Find at least 3!</div>`;
        startRoundTimer(45);
    }
}

function tinyLetterTap(el, letter) {
    el.style.color = 'var(--cyan)';
    el.style.animation = 'tapBounce 0.5s ease';
    novaReact('correct', `${letter.toUpperCase()}!`);
}

function tinyLetterMatch(el, chosen, isCorrect) {
    if (el.classList.contains('tapped')) return;
    el.classList.add('tapped');
    if (isCorrect) {
        showFloatingXP(10, el.getBoundingClientRect().left, el.getBoundingClientRect().top);
        spawnConfetti(15);
        setTimeout(() => scoreAnswer(true), 500);
    } else {
        novaReact('encouraging', 'Try another!');
    }
}

function wfAddLetter(el) {
    if (gState.answered || el.classList.contains('placed')) return;
    el.classList.add('placed');
    window._wfBuilding += el.dataset.letter;
    const zone = document.getElementById('wfBuildZone');
    zone.innerHTML = window._wfBuilding.split('').map(l => `<div class="gp-slot filled" style="animation:popIn 0.2s ease">${l.toUpperCase()}</div>`).join('');
    if (!window._wfTileStack) window._wfTileStack = [];
    window._wfTileStack.push(el);
}

function wfClear() {
    window._wfBuilding = '';
    document.getElementById('wfBuildZone').innerHTML = '';
    document.querySelectorAll('#wfTiles .gp-tile').forEach(t => t.classList.remove('placed'));
    window._wfTileStack = [];
}

function wfSubmitWord() {
    if (gState.answered) return;
    const word = window._wfBuilding.toLowerCase();
    if (word.length < 3) { novaReact('wrong', 'Too short!'); return; }
    if (window._wfFoundWords.includes(word)) { novaReact('wrong', 'Already found!'); wfClear(); return; }
    const pool = window._wfPool || [];
    if (pool.includes(word)) {
        window._wfFoundWords.push(word);
        document.getElementById('wfFoundList').textContent = window._wfFoundWords.join(', ');
        novaReact('correct', '⚒️ Forged!');
        showFloatingXP(50);
        spawnConfetti(20);
        wfClear();
        if (window._wfFoundWords.length >= 3) {
            setTimeout(() => scoreAnswer(true), 600);
        }
    } else {
        novaReact('wrong', 'Not a theme word!');
        wfClear();
    }
}

function placeWordLetter(tileEl) {
    if (gState.answered) return;
    if (tileEl.classList.contains('placed')) return;
    const letter = tileEl.dataset.letter;
    const slots = document.querySelectorAll('#wordSlots .gp-slot');
    const ag = getAgeGroup();

    if (ag === 'rising') {
        let nextEmpty = -1;
        slots.forEach((s, i) => { if (nextEmpty < 0 && !s.classList.contains('filled')) nextEmpty = i; });
        if (nextEmpty < 0) return;

        tileEl.classList.add('placed');
        slots[nextEmpty].textContent = letter.toUpperCase();
        slots[nextEmpty].classList.add('filled');
        window._wordProgress[nextEmpty] = letter;
        window._wordTileUsed.push({tile: tileEl, slotIndex: nextEmpty});

        const allFilled = [...slots].every(s => s.classList.contains('filled'));
        if (allFilled) {
            const built = window._wordProgress.join('');
            if (built === window._wordTarget) {
                slots.forEach(s => s.classList.add('correct-slot'));
                scoreAnswer(true);
            } else {
                slots.forEach(s => { if (!s.classList.contains('prefilled')) s.classList.add('wrong-slot'); });
                setTimeout(() => {
                    window._wordTileUsed.forEach(u => {
                        u.tile.classList.remove('placed');
                        slots[u.slotIndex].textContent = '';
                        slots[u.slotIndex].classList.remove('filled', 'wrong-slot');
                        window._wordProgress[u.slotIndex] = '_';
                    });
                    window._wordTileUsed = [];
                }, 800);
            }
        }
    } else {
        let nextEmpty = -1;
        slots.forEach((s, i) => { if (nextEmpty < 0 && s.textContent === '') nextEmpty = i; });
        if (nextEmpty < 0) return;

        tileEl.classList.add('placed');
        window._wordProgress.push(letter);
        window._wordTileUsed.push({tile: tileEl, slotIndex: nextEmpty});
        slots[nextEmpty].textContent = letter.toUpperCase();
        slots[nextEmpty].classList.add('filled');

        if (window._wordProgress.length === window._wordTarget.length) {
            const built = window._wordProgress.join('');
            if (built === window._wordTarget) {
                slots.forEach(s => s.classList.add('correct-slot'));
                scoreAnswer(true);
            } else {
                slots.forEach(s => s.classList.add('wrong-slot'));
                setTimeout(() => {
                    window._wordTileUsed.forEach(u => {
                        u.tile.classList.remove('placed');
                        slots[u.slotIndex].textContent = '';
                        slots[u.slotIndex].classList.remove('filled', 'wrong-slot');
                    });
                    window._wordProgress = [];
                    window._wordTileUsed = [];
                }, 800);
            }
        }
    }
}

function undoWordLetter() {
    if (gState.answered) return;
    if (!window._wordTileUsed || window._wordTileUsed.length === 0) return;
    const last = window._wordTileUsed.pop();
    const slots = document.querySelectorAll('#wordSlots .gp-slot');
    const ag = getAgeGroup();

    last.tile.classList.remove('placed');
    slots[last.slotIndex].textContent = '';
    slots[last.slotIndex].classList.remove('filled', 'correct-slot', 'wrong-slot');

    if (ag === 'rising') {
        window._wordProgress[last.slotIndex] = '_';
    } else {
        window._wordProgress.pop();
    }
}

// === SCIENCE LAB ===
const COLOR_MIXES = [
    {a:'red',b:'yellow',result:'orange',aHex:'#ef4444',bHex:'#eab308',rHex:'#f97316'},
    {a:'red',b:'blue',result:'purple',aHex:'#ef4444',bHex:'#3b82f6',rHex:'#8b5cf6'},
    {a:'blue',b:'yellow',result:'green',aHex:'#3b82f6',bHex:'#eab308',rHex:'#22c55e'},
    {a:'red',b:'white',result:'pink',aHex:'#ef4444',bHex:'#f1f5f9',rHex:'#f472b6'},
    {a:'blue',b:'white',result:'light blue',aHex:'#3b82f6',bHex:'#f1f5f9',rHex:'#7dd3fc'},
];
const SORT_ITEMS = [
    {name:'Dog',icon:'🐶',cat:'living'},{name:'Rock',icon:'🪨',cat:'nonliving'},
    {name:'Tree',icon:'🌳',cat:'living'},{name:'Chair',icon:'🪑',cat:'nonliving'},
    {name:'Fish',icon:'🐠',cat:'living'},{name:'Cup',icon:'☕',cat:'nonliving'},
    {name:'Flower',icon:'🌸',cat:'living'},{name:'Ball',icon:'⚽',cat:'nonliving'},
    {name:'Bird',icon:'🐦',cat:'living'},{name:'Book',icon:'📖',cat:'nonliving'},
];
const ELEMENTS_DATA = [
    {sym:'H',name:'Hydrogen',num:1},{sym:'O',name:'Oxygen',num:8},{sym:'C',name:'Carbon',num:6},
    {sym:'N',name:'Nitrogen',num:7},{sym:'Na',name:'Sodium',num:11},{sym:'Cl',name:'Chlorine',num:17},
    {sym:'Fe',name:'Iron',num:26},{sym:'Au',name:'Gold',num:79}
];
const ELEMENT_REACTIONS = [
    {a:'H',b:'O',result:'Water (H₂O)',emoji:'💧',desc:'Two hydrogen atoms bond with one oxygen atom'},
    {a:'Na',b:'Cl',result:'Salt (NaCl)',emoji:'🧂',desc:'Sodium and chlorine form table salt'},
    {a:'C',b:'O',result:'Carbon Dioxide (CO₂)',emoji:'💨',desc:'Carbon burns in oxygen to form CO₂'},
    {a:'Fe',b:'O',result:'Rust (Fe₂O₃)',emoji:'🟤',desc:'Iron reacts with oxygen to form rust'},
    {a:'H',b:'N',result:'Ammonia (NH₃)',emoji:'🌫️',desc:'Hydrogen and nitrogen form ammonia'},
];
const SCIENCE_TRIVIA = [
    {q:'What state of matter is ice?',opts:['Solid','Liquid','Gas','Plasma'],answer:'Solid',hint:'It is hard and cold'},
    {q:'Which force pulls things down?',opts:['Gravity','Magnetism','Friction','Wind'],answer:'Gravity',hint:'Isaac Newton discovered it'},
    {q:'What gas do we breathe in?',opts:['Oxygen','Carbon dioxide','Nitrogen','Helium'],answer:'Oxygen',hint:'We need it to live'},
    {q:'What is the chemical formula for water?',opts:['H₂O','CO₂','NaCl','O₂'],answer:'H₂O',hint:'Two hydrogen, one oxygen'},
    {q:'What is the powerhouse of the cell?',opts:['Mitochondria','Nucleus','Ribosome','Cell wall'],answer:'Mitochondria',hint:'It produces ATP'},
    {q:'Which planet is closest to the Sun?',opts:['Mercury','Venus','Earth','Mars'],answer:'Mercury',hint:'Very hot!'},
];

function setupScienceLab() {
    const ag = getAgeGroup();
    gState.total = ag === 'tiny' ? 6 : 8;
    gState.round = 0;
    if (ag === 'rising') { window._sciSelectedElements = []; }
    advanceRound();
}

function renderScienceLabRound() {
    const ag = getAgeGroup();
    const content = document.getElementById('gpContent');

    if (ag === 'tiny') {
        const roundType = gState.round % 2 === 1 ? 'color' : 'sort';
        if (roundType === 'color') {
            const mix = COLOR_MIXES[Math.floor(Math.random() * COLOR_MIXES.length)];
            window._colorMixAnswer = mix.result;
            content.innerHTML = `
                ${gameNovaHTML('Mix colors!')}
                <div class="gp-question" style="font-size:22px">🎨 Color Mixing Lab!</div>
                <div class="gp-hint">Tap two colors to mix them!</div>
                <div style="display:flex;gap:24px;justify-content:center;align-items:center;margin:20px 0">
                    <div class="color-beaker" style="background:${mix.aHex}" onclick="mixColor(this, 'a')">${mix.a}</div>
                    <div style="font-size:32px;font-weight:800;color:var(--text-muted)">+</div>
                    <div class="color-beaker" style="background:${mix.bHex}" onclick="mixColor(this, 'b')">${mix.b}</div>
                </div>
                <div class="mix-result" id="mixResult" style="background:rgba(255,255,255,0.03);border:2px dashed rgba(255,255,255,0.1)">
                    <div style="font-size:16px;color:var(--text-muted)">Tap both colors to mix!</div>
                </div>
                <div id="colorAnswer" style="text-align:center;margin-top:12px;display:none">
                    <div style="font-size:24px;font-weight:800;color:var(--cyan)">${mix.result.charAt(0).toUpperCase() + mix.result.slice(1)}!</div>
                </div>`;
            window._colorMixed = {a: false, b: false, hex: mix.rHex};
        } else {
            const shuffled = [...SORT_ITEMS].sort(() => Math.random() - 0.5).slice(0, 6);
            window._sortItems = shuffled;
            window._sortCorrect = 0;
            content.innerHTML = `
                ${gameNovaHTML('Sort them!')}
                <div class="gp-question" style="font-size:22px">🌿 Living or Non-Living?</div>
                <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin:16px 0" id="sortItems">
                    ${shuffled.map((item, i) => `<div class="sort-item" onclick="sortItemClick(this, '${item.cat}', ${i})" data-idx="${i}">${item.icon} ${item.name}</div>`).join('')}
                </div>
                <div style="display:flex;gap:16px;justify-content:center">
                    <div class="sort-bin" id="binLiving"><div class="sort-bin-label" style="color:var(--lime)">🌱 Living</div></div>
                    <div class="sort-bin" id="binNonliving"><div class="sort-bin-label" style="color:var(--cyan)">🪨 Non-Living</div></div>
                </div>
                <div class="gp-hint">Tap an item, then tap the right bin!</div>`;
            window._selectedSortItem = null;
        }
    } else if (ag === 'junior') {
        const roundType = gState.round % 2 === 1 ? 'matter' : 'trivia';
        if (roundType === 'matter') {
            content.innerHTML = `
                ${gameNovaHTML('Heat it up!')}
                <div class="gp-question">🧊 States of Matter Lab</div>
                <div class="gp-hint">Drag the thermometer to see what happens!</div>
                <div class="matter-display" id="matterDisplay" style="background:rgba(59,130,246,0.1);border:2px solid rgba(59,130,246,0.2)">
                    <div style="font-size:48px" id="matterEmoji">🧊</div>
                    <div style="font-size:20px;font-weight:800" id="matterState">SOLID</div>
                    <div class="matter-particles" id="matterParticles">${Array(12).fill('<div class="matter-particle solid"></div>').join('')}</div>
                </div>
                <div style="display:flex;align-items:center;gap:12px;padding:0 20px;margin-top:16px">
                    <span style="font-size:20px">❄️</span>
                    <input type="range" class="thermo-slider" id="thermoSlider" min="0" max="100" value="10" oninput="updateMatterState(this.value)">
                    <span style="font-size:20px">🔥</span>
                </div>
                <div style="text-align:center;margin-top:8px">
                    <span style="font-size:16px;font-weight:700;color:var(--text-secondary)" id="thermoTemp">-10°C</span>
                </div>
                <div style="text-align:center;margin-top:12px">
                    <button class="gp-btn primary" onclick="completeMatterExperiment()">I explored all states!</button>
                </div>`;
            window._matterStatesVisited = new Set(['solid']);
        } else {
            const q = SCIENCE_TRIVIA[Math.floor(Math.random() * SCIENCE_TRIVIA.length)];
            content.innerHTML = `
                ${gameNovaHTML('Think!')}
                <div style="font-size:36px;margin-bottom:8px">🔬</div>
                <div class="gp-question">${q.q}</div>
                <div class="gp-options">${q.opts.map(o =>
                    `<div class="gp-option" onclick="checkScienceAnswer(this, '${o.replace(/'/g,"\\'")}', '${q.answer.replace(/'/g,"\\'")}')">${o}</div>`
                ).join('')}</div>
                <div class="gp-hint">${q.hint}</div>`;
            startRoundTimer(18);
        }
    } else {
        const roundType = gState.round % 2 === 1 ? 'elements' : 'trivia';
        if (roundType === 'elements') {
            window._sciSelectedElements = [];
            content.innerHTML = `
                ${gameNovaHTML('Mix elements!')}
                <div class="gp-question">⚗️ Element Lab</div>
                <div class="gp-hint">Select two elements to see if they react!</div>
                <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:16px 0">
                    ${ELEMENTS_DATA.map(el => `<div class="element-card" onclick="selectElement(this, '${el.sym}')"><div class="el-symbol">${el.sym}</div><div class="el-name">${el.name}</div></div>`).join('')}
                </div>
                <div class="reaction-area" id="reactionArea">
                    <div style="color:var(--text-muted)">Select two elements to mix</div>
                </div>`;
            startRoundTimer(25);
        } else {
            const q = SCIENCE_TRIVIA[Math.floor(Math.random() * SCIENCE_TRIVIA.length)];
            content.innerHTML = `
                ${gameNovaHTML('Science time!')}
                <div style="font-size:36px;margin-bottom:8px">🔬</div>
                <div class="gp-question">${q.q}</div>
                <div class="gp-options">${q.opts.map(o =>
                    `<div class="gp-option" onclick="checkScienceAnswer(this, '${o.replace(/'/g,"\\'")}', '${q.answer.replace(/'/g,"\\'")}')">${o}</div>`
                ).join('')}</div>
                <div class="gp-hint">${q.hint}</div>`;
            startRoundTimer(15);
        }
    }
}

function mixColor(el, which) {
    if (!window._colorMixed) return;
    window._colorMixed[which] = true;
    el.style.transform = 'scale(0.9)';
    el.style.opacity = '0.6';
    if (window._colorMixed.a && window._colorMixed.b) {
        const result = document.getElementById('mixResult');
        result.style.background = window._colorMixed.hex;
        result.style.borderStyle = 'solid';
        result.style.borderColor = window._colorMixed.hex;
        result.classList.add('mixing');
        result.innerHTML = '<div style="font-size:48px">✨</div>';
        document.getElementById('colorAnswer').style.display = 'block';
        spawnConfetti(25);
        novaReact('correct', window._colorMixAnswer + '!');
        setTimeout(() => scoreAnswer(true), 1200);
    }
}

function sortItemClick(el, cat, idx) {
    if (el.classList.contains('placed')) return;
    if (window._selectedSortItem !== null) return;
    window._selectedSortItem = {el, cat, idx};
    el.style.borderColor = 'var(--cyan)';
    el.style.background = 'rgba(0,245,255,0.1)';
    document.getElementById('binLiving').onclick = () => dropInBin('living');
    document.getElementById('binNonliving').onclick = () => dropInBin('nonliving');
    document.getElementById('binLiving').classList.add('highlight');
    document.getElementById('binNonliving').classList.add('highlight');
}

function dropInBin(bin) {
    const sel = window._selectedSortItem;
    if (!sel) return;
    const binEl = document.getElementById(bin === 'living' ? 'binLiving' : 'binNonliving');
    if (sel.cat === bin) {
        binEl.classList.remove('highlight');
        binEl.classList.add('correct-drop');
        sel.el.classList.add('placed');
        sel.el.style.borderColor = 'var(--lime)';
        binEl.appendChild(sel.el.cloneNode(true));
        sel.el.style.display = 'none';
        window._sortCorrect++;
        showFloatingXP(15, sel.el.getBoundingClientRect().left, sel.el.getBoundingClientRect().top);
        novaReact('correct');
        if (window._sortCorrect >= window._sortItems.length) {
            setTimeout(() => scoreAnswer(true), 500);
        }
    } else {
        binEl.classList.add('wrong-drop');
        novaReact('encouraging', 'Think again!');
        setTimeout(() => { binEl.classList.remove('wrong-drop'); }, 500);
    }
    window._selectedSortItem = null;
    document.getElementById('binLiving').classList.remove('highlight');
    document.getElementById('binNonliving').classList.remove('highlight');
}

function updateMatterState(val) {
    val = parseInt(val);
    const temp = Math.round(val * 1.5 - 30);
    document.getElementById('thermoTemp').textContent = temp + '°C';
    const display = document.getElementById('matterDisplay');
    const emoji = document.getElementById('matterEmoji');
    const state = document.getElementById('matterState');
    const particles = document.getElementById('matterParticles');
    if (val < 33) {
        display.style.background = 'rgba(59,130,246,0.1)';
        display.style.borderColor = 'rgba(59,130,246,0.3)';
        emoji.textContent = '🧊';
        state.textContent = 'SOLID';
        state.style.color = '#3b82f6';
        particles.innerHTML = Array(12).fill('<div class="matter-particle solid"></div>').join('');
        window._matterStatesVisited.add('solid');
    } else if (val < 66) {
        display.style.background = 'rgba(16,185,129,0.1)';
        display.style.borderColor = 'rgba(16,185,129,0.3)';
        emoji.textContent = '💧';
        state.textContent = 'LIQUID';
        state.style.color = '#10b981';
        particles.innerHTML = Array(12).fill(0).map((_,i) => `<div class="matter-particle liquid" style="--wobble:${Math.random()*6-3}px"></div>`).join('');
        window._matterStatesVisited.add('liquid');
    } else {
        display.style.background = 'rgba(239,68,68,0.1)';
        display.style.borderColor = 'rgba(239,68,68,0.3)';
        emoji.textContent = '💨';
        state.textContent = 'GAS';
        state.style.color = '#ef4444';
        particles.innerHTML = Array(12).fill(0).map((_,i) => `<div class="matter-particle gas" style="--drift-x:${Math.random()*10-5}px;--drift-y:${Math.random()*10-5}px"></div>`).join('');
        window._matterStatesVisited.add('gas');
    }
}

function completeMatterExperiment() {
    if (gState.answered) return;
    if (window._matterStatesVisited.size >= 3) {
        novaReact('correct', 'All 3 states!');
        spawnConfetti(30);
        scoreAnswer(true);
    } else {
        novaReact('encouraging', `Found ${window._matterStatesVisited.size}/3 states!`);
    }
}

function selectElement(el, sym) {
    if (gState.answered) return;
    if (window._sciSelectedElements.length >= 2) return;
    el.classList.add('selected');
    window._sciSelectedElements.push(sym);
    if (window._sciSelectedElements.length === 2) {
        const [a, b] = window._sciSelectedElements;
        const reaction = ELEMENT_REACTIONS.find(r => (r.a === a && r.b === b) || (r.a === b && r.b === a));
        const area = document.getElementById('reactionArea');
        if (reaction) {
            area.classList.add('reacting');
            area.innerHTML = `
                <div style="text-align:center">
                    <div style="font-size:48px;margin-bottom:8px">${reaction.emoji}</div>
                    <div style="font-size:18px;font-weight:800;color:var(--lime)">${reaction.result}</div>
                    <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">${reaction.desc}</div>
                </div>`;
            spawnConfetti(25);
            novaReact('correct', 'Reaction!');
            scoreAnswer(true);
        } else {
            area.innerHTML = `<div style="color:var(--text-muted)">No reaction! Try different elements.</div>`;
            novaReact('wrong', 'No reaction!');
            setTimeout(() => {
                document.querySelectorAll('.element-card').forEach(c => c.classList.remove('selected'));
                window._sciSelectedElements = [];
                area.innerHTML = '<div style="color:var(--text-muted)">Select two elements to mix</div>';
                area.classList.remove('reacting');
            }, 1200);
        }
    }
}

function checkScienceAnswer(el, chosen, correct) {
    if (gState.answered) return;
    document.querySelectorAll('.gp-option').forEach(o => o.classList.add('disabled'));
    if (chosen === correct) {
        el.classList.add('correct');
        scoreAnswer(true);
    } else {
        el.classList.add('wrong');
        document.querySelectorAll('.gp-option').forEach(o => { if (o.textContent === correct) o.classList.add('correct'); });
        scoreAnswer(false);
    }
}

// === PATTERN QUEST ===
function setupPatternQuest() {
    gState.total = 10;
    gState.round = 0;
    advanceRound();
}

function renderPatternQuestRound() {
    const ag = getAgeGroup();
    const content = document.getElementById('gpContent');
    let q, opts, answer;

    if (ag === 'tiny') {
        const patterns = [
            {seq:['circle','square','circle','square'], next:'circle', opts:['circle','triangle','square']},
            {seq:['red','blue','red','blue'], next:'red', opts:['red','green','blue']},
            {seq:['big','small','big','small'], next:'big', opts:['big','medium','small']},
            {seq:['1','2','1','2'], next:'1', opts:['1','3','2']},
            {seq:['A','B','A','B'], next:'A', opts:['A','C','B']},
        ];
        const p = patterns[gState.round % patterns.length];
        q = `What comes next? ${p.seq.join(' \u2192 ')} \u2192 ?`;
        answer = p.next;
        opts = p.opts.sort(() => Math.random() - 0.5);
    } else if (ag === 'rising') {
        const step = Math.floor(Math.random()*5)+2;
        const start = Math.floor(Math.random()*10)+1;
        const seq = [];
        for (let i = 0; i < 5; i++) seq.push(start + step * i);
        const next = start + step * 5;
        answer = next;
        opts = [next, next+step, next-step, next+1].filter((v,i,a) => a.indexOf(v)===i).sort(() => Math.random()-0.5);
        if (opts.length < 4) opts.push(next + 2);
        q = `${seq.join(', ')}, ?`;
    } else {
        const step = Math.floor(Math.random()*4)+2;
        const start = Math.floor(Math.random()*5)+1;
        const seq = [];
        for (let i = 0; i < 4; i++) seq.push(start + step * i);
        const next = start + step * 4;
        answer = next;
        opts = [next, next+1, next-1, next+step].filter((v,i,a) => a.indexOf(v)===i).sort(() => Math.random()-0.5);
        q = `${seq.join(', ')}, ?`;
    }

    content.innerHTML = `
        <div style="font-size:36px;margin-bottom:8px">${icon('brain', 36)}</div>
        <div class="gp-question">${q}</div>
        <div class="gp-options">${opts.map(o =>
            `<div class="gp-option" onclick="checkPatternAnswer(this, '${o}', '${answer}')">${o}</div>`
        ).join('')}</div>
        <div class="gp-hint">Find the pattern!</div>`;
    startRoundTimer(ag === 'tiny' ? 20 : (ag === 'rising' ? 12 : 15));
}

function checkPatternAnswer(el, chosen, correct) {
    if (gState.answered) return;
    document.querySelectorAll('.gp-option').forEach(o => o.classList.add('disabled'));
    if (String(chosen) === String(correct)) {
        el.classList.add('correct');
        scoreAnswer(true);
    } else {
        el.classList.add('wrong');
        document.querySelectorAll('.gp-option').forEach(o => { if (o.textContent == correct) o.classList.add('correct'); });
        scoreAnswer(false);
    }
}

// === SPEED CHALLENGE ===
const SPEED_MATH = [
    {q:'7 + 8 = ?',opts:['15','14','16','13'],a:'15'},{q:'12 x 3 = ?',opts:['36','33','39','42'],a:'36'},
    {q:'56 / 7 = ?',opts:['8','7','9','6'],a:'8'},{q:'15 - 9 = ?',opts:['6','5','7','4'],a:'6'},
    {q:'9 x 9 = ?',opts:['81','72','90','63'],a:'81'},{q:'100 - 37 = ?',opts:['63','67','53','73'],a:'63'},
    {q:'25 + 48 = ?',opts:['73','72','74','71'],a:'73'},{q:'144 / 12 = ?',opts:['12','11','13','14'],a:'12'},
    {q:'8 x 7 = ?',opts:['56','54','48','63'],a:'56'},{q:'33 + 29 = ?',opts:['62','61','63','59'],a:'62'},
];
const SPEED_SPELL = [
    {q:'How do you spell the word for a large body of water?',opts:['Ocean','Oceon','Osean','Oacen'],a:'Ocean'},
    {q:'Which spelling is correct?',opts:['Necessary','Neccessary','Neccesary','Necesary'],a:'Necessary'},
    {q:'Correct spelling of a learning place?',opts:['School','Skool','Scool','Shool'],a:'School'},
    {q:'Which is spelled right?',opts:['Beautiful','Beautful','Beutiful','Beatiful'],a:'Beautiful'},
    {q:'Correct spelling?',opts:['Wednesday','Wensday','Wedensday','Wendsday'],a:'Wednesday'},
    {q:'How do you spell it?',opts:['Rhythm','Rythm','Rhthym','Rhythem'],a:'Rhythm'},
    {q:'Which is correct?',opts:['Separate','Seperate','Seprate','Separete'],a:'Separate'},
    {q:'Correct spelling?',opts:['Definitely','Definately','Definatly','Definitly'],a:'Definitely'},
    {q:'How do you spell it?',opts:['Accommodate','Accomodate','Acommodate','Acomodate'],a:'Accommodate'},
    {q:'Which is right?',opts:['Conscience','Concience','Consience','Conshence'],a:'Conscience'},
];

function setupSpeedChallenge() {
    const ag = getAgeGroup();
    let pool;
    if (ag === 'tiny') {
        pool = [
            {q:'2 + 1 = ?',opts:['3','2','4','1'],a:'3'},{q:'5 - 2 = ?',opts:['3','4','2','5'],a:'3'},
            {q:'3 + 3 = ?',opts:['6','5','7','4'],a:'6'},{q:'4 + 1 = ?',opts:['5','4','6','3'],a:'5'},
            {q:'Which is a fruit?',opts:['Apple','Chair','Book','Car'],a:'Apple'},
            {q:'How many legs does a cat have?',opts:['4','2','6','3'],a:'4'},
            {q:'What color is the sky?',opts:['Blue','Red','Green','Yellow'],a:'Blue'},
            {q:'Which is bigger?',opts:['Elephant','Mouse','Cat','Dog'],a:'Elephant'},
            {q:'1 + 2 = ?',opts:['3','1','4','2'],a:'3'},{q:'What do fish live in?',opts:['Water','Sand','Air','Mud'],a:'Water'},
        ];
    } else if (ag === 'rising') {
        pool = [...SPEED_MATH, ...SPEED_SPELL, ...SCIENCE_TRIVIA].sort(() => Math.random() - 0.5);
    } else {
        pool = [...SPEED_MATH, ...SPEED_SPELL, ...SCIENCE_TRIVIA].sort(() => Math.random() - 0.5);
    }
    const all = pool.sort(() => Math.random() - 0.5);
    gState.questions = all.slice(0, 10).map(q => ({q: q.q, opts: q.opts, a: q.a || q.answer}));
    gState.total = gState.questions.length;
    gState.round = 0;
    advanceRound();
}

function renderSpeedRound() {
    const q = gState.questions[(gState.round - 1) % gState.questions.length];
    const content = document.getElementById('gpContent');

    content.innerHTML = `
        <div style="font-size:36px;margin-bottom:8px">${icon('zap', 36)}</div>
        <div class="gp-question">${q.q}</div>
        <div class="gp-options">${q.opts.map(o =>
            `<div class="gp-option" onclick="checkSpeedAnswer(this, '${o.replace(/'/g,"\\'")}', '${(q.a || q.answer).replace(/'/g,"\\'")}')">${o}</div>`
        ).join('')}</div>`;
    startRoundTimer(12);
}

function checkSpeedAnswer(el, chosen, correct) {
    if (gState.answered) return;
    document.querySelectorAll('.gp-option').forEach(o => o.classList.add('disabled'));
    if (chosen === correct) {
        el.classList.add('correct');
        scoreAnswer(true);
    } else {
        el.classList.add('wrong');
        document.querySelectorAll('.gp-option').forEach(o => { if (o.textContent === correct) o.classList.add('correct'); });
        scoreAnswer(false);
    }
}

function connectGameWs() { renderGameSelect(); }

async function loadGamificationProfile() {
    const data = await apiCall('/gamification/profile');
    if (data) {
        document.getElementById('profileLevel').textContent = data.level || 1;
        const saved = localStorage.getItem('ob_profile');
        let savedProfile = null;
        try { savedProfile = JSON.parse(saved); } catch(e) {}
        if (!savedProfile) {
            document.getElementById('profileTitle').textContent = data.title || 'Curious Beginner';
        }
        document.getElementById('xpCurrent').textContent = (data.xp != null ? data.xp : 0).toLocaleString();
        document.getElementById('xpNext').textContent = (data.xp_for_next_level || 282).toLocaleString();
        document.getElementById('streakCount').textContent = data.streak != null ? data.streak : 0;
        if (data.xp_for_next_level) {
            const pct = (data.xp / data.xp_for_next_level) * 100;
            document.getElementById('xpBar').style.width = pct + '%';
        }
        const sessions = data.total_sessions || data.sessions || 0;
        const mastery = data.mastery_level || 0;
        const lessons = data.lessons_completed || 0;
        const time = data.total_time_minutes ? (data.total_time_minutes / 60).toFixed(1) + 'h' : '0h';
        document.getElementById('qsTotalSessions').textContent = sessions;
        document.getElementById('qsMastery').textContent = mastery + '%';
        document.getElementById('qsLessons').textContent = lessons;
        document.getElementById('qsTime').textContent = time;
    }
}

async function loadAchievements() {
    const data = await apiCall('/gamification/achievements');
    if (data && data.achievements) {
        const list = document.getElementById('achievementList');
        const unlocked = data.achievements.filter(a => a.unlocked).slice(0, 5);
        if (unlocked.length > 0) {
            list.innerHTML = '';
            unlocked.forEach(a => {
                const colors = {learning:'rgba(0,245,255,0.1)',streak:'rgba(255,165,0,0.1)',mastery:'rgba(0,255,136,0.1)',social:'rgba(139,92,246,0.1)'};
                list.innerHTML += `
                    <div class="achievement-item">
                        <div class="achievement-icon" style="background:${colors[a.category]||'rgba(0,245,255,0.1)'}">${a.icon ? icon(({'\u{1F31F}':'star','\u{1F525}':'flame','\u{1F9E0}':'brain','\u{1F4AC}':'chat','\u{1F3C6}':'trophy'})[a.icon] || 'trophy', 18) : icon('trophy', 18)}</div>
                        <div class="achievement-info">
                            <div class="achievement-name">${a.name}</div>
                            <div class="achievement-desc">${a.description}</div>
                        </div>
                    </div>`;
            });
        }
    }
}

function initThreeBackground() {
    const canvas = document.getElementById('three-bg');
    let scene, camera, renderer, particles, lines;

    try {
        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        renderer = new THREE.WebGLRenderer({canvas, alpha: true, antialias: true});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setClearColor(0x000000, 0);

        const particleCount = 80;
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        const velocities = [];
        const accentColors = [
            [0, 0.96, 1],
            [1, 0, 1],
            [0.545, 0.361, 0.965],
            [0, 1, 0.533]
        ];

        for (let i = 0; i < particleCount; i++) {
            positions[i*3] = (Math.random() - 0.5) * 30;
            positions[i*3+1] = (Math.random() - 0.5) * 20;
            positions[i*3+2] = (Math.random() - 0.5) * 15;
            velocities.push({
                x: (Math.random() - 0.5) * 0.01,
                y: (Math.random() - 0.5) * 0.01,
                z: (Math.random() - 0.5) * 0.005
            });
            const c = accentColors[Math.floor(Math.random() * accentColors.length)];
            colors[i*3] = c[0];
            colors[i*3+1] = c[1];
            colors[i*3+2] = c[2];
        }

        const particleGeom = new THREE.BufferGeometry();
        particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        particleGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        const particleMat = new THREE.PointsMaterial({
            size: 0.08,
            vertexColors: true,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending,
            sizeAttenuation: true,
        });
        particles = new THREE.Points(particleGeom, particleMat);
        scene.add(particles);

        const lineGeom = new THREE.BufferGeometry();
        const maxLines = particleCount * particleCount;
        const linePositions = new Float32Array(maxLines * 6);
        const lineColors = new Float32Array(maxLines * 6);
        lineGeom.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
        lineGeom.setAttribute('color', new THREE.BufferAttribute(lineColors, 3));
        const lineMat = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.3,
            blending: THREE.AdditiveBlending
        });
        lines = new THREE.LineSegments(lineGeom, lineMat);
        scene.add(lines);

        camera.position.z = 15;

        function animate() {
            requestAnimationFrame(animate);
            const pos = particles.geometry.attributes.position.array;
            for (let i = 0; i < particleCount; i++) {
                pos[i*3] += velocities[i].x;
                pos[i*3+1] += velocities[i].y;
                pos[i*3+2] += velocities[i].z;
                if (Math.abs(pos[i*3]) > 15) velocities[i].x *= -1;
                if (Math.abs(pos[i*3+1]) > 10) velocities[i].y *= -1;
                if (Math.abs(pos[i*3+2]) > 7.5) velocities[i].z *= -1;
            }
            particles.geometry.attributes.position.needsUpdate = true;

            let lineIdx = 0;
            const lp = lines.geometry.attributes.position.array;
            const lc = lines.geometry.attributes.color.array;
            for (let i = 0; i < particleCount; i++) {
                for (let j = i + 1; j < particleCount; j++) {
                    const dx = pos[i*3] - pos[j*3];
                    const dy = pos[i*3+1] - pos[j*3+1];
                    const dz = pos[i*3+2] - pos[j*3+2];
                    const dist = Math.sqrt(dx*dx + dy*dy + dz*dz);
                    if (dist < 4) {
                        const alpha = 1 - dist / 4;
                        lp[lineIdx*6] = pos[i*3]; lp[lineIdx*6+1] = pos[i*3+1]; lp[lineIdx*6+2] = pos[i*3+2];
                        lp[lineIdx*6+3] = pos[j*3]; lp[lineIdx*6+4] = pos[j*3+1]; lp[lineIdx*6+5] = pos[j*3+2];
                        lc[lineIdx*6] = 0; lc[lineIdx*6+1] = 0.96*alpha; lc[lineIdx*6+2] = alpha;
                        lc[lineIdx*6+3] = 0; lc[lineIdx*6+4] = 0.96*alpha; lc[lineIdx*6+5] = alpha;
                        lineIdx++;
                    }
                }
            }
            lineGeom.setDrawRange(0, lineIdx * 2);
            lines.geometry.attributes.position.needsUpdate = true;
            lines.geometry.attributes.color.needsUpdate = true;

            particles.rotation.y += 0.0003;
            particles.rotation.x += 0.0001;
            renderer.render(scene, camera);
        }
        animate();

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });
    } catch(e) {
        console.warn('Three.js background failed:', e);
    }
}

let lpData = [];

async function loadLearningPaths() {
    const data = await apiCall('/learning-paths');
    if (data && data.paths) {
        lpData = data.paths;
        renderLearningPaths();
    }
}

function renderLearningPaths() {
    const grid = document.getElementById('lpGrid');
    if (!grid) return;
    grid.innerHTML = lpData.map(p => {
        let btnClass = '';
        let btnText = 'Start Path';
        if (p.completed) { btnClass = 'completed'; btnText = icon('trophy', 14) + ' Completed'; }
        else if (p.enrolled) { btnClass = 'enrolled'; btnText = 'Continue'; }
        return `
        <div class="lp-card" onclick="openLpDetail('${p.id}')">
            <div class="lp-card-header">
                <div class="lp-card-icon" style="background:${p.color}22;border:1px solid ${p.color}44">${p.icon}</div>
                <div>
                    <div class="lp-card-title">${p.title}</div>
                    <div class="lp-card-subject" style="color:${p.color}">${p.subject}</div>
                </div>
            </div>
            <div class="lp-card-desc">${p.description}</div>
            <div class="lp-card-meta">
                <span>${p.milestone_count} milestones</span>
                <span>~${p.estimated_days} days</span>
            </div>
            ${p.enrolled ? `
                <div class="lp-progress-bar"><div class="lp-progress-fill" style="width:${p.progress_pct}%;background:${p.color}"></div></div>
                <div class="lp-progress-text"><span>${p.milestones_done}/${p.milestone_count} milestones</span><span>${p.progress_pct}%</span></div>
            ` : ''}
            <button class="lp-enroll-btn ${btnClass}" onclick="event.stopPropagation();${p.enrolled ? "openLpDetail('" + p.id + "')" : "enrollPath('" + p.id + "')"}">${btnText}</button>
        </div>`;
    }).join('');
}

async function enrollPath(pathId) {
    const data = await apiCall('/learning-paths/' + pathId + '/enroll', 'POST');
    if (data) {
        showToast(icon('path', 20), 'Enrolled!', 'You started a new learning path!');
        await loadLearningPaths();
        openLpDetail(pathId);
    }
}

async function openLpDetail(pathId) {
    const data = await apiCall('/learning-paths/' + pathId);
    if (!data) return;

    const modal = document.getElementById('lpDetailModal');
    const content = document.getElementById('lpDetailContent');

    let milestonesHtml = data.milestones.map(function(m, i) {
        const done = m.completed;
        const canComplete = data.enrolled && !done;
        return '<div class="lp-milestone ' + (done ? 'completed' : '') + '">' +
            '<div class="lp-milestone-check">' + (done ? icon('check', 14) : (i + 1)) + '</div>' +
            '<div class="lp-milestone-info">' +
                '<div class="lp-milestone-name">' + m.title + '</div>' +
                '<div class="lp-milestone-desc">' + m.description + '</div>' +
                (canComplete ? '<button class="lp-milestone-btn" onclick="completeMilestone(\'' + pathId + '\',\'' + m.id + '\')">Mark Complete</button>' : '') +
            '</div>' +
        '</div>';
    }).join('');

    let certHtml = '';
    if (data.completed && data.certificate_id) {
        certHtml = '<button class="lp-cert-btn" onclick="downloadCertificate(\'' + pathId + '\')">' + icon('certificate', 16) + ' Download Certificate</button>';
    }

    let enrollBtnHtml = '';
    if (!data.enrolled) {
        enrollBtnHtml = '<button class="lp-enroll-btn" onclick="enrollPath(\'' + pathId + '\')" style="margin-top:14px">Start This Path</button>';
    }

    content.innerHTML = '<button class="lp-detail-close" onclick="closeLpDetail()">&times;</button>' +
        '<div class="lp-detail-header">' +
            '<div class="lp-detail-icon" style="background:' + data.color + '22;border:1px solid ' + data.color + '44">' + data.icon + '</div>' +
            '<div>' +
                '<div class="lp-detail-title">' + data.title + '</div>' +
                '<div class="lp-detail-subject" style="color:' + data.color + '">' + data.subject + ' • ~' + data.estimated_days + ' days</div>' +
            '</div>' +
        '</div>' +
        '<div class="lp-detail-desc">' + data.description + '</div>' +
        (data.enrolled ? '<div class="lp-progress-bar" style="margin-bottom:4px"><div class="lp-progress-fill" style="width:' + data.progress_pct + '%;background:' + data.color + '"></div></div>' +
            '<div class="lp-progress-text" style="margin-bottom:16px"><span>' + data.milestones_done + '/' + data.milestones.length + ' milestones</span><span>' + data.progress_pct + '%</span></div>' : '') +
        '<div class="lp-milestones-title">Milestones</div>' +
        milestonesHtml +
        certHtml +
        enrollBtnHtml;

    modal.classList.add('active');
}

function closeLpDetail() {
    document.getElementById('lpDetailModal').classList.remove('active');
}

async function completeMilestone(pathId, milestoneId) {
    const data = await apiCall('/learning-paths/' + pathId + '/milestone/' + milestoneId + '/complete', 'POST');
    if (!data) return;

    if (data.path_completed) {
        showLpCelebration(icon('confetti', 24) + ' Path Complete!');
        showToast(icon('trophy', 20), 'Achievement Unlocked!', 'You completed a learning path!');
    } else {
        showToast(icon('star', 20), 'Milestone Complete!', data.milestones_done + '/' + data.total_milestones + ' milestones done');
    }

    await loadLearningPaths();
    openLpDetail(pathId);
}

function showLpCelebration(text) {
    const el = document.getElementById('lpCelebration');
    document.getElementById('lpCelebrationText').innerHTML = text;
    el.classList.add('active');
    setTimeout(function() { el.classList.remove('active'); }, 2000);
}

function downloadCertificate(pathId) {
    const url = API_BASE + '/learning-paths/' + pathId + '/certificate?student_name=Star%20Student';
    fetch(url, { headers: { 'Authorization': AUTH_HEADER } })
        .then(r => r.blob())
        .then(blob => {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'certificate_' + pathId + '.pdf';
            a.click();
            URL.revokeObjectURL(a.href);
        })
        .catch(() => showToast(icon('cross', 20), 'Error', 'Could not download certificate'));
}

let whiteboard = null;
let isListening = false;
let speechRecognition = null;
let autoReadEnabled = false;
let offlineStore = null;
let currentSpeech = null;

const avatarExpressions = {
    happy: '/assets/avatar-happy.png',
    thinking: '/assets/avatar-thinking.png',
    explaining: '/assets/avatar-explaining.png',
    celebrating: '/assets/avatar-celebrating.png',
    encouraging: '/assets/avatar-encouraging.png',
};

function setAvatarExpression(expression) {
    const img = document.getElementById('avatarImg');
    if (img && avatarExpressions[expression]) {
        img.src = avatarExpressions[expression];
    }
}

function setAvatarSpeech(text) {
    const el = document.getElementById('avatarSpeech');
    if (el) el.textContent = text;
}

function avatarReact(teachingStrategy, emotion) {
    const img = document.getElementById('avatarImg');
    if (img) {
        img.classList.remove('talking', 'celebrating', 'encouraging', 'thinking');
    }
    if (emotion === 'confused' || emotion === 'frustrated') {
        setAvatarExpression('encouraging');
        setAvatarSpeech("Don't worry, I'll help!");
        if (img) img.classList.add('encouraging');
    } else if (emotion === 'excited' || emotion === 'happy') {
        setAvatarExpression('celebrating');
        setAvatarSpeech("You're doing great!");
        if (img) img.classList.add('celebrating');
    } else if (teachingStrategy === 'socratic' || teachingStrategy === 'quiz') {
        setAvatarExpression('thinking');
        setAvatarSpeech('Hmm, think about it...');
        if (img) img.classList.add('thinking');
    } else if (teachingStrategy === 'explain' || teachingStrategy === 'example') {
        setAvatarExpression('explaining');
        setAvatarSpeech("Let me show you!");
        if (img) img.classList.add('talking');
    } else {
        setAvatarExpression('happy');
        setAvatarSpeech("I'm here for you!");
    }
    setTimeout(() => {
        if (img) img.classList.remove('talking', 'celebrating', 'encouraging', 'thinking');
    }, 3000);
}

function toggleVoiceInput() {
    const btn = document.getElementById('micBtn');
    if (isListening) {
        stopListening();
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast(icon('microphone', 20), 'Not Supported', 'Speech recognition is not available in this browser');
        return;
    }

    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = false;
    speechRecognition.interimResults = true;
    speechRecognition.lang = 'en-US';

    speechRecognition.onstart = () => {
        isListening = true;
        btn.classList.add('active');
        setAvatarExpression('thinking');
        setAvatarSpeech('Listening...');
    };

    speechRecognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        document.getElementById('chatInput').value = transcript;
        if (event.results[event.resultIndex].isFinal) {
            stopListening();
            setTimeout(() => sendChatMessage(), 300);
        }
    };

    speechRecognition.onerror = () => {
        stopListening();
        showToast(icon('microphone', 20), 'Error', 'Could not understand. Please try again.');
    };

    speechRecognition.onend = () => stopListening();

    speechRecognition.start();
}

function stopListening() {
    isListening = false;
    const btn = document.getElementById('micBtn');
    if (btn) btn.classList.remove('active');
    if (speechRecognition) {
        try { speechRecognition.stop(); } catch(e) {}
    }
    setAvatarExpression('happy');
    setAvatarSpeech('Ready to help!');
}

function toggleVoiceSettings() {
    const el = document.getElementById('voiceSettings');
    if (el) el.classList.toggle('show');
}

function toggleAutoRead() {
    autoReadEnabled = !autoReadEnabled;
    const toggle = document.getElementById('autoReadToggle');
    if (toggle) toggle.classList.toggle('on', autoReadEnabled);
}

async function speakText(text) {
    if (currentSpeech) {
        window.speechSynthesis.cancel();
        currentSpeech = null;
    }

    try {
        const res = await apiCall('/chat/tts', 'POST', { text: text.substring(0, 500) });
        if (res && res.audio) {
            const audio = new Audio('data:audio/mp3;base64,' + res.audio);
            const avatarImg = document.getElementById('avatarImg');
            if (avatarImg) avatarImg.classList.add('talking');
            audio.onended = () => {
                if (avatarImg) avatarImg.classList.remove('talking');
            };
            audio.play().catch(() => {
                if (avatarImg) avatarImg.classList.remove('talking');
                fallbackSpeak(text);
            });
            return;
        }
    } catch (e) {}

    fallbackSpeak(text);
}

function fallbackSpeak(text) {
    const rate = parseFloat(document.getElementById('voiceRate')?.value || '0.9');
    const pitch = parseFloat(document.getElementById('voicePitch')?.value || '1.1');
    const utterance = new SpeechSynthesisUtterance(text.replace(/[*#_`]/g, ''));
    utterance.rate = rate;
    utterance.pitch = pitch;
    const avatarImg = document.getElementById('avatarImg');
    if (avatarImg) avatarImg.classList.add('talking');
    utterance.onend = () => {
        if (avatarImg) avatarImg.classList.remove('talking');
    };
    currentSpeech = utterance;
    window.speechSynthesis.speak(utterance);
}

function addSpeakerButton(messageEl, text) {
    const btn = document.createElement('button');
    btn.className = 'voice-btn';
    btn.innerHTML = icon('speaker', 14);
    btn.title = 'Read aloud';
    btn.style.cssText = 'width:28px;height:28px;font-size:13px;margin-left:8px';
    btn.onclick = () => speakText(text);
    const meta = messageEl.querySelector('.msg-meta');
    if (meta) meta.appendChild(btn);
}

async function openLearningInsights() {
    const panel = document.getElementById('insightsPanel');
    panel.classList.add('open');
    const content = document.getElementById('insightsContent');
    content.innerHTML = `<div style="text-align:center;padding:40px 0;color:var(--text-muted)">
        <div class="typing-dots" style="justify-content:center"><span></span><span></span><span></span></div>
        <div style="margin-top:12px">Analyzing your learning patterns...</div>
    </div>`;

    const [profile, errors, trajectory] = await Promise.all([
        apiCall('/chat/metacognitive-profile', 'GET').catch(() => null),
        apiCall('/chat/error-patterns', 'GET').catch(() => null),
        apiCall(`/chat/learning-trajectory?age=${getStudentAge()}`, 'GET').catch(() => null)
    ]);

    let html = '';

    if (profile) {
        const mindset = profile.growth_mindset_score != null ? Math.round(profile.growth_mindset_score * 100) : null;
        const persistence = profile.persistence_score != null ? Math.round(profile.persistence_score * 100) : null;
        html += `<div class="insight-card">
            <h4>${icon('brain', 14)} Metacognitive Profile</h4>
            ${mindset != null ? `<div class="insight-stat"><span class="label">Growth Mindset</span><span class="value">${mindset}%</span></div>
            <div class="insight-meter"><div class="fill" style="width:${mindset}%;background:linear-gradient(90deg,var(--cyan),var(--purple))"></div></div>` : ''}
            ${persistence != null ? `<div class="insight-stat" style="margin-top:8px"><span class="label">Persistence</span><span class="value">${persistence}%</span></div>
            <div class="insight-meter"><div class="fill" style="width:${persistence}%;background:linear-gradient(90deg,var(--lime),var(--cyan))"></div></div>` : ''}
            ${profile.learning_style ? `<div class="insight-stat" style="margin-top:8px"><span class="label">Learning Style</span><span class="value">${profile.learning_style}</span></div>` : ''}
            ${profile.total_interactions != null ? `<div class="insight-stat"><span class="label">Total Interactions</span><span class="value">${profile.total_interactions}</span></div>` : ''}
            ${profile.preferred_strategies && profile.preferred_strategies.length ? `<div style="margin-top:8px"><span class="label" style="font-size:12px;color:var(--text-muted)">Preferred Strategies</span>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px">${profile.preferred_strategies.map(s => `<span class="meta-tag concept">${s}</span>`).join('')}</div></div>` : ''}
        </div>`;
    }

    if (errors && errors.total_errors != null) {
        html += `<div class="insight-card">
            <h4>${icon('target', 14)} Error Patterns</h4>
            <div class="insight-stat"><span class="label">Total Errors Tracked</span><span class="value">${errors.total_errors}</span></div>
            ${errors.top_patterns && errors.top_patterns.length ? errors.top_patterns.map(p => `
                <div class="insight-stat">
                    <span class="label">${p.skill || p.misconception_type || 'Unknown'}</span>
                    <span class="value" style="color:#ffaa00">${p.count || p.frequency || 0}x</span>
                </div>`).join('') : '<p>No error patterns detected yet. Keep learning!</p>'}
        </div>`;
    }

    if (trajectory) {
        html += `<div class="insight-card">
            <h4>${icon('chart', 14)} Learning Trajectory</h4>
            ${trajectory.overall_assessment ? `<p>${trajectory.overall_assessment}</p>` : ''}
            ${trajectory.daily_practice_minutes ? `<div class="insight-stat" style="margin-top:8px"><span class="label">Recommended Daily Practice</span><span class="value">${trajectory.daily_practice_minutes} min</span></div>` : ''}
            ${trajectory.skills_to_review && trajectory.skills_to_review.length ? `<div style="margin-top:8px"><span class="label" style="font-size:12px;color:var(--text-muted)">Skills to Review</span>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px">${trajectory.skills_to_review.map(s => `<span class="meta-tag strategy">${s}</span>`).join('')}</div></div>` : ''}
            ${trajectory.skills_to_advance && trajectory.skills_to_advance.length ? `<div style="margin-top:8px"><span class="label" style="font-size:12px;color:var(--text-muted)">Ready to Advance</span>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px">${trajectory.skills_to_advance.map(s => `<span class="meta-tag concept" style="color:var(--lime);border-color:rgba(0,255,136,0.2);background:rgba(0,255,136,0.08)">${s}</span>`).join('')}</div></div>` : ''}
            ${trajectory.parent_insights ? `<div style="margin-top:12px;padding:10px;border-radius:8px;background:rgba(0,245,255,0.04);border:1px solid rgba(0,245,255,0.1)"><span style="font-size:11px;font-weight:600;color:var(--cyan)">FOR PARENTS</span><p style="margin-top:4px">${trajectory.parent_insights}</p></div>` : ''}
        </div>`;
    }

    if (!html) {
        html = `<div class="insight-card">
            <h4>${icon('star', 14)} Getting Started</h4>
            <p>Chat with Nova to start building your learning profile! The more you interact, the more personalized your insights become.</p>
            <p style="margin-top:8px">Try asking a question about math, science, or reading to get started.</p>
        </div>`;
    }

    content.innerHTML = html;
}

function closeInsights() {
    document.getElementById('insightsPanel').classList.remove('open');
}

function openWhiteboard() {
    const overlay = document.getElementById('whiteboardOverlay');
    overlay.classList.add('show');
    if (!whiteboard) {
        const canvas = document.getElementById('whiteboardCanvas');
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
        whiteboard = new Whiteboard('whiteboardCanvas');
    } else {
        whiteboard.resize();
    }
}

function closeWhiteboard() {
    document.getElementById('whiteboardOverlay').classList.remove('show');
}

function setWbTool(tool, btn) {
    if (whiteboard) whiteboard.setTool(tool);
    document.querySelectorAll('.wb-tool-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
}

function setWbColor(color, el) {
    if (whiteboard) whiteboard.setColor(color);
    document.querySelectorAll('.wb-color').forEach(c => c.classList.remove('active'));
    if (el) el.classList.add('active');
}

function wbUndo() { if (whiteboard) whiteboard.undo(); }
function wbRedo() { if (whiteboard) whiteboard.redo(); }
function wbClear() { if (whiteboard) whiteboard.clear(); }

async function wbAIExplain() {
    const topic = document.getElementById('chatInput')?.value || currentSubject;
    showToast(icon('robot', 20), 'AI Whiteboard', 'Generating visual explanation...');
    try {
        const data = await apiCall('/chat/whiteboard', 'POST', {
            concept: topic || 'fractions',
            subject: currentSubject,
            age: getPlayerAge(),
        });
        if (data && data.steps) {
            whiteboard.clear();
            if (data.title) {
                whiteboard.drawText(data.title, whiteboard.canvas.width / 2, 30, '#4ecdc4', 24);
            }
            await whiteboard.renderAISteps(data.steps);
            showToast(icon('check', 20), 'Done', 'Visual explanation rendered!');
        }
    } catch (e) {
        showToast(icon('cross', 20), 'Error', 'Could not generate whiteboard content');
    }
}

function wbExport() {
    if (!whiteboard) return;
    const dataUrl = whiteboard.exportPNG();
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = 'whiteboard.png';
    a.click();
    showToast(icon('save', 20), 'Saved', 'Whiteboard exported as PNG');
}

function setupOfflineMode() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').then(() => {
            console.log('Service worker registered');
        }).catch(e => console.warn('SW registration failed:', e));
    }

    window.addEventListener('online', () => {
        document.getElementById('offlineBanner').classList.remove('show');
        const syncEl = document.getElementById('syncIndicator');
        syncEl.classList.add('show');
        setTimeout(() => syncEl.classList.remove('show'), 3000);
        showToast(icon('globe', 20), 'Back Online', 'Syncing your progress...');
    });

    window.addEventListener('offline', () => {
        document.getElementById('offlineBanner').classList.add('show');
        showToast(icon('wifi-off', 20), 'Offline', 'You can still learn! Progress will sync later.');
    });
}

async function initOfflineStore() {
    if (typeof OfflineStore !== 'undefined') {
        offlineStore = new OfflineStore();
        await offlineStore.init();
    }
}

let obSelectedSubjects = [];
let obSelectedAvatar = 'robot';
const obAvatarEmojis = {robot:icon('robot', 28),astro:icon('rocket', 28),star:icon('star', 28),cat:icon('sparkle', 28),dragon:icon('flame', 28)};

function obNext(step) {
    if (step === 3) {
        const name = document.getElementById('obNameInput').value.trim();
        if (!name) return;
        const initials = name.split(/\s+/).map(w => w[0]).join('').toUpperCase().slice(0,2);
        document.getElementById('obInitialsOption').textContent = initials || '?';
    }
    document.querySelectorAll('.onboarding-step').forEach(s => s.classList.remove('active'));
    document.getElementById('obStep' + step).classList.add('active');
    document.querySelectorAll('.ob-dot').forEach(d => {
        const ds = parseInt(d.dataset.step);
        d.classList.remove('active','done');
        if (ds === step) d.classList.add('active');
        else if (ds < step) d.classList.add('done');
    });
    if (step === 2) {
        setTimeout(() => document.getElementById('obNameInput').focus(), 100);
    }
}

document.addEventListener('input', function(e) {
    if (e.target.id === 'obNameInput') {
        document.getElementById('obNameBtn').disabled = !e.target.value.trim();
    }
});

function obUpdateAge(val) {
    document.getElementById('obAgeDisplay').textContent = val;
    const age = parseInt(val);
    document.querySelectorAll('.ob-age-group').forEach(g => g.classList.remove('selected'));
    if (age <= 5) document.querySelector('.ob-age-group[data-group="tiny"]').classList.add('selected');
    else if (age <= 8) document.querySelector('.ob-age-group[data-group="junior"]').classList.add('selected');
    else document.querySelector('.ob-age-group[data-group="rising"]').classList.add('selected');
}

function obSelectAgeGroup(el, group) {
    document.querySelectorAll('.ob-age-group').forEach(g => g.classList.remove('selected'));
    el.classList.add('selected');
    const slider = document.getElementById('obAgeSlider');
    if (group === 'tiny') { slider.value = 4; obUpdateAge(4); }
    else if (group === 'junior') { slider.value = 7; obUpdateAge(7); }
    else { slider.value = 10; obUpdateAge(10); }
}

function obToggleSubject(el) {
    el.classList.toggle('selected');
    obSelectedSubjects = Array.from(document.querySelectorAll('.ob-subject-card.selected'))
        .map(c => c.dataset.subj);
    document.getElementById('obSubjBtn').disabled = obSelectedSubjects.length === 0;
}

function obSelectAvatar(el) {
    document.querySelectorAll('.ob-avatar-option').forEach(a => a.classList.remove('selected'));
    el.classList.add('selected');
    obSelectedAvatar = el.dataset.avatar;
}

function obFinish() {
    const name = document.getElementById('obNameInput').value.trim() || 'Learner';
    const age = parseInt(document.getElementById('obAgeSlider').value);
    let ageGroup = 'junior';
    if (age <= 5) ageGroup = 'tiny';
    else if (age <= 8) ageGroup = 'junior';
    else ageGroup = 'rising';

    const profile = {
        name: name,
        age: age,
        ageGroup: ageGroup,
        subjects: obSelectedSubjects.length ? obSelectedSubjects : ['math'],
        avatar: obSelectedAvatar,
        onboarded: true,
        onboardedAt: new Date().toISOString()
    };

    localStorage.setItem('onboarded', 'true');
    localStorage.setItem('ob_profile', JSON.stringify(profile));

    applyOnboardingProfile(profile);

    apiCall('/adapt/onboarding', 'POST', {
        name: profile.name,
        age: profile.age,
        age_group: profile.ageGroup,
        subjects: profile.subjects,
        avatar: profile.avatar
    }).then(res => {
        if (res) showToast(icon('check', 20), 'Profile Saved', 'Your preferences are synced!');
    }).catch(() => {
        showToast(icon('warning', 20), 'Sync Pending', 'Your profile will sync when connected.');
    });

    document.getElementById('onboardingOverlay').classList.add('hidden');
}

function applyOnboardingProfile(profile) {
    const nameEl = document.getElementById('profileName');
    if (nameEl) nameEl.textContent = profile.name;

    const titleEl = document.getElementById('profileTitle');
    if (titleEl) {
        const titles = {tiny:'Tiny Explorer',junior:'Junior Learner',rising:'Rising Star'};
        titleEl.textContent = titles[profile.ageGroup] || 'Learner';
    }

    const metaEl = document.getElementById('lessonMeta');
    if (metaEl && profile.age) {
        const gradeLabels = {tiny:'Pre-K',junior:'Elementary',rising:'Advanced'};
        const ageLabel = gradeLabels[profile.ageGroup] || '';
        metaEl.textContent = 'Mathematics \u2022 Age ' + profile.age + ' \u2022 ' + ageLabel;
    }

    const avatarEl = document.querySelector('.profile-card .avatar');
    if (avatarEl) {
        if (profile.avatar === 'initials') {
            const initials = profile.name.split(/\s+/).map(w => w[0]).join('').toUpperCase().slice(0,2);
            avatarEl.textContent = initials;
            avatarEl.style.fontSize = '22px';
            avatarEl.style.fontWeight = '800';
        } else {
            avatarEl.innerHTML = obAvatarEmojis[profile.avatar] || icon('robot', 28);
        }
    }

    document.body.classList.remove('age-tiny', 'age-junior', 'age-rising');
    if (profile.ageGroup === 'tiny') document.body.classList.add('age-tiny');
    else if (profile.ageGroup === 'rising') document.body.classList.add('age-rising');

    const chatMsg = document.querySelector('#chatMessages .msg.ai .msg-bubble');
    if (chatMsg) {
        const greetings = {
            tiny: `<p>Hi <strong>${profile.name}</strong>! ${icon('wave', 18)} I'm Nova! I'm your learning buddy and I'm SO excited to explore with you!</p><p>What should we learn about today? We can play with <strong>${profile.subjects.join('</strong> or <strong>')}</strong>! Tap the ${icon('microphone', 14)} button to talk to me!</p>`,
            junior: `<p>Hello, <strong>${profile.name}</strong>! ${icon('wave', 18)} I'm Nova, your AI tutor! I'm here to help you learn and grow. I use the <strong>Socratic method</strong> — that means I'll ask you guiding questions to help you discover the answers yourself!</p><p>What would you like to explore today? You can ask me about <strong>${profile.subjects.join('</strong>, <strong>')}</strong>. You can also use the ${icon('microphone', 14)} microphone to talk to me!</p>`,
            rising: `<p>Hey <strong>${profile.name}</strong>! ${icon('wave', 18)} I'm Nova, your AI tutor. I use Socratic questioning to help you think critically and discover answers on your own.</p><p>Ready to dive in? I can help with <strong>${profile.subjects.join('</strong>, <strong>')}</strong>, or ask me anything. Use the ${icon('microphone', 14)} mic for voice chat.</p>`
        };
        chatMsg.innerHTML = greetings[profile.ageGroup] || greetings.junior;
    }
}

function loadSavedProfile() {
    const saved = localStorage.getItem('ob_profile');
    if (saved) {
        try {
            const profile = JSON.parse(saved);
            applyOnboardingProfile(profile);
        } catch(e) {}
    }
}

function populateIcons() {
    document.querySelectorAll('.ic[data-i]').forEach(function(el) {
        el.innerHTML = icon(el.dataset.i, parseInt(el.dataset.s) || undefined);
    });
}

function init() {
    populateIcons();
    const isOnboarded = localStorage.getItem('onboarded');
    if (isOnboarded) {
        document.getElementById('onboardingOverlay').classList.add('hidden');
        loadSavedProfile();
    }

    initThreeBackground();
    loadGamificationProfile();
    loadAchievements();
    loadVideoLibrary('all');
    loadLearningPaths();
    loadDailySchedule();
    initChatFeatures();
    setupOfflineMode();
    initOfflineStore();

    for (let i = 0; i < 10; i++) {
        emotionHistory.push(50 + Math.random() * 30);
    }
    drawSparkline();
    updateEmotionGauge('engaged', 0.65);

    if (isOnboarded) {
        const saved = localStorage.getItem('ob_profile');
        let userName = 'Learner';
        try { userName = JSON.parse(saved).name; } catch(e) {}
        setTimeout(() => showToast(icon('gamepad', 20), 'Welcome Back, ' + userName + '!', 'Your streak continues!'), 1500);
    }
}

document.addEventListener('DOMContentLoaded', init);

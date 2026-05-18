(function () {
  'use strict';

  const API_BASE = '/api/v2/profile';

  const state = {
    userId: getUserId(),
    summary: null,
    currentReading: null,
    constellation: null,
    sentences: [],
    timeline: [],
    questions: [],
    persona: null,
    lounges: [],
    readers: [],
    avatarDataUrl: null
  };

  const $ = (sel) => document.querySelector(sel);

  /* ─── Init ─────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    if (!localStorage.getItem('luma_token') && !state.userId) {
      window.location.href = '/auth/login';
      return;
    }
    initNav();
    loadAvatarFromStorage();
    bindActions();
    loadProfile();
    initTagline();
  });

  /* ─── Auth / User helpers ───────────────────────────── */
  function getStoredUser() {
    try { return JSON.parse(localStorage.getItem('luma_user') || '{}'); } catch (_) { return {}; }
  }
  function getUserId() {
    const params = new URLSearchParams(window.location.search);
    const stored = getStoredUser();
    return params.get('user_id') || stored.user_id || stored.id || '';
  }
  function authHeaders() {
    const token = localStorage.getItem('luma_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
  async function apiGet(path) {
    const qs = state.userId ? `?user_id=${encodeURIComponent(state.userId)}` : '';
    const url = `${API_BASE}${path}${qs}`;
    const res = await fetch(url, { headers: { Accept: 'application/json', ...authHeaders() } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.error || `API ${res.status}`);
    return data;
  }

  /* ─── Nav ───────────────────────────────────────────── */
  function initNav() {
    const el = $('#nav-user');
    if (!el) return;
    const user = getStoredUser();
    if (user.display_name || user.email) {
      const name = escHtml(user.display_name || user.email || '');
      el.innerHTML = `<span style="color:var(--muted);font-size:.74rem">${name}</span>
        <button class="nav-logout" onclick="logoutUser()">로그아웃</button>`;
    } else {
      el.innerHTML = '<a href="/auth/login" class="nav-login-btn">로그인</a>';
    }
  }
  window.logoutUser = function () {
    localStorage.removeItem('luma_token');
    localStorage.removeItem('luma_user');
    window.location.href = '/auth/login';
  };

  /* ─── Avatar photo (localStorage) ──────────────────── */
  function loadAvatarFromStorage() {
    const key = avatarStorageKey();
    const saved = localStorage.getItem(key) || localStorage.getItem('luma_avatar');
    if (!saved) return;
    setAvatarImage(saved);
    try {
      if (!localStorage.getItem(key)) localStorage.setItem(key, saved);
    } catch (_) {}
  }
  function avatarStorageKey() {
    return `luma_avatar_${state.userId || 'anonymous'}`;
  }

  function setAvatarImage(dataUrl) {
    if (!dataUrl) return;
    state.avatarDataUrl = dataUrl;
    ['#profile-avatar', '#modal-avatar-preview'].forEach((sel) => {
      const box = $(sel);
      if (box) box.classList.add('has-image');
    });
    ['#avatar-img', '#modal-avatar-img'].forEach((sel) => {
      const img = $(sel);
      if (!img) return;
      img.src = dataUrl;
      img.removeAttribute('hidden');
      img.style.display = 'block';
      img.style.visibility = 'visible';
      img.style.opacity = '1';
      img.style.zIndex = '3';
    });
    ['#avatar-initial', '#modal-avatar-initial'].forEach((sel) => {
      const el = $(sel);
      if (!el) return;
      el.style.display = 'none';
      el.setAttribute('aria-hidden', 'true');
    });
  }

  function bindAvatarUpload(inputId) {
    const input = $(inputId);
    if (!input) return;
    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        const url = e.target && e.target.result;
        if (!url) return;
        setAvatarImage(url);
        try {
          localStorage.setItem(avatarStorageKey(), url);
        } catch (_) {}
        toast('프로필을 저장했습니다. 🌿');
      };
      reader.readAsDataURL(file);
    });
  }

  /* ─── Load all profile data ─────────────────────────── */
  async function loadProfile() {
    const requests = {
      summary: apiGet('/summary'),
      currentReading: apiGet('/current-reading'),
      constellation: apiGet('/constellation'),
      sentences: apiGet('/sentences'),
      timeline: apiGet('/timeline'),
      questions: apiGet('/questions'),
      persona: apiGet('/persona'),
      lounges: apiGet('/lounges'),
      readers: apiGet('/similar-readers')
    };

    const results = await Promise.allSettled(
      Object.entries(requests).map(async ([key, p]) => [key, await p])
    );

    results.forEach((result) => {
      if (result.status === 'fulfilled') absorbResponse(...result.value);
    });

    renderAll();
  }

  function absorbResponse(key, data) {
    if (key === 'summary') state.summary = { ...(data.profile || {}), stats: data.stats || {} };
    if (key === 'currentReading') state.currentReading = data.current_reading || null;
    if (key === 'constellation') state.constellation = data.constellation || { nodes: [], links: [] };
    if (key === 'sentences') state.sentences = data.sentences || [];
    if (key === 'timeline') state.timeline = data.timeline || [];
    if (key === 'questions') state.questions = data.questions || [];
    if (key === 'persona') state.persona = data.persona || {};
    if (key === 'lounges') state.lounges = data.lounges || [];
    if (key === 'readers') state.readers = data.readers || [];
  }

  /* ─── Render all sections ───────────────────────────── */
  function renderAll() {
    renderSummary();
    renderConstellation();
    renderCurrentReading();
    renderPersona();
    renderSentences();
    renderTimeline();
    renderQuestions();
  }

  /* ─── Summary / Profile card ────────────────────────── */
  function renderSummary() {
    const stored = getStoredUser();
    const profile = {
      display_name: stored.display_name || stored.name || 'LUMA 독자',
      email: stored.email || state.userId,
      bio: stored.bio || '',
      tags: stored.tags || [],
      mbti: stored.mbti || '',
      persona: '사유형 독자',
      ...(state.summary || {})
    };
    const tags = Array.isArray(profile.tags) ? profile.tags : [];

    setText('#hero-name', profile.display_name);
    setText('#hero-bio', profile.bio);
    setText('#profile-name', profile.display_name);
    setText('#profile-email', profile.email || state.userId);
    setText('#profile-bio-text', profile.bio);
    setText('#hero-persona', profile.persona || '사유형 독자');
    setText('#profile-persona', profile.persona || '사유형 독자');
    setText('#luma-tagline', `${profile.persona || '사유형 독자'}의 독서 항해`);

    const initials = (profile.display_name || '나').trim().slice(0, 1);
    setText('#avatar-initial', initials);
    setText('#modal-avatar-initial', initials);
    if (state.avatarDataUrl) setAvatarImage(state.avatarDataUrl);

    renderTags('#hero-tags', tags);
    renderTags('#profile-tags', tags);

    const stats = profile.stats || {};
    setText('#stat-books', stats.books_read || stats.total_books || stats.books || 0);
    setText('#stat-memos', stats.memos || stats.saved_sentences || state.sentences.length || 0);
    setText('#stat-connections', stats.connections || 0);
    setText('#stat-streak', (stats.streak_days || stats.streak || 7) + '일');
  }

  /* ─── Constellation ─────────────────────────────────── */
  function renderConstellation() {
    const root = $('#constellation-view');
    if (!root) return;

    const data = state.constellation || {};
    const nodes = Array.isArray(data.nodes) ? data.nodes : [];
    const links = Array.isArray(data.links) ? data.links : [];

    if (nodes.length <= 1) {
      root.innerHTML = '<div class="empty-state">별자리 데이터를 불러오는 중입니다.</div>';
      return;
    }
    const displayNodes = nodes;
    const displayLinks = links;

    const W = 760, H = 320;
    const cx = W / 2, cy = H / 2;
    const positions = {};
    const userNode = displayNodes.find((n) => n.id === 'user');
    const orbitNodes = displayNodes.filter((n) => n.id !== 'user');
    positions['user'] = { x: cx, y: cy };
    orbitNodes.forEach((node, i) => {
      const angle = (Math.PI * 2 * i) / orbitNodes.length - Math.PI / 2;
      const radius = i % 2 === 0 ? 118 : 158;
      positions[node.id] = {
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius
      };
    });

    const lines = displayLinks.map((l) => {
      const s = positions[l.source] || { x: cx, y: cy };
      const t = positions[l.target] || { x: cx, y: cy };
      return `<line class="const-line" x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}"/>`;
    }).join('');

    const nodesSvg = displayNodes.map((node) => {
      const p = positions[node.id] || { x: cx, y: cy };
      const isUser = node.id === 'user';
      const r = isUser ? 30 : 18;
      const cls = `const-circle-${node.type || 'tag'}`;
      const label = escHtml(node.label || node.id);
      const shortLabel = label.length > 8 ? label.slice(0, 7) + '…' : label;
      return `
        <g class="const-node" tabindex="0">
          ${isUser
            ? `<circle cx="${p.x}" cy="${p.y}" r="${r}" class="${cls}"/>`
            : `<circle cx="${p.x}" cy="${p.y}" r="${r}" class="${cls}" opacity=".85"/>`
          }
          <text x="${p.x}" y="${p.y + r + 14}">${shortLabel}</text>
        </g>`;
    }).join('');

    const legendItems = [
      { type: 'book', label: '책', color: 'rgba(125,232,168,.6)' },
      { type: 'sentence', label: '문장', color: 'rgba(245,200,107,.55)' },
      { type: 'question', label: '질문', color: 'rgba(143,220,255,.55)' },
      { type: 'emotion', label: '감정', color: 'rgba(248,113,113,.55)' },
      { type: 'tag', label: '키워드', color: 'rgba(74,222,128,.5)' }
    ].map((item) =>
      `<span class="const-legend-item">
        <span class="const-dot" style="background:${item.color}"></span>${item.label}
      </span>`
    ).join('');

    root.innerHTML = `
      <svg class="constellation-svg" viewBox="0 0 ${W} ${H}" aria-label="생각의 별자리">
        <g>${lines}</g>${nodesSvg}
      </svg>
      <div class="const-legend">${legendItems}</div>`;
  }

  /* ─── Current Reading ───────────────────────────────── */
  function renderCurrentReading() {
    const root = $('#current-reading');
    if (!root) return;
    const book = state.currentReading || {};
    if (!book || !book.title) {
      root.innerHTML = '<article class="reading-card empty-state">별자리 데이터를 불러오는 중입니다.</article>';
      return;
    }
    const progress = Math.min(Math.max(Number(book.progress || book.progress_percent || 0), 0), 100);
    const tags = book.tags || [];

    root.innerHTML = `
      <article class="reading-card">
        <div class="book-cover-thumb">
          ${book.cover_url
            ? `<img src="${escAttr(book.cover_url)}" alt="">`
            : '📖'}
        </div>
        <div class="reading-body">
          <span class="section-kicker">지금 읽는 책</span>
          <h3>${escHtml(book.title || '')}</h3>
          <p class="muted">${escHtml(book.author || '칼 세이건')}</p>
          <div class="progress-row">
            <div class="progress-bar"><span style="width:${progress}%"></span></div>
            <strong>${progress}%</strong>
          </div>
          <blockquote>${escHtml(book.recent_memo || '인간은 우주를 이해하려고 하는 존재다.')}</blockquote>
          <div class="reading-meta">
            <span>최근 감정: ${escHtml(book.recent_emotion || '경외')}</span>
            ${tags.map((t) => `<span>#${escHtml(t)}</span>`).join('')}
          </div>
          <div class="button-row">
            <a class="soft-button" href="/heart">이어 읽기</a>
            <a class="soft-button" href="/deepdive">영상 보기</a>
            <a class="gold-button" href="/socrates">질문 만들기</a>
          </div>
        </div>
      </article>`;
  }

  /* ─── Persona ───────────────────────────────────────── */
  function renderPersona() {
    const root = $('#persona-view');
    if (!root) return;
    const persona = state.persona || {};
    const traits = persona.traits || [
      '질문을 남기며 읽습니다.',
      '철학과 인간 존재에 관심이 많습니다.',
      '감정보다 의미를 오래 붙잡습니다.'
    ];
    const topics = persona.top_subjects || persona.topics || persona.favorite_topics || [];
    const emotions = persona.top_emotions || persona.emotions || [];

    root.innerHTML = `
      <article class="persona-card">
        <div>
          <span class="section-kicker">독서 성향 분석</span>
          <h3>당신은 ${escHtml(persona.persona || '사유형 독자')}입니다.</h3>
          <p>${escHtml(persona.summary || '질문을 따라 책을 읽고, 문장 안에서 오래 머무는 독자입니다.')}</p>
        </div>
        <ul class="persona-traits">
          ${traits.map((t) => `<li>${escHtml(t)}</li>`).join('')}
        </ul>
        <div class="persona-grid">
          <span><strong>자주 읽는 주제</strong>${topics.map(escHtml).join(', ')}</span>
          <span><strong>자주 남기는 감정</strong>${emotions.map(escHtml).join(', ')}</span>
          <span><strong>추천 다음 활동</strong>${escHtml(persona.recommendation || '철학 Lounge에 참여해보세요.')}</span>
        </div>
        <div class="button-row">
          <a class="soft-button" href="/lounge">탐사 성운 가기</a>
          <a class="gold-button" href="/socrates">소크라테스 대화</a>
        </div>
      </article>`;
  }

  /* ─── Sentences ─────────────────────────────────────── */
  function renderSentences() {
    const root = $('#sentence-list');
    if (!root) return;
    if (!state.sentences.length) {
      root.innerHTML = '<div class="empty-state">읽는 책을 확인하는 중입니다.</div>';
      return;
    }
    const sentences = state.sentences;

    root.innerHTML = sentences.map((item) => `
      <article class="archive-card">
        <blockquote>${escHtml(item.sentence || item.quote || '')}</blockquote>
        <p class="card-meta">${escHtml(item.book_title || '나의 책장')} · ${formatDate(item.saved_at || item.created_at)}</p>
        <div class="tag-row compact">
          ${(item.tags || []).map((t) => `<span>#${escHtml(t)}</span>`).join('')}
        </div>
        <div class="button-row compact">
          <button type="button" class="soft-button" data-toast="다시 읽기 목록에 담았습니다.">다시 읽기</button>
          <a class="soft-button" href="/live">토론 만들기</a>
          <button type="button" class="soft-button" data-share="${escAttr(item.sentence || item.quote || '')}">공유</button>
        </div>
      </article>`).join('');
  }

  /* ─── Timeline ──────────────────────────────────────── */
  function renderTimeline() {
    const root = $('#timeline-list');
    if (!root) return;
    if (!state.timeline.length) {
      root.innerHTML = '<div class="empty-state">문장을 불러오는 중입니다.</div>';
      return;
    }
    const items = state.timeline;

    root.innerHTML = '<div class="timeline-list">' + items.map((item) => `
      <div class="timeline-item">
        <div class="timeline-dot">${item.emoji || '📌'}</div>
        <div class="timeline-content">
          <time>${escHtml(formatDate(item.date || item.created_at))}</time>
          <strong>${escHtml(item.title || item.event || '')}</strong>
          <p>${escHtml(item.detail || item.description || '')}</p>
        </div>
      </div>`).join('') + '</div>';
  }

  /* ─── Questions ─────────────────────────────────────── */
  function renderQuestions() {
    const root = $('#question-list');
    if (!root) return;
    if (!state.questions.length) {
      root.innerHTML = '<div class="empty-state">타임라인을 정리하는 중입니다.</div>';
      return;
    }
    const questions = state.questions;

    root.innerHTML = questions.map((item) => `
      <article class="question-card">
        <h3>${escHtml(item.question || item.title || '')}</h3>
        <p class="card-meta">${escHtml(item.book_title || item.book || '')}</p>
        <div class="tag-row compact">
          ${(item.tags || []).map((t) => `<span>#${escHtml(t)}</span>`).join('')}
        </div>
        <div class="button-row compact">
          <a class="soft-button" href="/socrates">다시 생각하기</a>
          <a class="gold-button" href="/lounge">Lounge 공유</a>
        </div>
      </article>`).join('');
  }

  /* ─── Actions ───────────────────────────────────────── */
  function bindActions() {
    bindAvatarUpload('#avatar-upload');
    bindAvatarUpload('#modal-avatar-upload');

    document.addEventListener('click', async (e) => {
      const action = e.target.closest('[data-action]');
      const toastEl = e.target.closest('[data-toast]');
      const shareEl = e.target.closest('[data-share]');

      if (toastEl) toast(toastEl.dataset.toast);
      if (shareEl) shareText(shareEl.dataset.share);
      if (!action) return;

      const act = action.dataset.action;
      if (act === 'edit-profile') openModal();
      if (act === 'close-modal') closeModal();
      if (act === 'save-profile') await saveProfile();
      if (act === 'share-thought') window.location.href = '/lounge';
    });

    // Close modal on backdrop click
    const modal = $('#profile-modal');
    if (modal) modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
  }

  /* ─── Modal ─────────────────────────────────────────── */
  function openModal() {
    const stored = getStoredUser();
    const profile = state.summary || {};
    const tags = profile.tags || stored.tags || [];

    const nameEl = $('#edit-name');
    const bioEl = $('#edit-bio');
    const tagsEl = $('#edit-tags');
    const emailEl = $('#edit-email');
    const mbtiEl = $('#edit-mbti');

    if (nameEl) nameEl.value = profile.display_name || stored.display_name || stored.name || '';
    if (bioEl) bioEl.value = profile.bio || stored.bio || '';
    if (tagsEl) tagsEl.value = Array.isArray(tags) ? tags.join(', ') : '';
    if (emailEl) emailEl.value = stored.email || state.userId;
    if (mbtiEl) mbtiEl.value = profile.mbti || stored.mbti || '';

    // Sync avatar preview in modal
    if (state.avatarDataUrl) {
      const img = $('#modal-avatar-img');
      const init = $('#modal-avatar-initial');
      if (img) { img.src = state.avatarDataUrl; img.style.display = 'block'; }
      if (init) init.style.display = 'none';
    } else {
      const init = $('#modal-avatar-initial');
      const stored2 = getStoredUser();
      if (init) init.textContent = (stored2.display_name || 'LUMA 독자').slice(0, 1);
    }

    $('#profile-modal').classList.add('open');
  }

  function closeModal() {
    const modal = $('#profile-modal');
    if (modal) modal.classList.remove('open');
  }

  /* ─── Save profile ──────────────────────────────────── */
  async function saveProfile() {
    const displayName = ($('#edit-name')?.value || '').trim() || 'LUMA 독자';
    const bio = ($('#edit-bio')?.value || '').trim();
    const tagsRaw = ($('#edit-tags')?.value || '').split(',').map((t) => t.trim()).filter(Boolean);
    const mbti = $('#edit-mbti')?.value || '';

    try {
      const res = await fetch('/api/v2/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...authHeaders() },
        body: JSON.stringify({ display_name: displayName, bio, genre_prefs: tagsRaw, mbti })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.ok === false) throw new Error(data.error || '저장 실패');
    } catch (_) {
      // offline / no-auth — persist locally only
    }

    // Always update local state + localStorage
    const stored = getStoredUser();
    const updated = { ...stored, display_name: displayName, bio, tags: tagsRaw, mbti };
    localStorage.setItem('luma_user', JSON.stringify(updated));
    state.summary = { ...(state.summary || {}), display_name: displayName, bio, tags: tagsRaw, mbti };

    renderSummary();
    closeModal();
    initNav();
    toast('프로필을 저장했습니다. 🌿');
  }

  /* ─── Share ─────────────────────────────────────────── */
  async function shareText(text) {
    if (!text) return;
    if (navigator.share) {
      try { await navigator.share({ text }); return; } catch (_) {}
    }
    try {
      await navigator.clipboard.writeText(text);
      toast('문장을 클립보드에 복사했습니다.');
    } catch (_) {
      toast('공유할 문장을 선택했습니다.');
    }
  }

  /* ─── Utilities ─────────────────────────────────────── */
  function renderTags(sel, tags) {
    const el = $(sel);
    if (!el) return;
    el.innerHTML = tags.map((t) => `<span>#${escHtml(t)}</span>`).join('');
  }
  function setText(sel, text) {
    const el = $(sel);
    if (el) el.textContent = text == null ? '' : String(text);
  }
  function toast(message, isError = false) {
    const node = $('#toast');
    if (!node) return;
    node.textContent = message;
    node.className = 'toast' + (isError ? ' error' : '');
    node.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => node.classList.remove('show'), 2800);
  }
  function formatDate(value) {
    if (!value) return '';
    if (/^\d{4}\./.test(value) || value.includes('월')) return value;
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return d.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' });
  }
  function escHtml(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }
  function escAttr(v) { return escHtml(v).replace(/`/g, '&#096;'); }

  /* ─── Rotating tagline ──────────────────────────────── */
  function initTagline() {
    const phrases = ['생각은 빛이 된다', '읽을수록 더 깊어진다', '나의 독서 우주를 탐험하세요', '나의 독서 우주를 탐험하세요'];
    const el = $('#luma-tagline');
    if (!el) return;
    let i = 0;
    function show(idx) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(-4px)';
      setTimeout(() => {
        el.textContent = phrases[idx];
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      }, 400);
    }
    show(0);
    setInterval(() => { i = (i + 1) % phrases.length; show(i); }, 9000);
  }
})();

(function () {
  'use strict';

  const API_BASE = '/api/v2/profile';
  const DEMO_USER_ID = 'user_demo';

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
    readers: []
  };

  const $ = (selector) => document.querySelector(selector);

  document.addEventListener('DOMContentLoaded', () => {
    paintStars();
    bindActions();
    loadProfile();
  });

  function getStoredUser() {
    try {
      return JSON.parse(localStorage.getItem('luma_user') || '{}');
    } catch (_error) {
      return {};
    }
  }

  function getUserId() {
    const params = new URLSearchParams(window.location.search);
    const stored = getStoredUser();
    return params.get('user_id') || stored.user_id || stored.id || DEMO_USER_ID;
  }

  function authHeaders() {
    const token = localStorage.getItem('luma_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function apiGet(path) {
    const url = `${API_BASE}${path}?user_id=${encodeURIComponent(state.userId)}`;
    const response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        ...authHeaders()
      }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `API error: ${response.status}`);
    }
    return data;
  }

  async function loadProfile() {
    setLoading();

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

    const entries = await Promise.allSettled(
      Object.entries(requests).map(async ([key, promise]) => [key, await promise])
    );

    const failed = [];
    entries.forEach((result) => {
      if (result.status === 'fulfilled') {
        const [key, data] = result.value;
        absorbResponse(key, data);
      } else {
        failed.push(result.reason && result.reason.message ? result.reason.message : '알 수 없는 오류');
      }
    });

    renderAll();
    if (failed.length) {
      toast('일부 데이터를 불러오지 못해 기본 화면으로 표시했습니다.');
    }
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

  function renderAll() {
    renderSummary();
    renderConstellation();
    renderCurrentReading();
    renderSentences();
    renderTimeline();
    renderQuestions();
    renderPersona();
    renderLounges();
    renderReaders();
  }

  function setLoading() {
    [
      '#constellation-view',
      '#current-reading',
      '#persona-view',
      '#sentence-list',
      '#timeline-list',
      '#question-list',
      '#lounge-list',
      '#reader-list'
    ].forEach((selector) => {
      const node = $(selector);
      if (node) node.innerHTML = '<div class="empty-state">데이터를 불러오는 중입니다.</div>';
    });
  }

  function renderSummary() {
    const stored = getStoredUser();
    const profile = {
      display_name: stored.display_name || stored.name || '박소연',
      email: stored.email || state.userId,
      bio: '사람의 마음과 우주, 고독에 대해 읽는 독자',
      tags: ['철학', '우주', '고독', '성장'],
      persona: '사유형 독자',
      ...(state.summary || {})
    };
    const tags = Array.isArray(profile.tags) && profile.tags.length ? profile.tags : ['철학', '우주', '고독', '성장'];

    setText('#hero-name', profile.display_name);
    setText('#hero-bio', profile.bio);
    setText('#profile-name', profile.display_name);
    setText('#profile-email', profile.email || profile.user_id || state.userId);
    setText('#profile-bio', profile.bio);
    setText('#profile-persona', profile.persona || '사유형 독자');
    setText('#nav-user', profile.display_name);
    setText('#luma-tagline', `${profile.persona || '사유형 독자'}의 독서 항해`);

    const initials = (profile.display_name || '나').trim().slice(0, 1);
    setText('#profile-avatar', initials || '나');
    renderTags('#hero-tags', tags);
    renderTags('#profile-tags', tags);

    const stats = profile.stats || {};
    setText('#stat-books', stats.books_read || stats.books_done || stats.total_books || stats.books || 3);
    setText('#stat-memos', stats.memos || stats.saved_sentences || state.sentences.length || 12);
    setText('#stat-connections', stats.connections || state.readers.length || 5);
    setText('#stat-streak', stats.streak_days || stats.reading_streak || stats.streak || 7);
  }

  function renderConstellation() {
    const root = $('#constellation-view');
    if (!root) return;

    const data = state.constellation || {};
    const nodes = Array.isArray(data.nodes) ? data.nodes : [];
    const links = Array.isArray(data.links) ? data.links : [];

    if (!nodes.length || nodes.length <= 1) {
      root.innerHTML = '<div class="empty-state">아직 별자리가 만들어지지 않았습니다.</div>';
      return;
    }

    const width = 720;
    const height = 380;
    const center = { x: width / 2, y: height / 2 };
    const positions = {};
    const orbitNodes = nodes.filter((node) => node.id !== 'user');
    positions.user = center;

    orbitNodes.forEach((node, index) => {
      const angle = (Math.PI * 2 * index) / orbitNodes.length - Math.PI / 2;
      const radius = index % 2 === 0 ? 132 : 172;
      positions[node.id] = {
        x: center.x + Math.cos(angle) * radius,
        y: center.y + Math.sin(angle) * radius
      };
    });

    const lineMarkup = links
      .map((link) => {
        const source = positions[link.source] || center;
        const target = positions[link.target] || center;
        return `<line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" />`;
      })
      .join('');

    const nodeMarkup = nodes
      .map((node) => {
        const point = positions[node.id] || center;
        const color = nodeColor(node.type);
        const label = escapeHtml(node.label || node.id);
        return `
          <g class="constellation-node constellation-node-${escapeHtml(node.type || 'tag')}">
            <circle cx="${point.x}" cy="${point.y}" r="${node.id === 'user' ? 34 : 24}" fill="${color}" />
            <text x="${point.x}" y="${point.y + (node.id === 'user' ? 52 : 42)}">${label}</text>
          </g>`;
      })
      .join('');

    const cards = nodes
      .filter((node) => node.id !== 'user')
      .map((node) => `
        <article class="constellation-chip">
          <span class="dot" style="background:${nodeColor(node.type)}"></span>
          <strong>${escapeHtml(node.label || '')}</strong>
          <small>${typeLabel(node.type)}</small>
        </article>`)
      .join('');

    root.innerHTML = `
      <svg class="constellation-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="생각의 별자리">
        <g class="constellation-lines">${lineMarkup}</g>
        ${nodeMarkup}
      </svg>
      <div class="constellation-cards">${cards}</div>
    `;
  }

  function renderCurrentReading() {
    const root = $('#current-reading');
    if (!root) return;
    const book = state.currentReading || {};
    const tags = book.tags || ['우주', '인간', '질문'];
    const progress = Number(book.progress || book.progress_percent || 62);

    root.innerHTML = `
      <article class="reading-card">
        <div class="book-cover">${book.cover_url ? `<img src="${escapeAttr(book.cover_url)}" alt="">` : '<span>Cosmos</span>'}</div>
        <div class="reading-body">
          <div class="section-kicker">지금 읽는 책</div>
          <h3>${escapeHtml(book.title || '코스모스')}</h3>
          <p class="muted">${escapeHtml(book.author || '칼 세이건')}</p>
          <div class="progress-row">
            <div class="progress-bar"><span style="width:${Math.min(Math.max(progress, 0), 100)}%"></span></div>
            <strong>${progress}% 읽는 중</strong>
          </div>
          <blockquote>${escapeHtml(book.recent_memo || '인간은 우주를 이해하려고 하는 존재다.')}</blockquote>
          <div class="reading-meta">
            <span>최근 감정: ${escapeHtml(book.recent_emotion || '경외')}</span>
            ${tags.map((tag) => `<span>#${escapeHtml(tag)}</span>`).join('')}
          </div>
          <div class="button-row">
            <a class="soft-button" href="/heart">이어 읽기</a>
            <a class="soft-button" href="/deepdive">영상 보기</a>
            <a class="gold-button" href="/socrates">질문 만들기</a>
          </div>
        </div>
      </article>`;
  }

  function renderSentences() {
    const root = $('#sentence-list');
    if (!root) return;
    const sentences = state.sentences.length ? state.sentences : [{
      sentence: '인간은 자유롭도록 선고받았다.',
      book_title: '실존주의와 인간감정',
      saved_at: '2026.05.11',
      tags: ['자유', '책임', '불안']
    }];

    root.innerHTML = sentences.map((item) => `
      <article class="archive-card">
        <blockquote>${escapeHtml(item.sentence || item.quote || '')}</blockquote>
        <p class="muted">${escapeHtml(item.book_title || item.title || '나의 책장')} · ${formatDate(item.saved_at || item.created_at)}</p>
        <div class="tag-row">${(item.tags || []).map((tag) => `<span>#${escapeHtml(tag)}</span>`).join('')}</div>
        <div class="button-row compact">
          <button type="button" class="soft-button" data-toast="다시 읽기 목록에 담았습니다.">다시 읽기</button>
          <a class="soft-button" href="/live">토론 만들기</a>
          <button type="button" class="soft-button" data-share="${escapeAttr(item.sentence || item.quote || '')}">공유</button>
        </div>
      </article>`).join('');
  }

  function renderTimeline() {
    const root = $('#timeline-list');
    if (!root) return;
    const items = state.timeline.length ? state.timeline : [
      { date: '5월', title: '코스모스 읽기 시작', detail: '우주 관련 질문 3개 생성' },
      { date: '5월', title: '소크라테스 대화 2회 완료', detail: '독서모임 1회 참여' }
    ];

    root.innerHTML = items.map((item) => `
      <article class="timeline-item">
        <time>${escapeHtml(formatDate(item.date || item.created_at))}</time>
        <div>
          <strong>${escapeHtml(item.title || item.event || '')}</strong>
          <p>${escapeHtml(item.detail || item.description || '')}</p>
        </div>
      </article>`).join('');
  }

  function renderQuestions() {
    const root = $('#question-list');
    if (!root) return;
    const questions = state.questions.length ? state.questions : [{
      question: '인간은 왜 자신의 위치를 알고 싶어할까?',
      book_title: '코스모스',
      tags: ['우주', '인간', '존재']
    }];

    root.innerHTML = questions.map((item) => `
      <article class="question-card">
        <h3>${escapeHtml(item.question || item.title || '')}</h3>
        <p class="muted">관련 책: ${escapeHtml(item.book_title || item.book || '코스모스')}</p>
        <div class="tag-row">${(item.tags || []).map((tag) => `<span>#${escapeHtml(tag)}</span>`).join('')}</div>
        <div class="button-row compact">
          <a class="soft-button" href="/socrates">다시 생각하기</a>
          <a class="gold-button" href="/lounge">Lounge 공유</a>
        </div>
      </article>`).join('');
  }

  function renderPersona() {
    const root = $('#persona-view');
    if (!root) return;
    const persona = state.persona || {};
    const traits = persona.traits || [
      '질문을 남기며 읽습니다.',
      '철학과 인간 존재에 관심이 많습니다.',
      '감정보다 의미를 오래 붙잡습니다.'
    ];
    const topics = persona.topics || persona.favorite_topics || ['철학', '인간', '우주'];
    const emotions = persona.emotions || ['경외', '고독', '호기심'];

    root.innerHTML = `
      <article class="persona-card">
        <div>
          <div class="section-kicker">독서 성향 분석</div>
          <h3>당신은 ${escapeHtml(persona.persona || '사유형 독자')}입니다.</h3>
          <p>${escapeHtml(persona.summary || '질문을 따라 책을 읽고, 문장 안에서 오래 머무는 독자입니다.')}</p>
        </div>
        <ul>${traits.map((trait) => `<li>${escapeHtml(trait)}</li>`).join('')}</ul>
        <div class="insight-grid">
          <span>자주 읽는 주제 <strong>${topics.map(escapeHtml).join(', ')}</strong></span>
          <span>자주 남기는 감정 <strong>${emotions.map(escapeHtml).join(', ')}</strong></span>
          <span>추천 다음 활동 <strong>${escapeHtml(persona.recommendation || '철학 Lounge에 참여해보세요.')}</strong></span>
        </div>
      </article>`;
  }

  function renderLounges() {
    const root = $('#lounge-list');
    if (!root) return;
    const lounges = state.lounges.length ? state.lounges : [{
      name: '코스모스 읽기 모임',
      book_title: '코스모스',
      members: 12,
      next_schedule: '금요일 오후 9시',
      recent_question: '과학책은 인간을 더 겸손하게 만들까?'
    }];

    root.innerHTML = lounges.map((room) => `
      <article class="lounge-card">
        <h3>${escapeHtml(room.name || room.title || '독서모임')}</h3>
        <p>${escapeHtml(room.book_title || room.book || '함께 읽는 책')}</p>
        <div class="lounge-meta">
          <span>${escapeHtml(String(room.members || room.member_count || 12))}명 참여 중</span>
          <span>다음 모임: ${escapeHtml(room.next_schedule || '금요일 오후 9시')}</span>
        </div>
        <blockquote>${escapeHtml(room.recent_question || '오늘의 질문을 준비하고 있습니다.')}</blockquote>
        <a class="gold-button" href="/live">입장하기</a>
      </article>`).join('');
  }

  function renderReaders() {
    const root = $('#reader-list');
    if (!root) return;
    const readers = state.readers.length ? state.readers : [{
      display_name: '김OO',
      common_tags: ['철학', '우주', '고독'],
      common_books: ['코스모스', '어린왕자'],
      question_style: '존재와 의미를 묻는 독자'
    }];

    root.innerHTML = readers.map((reader) => `
      <article class="reader-card">
        <div class="reader-avatar">${escapeHtml((reader.display_name || '독').slice(0, 1))}</div>
        <div>
          <h3>${escapeHtml(reader.display_name || reader.name || '비슷한 독자')}</h3>
          <p>공통 관심사: ${(reader.common_tags || []).map(escapeHtml).join(', ')}</p>
          <p>공통 책: ${(reader.common_books || []).map(escapeHtml).join(', ')}</p>
          <p class="muted">${escapeHtml(reader.question_style || '질문을 통해 책을 읽습니다.')}</p>
          <div class="button-row compact">
            <a class="soft-button" href="/profile">프로필 보기</a>
            <a class="gold-button" href="/lounge">대화 요청</a>
          </div>
        </div>
      </article>`).join('');
  }

  function bindActions() {
    document.addEventListener('click', async (event) => {
      const actionTarget = event.target.closest('[data-action]');
      const toastTarget = event.target.closest('[data-toast]');
      const shareTarget = event.target.closest('[data-share]');

      if (toastTarget) toast(toastTarget.dataset.toast);
      if (shareTarget) shareText(shareTarget.dataset.share);
      if (!actionTarget) return;

      const action = actionTarget.dataset.action;
      if (action === 'edit-profile') openModal();
      if (action === 'share-thought') window.location.href = '/lounge';
      if (action === 'close-modal') closeModal();
      if (action === 'save-profile') await saveProfile();
    });

    const modal = $('#profile-modal');
    if (modal) {
      modal.addEventListener('click', (event) => {
        if (event.target === modal) closeModal();
      });
    }
  }

  function openModal() {
    const profile = state.summary || {};
    const stored = getStoredUser();
    const tags = profile.tags || ['철학', '우주', '고독', '성장'];
    $('#edit-name').value = profile.display_name || stored.display_name || stored.name || '';
    $('#edit-bio').value = profile.bio || '';
    $('#edit-tags').value = tags.join(', ');
    $('#profile-modal').classList.add('is-open');
  }

  function closeModal() {
    const modal = $('#profile-modal');
    if (modal) modal.classList.remove('is-open');
  }

  async function saveProfile() {
    const displayName = $('#edit-name').value.trim() || '나';
    const bio = $('#edit-bio').value.trim();
    const tags = $('#edit-tags').value
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);

    try {
      const response = await fetch('/api/v2/auth/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...authHeaders()
        },
        body: JSON.stringify({
          display_name: displayName,
          bio,
          genre_prefs: tags
        })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.ok === false) throw new Error(data.error || '저장 실패');

      state.summary = {
        ...(state.summary || {}),
        display_name: displayName,
        bio,
        tags
      };
      const stored = getStoredUser();
      localStorage.setItem('luma_user', JSON.stringify({ ...stored, display_name: displayName, bio, tags }));
      renderSummary();
      closeModal();
      toast('프로필을 저장했습니다.');
    } catch (_error) {
      state.summary = {
        ...(state.summary || {}),
        display_name: displayName,
        bio,
        tags
      };
      renderSummary();
      closeModal();
      toast('로그인 정보가 없어 화면에만 임시 반영했습니다.');
    }
  }

  async function shareText(text) {
    if (!text) return;
    if (navigator.share) {
      try {
        await navigator.share({ text });
        return;
      } catch (_error) {
        // Clipboard fallback below.
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      toast('문장을 클립보드에 복사했습니다.');
    } catch (_error) {
      toast('공유할 문장을 선택했습니다.');
    }
  }

  function renderTags(selector, tags) {
    const root = $(selector);
    if (!root) return;
    root.innerHTML = tags.map((tag) => `<span>#${escapeHtml(tag)}</span>`).join('');
  }

  function setText(selector, text) {
    const node = $(selector);
    if (node) node.textContent = text == null ? '' : String(text);
  }

  function toast(message) {
    const node = $('#toast');
    if (!node) return;
    node.textContent = message;
    node.classList.add('is-visible');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => node.classList.remove('is-visible'), 2600);
  }

  function nodeColor(type) {
    return {
      user: '#d8b768',
      book: '#6cb79b',
      sentence: '#f0d89b',
      question: '#8fb8ff',
      emotion: '#e58aa4',
      tag: '#b3d86d',
      keyword: '#b3d86d'
    }[type] || '#d8b768';
  }

  function typeLabel(type) {
    return {
      book: '책',
      sentence: '문장',
      question: '질문',
      emotion: '감정',
      tag: '키워드',
      keyword: '키워드'
    }[type] || '연결';
  }

  function formatDate(value) {
    if (!value) return '';
    if (/^[0-9]{4}\.[0-9]{2}\.[0-9]{2}/.test(value) || value.includes('월')) return value;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' });
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, '&#096;');
  }

  function paintStars() {
    const canvas = $('#stars-cv');
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext('2d');
    const ratio = window.devicePixelRatio || 1;
    const resize = () => {
      canvas.width = Math.floor(window.innerWidth * ratio);
      canvas.height = Math.floor(Math.max(window.innerHeight, 720) * ratio);
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${Math.max(window.innerHeight, 720)}px`;
      draw();
    };
    const draw = () => {
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = 'rgba(216, 183, 104, 0.55)';
      for (let i = 0; i < 110; i += 1) {
        const x = seeded(i * 17) * width;
        const y = seeded(i * 31) * height;
        const radius = (seeded(i * 47) * 1.8 + 0.5) * ratio;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    };
    window.addEventListener('resize', resize, { passive: true });
    resize();
  }

  function seeded(value) {
    const x = Math.sin(value + 12.9898) * 43758.5453;
    return x - Math.floor(x);
  }
})();

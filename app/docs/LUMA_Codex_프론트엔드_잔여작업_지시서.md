# LUMA — Codex 프론트엔드 잔여 작업 지시서

> **작성일**: 2026-05-09  
> **대상**: GitHub Copilot (Codex)  
> **작업 범위**: 프론트엔드 HTML 파일의 API 연동 완성 및 UX 마무리  
> **기준 코드**: `e:\독서모임앱\LUMA\app\templates\`

---

## 현재 상태 요약 (작업 전 반드시 확인)

| 파일 | 완성도 | 남은 작업 |
|------|--------|----------|
| `auth.html` | ✅ 완료 | JWT 로그인/회원가입/리다이렉트 이미 구현됨 — 손대지 말 것 |
| `heart.html` | ✅ 완료 | `initNav()`, `authHeaders()`, `/api/v2` 연동 완료 |
| `social.html` | ✅ 완료 | `/api/v2/social/*` + `authHeaders()` 연동 완료 |
| `lounge.html` | ✅ 완료 | Discover 정원 페이지 완성 |
| `community.html` | ✅ 완료 | Google Places 3패널 지도 완성 |
| `dashboard.html` | 🔴 미완 | 통계/NAV가 Jinja2 하드코딩 → API 동적 연동 필요 |
| `socrates.html` | 🟡 검증 필요 | API 경로 점검 및 세션 목록 연동 |
| `live.html` | 🟡 검증 필요 | 폴링 연동 및 방 종료 리포트 |
| 전체 NAV | 🔴 미완 | `dashboard.html`에 로그인 사용자 표시 없음 |
| 모바일 | 🟡 부분 | 일부 화면 반응형 미적용 |

---

## 공통 패턴 (모든 작업에 필수 적용)

```javascript
// ── 사용자/토큰 ──────────────────────────────────────────
const UID   = JSON.parse(localStorage.getItem('luma_user') || '{}').user_id || 'user_demo';
const TOKEN = localStorage.getItem('luma_token') || '';

function authHeaders(extra = {}) {
  return TOKEN
    ? { ...extra, 'Content-Type': 'application/json', Authorization: 'Bearer ' + TOKEN }
    : { ...extra, 'Content-Type': 'application/json' };
}

// ── NAV 사용자 표시 ──────────────────────────────────────
function initNav() {
  const user = JSON.parse(localStorage.getItem('luma_user') || '{}');
  const el   = document.getElementById('nav-user');
  if (!el) return;
  if (user.display_name || user.email) {
    el.innerHTML = `
      <span>${user.emoji || '⭐'}</span>
      <span>${user.display_name || user.email}</span>
      <button onclick="logout()" class="nav-logout">로그아웃</button>`;
  } else {
    el.innerHTML = '<a href="/auth/login" class="nav-login-btn">로그인</a>';
  }
}
function logout() {
  localStorage.removeItem('luma_token');
  localStorage.removeItem('luma_user');
  window.location.href = '/landing';
}
document.addEventListener('DOMContentLoaded', initNav);

// ── Jinja2 충돌 방지 ({{ }} 사용 금지) ────────────────────
// ❌ const x = `{{ value }}`
// ✅ function statusLabel(s) { return {done:'완독', reading:'읽는 중'}[s] || s; }
```

---

## TASK 1 — dashboard.html: 통계/NAV API 연동

**파일**: `app/templates/dashboard.html` (현재 ~1413줄)

### 현재 문제

1. 좌측 통계 4개가 Jinja2 서버 변수로 하드코딩됨
   ```html
   <div class="stat-number">{{ stats.total_books }}</div>  <!-- 하드코딩 -->
   <div class="stat-number">{{ stats.total_memos }}</div>
   <div class="stat-number">{{ stats.connections }}</div>
   <div class="stat-number">{{ stats.this_month }}</div>
   ```
2. 헤더의 연속 독서 뱃지도 Jinja2: `{{ stats.reading_streak }}`
3. NAV 우측이 `<div class="avatar">나</div>` 하드코딩 — 로그인 사용자 표시 없음
4. `initDashboard()` 함수 없음 — 페이지 로드 시 API 호출 없음

### 작업 요청

#### 1-A. stat-number 요소에 id 추가

아래 4개 stat-card의 `.stat-number` div에 id를 추가한다.

```html
<!-- 변경 전 -->
<div class="stat-number">{{ stats.total_books }}</div>
<div class="stat-number">{{ stats.total_memos }}</div>
<div class="stat-number">{{ stats.connections }}</div>
<div class="stat-number">{{ stats.this_month }}</div>

<!-- 변경 후 -->
<div class="stat-number" id="stat-total-books">{{ stats.total_books }}</div>
<div class="stat-number" id="stat-total-memos">{{ stats.total_memos }}</div>
<div class="stat-number" id="stat-connections">{{ stats.connections }}</div>
<div class="stat-number" id="stat-this-month">{{ stats.this_month }}</div>
```

연속 독서 뱃지:
```html
<!-- 변경 전 -->
<div class="streak-badge">🔥 {{ stats.reading_streak }}일 연속 독서 중</div>

<!-- 변경 후 -->
<div class="streak-badge" id="streak-badge">🔥 {{ stats.reading_streak }}일 연속 독서 중</div>
```

#### 1-B. NAV 우측 id 추가

헤더의 `<div class="avatar">나</div>` 부분을 찾아 아래로 교체한다.

```html
<!-- 변경 후 -->
<div class="nav-user" id="nav-user">
  <span class="avatar">나</span>
</div>
```

NAV CSS 추가 (`<style>` 끝 직전):
```css
.nav-user { display:flex; align-items:center; gap:8px; font-size:.72rem; color:var(--sub); }
.nav-logout {
  background:rgba(248,113,113,.08); border:1px solid rgba(248,113,113,.22);
  color:#F87171; padding:5px 12px; border-radius:8px; font-size:.72rem; cursor:pointer;
}
.nav-login-btn {
  background:rgba(193,127,59,.12); border:1px solid rgba(193,127,59,.25);
  color:var(--amber); padding:6px 14px; border-radius:18px; font-size:.75rem;
  text-decoration:none;
}
```

#### 1-C. initDashboard() 함수 추가

기존 `<script>` 맨 아래, `initMemoForm()` 호출 직후에 추가한다.

```javascript
// ── 대시보드 초기화 ─────────────────────────────────────────────────────
async function initDashboard() {
  try {
    const [shelfRes, emoRes] = await Promise.all([
      fetch(`/api/v2/shelf?user_id=${encodeURIComponent(UID)}`, { headers: authHeaders() })
        .then(r => r.json()).catch(() => ({})),
      fetch(`/api/v2/emotions?user_id=${encodeURIComponent(UID)}`, { headers: authHeaders() })
        .then(r => r.json()).catch(() => ({})),
    ]);

    // 통계 업데이트
    const stats = shelfRes.stats || {};
    const setEl = (id, val) => { const el = document.getElementById(id); if (el && val !== undefined) el.textContent = val; };
    setEl('stat-total-books', stats.total   ?? stats.done ?? '—');
    setEl('stat-total-memos', stats.memos   ?? '—');
    setEl('stat-connections', stats.connections ?? '—');
    setEl('stat-this-month',  stats.this_month  ?? stats.reading ?? '—');

    // 연속 독서
    const streak = shelfRes.stats?.reading_streak ?? emoRes.stats?.reading_streak;
    if (streak !== undefined) {
      const badge = document.getElementById('streak-badge');
      if (badge) badge.textContent = `🔥 ${streak}일 연속 독서 중`;
    }

    // 우측 현재 읽는 책 업데이트
    const reading = (shelfRes.books || []).filter(b => b.status === 'reading');
    renderCurrentBook(reading[0] || null);

  } catch (e) {
    console.warn('[dashboard] initDashboard 실패:', e);
  }
}

function renderCurrentBook(book) {
  const el = document.getElementById('current-book-area');
  if (!el) return;
  if (!book) {
    el.innerHTML = '<div style="color:var(--sub);font-size:.8rem;text-align:center;padding:16px 0;">읽고 있는 책이 없습니다</div>';
    return;
  }
  el.innerHTML = `
    <div style="display:flex;gap:14px;align-items:flex-start;">
      <div style="font-size:2rem;flex-shrink:0;">${book.cover_emoji || '📖'}</div>
      <div>
        <div style="font-weight:600;font-size:.9rem;">${escHtml(book.title)}</div>
        <div style="font-size:.75rem;color:var(--sub);margin-top:2px;">${escHtml(book.author || '')}</div>
        <div style="margin-top:8px;height:4px;background:var(--border);border-radius:4px;overflow:hidden;">
          <div style="height:100%;background:var(--amber);width:${book.progress || 0}%;transition:.4s;"></div>
        </div>
        <div style="font-size:.68rem;color:var(--sub);margin-top:4px;">${book.progress || 0}% 읽음</div>
      </div>
    </div>`;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── initNav / logout ────────────────────────────────────────────────────
function initNav() {
  const user = JSON.parse(localStorage.getItem('luma_user') || '{}');
  const el   = document.getElementById('nav-user');
  if (!el) return;
  if (user.display_name || user.email) {
    el.innerHTML = `
      <span>${user.emoji || '⭐'}</span>
      <span style="color:var(--text)">${user.display_name || user.email}</span>
      <button onclick="logout()" class="nav-logout">로그아웃</button>`;
  } else {
    el.innerHTML = '<a href="/auth/login" class="nav-login-btn">로그인</a>';
  }
}
function logout() {
  localStorage.removeItem('luma_token');
  localStorage.removeItem('luma_user');
  window.location.href = '/landing';
}

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initDashboard();
});
```

> **주의**: `dashboard.html`의 별자리 데이터는 현재 Jinja2 서버 렌더링(`{{ constellation|safe }}`)을 그대로 유지한다. 별자리 D3 코드는 건드리지 않는다.

---

## TASK 2 — main.py: 대시보드 통계 API fallback 추가

**파일**: `app/routes/main.py`

현재 `dashboard()` 함수가 하드코딩된 `stats` dict를 Jinja2로 넘긴다. `/api/v2/shelf?user_id=user_demo`에서 실제 통계를 가져오도록 수정한다.

```python
# app/routes/main.py  — dashboard() 함수 수정

@main_bp.route('/')
def index():
    try:
        from app.services.reading_service import get_constellation
        constellation_data = get_constellation("user_demo")
        for node in constellation_data.get("nodes", []):
            node["title"] = node.get("title") or node.get("label", "")
            node["memos"] = node.get("memos", 0)
        for link in constellation_data.get("links", []):
            link["insight"] = link.get("insight") or link.get("theme", "")
    except Exception:
        constellation_data = generate_mock_constellation()

    # 실제 통계 시도 → 실패 시 안전한 기본값
    try:
        from app.services.shelf_service import get_shelf
        shelf = get_shelf("user_demo")
        shelf_stats = shelf.get("stats", {})
        stats = {
            "total_books":     shelf_stats.get("total", 23),
            "total_memos":     shelf_stats.get("memos", 147),
            "reading_streak":  shelf_stats.get("reading_streak", 12),
            "total_pages":     shelf_stats.get("total_pages", 6840),
            "this_month":      shelf_stats.get("this_month", 3),
            "connections":     shelf_stats.get("connections", 18),
        }
    except Exception:
        stats = {
            "total_books": 23, "total_memos": 147,
            "reading_streak": 12, "total_pages": 6840,
            "this_month": 3, "connections": 18,
        }

    recent_insights = [
        {"book1": "사피엔스", "book2": "총균쇠", "text": "문명의 흥망성쇠는 지리적 조건과 집단 허구의 결합으로 설명된다."},
        {"book1": "코스모스", "book2": "멋진 신세계", "text": "과학의 발전은 자유를 열어주기도, 새로운 통제의 도구가 되기도 한다."},
        {"book1": "데미안", "book2": "어린왕자", "text": "진정한 성장은 타인의 시선이 아닌 내면의 목소리를 따를 때 시작된다."},
    ]
    return render_template('dashboard.html',
                           constellation=json.dumps(constellation_data, ensure_ascii=False),
                           stats=stats,
                           insights=recent_insights)
```

---

## TASK 3 — socrates.html: API 경로 및 세션 목록 점검

**파일**: `app/templates/socrates.html`

### 확인 및 수정 사항

1. **API 경로 점검** — 아래 경로가 실제 `mysql_api.py`에 구현된 경로와 일치하는지 확인한다.

   | 기능 | 현재 경로 | 확인 |
   |------|----------|------|
   | 세션 시작 | `POST /api/v2/socrates/start` | □ |
   | 답변 전송 | `POST /api/v2/socrates/answer` | □ |
   | 강제 연결 | `POST /api/v2/socrates/connect` | □ |
   | 사전 조회 | `GET /api/v2/socrates/dictionary` | □ |
   | 사전 추가 | `POST /api/v2/socrates/dictionary` | □ |
   | 액션플랜 생성 | `POST /api/v2/socrates/action` | □ |
   | 액션플랜 체크인 | `POST /api/v2/socrates/action/{id}/checkin` | □ |

2. **세션 목록 로딩** — 페이지 로드 시 이전 세션을 불러오는 함수를 추가한다.

```javascript
// 세션 목록 패널이 있으면 로드
async function loadSessionList() {
  const container = document.getElementById('session-list');
  if (!container) return;
  try {
    const d = await fetch(
      `/api/v2/socrates/sessions?user_id=${encodeURIComponent(UID)}`,
      { headers: authHeaders() }
    ).then(r => r.json());
    if (!d.ok || !d.sessions?.length) {
      container.innerHTML = '<div style="color:var(--sub);font-size:.8rem;padding:12px 0;">이전 세션이 없습니다</div>';
      return;
    }
    container.innerHTML = d.sessions.map(s => `
      <div class="session-item" onclick="resumeSession('${s.session_id}')">
        <div style="font-size:.82rem;font-weight:600;">${escHtml(s.book_title || '책 미지정')}</div>
        <div style="font-size:.72rem;color:var(--sub);margin-top:3px;">${escHtml(s.passage_preview || '')}${s.completed ? ' ✅' : ''}</div>
      </div>`).join('');
  } catch (e) {}
}

async function resumeSession(sessionId) {
  try {
    const d = await fetch(
      `/api/v2/socrates/sessions/${encodeURIComponent(sessionId)}/resume`,
      { headers: authHeaders() }
    ).then(r => r.json());
    if (!d.ok) { showToast(d.error || '세션을 불러올 수 없습니다.'); return; }
    // 대화 패널 열기
    curSession = { session_id: sessionId };
    showDialogue();
    if (d.final_insight) {
      addInsightCard(d.final_insight);
    } else if (d.question) {
      addAiMsg(d.question, d.stage + 1, 5);
    }
  } catch (e) { showToast('세션 재개 실패'); }
}
```

3. **authHeaders 미적용 API 호출이 있으면** 모두 `authHeaders()` 포함으로 수정한다.

4. **`escHtml` 함수** — 없으면 추가한다.
   ```javascript
   function escHtml(s) {
     return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
   }
   ```

---

## TASK 4 — live.html: 폴링 및 방 종료 리포트

**파일**: `app/templates/live.html`

### 확인 및 수정 사항

1. **loadRooms()** — 현재 단일 fetch인지 확인. 아래 패턴으로 교체한다.

```javascript
async function loadRooms() {
  try {
    const [live, waiting] = await Promise.all([
      fetch('/api/v2/live/rooms?status=live', { headers: authHeaders() }).then(r => r.json()).catch(() => ({ rooms: [] })),
      fetch('/api/v2/live/rooms?status=waiting', { headers: authHeaders() }).then(r => r.json()).catch(() => ({ rooms: [] })),
    ]);
    const rooms = [...(live.rooms || []), ...(waiting.rooms || [])];
    renderRoomList(rooms);
  } catch (e) { renderRoomList([]); }
}
```

2. **폴링 시작/종료** — `enterRoom()` 이후 폴링이 없으면 추가한다.

```javascript
let pollInterval = null;
let lastMsgId = 0;

function startPolling(roomId) {
  stopPolling();
  lastMsgId = 0;
  pollInterval = setInterval(async () => {
    try {
      const d = await fetch(
        `/api/v2/live/rooms/${roomId}/poll?since=${lastMsgId}`,
        { headers: authHeaders() }
      ).then(r => r.json());
      if (!d.ok) return;
      (d.messages || []).forEach(m => {
        if (m.peer_id !== myPeerId) addMsg(m);
      });
      if (d.messages?.length) lastMsgId = d.messages.at(-1).id || d.messages.at(-1).msg_id || lastMsgId;
      if (typeof updateMemberCount === 'function') updateMemberCount(d.member_count);
      if (typeof addKeywords === 'function') addKeywords(d.keywords || []);
    } catch (e) {}
  }, 3000);
}

function stopPolling() {
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
}
```

`enterRoom()` 함수 끝에 `startPolling(roomId)` 호출을 추가한다.

3. **endRoom()** — 방 종료 시 폴링 중단 + 리포트 표시를 확인한다.

```javascript
async function endRoom() {
  stopPolling();
  try {
    const d = await fetch(`/api/v2/live/rooms/${currentRoomId}/end`, {
      method: 'POST', headers: authHeaders()
    }).then(r => r.json());
    if (d.ok && d.report && typeof renderReport === 'function') {
      renderReport(d.report);
      switchTab('report');
    }
  } catch (e) {}
}
```

4. **authHeaders 미적용 호출** 이 있으면 모두 수정한다.

---

## TASK 5 — 모바일 반응형: heart / socrates / live / social

**대상 파일**: `heart.html`, `socrates.html`, `live.html`, `social.html`

각 파일의 `</style>` 직전에 아래 미디어 쿼리를 추가한다. 파일마다 기존 CSS 변수와 class명이 다를 수 있으니, 실제 HTML에서 class명을 확인한 뒤 적용한다.

```css
/* ── 태블릿 (1024px 이하) ───────────────────────────── */
@media (max-width: 1024px) {
  /* heart.html */
  .app-body { grid-template-columns: 200px 1fr !important; }
  .panel-right { display: none; }
  /* live.html */
  .right, .right-panel { display: none; }
  /* socrates.html */
  .dict-panel, .session-list-panel { display: none; }
}

/* ── 모바일 (768px 이하) ────────────────────────────── */
@media (max-width: 768px) {
  /* 3열 → 1열 */
  .app-body, .app, .main, .room-layout {
    grid-template-columns: 1fr !important;
    grid-template-rows: auto !important;
  }
  /* 사이드바 숨김 */
  .sidebar, .left-panel, .sidebar-left, .nav-sidebar { display: none !important; }
  /* NAV 압축 */
  .nav, header { padding: 0 14px !important; height: 52px !important; }
  .nav a, .npill { padding: 4px 8px !important; font-size: .65rem !important; }
  /* 카드/패널 패딩 */
  .panel-scroll, .content, .feed-col { padding: 12px 14px !important; }
  /* 웹캠 그리드 */
  .webcam-grid { grid-template-columns: repeat(2, 1fr) !important; }
  /* 카드 폭 */
  .book-card, .feed-card { width: 100% !important; }
  body { padding-bottom: 60px; }
}

/* ── 모바일 하단 네비게이션 ─────────────────────────── */
@media (max-width: 768px) {
  .bottom-nav {
    display: flex !important;
    position: fixed; bottom: 0; left: 0; right: 0; height: 56px;
    background: rgba(11,22,18,.97); border-top: 1px solid rgba(255,255,255,.07);
    z-index: 200;
  }
  .bn-item {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    font-size: .58rem; color: var(--sub, #8FA89A);
    text-decoration: none; gap: 3px;
  }
  .bn-item.active { color: var(--amber, #C17F3B); }
  .bn-icon { font-size: 1.1rem; }
}
```

각 파일의 `</body>` 직전에 하단 네비게이션 HTML을 추가한다 (기본으로 `display:none`, 미디어 쿼리에서만 활성화).

```html
<nav class="bottom-nav" style="display:none;">
  <a href="/"         class="bn-item"><span class="bn-icon">✦</span>별자리</a>
  <a href="/heart"    class="bn-item"><span class="bn-icon">📖</span>서재</a>
  <a href="/discover" class="bn-item"><span class="bn-icon">🌱</span>발견</a>
  <a href="/live"     class="bn-item"><span class="bn-icon">🎥</span>라이브</a>
  <a href="/socrates" class="bn-item"><span class="bn-icon">🧠</span>AI</a>
</nav>
```

현재 페이지에 해당하는 `<a>` 태그에 `active` class를 추가한다.  
예: `heart.html`이면 `/heart` 링크에 `class="bn-item active"`.

---

## TASK 6 — profile.html / landing.html / ocr.html: NAV 로그인 상태

**대상 파일**: `profile.html`, `landing.html`, `ocr.html`

각 파일의 NAV 우측 영역을 찾아 다음으로 교체한다.

```html
<!-- NAV 우측 -->
<div class="nav-user" id="nav-user">
  <span class="avatar">나</span>
</div>
```

해당 파일 `<script>` 맨 아래에 추가:

```javascript
function initNav() {
  const user = JSON.parse(localStorage.getItem('luma_user') || '{}');
  const el   = document.getElementById('nav-user');
  if (!el) return;
  if (user.display_name || user.email) {
    el.innerHTML = `
      <span>${user.emoji || '⭐'}</span>
      <span>${user.display_name || user.email}</span>
      <button onclick="logout()" class="nav-logout">로그아웃</button>`;
  } else {
    el.innerHTML = '<a href="/auth/login" class="nav-login-btn">로그인</a>';
  }
}
function logout() {
  localStorage.removeItem('luma_token');
  localStorage.removeItem('luma_user');
  window.location.href = '/landing';
}
document.addEventListener('DOMContentLoaded', initNav);
```

CSS (기존 변수 활용, `</style>` 직전 추가):
```css
.nav-user { display:flex; align-items:center; gap:8px; font-size:.72rem; }
.nav-logout {
  background:rgba(248,113,113,.08); border:1px solid rgba(248,113,113,.22);
  color:#F87171; padding:5px 12px; border-radius:8px; font-size:.72rem; cursor:pointer;
}
.nav-login-btn {
  background:rgba(193,127,59,.12); border:1px solid rgba(193,127,59,.25);
  color:var(--amber); padding:6px 14px; border-radius:18px; font-size:.75rem;
  text-decoration:none;
}
```

---

## 완료 기준 체크리스트

- [ ] `dashboard.html` 로드 시 통계 숫자가 API에서 동적으로 채워진다
- [ ] `dashboard.html` NAV 우측에 로그인 사용자 이름/이모지가 표시된다
- [ ] `dashboard.html` 로그아웃 버튼 클릭 시 `/landing`으로 이동한다
- [ ] `main.py` dashboard()가 실제 shelf 통계를 먼저 시도한다
- [ ] `socrates.html` 세션 목록 로딩이 동작한다
- [ ] `socrates.html` 모든 API 호출에 `authHeaders()` 포함 확인
- [ ] `live.html` 방 입장 후 3초 폴링이 시작된다
- [ ] `live.html` 방 종료 시 폴링이 중단되고 리포트가 표시된다
- [ ] `heart.html`, `socrates.html`, `live.html`, `social.html` 768px 이하에서 하단 NAV 표시
- [ ] `profile.html`, `landing.html`, `ocr.html` NAV 로그인 상태 표시

---

## 작업 금지 사항

- `auth.html` — 이미 완성됨, 수정 금지
- `heart.html` — `initNav()` 이미 구현됨, 중복 추가 금지
- `social.html` — `/api/v2/social/*` 이미 연동됨, 경로 변경 금지
- `lounge.html` / `community.html` — 이미 완성됨, 수정 금지
- `dashboard.html` D3 별자리 코드 — 건드리지 않는다
- Jinja2 `{{ }}` 문법을 JS 문자열 내부에서 사용 금지
- 기존 CSS 변수 (`--amber`, `--forest`, `--bg` 등) 변경 금지

---

*LUMA — 읽는 행위를 넘어, 생각의 우주를 연결하다 🌿*

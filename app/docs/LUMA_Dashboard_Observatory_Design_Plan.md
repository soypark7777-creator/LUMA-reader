# LUMA Dashboard — "우주 관측소 홈" 프론트엔드 설계 계획서

> **작성 기준**: 현재 `dashboard.html` 코드 분석 완료  
> **보유 에셋**: `galaxy_21.png`, `galaxy_20.png`, `thoght_orb_1~22.png`, `Luma_logo_1.png`  
> **작성자 관점**: Senior Frontend Developer  
> **구현 목표**: 단순 대시보드 → LUMA 세계관의 "관측소 홈"으로 격상

---

## 1. 세계관 매핑 정의

| 실제 개념 | 우주 메타포 | 시각 표현 |
|----------|------------|---------|
| 내 책 | 행성 (Planet) | `thoght_orb_*.png` PNG 회전 |
| 메모 | 별빛 (Starlight) | 메모 수 → 행성 글로우 강도 |
| 책 연결 | 별자리 (Constellation) | D3 링크 선 → 빛나는 궤도선 |
| 최근 읽은 책 | 밝은 행성 | brightness/opacity 가중 |
| 많이 연결된 책 | 궤도 링 있는 행성 | `ring` 요소 두께 차등 |
| Discover | 탐사 망원경 | 왼쪽 패널 아이콘 + 호버 이펙트 |
| 새 메모 추가 | 별 심기 | FAB 버튼 → "별 심기" 텍스트 |

---

## 2. 디자인 시스템

### 2.1 색상 팔레트 (기존 유지 + 확장)

```css
:root {
  /* Core (기존) */
  --bg:     #0B1612;      /* 더 깊은 우주 흑 — 현재 #0D1B14에서 조정 */
  --panel:  #0F1E18;
  --text:   #E8DCC8;
  --sub:    #8FA89A;
  --amber:  #C17F3B;
  --line:   rgba(255,255,255,.07);
  --card:   rgba(255,255,255,.04);

  /* New — 관측소 전용 */
  --star:   #F4CD89;      /* 별빛 골드 */
  --nebula: rgba(193,127,59,.14);  /* 성운 glare */
  --orbit:  rgba(244,205,137,.55); /* 궤도 링 */
  --glow-sm: 0 0 12px rgba(244,205,137,.22);
  --glow-md: 0 0 28px rgba(244,205,137,.35);
  --glow-lg: 0 0 52px rgba(244,205,137,.42);
}
```

### 2.2 타이포그래피

| 용도 | Font | Weight | Size |
|------|------|--------|------|
| 헤더 로고 대용 문구 | DM Serif Display | 400 | — (이미지로 대체) |
| 패널 섹션 레이블 | Pretendard | 600 | 0.67rem |
| 행성 타이틀 | Noto Serif KR | 400 | 11–13px |
| 모달 제목 | Noto Serif KR | 600 | 1.3rem |
| 메모 본문 | Noto Serif KR | 300 | 0.88rem |
| 통계 숫자 | DM Serif Display | 400 | 1.55rem |

### 2.3 공간 & 레이아웃 그리드

```
┌──────────────────────────────────────────────────────────────────┐
│  HEADER  64px  [Logo 이미지] [나의 독서 우주] [streak][user]      │
├─────────────────┬────────────────────────────┬───────────────────┤
│  LEFT PANEL     │   CENTER CANVAS            │  RIGHT PANEL      │
│  220px          │   flex: 1                  │  280px            │
│                 │   (galaxy 배경)            │                   │
│  탐사 장치 메뉴  │   D3 constellation         │  관측 리포트       │
│                 │   (행성 노드 고도화)         │                   │
└─────────────────┴────────────────────────────┴───────────────────┘
```

- 현재 260px → **220px** (좌측 압축, 중앙 확보)
- 현재 300px → **280px** (우측 약간 압축)
- 헤더 60px → **64px**

---

## 3. 헤더 설계

### 3.1 현재 문제

- "LUMA" 텍스트 로고 (Noto Serif KR, amber색)
- "생각의 별자리를 연결하다" 중앙 서브텍스트
- 오른쪽: 연속 독서일 뱃지 + 하드코딩 "나" 아바타

### 3.2 목표 설계

```
LEFT:   <img src="/asset/images/Luma_logo_1.png" height="36" alt="LUMA">
        "나의 독서 우주"  (font-size: .72rem, color: var(--sub), letter-spacing: .1em)

CENTER: (비움 — 로고가 왼쪽을 장악)

RIGHT:  [🔥 12일] [연속 독서]   [아바타+이름] [설정 아이콘]
```

### 3.3 CSS 명세

```css
header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(11,22,18,.97);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(16px);
  z-index: 10;
}

.header-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}
.header-logo img {
  height: 36px;
  filter: drop-shadow(0 0 8px rgba(193,127,59,.4));
}
.header-tagline {
  font-size: .72rem;
  color: var(--sub);
  letter-spacing: .12em;
  text-transform: uppercase;
}

.streak-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(193,127,59,.1);
  border: 1px solid rgba(193,127,59,.22);
  border-radius: 999px;
  padding: 6px 13px;
  font-size: .76rem;
  color: var(--amber);
}
```

---

## 4. 좌측 패널 — 탐사 장치

### 4.1 현재 문제

- 평범한 텍스트 버튼 나열
- "페이지 목록"처럼 보임
- 아이콘이 이모지로 단순 처리됨

### 4.2 목표 설계: 탐사 장치 스타일

각 메뉴 버튼을 "탐사 도구 슬롯"처럼 디자인.

```
┌──────────────────────────────┐
│  ━━━ 탐사 장치  ━━━━━━━━━━━  │  (section label)
│                              │
│  ✦  별자리 지도    ← active  │  ← 현재 관측 중
│     내 책들의 우주 지도       │  ← 서브텍스트
│                              │
│  ♡  마음 행성계              │
│     감정별 책과 메모 아카이브  │
│                              │
│  ☘  탐사 성운               │  ← Lounge = Discover
│     새로운 책을 발견하는 망원경 │
│                              │
│  ◉  궤도 정거장              │  ← Live
│  ?  지성의 위성              │  ← Socrates
│  ⌁  심층 관측소              │  ← Deepdive
│  ◎  은하 공동체              │  ← Community
│  #  독자 피드                │  ← Social
│  ▣  광학 스캐너              │  ← OCR
│  ◌  나의 조종석              │  ← Profile
│                              │
│  ✎  메모 전체                │
└──────────────────────────────┘
```

### 4.3 CSS 명세

```css
.nav-item {
  border: 0;
  background: transparent;
  color: var(--sub);
  font-family: inherit;
  text-align: left;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  width: 100%;
  transition: .18s;
  line-height: 1;
}
.nav-item:hover {
  background: rgba(193,127,59,.08);
  color: var(--amber);
}
.nav-item.active {
  background: rgba(193,127,59,.13);
  color: var(--amber);
  box-shadow: inset 2px 0 0 var(--amber);
}
.nav-icon {
  font-size: 1rem;
  margin-right: 9px;
  display: inline-block;
  width: 18px;
  text-align: center;
}
.nav-label { font-size: .82rem; font-weight: 600; }
.nav-sub {
  display: block;
  font-size: .64rem;
  color: var(--sub);
  margin-top: 2px;
  padding-left: 27px;
  line-height: 1.3;
  opacity: .8;
}

/* 호버 시 서브텍스트 노출 */
.nav-item:hover .nav-sub,
.nav-item.active .nav-sub {
  opacity: 1;
  color: rgba(143,168,154,.85);
}
```

### 4.4 좌측 하단 통계

현재 4개 stat-card 유지하되 디자인 고도화.

```css
.stat-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 11px 12px;
  text-align: center;
  transition: .2s;
}
.stat-card:hover {
  border-color: rgba(193,127,59,.25);
  background: rgba(193,127,59,.05);
}
.stat-num {
  font-family: 'DM Serif Display', serif;
  font-size: 1.5rem;
  color: var(--star);
  line-height: 1;
}
.stat-label { font-size: .62rem; color: var(--sub); margin-top: 3px; }
```

---

## 5. 중앙 우주 캔버스 — 고도화 설계

### 5.1 현재 구현 분석

- D3 force-directed simulation ✅
- `thoght_orb_*.png` 행성 이미지 회전 ✅
- 별 캔버스 (canvas) 애니메이션 ✅
- 링크 선 `stroke-dasharray` ✅
- galaxy_21.png 배경 ✅
- 툴팁 호버 ✅
- 드래그 ✅

### 5.2 고도화 포인트

#### A. 행성 노드 3단계 크기 체계

```javascript
// 메모 수 기반 크기 (현재: 고정 d.size)
function planetRadius(d) {
  const base = 22;
  const memoBonus = Math.min(d.memos * 2.5, 22); // 최대 +22px
  return base + memoBonus;
}

// 최근 읽은 책일수록 밝음 (recency 0~1 값)
function planetBrightness(d) {
  // d.last_read_days: 며칠 전에 읽었는지
  const days = d.last_read_days || 60;
  return Math.max(0.2, 1 - (days / 60));
}
```

#### B. 궤도 링 (연결 많은 책)

```javascript
// 연결 수 3개 이상이면 궤도 링 추가
if (d.connections >= 3) {
  ne.append('ellipse')
    .attr('class', 'orbit-ring')
    .attr('rx', d => d.size * 1.7)
    .attr('ry', d => d.size * 0.45)
    .attr('fill', 'none')
    .attr('stroke', 'rgba(244,205,137,.35)')
    .attr('stroke-width', 1.2)
    .attr('stroke-dasharray', '3,5');
  // CSS: animation: orbitSpin 8s linear infinite
}
```

```css
@keyframes orbitSpin {
  to { transform: rotateX(60deg) rotate(360deg); }
}
```

#### C. 글로우 강도 — 메모 수 연동

```javascript
ne.append('circle')
  .attr('class', 'planet-glow')
  .attr('r', d => d.size + 14)
  .attr('fill', d => d.color || '#C17F3B')
  .attr('opacity', d => 0.12 + Math.min(d.memos * 0.03, 0.25));
  // 메모 0개: opacity 0.12 / 메모 10개: opacity 0.42
```

#### D. 별자리 연결선 고도화

```javascript
// 현재: 단순 dashed line
// 변경: 강도에 따른 빛나는 선

le.attr('stroke', d => {
  const alpha = 0.25 + d.strength * 0.5;
  return `rgba(244,205,137,${alpha})`;
})
.attr('stroke-width', d => 0.8 + d.strength * 2.2)
.attr('filter', 'url(#glow-filter)'); // SVG filter 추가
```

SVG 필터 (링크 글로우):
```html
<defs>
  <filter id="glow-filter" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="2.5" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
</defs>
```

#### E. 배경 레이어 강화

```css
.center {
  position: relative;
  overflow: hidden;
  background:
    /* 중심 성운 빛 */
    radial-gradient(ellipse 55% 45% at 50% 50%,
      rgba(193,127,59,.09), transparent),
    /* 상단 성운 */
    radial-gradient(ellipse 40% 30% at 25% 18%,
      rgba(79,107,74,.08), transparent),
    /* 어두운 우주 */
    linear-gradient(180deg, rgba(5,11,8,.3), rgba(7,15,11,.75)),
    /* 은하 배경 */
    url('/asset/images/dashboard/background/galaxy_21.png') center / cover no-repeat;
}
```

---

## 6. 행성 클릭 모달 — 고도화 설계

### 6.1 현재 문제

- 단순 2단 그리드 (표지 | 정보)
- "메모 없음" 메시지만 표시
- 연결된 다른 책이 보이지 않음

### 6.2 목표 레이아웃

```
┌──────────────────────────────────────────────────────┐
│  [책의 별 기록]                               [×]     │
├──────────────────────────────────────────────────────┤
│                                                       │
│  [행성 이미지 180px]  제목 (DM Serif Display 1.6rem)  │
│     회전 애니메이션    저자 · 장르                     │
│                        ─────────────────────────      │
│                        상태 뱃지 · 메모 수 · 연결 수   │
│                        읽기 진행률 바                  │
│                        [이 책에 메모 추가] 버튼        │
│                                                       │
├─ TABS ───────────────────────────────────────────────┤
│  [내 메모]  [연결된 책]  [책 정보]                     │
├──────────────────────────────────────────────────────┤
│  탭 내용 영역 (스크롤 가능)                            │
└──────────────────────────────────────────────────────┘
```

### 6.3 탭별 내용

**[내 메모] 탭**
- 메모 카드 리스트 (기분 아이콘, 페이지, 태그, 내용)
- 없으면: "아직 이 행성에 별빛이 없습니다. 첫 메모를 남겨보세요."

**[연결된 책] 탭**
- CONSTELLATION_DATA.links에서 해당 책 id 연관 링크 추출
- 미니 행성 카드 (planet img + 제목 + 연결 주제)
- 없으면: "아직 연결된 별이 없습니다."

**[책 정보] 탭**
- ISBN, 출판사, 출간일
- 외부 링크 (있는 경우)

### 6.4 CSS 핵심

```css
.modal-tabs {
  display: flex;
  border-bottom: 1px solid var(--line);
  padding: 0 24px;
  gap: 0;
}
.mtab {
  padding: 11px 16px;
  font-size: .78rem;
  color: var(--sub);
  cursor: pointer;
  border: none;
  background: transparent;
  border-bottom: 2px solid transparent;
  transition: .15s;
}
.mtab.active {
  color: var(--amber);
  border-bottom-color: var(--amber);
}
.modal-tab-content {
  padding: 20px 24px;
  max-height: 340px;
  overflow-y: auto;
}
.memo-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 10px;
}
.memo-mood { font-size: .66rem; color: var(--sub); margin-bottom: 6px; }
.memo-body { font-family: 'Noto Serif KR', serif; font-size: .86rem; line-height: 1.7; }
.memo-tags { margin-top: 8px; display: flex; gap: 5px; flex-wrap: wrap; }
.memo-tag {
  font-size: .64rem; padding: 2px 8px;
  border: 1px solid rgba(193,127,59,.2);
  border-radius: 999px; color: var(--amber);
}

/* 연결된 책 카드 */
.link-book-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  margin-bottom: 10px;
}
.link-planet-img {
  width: 52px; height: 52px;
  border-radius: 50%;
  object-fit: contain;
  animation: spin 20s linear infinite;
  filter: drop-shadow(0 0 8px rgba(244,205,137,.25));
}
.link-theme { font-size: .72rem; color: var(--sub); font-style: italic; margin-top: 3px; }
```

---

## 7. 우측 패널 — 오늘의 관측 리포트

### 7.1 현재 문제

- "AI 인사이트 엔진" 정적 텍스트
- Jinja2 하드코딩 insights 루프
- "강제 연결 반짝이기" 버튼 노출 (디버그 느낌)
- 독서 모임 하드코딩

### 7.2 목표 구조

```
┌──────────────────────────────┐
│  ━━ 오늘의 관측 리포트 ━━━━  │
│                              │
│  [오늘 읽을 만한 책]          │  ← /api/v2/discover/today hero
│  책 표지 + 제목 + 짧은 이유   │
│  [탐사 성운으로 →] CTA       │
│                              │
│  [최근 남긴 메모]             │  ← /api/memos/list 최근 2개
│  책 제목 · 메모 미리보기       │
│                              │
│  [새로 생긴 연결]             │  ← constellation links 중 recent
│  "A → B: 공통 주제..."       │
│  [별자리에서 확인] CTA        │
│                              │
│  [AI 발견한 생각의 연결]      │  ← Gemini insight
│  아이콘 + 한 줄 인사이트       │
│                              │
└──────────────────────────────┘
```

### 7.3 API 연결

```javascript
async function initObservatoryReport() {
  // 병렬 로드
  const [discoverRes, memosRes] = await Promise.all([
    fetch(`/api/v2/discover/today?user_id=${UID}`, {headers:headers()})
      .then(r=>r.json()).catch(()=>({})),
    fetch(`/api/memos/list?user_id=${UID}&limit=2`, {headers:headers()})
      .then(r=>r.json()).catch(()=>({})),
  ]);

  renderTodayBook(discoverRes.hero || null);
  renderRecentMemos(memosRes.memos || []);
  renderNewConnections();  // CONSTELLATION_DATA.links 활용 (서버 데이터)
}
```

### 7.4 "오늘 읽을 만한 책" 카드

```css
.today-book-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.today-book-cover {
  width: 52px; height: 78px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  background: linear-gradient(135deg, #2D4A3E, var(--amber));
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem;
}
.today-book-title { font-family: 'Noto Serif KR', serif; font-size: .88rem; color: var(--text); }
.today-book-reason { font-size: .72rem; color: var(--sub); margin-top: 5px; line-height: 1.5; }
.cta-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: .72rem;
  color: var(--amber);
  margin-top: 8px;
  text-decoration: none;
}
.cta-link:hover { text-decoration: underline; }
```

---

## 8. 플로팅 버튼 (FAB) 재설계

### 8.1 현재

- 오른쪽 하단 `＋` 버튼 (새 메모)
- `✎` 버튼 (메모 전체)

### 8.2 목표

```
[중앙 하단 오른쪽]
  🔭  → /lounge  (Discover)       ← 새로 추가
  ✎   → toggleMemoPanel()
  ＋   → openMemoModal()            ← 주 버튼 (가장 큰)
```

**FAB 그룹 레이아웃**
```css
.fab-group {
  position: absolute;
  bottom: 28px;
  right: 24px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  z-index: 6;
}
.fab-main {
  width: 54px; height: 54px;
  border-radius: 50%;
  border: 0;
  background: linear-gradient(135deg, var(--amber), #E8A85A);
  color: #07110f;
  font-size: 1.5rem;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(193,127,59,.45);
  transition: .2s;
}
.fab-main:hover { transform: scale(1.07); box-shadow: 0 6px 28px rgba(193,127,59,.6); }
.fab-sub {
  width: 42px; height: 42px;
  border-radius: 50%;
  border: 1px solid rgba(193,127,59,.3);
  background: rgba(193,127,59,.1);
  color: var(--amber);
  font-size: 1.05rem;
  cursor: pointer;
  transition: .2s;
}
.fab-sub:hover { background: rgba(193,127,59,.2); }
.fab-tooltip {
  position: absolute;
  right: calc(100% + 10px);
  top: 50%;
  transform: translateY(-50%);
  background: rgba(13,27,20,.92);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 5px 10px;
  font-size: .7rem;
  color: var(--sub);
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition: .15s;
}
.fab-item:hover .fab-tooltip { opacity: 1; }
```

---

## 9. 인터랙션 & 애니메이션

### 9.1 행성 호버 효과

```javascript
ne.on('mouseover', function(e, d) {
  d3.select(this).select('.planet-glow')
    .transition().duration(200)
    .attr('r', d.size + 22)
    .attr('opacity', 0.38);
  d3.select(this).select('.planet-img')
    .transition().duration(200)
    .attr('filter', 'drop-shadow(0 0 22px rgba(244,205,137,.55)) brightness(1.2)');
});
ne.on('mouseout', function(e, d) {
  d3.select(this).select('.planet-glow')
    .transition().duration(300)
    .attr('r', d.size + 14)
    .attr('opacity', 0.12 + Math.min(d.memos * 0.03, 0.25));
  d3.select(this).select('.planet-img')
    .transition().duration(300)
    .attr('filter', 'drop-shadow(0 0 14px rgba(244,205,137,.25))');
});
```

### 9.2 새 메모 저장 시 "별빛 폭발" 효과

```javascript
function burstStarEffect(nodeId) {
  // 특정 행성 노드에서 파티클 방출
  const node = nodes.find(n => n.id == nodeId);
  if (!node) return;

  const particles = Array.from({length: 12}, (_, i) => ({
    angle: (i / 12) * Math.PI * 2,
    dist: 0,
    maxDist: 40 + Math.random() * 20,
    opacity: 1,
  }));

  // requestAnimationFrame으로 파티클 애니메이션
  // SVG circle 요소들을 생성 후 이동 → fade out → 제거
}
```

### 9.3 별자리 연결선 호버 (링크 팝업)

```javascript
le.on('mouseover', function(e, d) {
  d3.select(this)
    .attr('stroke', 'rgba(244,205,137,.9)')
    .attr('stroke-width', d.strength * 3.5)
    .attr('stroke-dasharray', '0');

  const popup = document.getElementById('link-popup');
  popup.innerHTML = `
    <div style="font-size:.7rem;color:var(--sub)">${d.source.title} → ${d.target.title}</div>
    <div style="margin-top:5px;font-size:.82rem;line-height:1.5">${d.insight}</div>`;
  popup.style.left = e.offsetX + 14 + 'px';
  popup.style.top  = e.offsetY + 14 + 'px';
  popup.classList.add('show');
});
```

### 9.4 페이지 로드 "우주 형성" 애니메이션

```javascript
// 시뮬레이션 초기 alpha 높게 → 행성들이 흩어져 있다가 중심으로 모이는 느낌
const sim = d3.forceSimulation(nodes)
  .alpha(1.2)         // 현재보다 높게
  .alphaDecay(0.02)   // 천천히 안정화
  // ...

// 행성 노드 초기 opacity 0 → 1 페이드인
ne.attr('opacity', 0)
  .transition()
  .delay((d, i) => i * 80)
  .duration(600)
  .attr('opacity', 1);
```

---

## 10. 반응형 전략

| 브레이크포인트 | 레이아웃 변경 |
|-------------|-------------|
| > 1200px | 3열 풀 레이아웃 |
| 900–1200px | 좌측 패널 160px로 압축, 아이콘+레이블만 |
| 600–900px | 우측 패널 숨김, 모바일 하단 Nav 추가 |
| < 600px | 좌측 패널도 숨김, 모바일 전용 FAB |

```css
@media (max-width: 900px) {
  body { grid-template-columns: 1fr; }
  .left, .right { display: none; }
  .fab-group { bottom: 74px; } /* 하단 Nav 위로 */
}
```

---

## 11. 구현 우선순위 & 단계

### Phase 1 — 즉시 적용 가능 (시각 임팩트 최대)

| 순서 | 작업 | 예상 LOC |
|------|------|---------|
| 1 | 헤더 로고 `Luma_logo_1.png` 교체 | ~5줄 |
| 2 | 좌측 패널 탐사 장치 서브텍스트 추가 | ~30줄 |
| 3 | 우측 패널 `initObservatoryReport()` 연동 | ~80줄 |
| 4 | FAB 그룹 재설계 (🔭 버튼 추가) | ~20줄 |

### Phase 2 — 행성 노드 고도화

| 순서 | 작업 | 예상 LOC |
|------|------|---------|
| 5 | 행성 크기를 메모 수 기반으로 동적 계산 | ~15줄 |
| 6 | 글로우 강도 메모 수 연동 | ~10줄 |
| 7 | 연결 많은 책에 궤도 링 추가 | ~20줄 |
| 8 | SVG glow-filter 추가 | ~15줄 |
| 9 | 행성 클릭 모달 탭 3개로 고도화 | ~100줄 |

### Phase 3 — 인터랙션 & 애니메이션

| 순서 | 작업 |
|------|------|
| 10 | 행성 호버 효과 강화 |
| 11 | 새 메모 저장 시 별빛 폭발 파티클 |
| 12 | 페이지 로드 우주 형성 애니메이션 |
| 13 | 연결선 호버 팝업 개선 |

---

## 12. 페이지별 우주 세계관 일람

| 경로 | 세계관 명칭 | 핵심 UI 메타포 |
|------|------------|-------------|
| `/` | 관측소 홈 | 내 책들의 행성계, 별자리 연결 지도 |
| `/heart` | 마음 행성계 | 감정별 행성 궤도, 감정 타임라인 = 공전 기록 |
| `/lounge` (`/discover`) | 탐사 성운 | 미지의 책 = 새로운 행성, 씨앗 심기 = 착륙 |
| `/social` | 독자 은하 피드 | 다른 독자들의 별빛 = 메모 카드 |
| `/live` | 궤도 정거장 | 같은 시간 읽는 독자들과 도킹 |
| `/socrates` | 지성의 위성 | AI 질문 = 위성에서 보내는 신호 |
| `/deepdive` | 심층 관측소 | 한 행성을 깊이 탐사, 블랙홀 입구 |
| `/community` | 은하 공동체 | 독서 모임 = 성단, 장소 = 행성 기지 |
| `/profile` | 나의 조종석 | 독서 기록 = 항해 일지, 성향 = 항법 장치 |

---

## 13. 파일 수정 범위 요약

```
dashboard.html
├── <style> 수정
│   ├── header CSS 교체 (로고 이미지용)
│   ├── .nav-item 서브텍스트 CSS 추가
│   ├── .fab-group 재설계
│   ├── .modal-tabs CSS 추가
│   ├── .today-book-card CSS 추가
│   └── .orbit-ring CSS 추가
│
├── HTML 수정
│   ├── <header>: img src Luma_logo_1.png
│   ├── <aside.left>: 탐사 장치 서브텍스트 추가
│   ├── <aside.right>: 관측 리포트 구조 교체
│   ├── <main>: FAB 그룹 HTML 재구성
│   └── <svg>: SVG defs glow-filter 추가
│
└── <script> 수정
    ├── initObservatoryReport() 신규 추가
    ├── openBookDetailModal() 탭 UI로 재구성
    ├── D3 행성 노드 크기/글로우 동적화
    ├── 궤도 링 조건부 렌더
    └── FAB 🔭 버튼 이벤트 추가

app/routes/main.py
└── index() 함수: 실제 shelf stats 연동 (TASK 2 참조)
```

---

*설계 기준일: 2026-05-10*  
*LUMA — 읽는 행위를 넘어, 생각의 우주를 연결하다 ✦*

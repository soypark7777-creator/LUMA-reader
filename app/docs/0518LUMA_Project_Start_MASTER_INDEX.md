
# LUMA 프로젝트 시작용 MASTER INDEX

Version: v1.0  
Project: LUMA 독서모임 앱  
Purpose: Codex / Claude Code 협업 시작 전 기준 문서

---

## 1. 사용 순서

아래 순서대로 진행한다.

1. `LUMA_Backend_Codex_Master_Prompt.md`
2. `LUMA_Frontend_ClaudeCode_Master_Prompt.md`
3. Codex: 현재 백엔드 구조 audit
4. Claude Code: 현재 프론트 구조 audit
5. Codex: Lounge 데이터 정제 파이프라인 구현
6. Claude Code: Lounge Filter UI 연결
7. Community / DeepDive / Profile / Places / Socrates 순서로 확장

---

## 2. 역할 분리

### Codex 담당

- Backend API
- DB / service layer
- 도서 데이터 수집
- 도서 표준화
- 중복 제거
- 태깅
- 점수화
- 추천 API
- YouTube API
- Places 저장 API
- mock fallback

### Claude Code 담당

- UI/UX
- 공통 네비게이션
- 카드 레이아웃
- 필터 UI
- 이미지 fallback UI
- 모바일 대응
- loading / empty / error 상태
- interaction polish

---

## 3. 가장 중요한 원칙

- 기존 코드를 지우지 말고 확장한다.
- 기존 route/API를 바꾸지 않는다.
- 새 기능은 새 service/route로 분리한다.
- 프론트는 API 계약을 바꾸지 않는다.
- API key는 절대 프론트에 노출하지 않는다.
- 이미지가 없어도 fallback이 보여야 한다.
- 모바일에서 깨지면 완료가 아니다.

---

## 4. 우선순위

### 1순위

Lounge 도서 추천 데이터 정제:

```text
수집 → 표준화 → 중복 제거 → 태깅 → 점수화 → 추천 API → Filter UI
```

### 2순위

Community 카드형 생각 피드

### 3순위

DeepDive YouTube 검색 기반 큐레이션

### 4순위

Places 내 위치 + 지도 + 카페/도서관 검색

### 5순위

Profile 나의 독서 우주

### 6순위

Socrates 철학 토론광장 보완

---

## 5. 공통 네비게이션

```text
LUMA
생각은 빛이 된다

[별자리 지도]
[마음 행성계]
[탐사 성운]
[독자 광장]
[라이브]
[소크라테스]
[딥다이브]
[프로필]
[모임 장소]
```

---

## 6. 공통 디자인

```text
Deep Forest Green
Premium Reading Club
Exploration Device
Thought Constellation
Dark Glass Panel
Gold Accent
Calm Intellectual UI
```

---

## 7. 최종 체크리스트

- 기존 기능이 깨지지 않았는가
- API 응답이 통일되어 있는가
- fallback이 있는가
- 책 표지가 잘 나오는가
- 표지 없을 때 대체 UI가 있는가
- YouTube key가 노출되지 않는가
- Kakao 지도 도메인이 등록되어 있는가
- 모바일에서 깨지지 않는가
- Lounge 추천 결과가 필터에 따라 바뀌는가

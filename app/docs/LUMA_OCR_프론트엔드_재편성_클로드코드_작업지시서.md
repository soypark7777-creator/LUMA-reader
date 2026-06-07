# LUMA OCR 프론트엔드 재편성 Claude Code 작업지시서

## 0. 작업 목표

`http://localhost:5000/ocr` 페이지를 기존 기능을 유지하면서, 사용자가 책 페이지 이미지를 올리고 문장을 추출한 뒤 직접 책 정보를 확정하고 문장을 다듬고 분석/저장까지 자연스럽게 이어갈 수 있는 “독서 문장 정리 작업대”로 재편성한다.

이번 작업의 핵심은 단순한 시각 변경이 아니라 OCR 작업 흐름을 명확히 만드는 것이다.

- 책 제목은 사용자가 직접 입력한 값을 최우선으로 유지한다.
- 자동 책 정보 감지는 추천값으로만 다루고, 사용자의 입력을 덮어쓰지 않는다.
- OCR 원문과 다듬은 문장을 비교할 수 있게 한다.
- 텍스트 개선, 표지 감지, 메모 초안 생성, 전체 분석이 모두 같은 책 제목/작가/쪽수 context를 사용하게 한다.
- 분석 결과는 한국어로 읽기 좋게 구조화한다.
- 기존 API와 저장 흐름을 깨지 않는다.

## 1. 작업 대상

주요 작업 파일:

```text
app/templates/ocr.html
```

필요 시 함께 확인할 파일:

```text
app/routes/ocr.py
app/services/ocr_service.py
app/docs/LUMA_OCR_페이지_개선_작업계획서.md
app/docs/OCR_SETUP.md
```

이번 지시서의 기본 범위는 프론트엔드 재편성이다. 백엔드 수정이 꼭 필요할 때만 최소 범위로 수정한다.

## 2. 절대 지켜야 할 원칙

- `/ocr` 페이지 자체는 계속 Flask template로 동작해야 한다.
- 새 프레임워크를 추가하지 않는다.
- 기존 API endpoint 이름은 바꾸지 않는다.
- 사용자가 입력한 `book-title`, `book-author`, `page-number` 값은 자동 감지 결과로 덮어쓰지 않는다.
- mock 또는 fallback 책 정보가 UI 입력칸에 자동으로 들어가면 안 된다.
- `Content-Type`을 수동으로 multipart/form-data로 지정하지 않는다. `FormData`는 브라우저가 boundary를 붙이게 둔다.
- 긴 설명문을 화면에 많이 붙이지 않는다. 화면은 실제 작업 도구처럼 보여야 한다.
- UI 카드를 중첩하지 않는다.
- 모바일에서 텍스트와 버튼이 겹치거나 잘리지 않게 한다.

## 3. 현재 기능 계약

프론트엔드에서 사용하는 API 객체는 다음 구조를 유지한다.

```javascript
const API = {
  status: '/api/ocr/status',
  scan: '/api/ocr/scan',
  enhance: '/api/ocr/enhance',
  bookCover: '/api/ocr/book-cover',
  generateMemo: '/api/ocr/generate-memo',
  saveMemo: '/api/ocr/save-memo',
  pipeline: '/api/ocr/full-pipeline'
};
```

각 버튼의 의미는 다음과 같다.

- `OCR 추출`: 선택한 이미지에서 OCR 텍스트 추출
- `텍스트 개선`: 현재 텍스트를 책 context와 함께 다듬기
- `표지에서 책 정보 감지`: 이미지에서 책 제목/작가/출판사 후보 추출
- `메모 초안 생성`: 현재 텍스트와 확정된 책 정보를 기준으로 메모 생성
- `전체 분석 실행`: 현재 텍스트 또는 이미지로 분석, 자료, 메모를 생성
- `DB 저장 + 분석`: 메모를 저장하고 분석 결과 반영

## 4. 새 화면 구조

기존 2열 그리드를 다음의 작업대 구조로 재편성한다.

### 데스크톱

3개 작업 영역으로 구성한다.

```text
┌────────────────────────────────────────────────────────────┐
│ 상단: 페이지 제목, OCR 상태, 진행 단계 표시                 │
├─────────────────┬────────────────────────┬─────────────────┤
│ 이미지 입력      │ 텍스트 작업              │ 책 정보/분석      │
│ 업로드/촬영      │ 원문/개선문 비교          │ 책 제목/작가/쪽수 │
│ 미리보기         │ 다듬기 강도               │ 분석 요약/저장    │
└─────────────────┴────────────────────────┴─────────────────┘
```

권장 grid:

```css
.ocr-workspace {
  display: grid;
  grid-template-columns: minmax(260px, .85fr) minmax(360px, 1.35fr) minmax(280px, .9fr);
  gap: 16px;
  align-items: start;
}
```

### 모바일

단일 컬럼으로 다음 순서가 되게 한다.

```text
1. 이미지 입력
2. 책 정보 확정
3. 텍스트 원문/다듬기
4. 메모 초안
5. 분석과 자료
6. 저장
```

## 5. 상단 상태 영역

상단에는 다음만 배치한다.

- H1: `OCR 문장 작업대`
- 보조 문장: `책 페이지를 문장으로 바꾸고, 다듬고, 메모로 저장합니다.`
- 상태 badge: Google Vision 연결 상태
- 단계 표시: `이미지`, `텍스트`, `책 정보`, `분석`, `저장`

단계 표시는 실제 상태에 따라 active/completed 스타일을 바꾼다.

상태 기준:

- 이미지 선택됨: `state.file`
- OCR 텍스트 있음: `extracted-text.value.trim()`
- 책 제목 있음: `book-title.value.trim()`
- 메모 있음: `state.generatedMemo`
- 저장됨: `state.savedMemo`

## 6. 이미지 입력 패널

이미지 입력 패널에는 다음을 둔다.

- 드래그 앤 드롭 영역
- 파일 선택 버튼
- 카메라 촬영 버튼
- 이미지 미리보기
- 파일 메타 정보: 파일명, 용량, 이미지 크기
- OCR 추출 버튼
- 초기화 버튼

개선 요구:

- 이미지를 선택하면 파일명과 용량 외에 가능한 경우 해상도도 표시한다.
- OCR 추출 중에는 버튼 label을 `추출 중...`으로 바꾸고 disabled 처리한다.
- Google Vision 결과 텍스트가 비어 있으면 에러가 아니라 안내 상태로 표시한다.

추천 안내 문구:

```text
텍스트가 거의 감지되지 않았습니다. 페이지를 더 밝게 촬영하거나 글자가 화면 중앙에 오도록 다시 시도해 주세요.
```

## 7. 책 정보 확정 패널

책 정보는 “분석에 쓰이는 기준값”이므로 별도 패널로 분리한다.

필드:

```html
<input id="book-title" placeholder="책 제목">
<input id="book-author" placeholder="작가">
<input id="page-number" type="number" min="1" placeholder="쪽수">
```

필수 동작:

- 사용자가 직접 입력한 값은 자동 감지 결과가 덮어쓰지 않는다.
- 표지 감지 결과는 즉시 input에 넣지 말고, “감지 후보” 영역에 보여준다.
- 후보 적용 버튼을 눌렀을 때만 입력칸에 반영한다.

후보 UI 예시:

```text
감지 후보
제목: 데미안
작가: 헤르만 헤세
출판사: 민음사
[이 정보 적용]
```

프론트 상태 추가:

```javascript
state.detectedBook = null;
```

새 helper 제안:

```javascript
function getBookContext() {
  return {
    book_title: $('book-title').value.trim(),
    book_author: $('book-author') ? $('book-author').value.trim() : '',
    page_number: $('page-number').value || null
  };
}
```

모든 JSON 요청과 pipeline form 요청은 이 context를 사용한다.

## 8. 텍스트 작업 패널

OCR 원문과 다듬은 문장을 분리한다.

필드:

- `original-text`: OCR 원문 textarea 또는 readonly 영역
- `extracted-text`: 현재 적용된 작업 텍스트 textarea
- `enhanced-preview`: 다듬은 문장 미리보기 영역

최소 구현이 부담되면 기존 `extracted-text`는 유지하되, 아래 상태를 추가한다.

```javascript
state.originalText = '';
state.enhancedText = '';
```

OCR 추출 후:

- `state.originalText = text`
- `extracted-text.value = text`
- 원문 탭/영역에 같은 텍스트 표시

텍스트 개선 후:

- `state.enhancedText = data.corrected || data.enhanced`
- 바로 덮어쓰지 말고 preview 영역에 표시
- 사용자가 `다듬은 문장 적용` 버튼을 누르면 `extracted-text.value`에 반영

버튼:

- `텍스트 개선`
- `다듬은 문장 적용`
- `원문으로 되돌리기`
- `다시 다듬기`

다듬기 강도:

```html
<select id="enhance-mode">
  <option value="strict">정확 교정</option>
  <option value="natural">자연 문장</option>
  <option value="memo">메모형 정리</option>
</select>
```

현재 백엔드가 mode를 안 쓰더라도 프론트 payload에는 포함한다.

```javascript
body: JSON.stringify({
  text,
  enhance_mode: $('enhance-mode').value,
  ...getBookContext()
})
```

## 9. 메모 초안 패널

메모 초안은 분석 패널과 분리해서 표시한다.

표시 항목:

- 메모 초안 본문
- 태그 chips
- mood
- insight
- 생성 source

메모 초안 생성 버튼은 다음 조건에서 활성화한다.

- `extracted-text`에 텍스트가 있음
- 책 제목은 필수는 아니지만, 비어 있으면 “책 제목 없이 생성” 상태를 명확히 표시

메모 생성 payload:

```javascript
{
  text: $('extracted-text').value.trim(),
  ...getBookContext()
}
```

## 10. 분석과 자료 패널

분석 결과를 한 문단에 몰아넣지 말고 구조화한다.

필수 영역:

- `요약`
- `주제`
- `감정`
- `다시 생각할 질문`
- `키워드`
- `관련 영상`
- `참고 자료`

렌더링 함수 개선:

```javascript
function renderAnalysis(analysis) {
  // summary/theme/emotion/question/keywords를 각각 독립 영역에 출력
}
```

현재처럼 `analysis-text` 하나에 이어 붙이는 방식은 폐기하거나 fallback으로만 둔다.

전체 분석 실행 payload:

텍스트가 있는 경우:

```javascript
{
  text: $('extracted-text').value.trim(),
  ...getBookContext()
}
```

이미지만 있는 경우:

```javascript
form.append('image', state.file);
form.append('book_title', context.book_title);
form.append('book_author', context.book_author);
form.append('page_number', context.page_number || '');
form.append('language', 'ko');
```

전체 분석 후에도 책 정보 적용은 `preserveManual: true`를 사용한다.

## 11. 저장 패널

저장 전에 작은 확인 영역을 둔다.

표시:

```text
저장될 책: {book_title || '제목 없음'}
작가: {book_author || '-'}
쪽수: {page_number || '-'}
저장될 메모: memo_draft 또는 현재 텍스트
```

저장 버튼 조건:

- 저장할 메모나 텍스트가 있어야 한다.
- 저장 중 disabled 처리한다.
- 저장 완료 후 memo_id를 표시한다.

저장 payload:

```javascript
{
  content: draft,
  text: $('extracted-text').value.trim(),
  ...getBookContext(),
  tags: state.generatedMemo?.tags || [],
  mood: state.generatedMemo?.mood || 'neutral'
}
```

## 12. 상태 관리

현재 `state`를 다음처럼 확장한다.

```javascript
const state = {
  file: null,
  originalText: '',
  enhancedText: '',
  detectedBook: null,
  generatedMemo: null,
  savedMemo: null,
  analysis: null,
  stream: null,
  facingMode: 'environment',
  busy: {
    scan: false,
    enhance: false,
    bookDetect: false,
    memo: false,
    pipeline: false,
    save: false
  }
};
```

버튼 disabled 상태는 상태 기반으로 갱신하는 helper를 만든다.

```javascript
function updateActionStates() {
  const hasFile = Boolean(state.file);
  const hasText = Boolean($('extracted-text').value.trim());
  $('btn-scan').disabled = !hasFile || state.busy.scan;
  $('btn-enhance').disabled = !hasText || state.busy.enhance;
  $('btn-memo').disabled = !hasText || state.busy.memo;
  $('btn-pipeline').disabled = (!hasText && !hasFile) || state.busy.pipeline;
}
```

## 13. CSS 방향

현재 우주 테마는 유지하되 장식은 줄인다. 페이지는 “도구”처럼 읽혀야 한다.

권장 palette:

```css
:root {
  --bg: #07090f;
  --surface: rgba(15, 19, 29, .92);
  --surface-2: rgba(20, 26, 38, .92);
  --line: rgba(255,255,255,.10);
  --text: #edf2f7;
  --muted: #9aa7b8;
  --accent: #7dd3fc;
  --accent-2: #f2c86b;
  --ok: #79e2a7;
  --danger: #ff8d8d;
}
```

컴포넌트 원칙:

- 패널 radius는 8px 정도
- 입력 영역은 넓고 읽기 편하게
- textarea line-height는 1.7 이상
- 버튼 높이는 일정하게
- chips는 작게, 결과 본문과 겹치지 않게
- 모바일에서 grid는 1열

피해야 할 것:

- 카드 안에 카드 중첩
- 너무 큰 hero
- 과한 gradient/orb 장식
- 긴 설명문
- 버튼 텍스트 줄바꿈으로 인한 레이아웃 흔들림

## 14. 에러/빈 상태 처리

각 기능은 실패해도 화면 전체를 깨지 말고 해당 영역에만 표시한다.

상태 문구:

- OCR 빈 결과: `텍스트가 감지되지 않았습니다. 더 선명한 이미지로 다시 시도해 주세요.`
- 책 정보 감지 실패: `책 정보를 확신할 수 없습니다. 제목과 작가를 직접 입력해 주세요.`
- 텍스트 개선 실패: `문장 다듬기에 실패했습니다. 원문은 그대로 사용할 수 있습니다.`
- 분석 실패: `분석을 완료하지 못했습니다. 텍스트를 조금 더 입력한 뒤 다시 시도해 주세요.`
- 저장 실패: `저장하지 못했습니다. 로그인 상태와 네트워크를 확인해 주세요.`

## 15. 접근성/사용성

- 모든 버튼은 실제 `button` 요소 사용
- 파일 업로드 drop zone은 label/input 구조 유지
- textarea와 input에는 명확한 placeholder 제공
- 상태 badge는 색상만으로 의미를 전달하지 말고 텍스트도 함께 표시
- toast는 2.5-3초 후 사라지되, 중요한 오류는 패널 안에도 남긴다
- 모바일에서 터치 타깃은 최소 40px 이상

## 16. 검증 체크리스트

작업 완료 후 반드시 확인한다.

- `/ocr` 페이지가 정상 로드된다.
- 책 제목에 `데미안`을 직접 입력하고 OCR/표지 감지를 해도 `어린왕자` 등 다른 제목으로 바뀌지 않는다.
- 작가 입력값도 자동 감지로 덮어써지지 않는다.
- 텍스트 개선 요청 payload에 `book_title`, `book_author`, `page_number`, `enhance_mode`가 포함된다.
- 다듬은 문장 적용 전에는 원문이 보존된다.
- 메모 초안 생성 결과가 입력한 책 제목 기준으로 표시된다.
- 전체 분석 결과가 요약/주제/감정/질문/키워드로 분리되어 보인다.
- 저장 전 확인 영역에 책 제목/작가/쪽수가 정확히 표시된다.
- 모바일 너비 390px에서 텍스트, 버튼, 패널이 겹치지 않는다.
- 데스크톱 너비 1440px에서 3개 작업 영역이 균형 있게 보인다.

## 17. 권장 수동 테스트 시나리오

### 시나리오 A: 직접 입력 우선

1. `/ocr` 접속
2. 책 제목에 `데미안`, 작가에 `헤르만 헤세` 입력
3. 이미지 업로드
4. OCR 추출
5. 표지에서 책 정보 감지 실행
6. 책 제목과 작가가 유지되는지 확인
7. 텍스트 개선
8. 메모 초안 생성
9. 전체 분석 실행

기대 결과:

- 입력한 책 제목/작가가 유지된다.
- 분석 결과에 `데미안` context가 반영된다.

### 시나리오 B: 감지 후보 적용

1. 책 제목/작가를 비운 상태로 이미지 업로드
2. 표지에서 책 정보 감지 실행
3. 감지 후보가 별도 영역에 표시되는지 확인
4. `이 정보 적용` 클릭
5. 입력칸에 후보가 반영되는지 확인

기대 결과:

- 후보 적용 전에는 input이 자동 변경되지 않는다.
- 버튼 클릭 후에만 input이 바뀐다.

### 시나리오 C: 원문/개선문 비교

1. 텍스트를 직접 붙여넣기
2. 텍스트 개선 실행
3. 원문과 개선문이 동시에 보이는지 확인
4. 다듬은 문장 적용
5. 원문으로 되돌리기

기대 결과:

- 원문을 잃지 않는다.
- 적용/되돌리기가 명확히 동작한다.

## 18. 완료 보고 형식

Claude Code는 작업 완료 후 다음 형식으로 보고한다.

```text
수정 파일:
- app/templates/ocr.html
- 필요 시 추가 파일

주요 변경:
- ...

검증:
- /ocr 로드 확인
- 직접 입력 책 제목 유지 확인
- 텍스트 개선 payload 확인
- 모바일/데스크톱 레이아웃 확인

남은 이슈:
- ...
```

## 19. 이번 작업에서 하지 말 것

- OCR 백엔드 전체 재작성
- DB schema 변경
- 로그인/인증 구조 변경
- `/heart`, `/social`, `/deepdive` 전체 리디자인
- 새 프론트엔드 빌드 도구 도입
- Google Vision key 내용 출력 또는 커밋

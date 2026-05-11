# LUMA AI 소크라테스 백엔드 인수인계

이 문서는 Claude Code가 소크라테스 프론트엔드/후속 백엔드 작업을 이어받기 위한 요약입니다.

## 작업 요약

기존 `/api/socrates/*` API를 유지하면서, AI 소크라테스 페이지를 단순 5단계 질문 페이지에서 “책 토론 준비실” 흐름으로 확장했습니다.

기존 API는 삭제하거나 이름을 바꾸지 않았고, 기존 응답 구조도 깨지지 않도록 유지했습니다. 새 기능은 `/api/socrates/*`와 `/api/v2/socrates/*` 양쪽에 모두 추가되어 있습니다.

## 수정 파일

### `app/services/socrates_discussion_service.py`

신규 서비스 파일입니다.

담당 기능:

- 책 이해 카드 생성
- 독서모임용 토론 질문 생성
- 찬반 토론 주제 생성
- Lounge 공유 카드 생성
- `discussion_mode` 정규화
- Gemini 실패 시 mock 응답 반환

### `app/services/live_socrates_service.py`

기존 소크라테스 5단계 세션 로직을 유지하면서 `discussion_mode`를 추가했습니다.

변경 사항:

- `start_session(data)`에서 `discussion_mode` 수신
- 값이 없으면 `appreciation` 기본값 사용
- 시작 응답에 `discussion_mode` 추가
- 질문 생성 프롬프트에 대화 모드 반영
- 기존 응답 필드는 유지

### `app/routes/new_features.py`

`/api/socrates/*` 신규 API를 추가했습니다.

### `app/routes/mysql_api.py`

`/api/v2/socrates/*`에도 동일 신규 API를 추가했습니다.

## 기존 API 호환성

다음 기존 API는 유지되어야 하며, 현재 그대로 남아 있습니다.

```text
POST /api/socrates/start
POST /api/socrates/answer
GET  /api/socrates/sessions
GET  /api/socrates/sessions/<session_id>/resume
POST /api/socrates/dictionary
GET  /api/socrates/dictionary
POST /api/socrates/action
GET  /api/socrates/actions
POST /api/socrates/action/<plan_id>/checkin
```

`POST /api/socrates/start`는 선택적으로 `discussion_mode`를 받습니다.

```json
{
  "passage": "인간은 자유롭도록 선고받았다",
  "book_title": "실존주의와 인간감정",
  "user_id": "user_demo",
  "discussion_mode": "debate"
}
```

기존 클라이언트가 `discussion_mode`를 보내지 않아도 동작합니다. 기본값은 `appreciation`입니다.

가능한 값:

```text
appreciation  감상형
analysis      분석형
debate        토론형
life          삶 연결형
character     인물 분석형
```

응답 예시:

```json
{
  "ok": true,
  "session_id": "sess_xxxxxxxx",
  "question": "첫 질문",
  "stage": 0,
  "total_stages": 5,
  "discussion_mode": "debate"
}
```

## 추가된 API

### 1. 책 이해 카드

```text
POST /api/socrates/book-brief
POST /api/v2/socrates/book-brief
```

Request:

```json
{
  "passage": "책 구절",
  "book_title": "책 제목",
  "user_id": "user_demo"
}
```

Response:

```json
{
  "ok": true,
  "brief": {
    "summary": [
      "핵심 요약 1",
      "핵심 요약 2",
      "핵심 요약 3"
    ],
    "keywords": ["자유", "책임", "불안"],
    "main_question": "이 구절은 우리에게 어떤 선택의 무게를 묻고 있나요?",
    "discussion_hint": "이 구절은 자유와 책임의 관계를 중심으로 토론할 수 있습니다."
  }
}
```

### 2. 토론 질문 생성

```text
POST /api/socrates/discussion-questions
POST /api/v2/socrates/discussion-questions
```

Request:

```json
{
  "session_id": "sess_xxxxxxxx",
  "passage": "책 구절",
  "book_title": "책 제목",
  "insight": "최종 인사이트",
  "discussion_mode": "debate",
  "user_id": "user_demo"
}
```

Response:

```json
{
  "ok": true,
  "questions": [
    {
      "type": "understanding",
      "label": "이해 질문",
      "question": "이 구절에서 가장 중요한 단어는 무엇인가요?"
    },
    {
      "type": "emotion",
      "label": "감정 질문",
      "question": "이 문장을 읽었을 때 어떤 감정이 들었나요?"
    },
    {
      "type": "debate",
      "label": "토론 질문",
      "question": "당신은 이 문장의 주장에 동의하나요?"
    }
  ]
}
```

### 3. 찬반 토론 주제 생성

```text
POST /api/socrates/debate-topic
POST /api/v2/socrates/debate-topic
```

Request:

```json
{
  "passage": "책 구절",
  "book_title": "책 제목",
  "insight": "최종 인사이트",
  "user_id": "user_demo"
}
```

Response:

```json
{
  "ok": true,
  "debate": {
    "topic": "인간은 자유로울수록 더 행복한가?",
    "pros": [
      "자유는 자기 삶을 선택할 수 있게 한다.",
      "선택권은 인간의 존엄과 연결된다."
    ],
    "cons": [
      "자유는 책임과 불안을 함께 가져온다.",
      "선택이 많을수록 오히려 혼란이 커질 수 있다."
    ],
    "neutral_question": "자유와 안정 중 당신에게 더 중요한 것은 무엇인가요?"
  }
}
```

### 4. Lounge 공유 카드 생성

```text
POST /api/socrates/lounge-card
POST /api/v2/socrates/lounge-card
```

Request:

```json
{
  "passage": "책 구절",
  "book_title": "책 제목",
  "insight": {
    "refined_thought": "최종 인사이트",
    "tags": ["자유", "책임", "불안"]
  },
  "discussion_questions": [
    {
      "type": "debate",
      "label": "토론 질문",
      "question": "자유는 우리를 행복하게 만드는가?"
    }
  ],
  "debate": {
    "neutral_question": "자유와 안정 중 무엇이 더 중요한가요?"
  },
  "user_id": "user_demo"
}
```

Response:

```json
{
  "ok": true,
  "card": {
    "title": "자유에 대한 질문",
    "book_title": "실존주의와 인간감정",
    "passage_preview": "인간은 자유롭도록 선고받았다...",
    "main_question": "자유와 안정 중 무엇이 더 중요한가요?",
    "tags": ["자유", "책임", "불안"],
    "discussion_questions": [
      "자유는 우리를 행복하게 만드는가?"
    ]
  }
}
```

## 프론트엔드 연결 흐름

권장 흐름:

1. 사용자가 책 구절과 책 제목 입력
2. 사용자가 대화 모드 선택
3. `POST /api/socrates/book-brief`
4. `POST /api/socrates/start`
5. 기존처럼 `POST /api/socrates/answer` 5회 진행
6. 완료 응답의 `insight` 저장
7. `POST /api/socrates/discussion-questions`
8. `POST /api/socrates/debate-topic`
9. `POST /api/socrates/lounge-card`
10. Lounge 화면/모임 생성 흐름에 카드 데이터 전달

프론트에서 연결해야 할 endpoint 목록:

```text
POST /api/socrates/book-brief
POST /api/socrates/start
POST /api/socrates/answer
POST /api/socrates/discussion-questions
POST /api/socrates/debate-topic
POST /api/socrates/lounge-card
GET  /api/socrates/sessions
GET  /api/socrates/sessions/<session_id>/resume
```

`/api/v2/socrates/*` 기준으로 작업하는 화면이면 동일 경로 앞에 `/api/v2`를 사용하면 됩니다.

## Gemini / Mock 동작

신규 서비스는 기존 `gemini_service`의 내부 헬퍼를 사용합니다.

```python
from app.services.gemini_service import _call_gemini, _parse_json_safe
```

Gemini 호출 실패, API 키 없음, 응답 파싱 실패 시 모두 mock 응답을 반환합니다.

프론트엔드는 Gemini 연결 상태와 무관하게 항상 응답을 렌더링할 수 있습니다.

## 테스트 방법

외부 Gemini 호출을 끄고 테스트하는 것을 권장합니다.

```powershell
$env:LUMA_DISABLE_EXTERNAL_AI='1'
py -m pytest tests\test_all.py -q
```

현재 확인 결과:

```text
50 passed
```

주의:

`.pytest_cache` 권한 warning이 출력될 수 있지만 테스트 실패는 아닙니다.

## 스모크 테스트 예시

```powershell
$env:LUMA_DISABLE_EXTERNAL_AI='1'
py -c "from app.factory import create_app; app=create_app(); c=app.test_client(); payload={'passage':'인간은 자유롭도록 선고받았다','book_title':'실존주의와 인간감정','user_id':'user_demo','discussion_mode':'debate'}; print(c.post('/api/socrates/start', json=payload).json); print(c.post('/api/socrates/book-brief', json=payload).json); print(c.post('/api/socrates/discussion-questions', json={**payload,'insight':'자유는 책임을 동반한다'}).json); print(c.post('/api/socrates/debate-topic', json=payload).json); print(c.post('/api/socrates/lounge-card', json={**payload,'insight':{'tags':['자유','책임','불안']}}).json)"
```

## 후속 작업 메모

- 현재 `app/templates/socrates.html`은 새 “책 토론 준비실” UI로 완전히 개편되지 않았을 수 있습니다.
- 기존 프론트는 `/api/socrates/start`, `/api/socrates/answer` 중심으로 동작합니다.
- 새 UI에서는 `discussion_mode` 선택 UI와 책 이해 카드/토론 질문/찬반 주제/Lounge 카드 섹션을 추가하면 됩니다.
- 기존 응답 구조를 전제로 한 화면은 계속 동작하도록 유지해야 합니다.
- Lounge 공유는 아직 실제 저장 API에 직접 연결하지 않고 카드 데이터 생성까지만 담당합니다.

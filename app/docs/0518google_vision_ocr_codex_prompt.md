# Google Vision OCR MVP 구현용 Codex 프롬프트

## 현재 상황

현재 프로젝트에는 OCR 기능이 있으며, 사용자는 다음 주소에서 OCR을 사용하려고 한다.

```text
http://localhost:5000/ocr
```

이미 Google Vision API 인증 준비는 끝났다.

```text
secrets/google-vision-key.json
```

`.env`에는 아래 설정이 등록되어 있다.

```env
# ── Google OCR ──────────────────────────────────
GOOGLE_APPLICATION_CREDENTIALS=./secrets/google-vision-key.json
```

목표는 기존 코드를 꼬이게 하지 않고, 현재 `/ocr` 엔드포인트에서 Google Cloud Vision API를 이용해 이미지 OCR 텍스트를 안정적으로 추출하는 것이다.

---

## Codex에게 붙여넣을 최종 프롬프트

```text
너는 FastAPI 백엔드와 OCR 연동을 잘 아는 시니어 개발자다.

현재 프로젝트에는 OCR 기능이 있지만 http://localhost:5000/ocr 에서 OCR 텍스트 추출이 제대로 되지 않고 있다.
Google Cloud Vision API를 이용해서 OCR MVP를 안정적으로 구현해야 한다.

이미 준비된 내용:

1. 서비스 계정 JSON 키 파일 위치
   secrets/google-vision-key.json

2. .env 설정
   GOOGLE_APPLICATION_CREDENTIALS=./secrets/google-vision-key.json

중요 원칙:

- 기존 프로젝트 구조를 먼저 분석한 뒤 수정한다.
- 기존 main.py, app.py, router, blueprint, prefix 구조를 함부로 바꾸지 않는다.
- 기존 /ocr 화면 또는 프론트엔드가 있다면 요청/응답 흐름을 깨지 않는다.
- API 키 또는 JSON 파일 내용은 절대 코드에 직접 쓰지 않는다.
- secrets/google-vision-key.json 파일은 Git에 올라가지 않게 한다.
- 먼저 현재 OCR 실패 원인을 진단하고, 그다음 최소 수정으로 고친다.

작업 순서:

1. 프로젝트 구조 확인

- 현재 프로젝트가 FastAPI인지 Flask인지 먼저 확인한다.
- 서버 실행 파일이 main.py, app.py, run.py 중 무엇인지 확인한다.
- http://localhost:5000/ocr 엔드포인트가 어디에 정의되어 있는지 찾는다.
- 프론트엔드에서 /ocr로 요청하는 코드가 있는지 찾는다.
- 요청 방식이 multipart/form-data인지, JSON/base64 방식인지 확인한다.

2. 의존성 확인 및 추가

requirements.txt 또는 pyproject.toml을 확인하고 아래 패키지가 없으면 추가한다.

- google-cloud-vision
- python-multipart
- python-dotenv
- pillow
- opencv-python

주의:
- 이미 requirements.txt가 있으면 기존 내용을 유지하고 필요한 패키지만 추가한다.
- 패키지 버전 충돌이 예상되면 무리하게 고정하지 말고 최소 추가만 한다.

3. 환경변수 로딩 확인

- .env가 서버 시작 시 로딩되는지 확인한다.
- python-dotenv가 사용되고 있지 않다면 서버 진입점에서 안전하게 load_dotenv()를 추가한다.
- 단, 기존 설정 로딩 방식이 있다면 그 방식을 우선한다.

확인해야 할 환경변수:

GOOGLE_APPLICATION_CREDENTIALS=./secrets/google-vision-key.json

4. 보안 설정 확인

.gitignore에 아래 항목이 없으면 추가한다.

secrets/
*.json

주의:
- .env를 Git에 올리는 정책이 기존에 있으면 유지하되, 최소한 secrets/는 반드시 제외한다.
- 실제 google-vision-key.json 파일 내용은 절대 출력하거나 커밋하지 않는다.

5. OCR 서비스 모듈 분리

가능하면 OCR 로직을 라우터 안에 직접 길게 넣지 말고 서비스 파일로 분리한다.

예시 구조 중 현재 프로젝트에 맞는 쪽을 선택한다.

FastAPI 예시:

app/
  routes/
    ocr.py
  services/
    google_vision_ocr.py

또는 기존 구조가 다르면 기존 구조를 따른다.

서비스 함수 예시 책임:

- 이미지 bytes 입력 받기
- Google Vision ImageAnnotatorClient 생성
- document_text_detection 실행
- full_text_annotation.text 추출
- 에러 발생 시 명확한 예외 반환

6. /ocr 엔드포인트 구현

http://localhost:5000/ocr 에서 반드시 동작해야 한다.

POST /ocr 조건:

- multipart/form-data 방식으로 file 필드를 받는다.
- file이 없으면 400 반환
- 이미지 파일이 아니면 400 반환
- Google Vision API document_text_detection 사용
- 추출된 텍스트가 없더라도 success=true와 빈 text를 반환한다.
- Google Vision API 자체 에러가 있으면 success=false 또는 적절한 HTTP 에러로 반환한다.

권장 응답 형식:

성공:

{
  "success": true,
  "engine": "google_vision",
  "filename": "sample.jpg",
  "text": "추출된 텍스트",
  "text_length": 123
}

실패:

{
  "success": false,
  "engine": "google_vision",
  "error": "실패 이유"
}

7. health 체크 엔드포인트 추가

가능하면 아래 중 하나를 추가한다.

GET /ocr/health
또는
GET /health/ocr

반환 내용:

{
  "success": true,
  "engine": "google_vision",
  "credentials_path": "./secrets/google-vision-key.json",
  "credentials_exists": true
}

주의:
- JSON 키 내용은 절대 반환하지 않는다.
- 경로와 존재 여부만 확인한다.

8. 프론트엔드 요청 확인

프론트엔드에서 OCR 요청 코드가 있다면 아래 조건과 맞는지 확인한다.

정상 예시:

const formData = new FormData();
formData.append("file", imageFile);

const response = await fetch("http://localhost:5000/ocr", {
  method: "POST",
  body: formData,
});

const result = await response.json();

주의:
- Content-Type을 수동으로 multipart/form-data로 지정하지 않는다.
- 브라우저가 boundary를 자동으로 넣게 둔다.
- 백엔드 file 필드명과 프론트 formData.append("file", ...) 이름이 반드시 같아야 한다.

9. CORS 확인

프론트엔드가 다른 포트에서 실행된다면 CORS 문제를 확인한다.

예:
- 백엔드: http://localhost:5000
- 프론트엔드: http://localhost:5500 또는 http://localhost:3000

기존 CORS 설정이 있다면 유지하고, 필요한 origin만 추가한다.

예시 origin:

http://localhost:3000
http://localhost:5173
http://localhost:5500
http://127.0.0.1:5500

10. 테스트 파일 추가

가능하면 간단한 테스트 스크립트를 추가한다.

scripts/test_google_vision_ocr.py

기능:

- .env 로딩
- GOOGLE_APPLICATION_CREDENTIALS 경로 출력
- 파일 존재 여부 확인
- ImageAnnotatorClient 생성 가능 여부 확인

단, JSON 내용은 절대 출력하지 않는다.

11. 문서 작성

아래 파일을 생성하거나 업데이트한다.

docs/OCR_SETUP.md

포함할 내용:

- Google Vision API 사용 조건
- 서비스 계정 JSON 키 위치
- .env 설정
- .gitignore 주의사항
- 서버 실행 방법
- curl 테스트 방법
- 자주 나는 오류와 해결법

curl 테스트 명령어 예시:

curl -X POST "http://localhost:5000/ocr" -F "file=@test.jpg"

Windows PowerShell 예시도 추가한다.

12. 완료 후 보고

작업이 끝나면 아래 형식으로 보고한다.

- 수정한 파일 목록
- 추가한 파일 목록
- /ocr 동작 방식
- 실행 명령어
- 테스트 명령어
- 아직 사용자가 직접 해야 하는 것
- 주의할 점

절대 하지 말 것:

- 서비스 계정 JSON 내용을 코드에 붙여넣지 말 것
- secrets 폴더를 Git에 포함하지 말 것
- 기존 라우팅 구조를 무리하게 갈아엎지 말 것
- 기존 프론트엔드 화면을 불필요하게 수정하지 말 것
- OCR 결과를 DB에 저장하는 기능까지 한 번에 과하게 만들지 말 것

이번 작업의 범위:

1차 MVP 범위는 오직 다음이다.

- Google Vision 인증 확인
- /ocr 이미지 업로드 OCR 추출
- 안정적인 JSON 응답
- health 체크
- 테스트 방법 문서화

DB 저장, PDF 다중 페이지 OCR, 이미지 전처리, AI 요약/교정은 이번 작업 범위에서 제외한다.
```

---

## Codex 작업 후 사람이 확인할 체크리스트

```text
[ ] 서버가 http://localhost:5000 에서 실행된다.
[ ] POST http://localhost:5000/ocr 가 존재한다.
[ ] form-data file 업로드가 된다.
[ ] OCR 결과 text가 반환된다.
[ ] .env의 GOOGLE_APPLICATION_CREDENTIALS 경로가 맞다.
[ ] secrets/google-vision-key.json 파일이 실제로 존재한다.
[ ] .gitignore에 secrets/ 와 *.json 이 있다.
[ ] docs/OCR_SETUP.md가 생성되었다.
[ ] curl 테스트 명령어가 성공한다.
[ ] 프론트엔드 OCR 버튼이 같은 /ocr로 요청한다.
```

---

## 테스트 명령어

### 서버 실행 예시

프로젝트마다 다를 수 있으므로 Codex가 실제 구조를 확인한 뒤 정확한 명령어를 안내해야 한다.

예시:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

또는:

```bash
python app.py
```

---

### curl 테스트

```bash
curl -X POST "http://localhost:5000/ocr" -F "file=@test.jpg"
```

---

### PowerShell 테스트

```powershell
curl.exe -X POST "http://localhost:5000/ocr" -F "file=@test.jpg"
```

---

## 자주 나는 오류

### 1. Could not automatically determine credentials

원인:

```text
GOOGLE_APPLICATION_CREDENTIALS 경로가 틀렸거나 .env가 로딩되지 않음
```

확인:

```powershell
echo $env:GOOGLE_APPLICATION_CREDENTIALS
```

---

### 2. File not found

원인:

```text
secrets/google-vision-key.json 파일 위치가 틀림
```

확인:

```text
프로젝트 루트/secrets/google-vision-key.json
```

---

### 3. 403 Permission denied

원인:

```text
Cloud Vision API가 비활성화되어 있거나 서비스 계정 권한이 부족함
```

해결:

```text
Google Cloud Console → Cloud Vision API 활성화
IAM → 서비스 계정 권한에 Cloud Vision AI User 추가
```

---

### 4. 422 Unprocessable Entity

원인:

```text
백엔드는 file 필드를 기다리는데 프론트엔드가 다른 이름으로 보냄
```

해결:

```javascript
formData.append("file", imageFile);
```

---

### 5. CORS 에러

원인:

```text
프론트엔드 포트와 백엔드 포트가 다름
```

해결:

```text
백엔드 CORS origin에 프론트 주소 추가
```

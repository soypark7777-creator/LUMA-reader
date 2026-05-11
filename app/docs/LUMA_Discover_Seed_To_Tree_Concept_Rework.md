
# LUMA Discover Page 수정 방향 — 씨앗이 나무가 되는 컨셉

## 변경 목적

기존 Discover 페이지는 우주/성운 기반 콘셉트로 설계되어 있었다.

이번 수정 방향은:

“생각의 씨앗이 자라 하나의 나무가 된다”

라는 방향으로 변경한다.

즉 사용자는:
- 책을 발견하고
- 감정을 남기고
- 생각을 기록하고
- 관계를 연결하며
- 점점 자신만의 숲을 만들어가는 경험

을 하게 된다.

Discover는 단순 탐색 페이지가 아니라:
“새로운 씨앗을 발견하는 정원”
역할을 한다.

---

# 1. 전체 디자인 방향 변경

## 기존 방향
- 우주
- 성운
- 별자리
- 블랙홀
- 네온 glow

## 새로운 방향
- 씨앗
- 나무
- 숲
- 햇빛
- 흙
- 잎사귀
- 성장
- 자연광
- 따뜻한 종이 질감

---

# 2. Discover 페이지 핵심 컨셉

Discover는:
“새로운 생각의 씨앗을 발견하는 정원”

사용자는 여기서:
- 새로운 책 씨앗을 발견하고
- 관심을 저장하고
- 읽으며 성장시키고
- 자신의 생각 나무를 만든다.

---

# 3. 디자인 무드

## 느낌
- 따뜻함
- 조용함
- 성장
- 사색
- 아날로그 감성
- 자연의 숨결

## 참고 이미지 키워드
- forest reading room
- botanical library
- warm paper texture
- morning sunlight through leaves
- wooden bookshelf aesthetic
- seed growing illustration
- cozy reading garden

---

# 4. 컬러 시스템 변경

## 기존 우주 컬러 제거
- Deep Navy
- Neon Cyan
- Cosmic Glow

## 새 컬러 시스템

### Main Background
#F6F1E8

### Forest Green
#4F6B4A

### Warm Brown
#8A684A

### Leaf Green
#8FBF7A

### Seed Gold
#D7B56D

### Paper Beige
#EFE7DA

### Warm Shadow
rgba(60,40,20,0.12)

---

# 5. Discover Hero 수정

## 기존
거대한 우주 배경 + 성운

## 변경
햇살이 들어오는 숲속 독서 정원

### 구성
- 큰 책 표지
- 나뭇잎 그림자
- 씨앗 일러스트
- 부드러운 빛
- 종이 질감 배경

### 메인 문구 예시
오늘 당신 안에 심어질 새로운 문장

한 권의 책이 작은 씨앗이 되어  
당신의 생각을 자라게 합니다

---

# 6. Search Dock 수정

## 기존
Glass HUD 스타일

## 변경
Wood + Paper 스타일 탐색창

### 디자인
- 종이 카드 느낌
- 나무 테두리
- 따뜻한 그림자
- focus 시 부드러운 초록 glow

### Placeholder
어떤 생각의 씨앗을 찾고 있나요?

---

# 7. Filter Chips 수정

## 기존
빛나는 행성 느낌

## 변경
씨앗 태그 / 잎사귀 태그 느낌

### 스타일
- 둥근 organic shape
- 종이 텍스처
- 선택 시 초록빛 강조
- hover 시 살짝 떠오르는 느낌

### 감정 태그 예시
- 평온
- 위로
- 성장
- 용기
- 호기심
- 사색
- 따뜻함

---

# 8. Book Card 방향 수정

## 핵심
“책 = 씨앗”

책을 저장하는 것은:
“씨앗을 심는 행동”

## 카드 디자인
- 책 표지가 중심
- 카드 하단에 작은 잎사귀 아이콘
- 저장 버튼:
“씨앗 심기”

## 저장 후 상태
- 작은 새싹 애니메이션
- 저장됨 → “자라는 중”

---

# 9. 추천 섹션 이름 수정

## 기존
오늘의 추천 책

## 변경
오늘의 씨앗

---

## 기존
새로 만나는 책

## 변경
새로운 숲을 여는 책

---

## 기존
많이 읽는 책

## 변경
많은 사람들이 키우는 책

---

## 기존
감정 기반 추천

## 변경
지금 당신에게 필요한 문장

---

# 10. 애니메이션 방향 변경

## 제거
- 네온 pulse
- 우주 particle
- 강한 glow

## 추가
- 나뭇잎 흔들림
- 햇빛 먼지
- 천천히 떠다니는 씨앗
- 부드러운 fade
- scroll growth animation

---

# 11. 모바일 UX 방향

## 핵심
“작은 숲속 수첩 느낌”

### 구성
- 부드러운 여백
- 손에 잡히는 카드 크기
- 스크롤 시 자연스러운 흐름
- 너무 빽빽하지 않게 구성

---

# 12. discover.html 수정 방향

## 클래스 이름 예시

discover-garden

seed-section

forest-hero

leaf-chip

book-seed-card

growing-books

---

# 13. discover.css 수정 방향

반드시 포함:
- paper texture
- soft shadow
- warm gradients
- organic border radius
- subtle hover animation

금지:
- neon cyber 느낌
- SF HUD UI
- 과도한 glow
- 너무 차가운 컬러

---

# 14. discover.js 수정 방향

## 저장 버튼 변경

기존:
saveBook()

변경 UX:
plantSeed()

### 저장 시
- 씨앗 심기 애니메이션
- 작은 새싹 표시
- 저장 완료 토스트:
“생각의 씨앗이 심어졌습니다”

---

# 15. Claude Code 최종 수정 프롬프트

```md
Discover 페이지의 기존 우주 컨셉을 제거하고,
“씨앗이 나무가 되는 독서 정원” 컨셉으로 전면 수정한다.

디자인 방향:
- 숲속 독서 공간
- 따뜻한 종이 질감
- 햇빛과 나무 그림자
- 책 = 씨앗
- 저장 = 씨앗 심기
- 성장형 UX

반드시 수정할 요소:
1. 컬러 시스템
2. Hero 영역
3. Search Dock
4. Filter Chips
5. Book Cards
6. 추천 섹션 이름
7. hover animation
8. 저장 버튼 UX

반드시 유지:
- 책 표지 중심 UI
- 캐러셀 구조
- 모바일 대응
- API 연결 구조

금지:
- 우주/성운/SF 느낌
- neon cyber UI
- HUD 스타일
- 과도한 glow
```

---

# 16. 최종 UX 핵심

이 앱은:
“책을 소비하는 앱”이 아니라

“생각의 씨앗을 심고 키우는 앱”

처럼 느껴져야 한다.

사용자는:
- 책을 발견하고
- 감정을 남기고
- 생각을 키우고
- 자신의 숲을 만들어간다.

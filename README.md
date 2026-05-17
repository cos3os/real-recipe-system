# 🧊 RefrigerAI

> **냉장고 속 재료로 오늘 뭐 먹지?**
> 1인 가구를 위한 냉장고 기반 개인화 영양·레시피 최적화 앱

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red.svg)](https://streamlit.io)
[![Neo4j](https://img.shields.io/badge/Neo4j-Aura-green.svg)](https://neo4j.com)
[![Claude API](https://img.shields.io/badge/Claude-Haiku_4.5-orange.svg)](https://anthropic.com)

---

## 📌 프로젝트 소개

RefrigerAI는 냉장고에 있는 재료를 기반으로 영양·비용·유통기한을 동시에 최적화한 레시피를 추천하고, AI 코치와 대화하며 실시간으로 레시피를 커스터마이징할 수 있는 스마트 요리 도우미입니다.

**타겟 유저:** 요리 동기는 있으나 실행 장벽이 있는 20~30대 1인 가구

### 핵심 기술 — 3-엔진 구조

```
사용자 입력 (냉장고 재료 + 영양 목표)
        ↓
  [KG] Knowledge Graph        ← 재료·레시피·대체재 관계 모델링 (Neo4j)
        ↓
  [LP] Linear Programming     ← 영양·비용·유통기한 동시 최적화 (PuLP/HiGHS)
        ↓
  [LLM] Claude API            ← 자연어 설명 + 실시간 레시피 커스터마이징
        ↓
      추천 레시피 + AI 조리 가이드
```

---

## 🖥️ 주요 기능

### 1. 냉장고 재료 기반 레시피 매칭
- 보유 재료 입력 → KG에서 실행 가능한 레시피 탐색
- 재료 매칭률, 유통기한 임박 재료 우선 소진

### 2. LP 기반 영양 최적화
- TDEE 기반 잔여 영양소 자동 계산
- 칼로리·단백질·지방·탄수화물·예산 동시 제약
- 목적함수: `0.5 × 영양점수 + 0.3 × 비용점수 + 0.2 × 유통기한점수`

### 3. 인터랙티브 조리 가이드
- 단계별 조리 카드 (화력·시간·완성 기준·팁)
- 인분 조절 시 조리 시간·재료 양 자동 스케일링
- 단계별 타이머 (시작·정지·리셋)
- 진행률 체크박스

### 4. AI 코치 (Claude API 연동)
- **KG-RAG 구조:** KG 대체재 데이터를 컨텍스트로 주입 → 할루시네이션 최소화
- **대체재 추천:** 없는 재료를 냉장고 보유 재료로 대체, 레시피 카드 실시간 수정
- **자연어 인분 조절:** "3인분으로 늘려줘" → 즉시 반영
- **follow-up 칩:** AI가 선택지 제공 → 클릭으로 빠른 상호작용

---

## 📁 프로젝트 구조

```
real-recipe-system/
├── app.py                    # Streamlit 메인 진입점
├── pages/
│   ├── 1_내정보.py           # 사용자 프로필 (TDEE 계산)
│   ├── 2_오늘식사.py         # 오늘 식사 기록
│   ├── 3_냉장고.py           # 냉장고 재료 입력
│   ├── 4_추천결과.py         # LP 최적화 결과 + 레시피 카드
│   └── 5_조리가이드.py       # 인터랙티브 조리 가이드 + AI 코치
├── core/
│   ├── kg_query.py           # KG 쿼리 모듈 (Neo4j / CSV fallback)
│   └── scaling.py            # 인분별 조리 시간 스케일링
├── app/
│   ├── api/
│   │   └── recipes.py        # FastAPI 레시피 엔드포인트
│   ├── lp/
│   │   ├── kg_queries.py     # KG → LP 데이터 추출
│   │   ├── lp_engine.py      # PuLP LP 최적화 엔진
│   │   └── pipeline.py       # KG→LP 통합 파이프라인
│   ├── services/
│   │   └── user_service.py   # 사용자 서비스 로직
│   ├── database.py           # SQLite DB (User / FridgeStock / CookHistory)
│   └── main.py               # FastAPI 앱
├── data/
│   ├── structured_steps/     # 레시피 단계별 JSON
│   │   ├── 137_된장두부찌개.json
│   │   ├── 231_두부달걀덮밥.json
│   │   ├── 250_단호박제육볶음.json
│   │   ├── 943_영양달걀찜.json
│   │   └── 1047_팽이버섯야채볶음.json
│   ├── mini_recipes_master.csv
│   ├── mini_recipes_ingredients.csv
│   └── mini_substitutes.csv
├── db.env                    # 환경변수 (Neo4j, API Key)
└── requirements.txt
```

---

## ⚙️ 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`db.env` 파일에 아래 내용을 추가하세요:

```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
ANTHROPIC_API_KEY=sk-ant-...
```

> Neo4j 연결 실패 시 자동으로 CSV fallback 모드로 동작합니다.

### 3. Streamlit 앱 실행

```bash
streamlit run app.py
```

### 4. FastAPI 백엔드 실행 (선택)

```bash
uvicorn app.main:app --reload
```

Swagger UI: `http://localhost:8000/docs`

---

## 🔧 기술 스택

| 분류 | 기술 |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Database | SQLite (사용자 데이터), Neo4j Aura (KG) |
| LP Solver | PuLP + HiGHS (CBC fallback) |
| LLM | Claude Haiku 4.5 (Anthropic API) |
| 데이터 출처 | 식약처 식품영양성분DB, KAMIS(가격), 공공데이터포털(레시피) |

---

## 🧠 핵심 알고리즘

### 인분별 조리 시간 스케일링

```
t_scaled = t_base × (target / base) ^ α
```

| 조리 방식 | α 값 | 이유 |
|---|---|---|
| 썰다 / 다듬다 | 0.9 | 재료량에 거의 비례 |
| 볶다 / 굽다 | 0.3 | 팬 표면적 제한 |
| 끓이다 / 조리다 | 0.5 | 열용량 영향 |
| 섞다 / 마무리 | 0.1 | 거의 고정 |
| 재우다 | 0.0 | 인분 무관 |

### KG-RAG 구조 (AI 코치)

```
사용자 질문
    → KG에서 대체재 조회 (ingredient_a → ingredient_b, similarity)
    → 냉장고 보유 재료 우선 정렬
    → Claude API 컨텍스트에 주입
    → KG 데이터 기반 추천 생성
```

---

## 📊 LP 목적함수

```
Maximize: 0.5 × 영양충족도 + 0.3 × (1 - 비용/예산) + 0.2 × 유통기한긴급도

Subject to:
  C1. 칼로리 ≤ 잔여 칼로리
  C2. 단백질 ≥ 잔여 단백질 목표
  C3. 탄수화물 ≤ 잔여 탄수화물
  C4. 지방 ≤ 잔여 지방
  C5. 비용 ≤ 잔여 예산
```

---

## 🗂️ 데이터 출처

- **식품영양성분:** 식약처 식품영양성분 데이터베이스
- **식재료 가격:** KAMIS (농산물유통정보)
- **레시피:** 공공데이터포털 레시피 데이터
- **대체재 유사도:** 자체 구축 (KG `CAN_SUBSTITUTE` 관계, `final_similarity` 가중치)

---

## 📝 라이선스

본 프로젝트는 캡스톤 디자인 프로젝트로 작성되었습니다.
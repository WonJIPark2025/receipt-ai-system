# Receipt AI System

영수증 이미지를 업로드하면 Gemini가 소비 데이터를 자동 추출·저장하고, AI가 지출 패턴을 분석·조언하는 개인 고도화 시스템.

## 개요

영수증 이미지를 업로드하면 Gemini가 가게명 / 날짜 / 합계 / 카테고리 / 구매 방식 / 품목을 한 번에 추출하고 DB에 저장한다.
축적된 데이터를 바탕으로 Gemini LLM이 소비 패턴 분석과 절약 조언을 제공한다.

## 기술 스택

| 영역 | 기술 |
|------|------|
| UI | Streamlit |
| AI | Gemini Flash (google-genai) |
| DB / Storage | Supabase |
| 시각화 | Plotly |
| 환경 | Python 3.10 / Anaconda |

## 프로젝트 구조

```
receipt-ai-system/
├── frontend/                       # Streamlit UI
│   ├── app.py                      # 메인 진입점 (데스크톱/모바일 분기)
│   ├── receipt_front.py            # 데스크톱 UI
│   └── receipt_mobile.py           # 모바일 UI
│
├── backend/                        # Supabase 연동 API 레이어
│   ├── database.py                 # 클라이언트 싱글톤
│   ├── models.py                   # 데이터 모델
│   └── api/                        # 테이블별 CRUD
│       ├── receipts.py
│       ├── receipt_items.py
│       ├── receipt_embeddings.py
│       ├── categories.py
│       ├── users.py
│       └── storage.py
│
├── services/
│   └── ai/                         # AI 서비스
│       ├── gemini.py               # Gemini 영수증 분석 (추출 + 추론 통합)
│       ├── validator.py            # 필수값 검증 (success / review_required / error)
│       ├── embedder.py             # RAG용 텍스트 임베딩
│       ├── analyzer.py             # Gemini 소비 분석
│       └── rag/                    # RAG 기반 조언 (구현 예정)
│
├── utils/
│   └── config.py                   # 환경변수 로드
│
├── tests/
│   ├── test_setup.py               # 환경 검증 (DB + Storage)
│   └── test_ai/                    # Gemini / 벡터 DB 테스트 및 평가
│
├── data/
│   └── receipts/                   # 평가용 영수증 이미지
│
├── .env.example
├── environment.yml
└── requirements.txt
```

## 분석 파이프라인 흐름

```
영수증 이미지
    │
    ▼
[Gemini] 한 번의 API 호출로 전체 추출
    - raw_text, store_name, date, total
    - category, purchase_type, items
    │
    ▼
[Validation] 필수값 검증 → success / review_required / error
    │
    ▼
사용자가 프론트엔드에서 내용 확인·수정 후 "저장" 클릭
    │
    ▼
[DB 저장] receipts + receipt_items + 임베딩(RAG)
```

## 구현 현황

| 기능 | 상태 |
|------|------|
| 영수증 데이터 추출 (이미지 → 검증 → 저장) | 완료 |
| Supabase 백엔드 API (CRUD) | 완료 |
| Streamlit 프론트엔드 (데스크톱 / 모바일) | 완료 |
| RAG 임베딩 저장 | 완료 |
| 소비 패턴 분석 및 조언 | Supabase 연동 작업 중 |
| RAG 기반 맞춤 조언 | 예정 |

## 환경 설정

```bash
# 1. 가상환경 생성 및 활성화
conda env create -f environment.yml
conda activate receipt-ai

# 2. 환경변수 설정
cp .env.example .env
# .env에 SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY 입력

# 3. 실행
streamlit run frontend/app.py
```

## 환경변수

| 키 | 설명 |
|----|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase anon key |
| `GEMINI_API_KEY` | Gemini API 키 |

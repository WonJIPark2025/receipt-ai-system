# Receipt AI System

영수증 OCR 파이프라인을 기반으로 소비 데이터를 자동 저장하고, AI가 지출 패턴을 분석·조언하는 개인 고도화 시스템.

## 개요

영수증 이미지를 업로드하면 텍스트 추출 → 파싱 → 검증 → DB 저장까지 자동화되며,
축적된 데이터를 바탕으로 Gemini LLM이 소비 패턴 분석과 절약 조언을 제공한다.

## 기술 스택

| 영역 | 기술 |
|------|------|
| UI | Streamlit |
| OCR | Google Cloud Vision |
| AI 분석 | Gemini (google-generativeai) |
| DB / Storage | Supabase |
| 시각화 | Plotly |
| 환경 | Python 3.10 / Anaconda |

## 프로젝트 구조

```
receipt-ai-system/
├── frontend/                       # Streamlit UI
│   ├── app.py                      # 메인 진입점
│   ├── OCR_front.py                # 영수증 업로드 / OCR 결과 확인
│   └── OCR_mobile.py               # 모바일 최적화 뷰
│
├── backend/                        # Supabase 연동 API 레이어
│   ├── database.py                 # 클라이언트 싱글톤
│   ├── models.py                   # 데이터 모델
│   └── api/                        # 테이블별 CRUD
│       ├── receipts.py
│       ├── categories.py
│       ├── payment_methods.py
│       ├── users.py
│       └── storage.py
│
├── services/
│   ├── ocr_pipeline/               # OCR 처리 파이프라인
│   │   ├── ocr/                    # Google Vision 어댑터
│   │   ├── parsing/                # 가게명 / 날짜 / 합계 / 품목 추출
│   │   ├── validation/             # 필수값 검증 (success / review_required / error)
│   │   ├── pipeline/               # 파이프라인 오케스트레이터
│   │   ├── persistence/            # DB insert payload 매핑
│   │   ├── domain/                 # ReceiptDraft 도메인 객체
│   │   └── logging/                # 파이프라인 이벤트 로거
│   │
│   ├── ai/                         # AI 분석 서비스
│   │   ├── analyzer.py             # Gemini 소비 분석 (Supabase 연동 예정)
│   │   └── rag/                    # RAG 기반 조언 (구현 예정)
│   │
│   └── indicators/                 # 경제지표 연동 (구현 예정)
│
├── utils/
│   └── config.py                   # 환경변수 로드
│
├── tests/
│   ├── test_connection.py          # Supabase 연결 테스트
│   ├── test_storage.py             # 스토리지 업로드 테스트
│   └── test_pipeline/              # 파이프라인 평가 스크립트 및 결과
│
├── data/
│   └── receipts/                   # 평가용 영수증 이미지
│
├── .env.example
├── environment.yml
└── requirements.txt
```

## OCR 파이프라인 흐름

```
영수증 이미지
    │
    ▼
[OCR] Google Vision → 원문 텍스트 추출
    │
    ▼
[Parsing] 가게명 / 날짜 / 합계 / 결제수단 / 카테고리 / 품목 구조화
    │
    ▼
[Validation] 필수값 검증 → success / review_required / error
    │
    ▼
[Draft] 결과 초안 객체 생성
    │
    ▼
[DB Payload] 검증 성공 시 Supabase insert payload 준비
    │
    ▼
사용자가 프론트엔드에서 "저장" 클릭 → DB 저장
```

## 구현 현황

| 기능 | 상태 |
|------|------|
| OCR 파이프라인 (추출 → 파싱 → 검증 → 저장) | 완료 |
| Supabase 백엔드 API (CRUD) | 완료 |
| Streamlit 프론트엔드 | 완료 |
| Gemini AI 소비 분석 | Supabase 연동 작업 중 |
| RAG 기반 맞춤 조언 | 예정 |
| 경제지표 연동 | 예정 |

## 환경 설정

```bash
# 1. 가상환경 생성 및 활성화
conda env create -f environment.yml
conda activate ocr-receipt

# 2. 환경변수 설정
cp .env.example .env
# .env에 SUPABASE_URL, SUPABASE_KEY, GOOGLE_APPLICATION_CREDENTIALS, GEMINI_API_KEY 입력

# 3. 실행
streamlit run frontend/app.py
```

## 환경변수

| 키 | 설명 |
|----|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase anon key |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Vision 서비스 계정 JSON 경로 |
| `GEMINI_API_KEY` | Gemini API 키 |

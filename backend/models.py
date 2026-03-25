"""
models.py - 데이터 모델 정의

담당: 백엔드
설명: Supabase 테이블과 매칭되는 데이터 구조 정의
    - v2 스키마 기준: categories, receipts, receipt_items
    - payment_methods 테이블 제거됨 (docs/migrations/v2_schema.sql 참고)
"""

# =============================================================================
# 테이블 이름 상수
# =============================================================================
# Supabase 쿼리 시 사용하는 테이블명
# 오타 방지를 위해 상수로 관리
# =============================================================================

TABLE_CATEGORIES    = "categories"
TABLE_RECEIPTS      = "receipts"
TABLE_RECEIPT_ITEMS = "receipt_items"


# =============================================================================
# categories 테이블  (v2: 2개)
# =============================================================================
# 역할: 분석 대상 여부 필터
#       서비스 범위가 식습관으로 한정되어 있어 2개면 충분
#
# 컬럼:
#   - id (PK): 자동 생성
#   - name (UQ): '식비' | '기타'
#   - icon: 이모지
#
#   식비 (id=1) : 분석 대상 — purchase_type 있는 식음료 영수증
#   기타 (id=2) : 분석 제외 — 교통, 의료, 쇼핑 등 비식품 영수증
# =============================================================================


# =============================================================================
# receipts 테이블  (v2 핵심 테이블)
# =============================================================================
# 컬럼:
#   - id (PK)
#   - user_id (integer): 사용자 식별자
#   - category_id (FK → categories.id): 대분류
#   - paid_at (TIMESTAMPTZ): 결제 일시 — 야간·주말 패턴 분석용
#   - total_amount: 총 금액
#   - store_name: 상호명
#   - purchase_type: 'delivery' | 'takeout' | 'dine_in' | 'cooking' | NULL
#   - memo: 감정·상황 자유 메모 (RAG 소스로도 활용 예정)
#   - image_path: 영수증 이미지 경로
#   - created_at: 레코드 생성 일시 (DB default now())
#
# v1 → v2 제거된 컬럼:
#   - payment_method_id: 분석 가치 없음, 테이블 자체 제거
#   - date(DATE): paid_at(TIMESTAMPTZ)으로 교체
#   - details(JSONB): receipt_items 테이블로 정규화
# =============================================================================

PURCHASE_TYPES = ("delivery", "takeout", "dine_in", "cooking")


# =============================================================================
# receipt_items 테이블  (v2 신규)
# =============================================================================
# 역할: 품목 단위 행동 패턴 분석
#       receipts.details JSONB 를 정규화한 테이블
#
# 컬럼:
#   - id (PK)
#   - receipt_id (FK → receipts.id, CASCADE DELETE)
#   - name: 품목명
#   - quantity: 수량
#   - price: 단가
#   - activity_tag: 행동 패턴 태그 (아래 ACTIVITY_TAGS 참고)
#
# activity_tag 허용값:
#   caffeine   : 아메리카노, 라떼, 에너지드링크 등 — 키워드 매칭
#   alcohol    : 맥주, 소주, 와인 등 — 키워드 매칭
#   late_snack : 야간(22시~) 결제 항목 — paid_at 시간 기준 파생, 키워드 불필요
#   None       : 분류 불가
#
# 배달음식은 receipts.purchase_type='delivery' 로 영수증 단위에서 처리
# =============================================================================

ACTIVITY_TAGS = (
    "caffeine",
    "alcohol",
    "late_snack",
)

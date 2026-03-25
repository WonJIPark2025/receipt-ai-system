-- =============================================================================
-- v2_schema.sql  —  스키마 리팩토링 마이그레이션 (2026-03-25)
-- =============================================================================
-- 변경 요약:
--   - payment_methods 테이블 및 FK 제거 (분석 가치 없음)
--   - categories 8개 → 2개 (식비/기타) : 서비스 범위 식습관으로 한정
--   - receipts.date(DATE) → paid_at(TIMESTAMPTZ) : 시간대 패턴 분석 목적
--   - receipts.purchase_type : delivery/takeout/dine_in/cooking 4개
--   - receipts 에 memo, user_id 컬럼 추가
--   - receipts.details(JSONB) 제거 → receipt_items 테이블로 정규화
--   - receipt_items 신규 테이블: activity_tag (caffeine/alcohol/late_snack)
-- =============================================================================
-- 실행 순서: Supabase SQL Editor 에 전체 복사 후 실행
-- 전제조건: receipts rows=0 (데이터 없음 확인 후 실행)
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 1. payment_methods 제거
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE receipts DROP CONSTRAINT IF EXISTS receipts_payment_method_id_fkey;
ALTER TABLE receipts DROP COLUMN  IF EXISTS payment_method_id;
DROP  TABLE IF EXISTS payment_methods;


-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 2. categories → 2개로 단순화
-- ─────────────────────────────────────────────────────────────────────────────
-- 서비스 범위를 식습관으로 한정
--   식비 (id=1) : 분석 대상 — purchase_type 있는 식음료 영수증
--   기타 (id=2) : 분석 제외 — 교통, 의료, 쇼핑 등 비식품 영수증
-- id 가 1,2 로 재부여됨 → db_mapper.py 의 CATEGORY_MAP 과 일치

TRUNCATE TABLE categories RESTART IDENTITY CASCADE;

INSERT INTO categories (name, icon) VALUES
    ('식비', '🍽️'),   -- id=1  분석 대상
    ('기타', '📦');   -- id=2  분석 제외


-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 3. receipts 컬럼 변경
-- ─────────────────────────────────────────────────────────────────────────────

-- 3-1. user_id 추가 (기존 스키마에 누락되어 있던 컬럼)
ALTER TABLE receipts
    ADD COLUMN IF NOT EXISTS user_id integer;

-- 3-2. date(DATE) → paid_at(TIMESTAMPTZ) : 야간/주말 시간대 분석용
ALTER TABLE receipts RENAME COLUMN date TO paid_at;
ALTER TABLE receipts
    ALTER COLUMN paid_at TYPE timestamptz
    USING paid_at::timestamptz;

-- 3-3. purchase_type 추가 : 식사 방식 구분 (식습관 분석 핵심 축)
--   delivery : 배달시켜 먹음
--   takeout  : 포장해서 먹음
--   dine_in  : 식당에서 먹음
--   cooking  : 장봐서 직접 요리 (마트·슈퍼 영수증)
--   NULL     : 비식품 영수증 (교통, 의료 등)
ALTER TABLE receipts
    ADD COLUMN IF NOT EXISTS purchase_type text
    CHECK (purchase_type IN ('delivery', 'takeout', 'dine_in', 'cooking'));

-- 3-4. memo 추가 : 감정·상황 자유 메모 (RAG 검색 소스로도 활용 예정)
ALTER TABLE receipts
    ADD COLUMN IF NOT EXISTS memo text;

-- 3-5. details(JSONB) 제거 → receipt_items 테이블로 이관
ALTER TABLE receipts
    DROP COLUMN IF EXISTS details;


-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 4. receipt_items 신규 테이블
-- ─────────────────────────────────────────────────────────────────────────────
-- activity_tag 허용값:
--   caffeine   : 아메리카노, 라떼, 에너지드링크 등 — 키워드 매칭으로 자동 태깅
--   alcohol    : 맥주, 소주, 와인 등 — 키워드 매칭으로 자동 태깅
--   late_snack : 야간(22시~) 결제 항목 — 통계 쿼리에서 paid_at 기준 파생 처리
--               (저장 시점에 insert 하지 않음, CHECK 허용값에만 포함)
--   NULL       : 분류 불가 항목
--
-- 배달음식은 receipts.purchase_type='delivery' 로 영수증 단위에서 처리

CREATE TABLE IF NOT EXISTS receipt_items (
    id           serial  PRIMARY KEY,
    receipt_id   integer NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    name         text    NOT NULL,
    quantity     integer,
    price        integer,
    activity_tag text    CHECK (
        activity_tag IN ('caffeine', 'alcohol', 'late_snack')
    )
);

ALTER TABLE receipt_items ENABLE ROW LEVEL SECURITY;

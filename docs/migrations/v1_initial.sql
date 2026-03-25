-- =============================================================================
-- v1_initial.sql  —  현재 스키마 백업 (2026-03-25 기준)
-- =============================================================================
-- 목적: v2 마이그레이션 실패 시 롤백 참고용
-- 주의: receipts 테이블 rows=0 이므로 데이터 손실 없음
-- =============================================================================

-- categories (8개 세분화)
CREATE TABLE IF NOT EXISTS categories (
    id   serial      PRIMARY KEY,
    name text UNIQUE NOT NULL,
    icon text
);

INSERT INTO categories (name, icon) VALUES
    ('식비',   '🍽️'),
    ('카페',   '☕'),
    ('교통',   '🚌'),
    ('쇼핑',   '🛍️'),
    ('의료',   '🏥'),
    ('편의점', '🏪'),
    ('주유',   '⛽'),
    ('기타',   '📦');

-- payment_methods
CREATE TABLE IF NOT EXISTS payment_methods (
    id   serial      PRIMARY KEY,
    name text UNIQUE NOT NULL
);

INSERT INTO payment_methods (name) VALUES
    ('카드'),
    ('현금'),
    ('앱결제');

-- receipts (핵심 테이블)
CREATE TABLE IF NOT EXISTS receipts (
    id                serial PRIMARY KEY,
    category_id       integer REFERENCES categories(id),
    payment_method_id integer REFERENCES payment_methods(id),
    date              date,
    total_amount      integer,
    store_name        text,
    image_path        text,
    details           jsonb DEFAULT '[]'::jsonb,
    created_at        timestamptz DEFAULT now()
);

-- RLS
ALTER TABLE categories      ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipts        ENABLE ROW LEVEL SECURITY;

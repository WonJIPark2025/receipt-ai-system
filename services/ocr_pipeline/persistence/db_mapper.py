"""
db_mapper.py - 파싱 결과 DB 스키마 매핑

담당: OCR
설명: 파이프라인 파싱 결과를 Supabase receipts 테이블 insert용 payload로 변환
    - category / payment 문자열 → FK id로 변환 (CATEGORY_MAP, PAYMENT_MAP)
    - user_id는 프론트엔드 로그인 세션에서 전달받아 사용
주의:
    - created_at은 DB default now() 사용 → Python에서 보내지 않음
    - category / payment는 FK id로 변환 필요
"""

# 카테고리 매핑 (DB categories 테이블 기준으로 맞춰야 함)
CATEGORY_MAP = {
    "식비": 1,
    "카페": 2,
    "교통": 3,
    "쇼핑": 4,
    "의료": 5,
    "편의점": 6,
    "주유": 7,
    "기타": 8
}

# 결제수단 매핑 (payment_methods 테이블 기준으로 맞춰야 함)
PAYMENT_MAP = {
    "card": 1,
    "cash": 2,
    "app": 3
}


# [변경] user_id 파라미터 추가 - 기존에는 user_id=1로 고정되어 있었음
# 프론트엔드에서 로그인한 사용자의 PK(session_state['user_pk'])를 전달받아 사용
def map_to_db_schema(image_path: str, parsed: dict, user_id: int = 1) -> dict:
    """
    Supabase receipts 테이블 insert용 payload 생성
    """

    return {
        # [변경] 고정값 1 대신 파라미터로 받은 user_id 사용
        # "user_id": 1,  # 현재 고정 (추후 로그인 사용자로 변경)
        "user_id": user_id,

        # FK
        "category_id": CATEGORY_MAP.get(parsed.get("category")),
        "payment_method_id": PAYMENT_MAP.get(parsed.get("payment")),

        # 기본 필드
        "date": parsed.get("transaction_date"),
        "total_amount": parsed.get("total"),
        "store_name": parsed.get("store_name"),
        "image_path": image_path,

        # JSONB
        "details": parsed.get("items", [])
    }
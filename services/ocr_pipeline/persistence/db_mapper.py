"""
db_mapper.py - 파싱 결과 DB 스키마 매핑

담당: OCR
설명: 파이프라인 파싱 결과를 Supabase insert용 payload로 변환
    - v2 스키마 기준: receipt payload + items payload 분리 반환
    - CATEGORY_MAP  : parser 출력 → 식비(1) / 기타(2) 매핑
    - ACTIVITY_RULES: 품목명 키워드 → activity_tag 자동 태깅
    - purchase_type : 파이프라인에서 전달받거나 None(비식품)
주의:
    - created_at 은 DB default now() 사용 → Python에서 보내지 않음
    - paid_at 은 TIMESTAMPTZ — parser 가 시간 포함 문자열을 넘겨야 함
"""

# =============================================================================
# 카테고리 매핑
# =============================================================================
# parser.py 출력(구 카테고리명) → v2 DB categories id
#   id=1 : 식비 (분석 대상)
#   id=2 : 기타 (분석 제외 — 교통, 의료 등 비식품)

CATEGORY_MAP = {
    "식비":   1,
    "카페":   1,
    "편의점": 1,
    "교통":   2,
    "주유":   2,
    "쇼핑":   2,
    "의료":   2,
    "기타":   2,
}


# =============================================================================
# activity_tag 자동 태깅 룰
# =============================================================================
# 품목명에 아래 키워드가 포함되면 해당 태그 부여
# 우선순위: 위에서 아래 순서 (먼저 매칭된 태그 사용)

ACTIVITY_RULES = {
    "caffeine": [
        "아메리카노", "라떼", "카페라떼", "콜드브루", "에스프레소",
        "카푸치노", "모카", "마끼아또", "프라푸치노",
        "에너지드링크", "레드불", "몬스터", "핫식스",
        "녹차", "말차", "홍차",
    ],
    "alcohol": [
        "맥주", "소주", "와인", "막걸리", "하이볼",
        "위스키", "보드카", "칵테일", "생맥주",
        "캔맥주", "병맥주", "사케", "청주",
    ],
}

# late_snack 은 키워드가 아닌 paid_at 시간 기준 파생
# → 22시 이후 결제된 receipt_items 전체를 통계 쿼리에서 late_snack 으로 처리
# → 저장 시점 태깅 불필요, DB에 late_snack 값은 직접 insert 하지 않음

# 배달음식은 receipts.purchase_type='delivery' 로 영수증 단위에서 처리
# → activity_tag 에 포함하지 않음


# =============================================================================
# 내부 헬퍼
# =============================================================================

def _resolve_activity_tag(item_name: str) -> str | None:
    """
    품목명에서 activity_tag 자동 추론
    매칭 없으면 None 반환
    """
    name = item_name.lower()
    for tag, keywords in ACTIVITY_RULES.items():
        if any(kw in name for kw in keywords):
            return tag
    return None


# =============================================================================
# 메인 매핑 함수
# =============================================================================

def map_to_db_schema(
    image_path: str,
    parsed: dict,
    user_id: int = 1,
    purchase_type: str = None,
) -> dict:
    """
    파싱 결과를 DB insert용 payload 두 개로 변환

    Args:
        image_path    : 영수증 이미지 경로
        parsed        : parser.py 출력 dict
                        필드: store_name, category, transaction_date,
                              total, items
        user_id       : 로그인 사용자 id (프론트에서 전달)
        purchase_type : 'delivery' | 'takeout' | 'dine_in' | 'cooking' | None

    Returns:
        dict: {
            "receipt"  : receipts 테이블 insert payload,
            "items"    : receipt_items 테이블 insert payload 리스트
        }

    사용 예시:
        payload = map_to_db_schema(image_path, parsed, user_id=3)
        receipt = create_receipt(**payload["receipt"])
        create_receipt_items(receipt["id"], payload["items"])
    """

    # ── receipt payload ──────────────────────────────────────────────────────
    receipt_payload = {
        "user_id":       user_id,
        "category_id":   CATEGORY_MAP.get(parsed.get("category"), 2),  # 미분류 → 기타
        "paid_at":       parsed.get("transaction_date"),
        "total_amount":  parsed.get("total"),
        "store_name":    parsed.get("store_name"),
        "purchase_type": purchase_type,
        "memo":          None,          # 사용자가 직접 입력하는 필드
        "image_path":    image_path,
    }

    # ── items payload ─────────────────────────────────────────────────────────
    raw_items = parsed.get("items", [])
    items_payload = [
        {
            "name":         item.get("name", ""),
            "quantity":     item.get("quantity"),
            "price":        item.get("price"),
            "activity_tag": _resolve_activity_tag(item.get("name", "")),
        }
        for item in raw_items
        if item.get("name")
    ]

    return {
        "receipt": receipt_payload,
        "items":   items_payload,
    }

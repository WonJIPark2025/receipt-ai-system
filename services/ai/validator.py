"""
validator.py - 영수증 데이터 검증

담당: AI
설명: 추출된 영수증 데이터의 유효성 검증
    - 필수값(가게명, 합계, 날짜) 누락 여부 확인
    - 판정: success / review_required / error
"""


def validate_receipt(data: dict) -> dict:
    """
    추출 결과 자동 검증

    Returns:
        dict: {
            "validation_status": "success" | "review_required" | "error",
            "issues": list[str]
        }
    """
    issues = []

    store = data.get("store_name", "")
    total = data.get("total", 0)
    date  = data.get("date", "")
    category = data.get("category", "기타")

    if not store or len(store) < 2:
        issues.append("store_name_invalid")

    if total <= 0:
        issues.append("total_invalid")

    if not date:
        issues.append("date_missing")

    if category == "기타":
        issues.append("category_uncertain")

    if "total_invalid" in issues or "store_name_invalid" in issues:
        status = "error"
    elif issues:
        status = "review_required"
    else:
        status = "success"

    return {
        "validation_status": status,
        "issues": issues,
    }

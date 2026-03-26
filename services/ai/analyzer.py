"""
analyzer.py - AI 지출 분석 서비스

담당: AI
설명: Gemini LLM을 사용한 월별 식습관 소비 분석
    - Supabase에서 해당 월 영수증 데이터 로드
    - purchase_type / activity_tag 기반 식습관 패턴 분석
    - 절약 조언 및 식습관 개선 제안 제공
"""

import json
from utils.config import GEMINI_API_KEY, DEFAULT_USER_ID
from backend.api.receipts import get_receipts_by_date_range
from backend.api.receipt_items import get_items_by_receipt

PURCHASE_TYPE_KO = {
    "general":  "간편",
    "delivery": "배달",
    "takeout":  "포장",
    "dine_in":  "매장",
    "cooking":  "직접 요리",
}

ACTIVITY_TAG_KO = {
    "caffeine":   "카페인",
    "alcohol":    "음주",
    "late_snack": "야식",
}


def analyze(year_month: str) -> str:
    """
    특정 월의 식습관 소비 데이터를 Gemini로 분석

    Args:
        year_month: "2026-03" 형식

    Returns:
        str: Gemini 분석 결과 (마크다운)
    """
    from google import genai

    if not GEMINI_API_KEY:
        return "GEMINI_API_KEY가 설정되지 않았습니다."

    # 해당 월 날짜 범위 계산
    import calendar
    year, month = map(int, year_month.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    start = f"{year_month}-01T00:00:00+09:00"
    end   = f"{year_month}-{last_day:02d}T23:59:59+09:00"

    # Supabase에서 영수증 데이터 로드
    receipts = get_receipts_by_date_range(DEFAULT_USER_ID, start, end)

    if not receipts:
        return f"{year_month} 데이터가 없습니다."

    # 분석용 데이터 구성
    data = []
    for r in receipts:
        purchase_ko = PURCHASE_TYPE_KO.get(r.get("purchase_type"), "미분류")

        # 품목 및 activity_tag 로드
        items = get_items_by_receipt(r["id"])
        tags = list({
            ACTIVITY_TAG_KO[i["activity_tag"]]
            for i in items
            if i.get("activity_tag") in ACTIVITY_TAG_KO
        })

        entry = {
            "날짜":     r["paid_at"][:10],
            "상호명":   r.get("store_name", ""),
            "금액":     r.get("total_amount", 0),
            "구매방식": purchase_ko,
        }
        if tags:
            entry["태그"] = tags
        if r.get("memo"):
            entry["메모"] = r["memo"]

        data.append(entry)

    total = sum(r.get("total_amount", 0) for r in receipts)

    prompt = f"""{year_month} 월 식습관 소비 데이터입니다. 총 {len(receipts)}건, 합계 {total:,}원.

{json.dumps(data, ensure_ascii=False, indent=2)}

다음 내용을 한국어로 분석해주세요:

1. 이번 달 식습관 패턴 요약 (배달/포장/매장/직접 요리 비율 포함)
2. 카페인·음주·야식 등 주목할 행동 패턴
3. 절약 또는 식습관 개선을 위한 구체적 조언
4. 한 줄 요약

마크다운 형식으로 작성해주세요."""

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text

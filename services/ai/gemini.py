"""
gemini.py - Gemini 기반 영수증 데이터 추출

담당: AI
설명: 영수증 이미지에서 모든 필드를 한 번의 Gemini 호출로 추출
    - raw_text + 파싱(store/date/total/category) + 추론(purchase_type/items) 통합
    - 단일 GEMINI_API_KEY만 필요
"""

import json
from pathlib import Path
from utils.config import GEMINI_API_KEY

VALID_PURCHASE_TYPES = {"general", "delivery", "takeout", "dine_in", "cooking"}
VALID_CATEGORIES = {"식비", "기타"}

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

PROMPT = """이 영수증 이미지를 분석하여 아래 JSON 형식으로만 답하세요. 다른 말은 하지 마세요.

{
  "raw_text": "영수증의 모든 텍스트를 줄바꿈 포함하여 그대로 추출",
  "store_name": "가게명",
  "date": "2024-03-15T21:47:32",
  "total": 15000,
  "category": "식비 | 기타",
  "purchase_type": "delivery | takeout | dine_in | cooking | general",
  "items": [
    {"name": "품목명", "quantity": 1, "price": 5000}
  ]
}

category 기준:
- 식비: 음식점, 카페, 편의점 식품, 배달, 마트 식재료
- 기타: 교통, 의료, 쇼핑, 주유 등 비식품

purchase_type 기준:
- delivery  : 배달 앱/전화 주문 (배달의민족, 쿠팡이츠 등)
- takeout   : 식당/카페에서 포장
- dine_in   : 식당/카페에서 직접 취식
- cooking   : 마트/시장에서 식재료 구매 후 직접 요리
- general   : 편의점, 마트 간식, 기타 일반 구매

date 형식:
- 시간 포함 시: "2024-03-15T21:47:32"
- 날짜만: "2024-03-15"
- 날짜 없으면: ""

items 기준:
- 합계, 부가세, 할인, 배달비, 카드 정보는 제외
- 품목이 없으면 빈 배열 []
- total은 정수 (원화, 콤마 없이)"""


def extract_receipt_data(image_path: str) -> dict:
    """
    영수증 이미지에서 모든 필드를 한 번에 추출

    Returns:
        dict: {
            "raw_text": str,
            "store_name": str,
            "date": str,          # ISO 8601 또는 빈 문자열
            "total": int,
            "category": "식비" | "기타",
            "purchase_type": "delivery" | "takeout" | "dine_in" | "cooking" | "general",
            "items": [{"name": str, "quantity": int, "price": int}, ...]
        }
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")

    from google import genai
    from google.genai import types

    suffix = Path(image_path).suffix.lower()
    mime_type = "image/png" if suffix == ".png" else "image/jpeg"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            PROMPT,
        ],
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    result = json.loads(text)

    purchase_type = result.get("purchase_type", "general")
    if purchase_type not in VALID_PURCHASE_TYPES:
        purchase_type = "general"

    category = result.get("category", "기타")
    if category not in VALID_CATEGORIES:
        category = "기타"

    items = [
        {
            "name":     str(i.get("name", "")),
            "quantity": int(i.get("quantity", 1)),
            "price":    int(i.get("price", 0)),
        }
        for i in result.get("items", [])
        if i.get("name")
    ]

    return {
        "raw_text":      result.get("raw_text", ""),
        "store_name":    result.get("store_name", ""),
        "date":          result.get("date", ""),
        "total":         int(result.get("total", 0)),
        "category":      category,
        "purchase_type": purchase_type,
        "items":         items,
    }


def resolve_activity_tag(item_name: str, hour: int | None = None) -> str | None:
    """품목명과 결제 시간으로 activity_tag 추론

    우선순위: caffeine/alcohol(품목 키워드) > late_snack(22시 이후)
    hour: paid_at에서 추출한 결제 시각 (0~23), None이면 시간 판단 생략
    """
    name = item_name.lower()
    for tag, keywords in ACTIVITY_RULES.items():
        if any(kw in name for kw in keywords):
            return tag
    if hour is not None and hour >= 22:
        return "late_snack"
    return None

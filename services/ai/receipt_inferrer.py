"""
receipt_inferrer.py - 영수증 필드 통합 추론

담당: AI
설명: OCR raw_text에서 식사 방식 + 품목을 한 번의 LLM 호출로 추론
    - purchase_type_inferrer + item_inferrer 통합 버전
    - 반환값: {"purchase_type": str, "items": list}
"""

import json
from utils.config import GEMINI_API_KEY

VALID_PURCHASE_TYPES = {"general", "delivery", "takeout", "dine_in", "cooking"}


def infer_receipt_fields(raw_text: str) -> dict:
    """
    OCR raw_text에서 식사 방식과 품목을 한 번에 추론

    Args:
        raw_text: OCR 추출 전체 텍스트

    Returns:
        dict: {
            "purchase_type": "general" | "delivery" | "takeout" | "dine_in" | "cooking",
            "items": [{"name": str, "quantity": int, "price": int}, ...]
        }
        실패 시 {"purchase_type": "general", "items": []}
    """
    default = {"purchase_type": "general", "items": []}

    if not GEMINI_API_KEY or not raw_text:
        return default

    from google import genai

    prompt = f"""다음은 영수증 OCR 텍스트입니다.

[영수증 텍스트]
{raw_text[:1000]}

아래 JSON 형식으로만 답하세요. 다른 말은 하지 마세요.

{{
  "purchase_type": "delivery | takeout | dine_in | cooking | general",
  "items": [
    {{"name": "품목명", "quantity": 1, "price": 5000}},
    ...
  ]
}}

purchase_type 기준:
- delivery  : 배달 앱/전화 주문 (배달비, 배달팁, 배달의민족, 쿠팡이츠 등)
- takeout   : 식당/카페에서 포장
- dine_in   : 식당/카페에서 직접 취식
- cooking   : 마트/시장에서 식재료 구매 후 직접 요리
- general   : 편의점, 마트 간식, 기타 일반 구매

items 기준:
- 합계, 부가세, 할인, 배달비, 카드 정보는 제외
- 품목이 없으면 빈 배열 []"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        result = json.loads(text)

        purchase_type = result.get("purchase_type", "general")
        if purchase_type not in VALID_PURCHASE_TYPES:
            purchase_type = "general"

        items = [
            {
                "name":     str(i.get("name", "")),
                "quantity": int(i.get("quantity", 1)),
                "price":    int(i.get("price", 0)),
            }
            for i in result.get("items", [])
            if i.get("name")
        ]

        return {"purchase_type": purchase_type, "items": items}

    except Exception as e:
        print(f"[receipt_inferrer] 추론 실패: {e}")
        return default
